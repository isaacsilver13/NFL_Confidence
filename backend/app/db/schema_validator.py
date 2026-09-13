"""Read-only validation of the database schema required by the ORM models."""

from collections.abc import Iterable

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.schema import Column, ForeignKeyConstraint, Table, UniqueConstraint
from sqlalchemy.sql.sqltypes import Enum

from app.db.session import Base

SchemaIssue = dict[str, str]


def _columns_signature(columns: Iterable[Column]) -> tuple[str, ...]:
    return tuple(column.name for column in columns)


def _type_matches(expected: object, actual: object) -> bool:
    if isinstance(expected, Enum):
        return isinstance(actual, Enum) and expected.enums == actual.enums

    expected_affinity = getattr(expected, "_compare_type_affinity", None)
    if expected_affinity is None or not expected_affinity(actual):
        return False

    for attribute in ("length", "precision", "scale", "timezone"):
        expected_value = getattr(expected, attribute, None)
        actual_value = getattr(actual, attribute, None)
        if expected_value is not None and expected_value != actual_value:
            return False
    return True


def _index_signatures(table: Table) -> set[tuple[tuple[str, ...], bool]]:
    return {(_columns_signature(index.columns), bool(index.unique)) for index in table.indexes}


def _unique_constraint_signatures(table: Table) -> set[tuple[str, ...]]:
    return {
        _columns_signature(constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _foreign_key_signatures(table: Table) -> set[tuple[tuple[str, ...], str, tuple[str, ...]]]:
    return {
        (
            _columns_signature(constraint.columns),
            constraint.elements[0].column.table.name,
            tuple(element.column.name for element in constraint.elements),
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def _primary_key_signature(table: Table) -> tuple[str, ...]:
    return _columns_signature(table.primary_key.columns)


def _validate_table(table: Table, inspector) -> list[SchemaIssue]:
    issues: list[SchemaIssue] = []
    if not inspector.has_table(table.name):
        return [{"kind": "missing_table", "table": table.name}]

    actual_columns = {column["name"]: column for column in inspector.get_columns(table.name)}
    for expected_column in table.columns:
        actual_column = actual_columns.get(expected_column.name)
        if actual_column is None:
            issues.append(
                {
                    "kind": "missing_column",
                    "table": table.name,
                    "column": expected_column.name,
                }
            )
            continue
        if expected_column.nullable != actual_column["nullable"]:
            issues.append(
                {
                    "kind": "column_nullability_mismatch",
                    "table": table.name,
                    "column": expected_column.name,
                }
            )
        if not _type_matches(expected_column.type, actual_column["type"]):
            issues.append(
                {
                    "kind": "column_type_mismatch",
                    "table": table.name,
                    "column": expected_column.name,
                }
            )

    actual_indexes = inspector.get_indexes(table.name)
    actual_index_signatures = {
        (tuple(index["column_names"]), bool(index["unique"])) for index in actual_indexes
    }
    actual_unique_signatures = {
        tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints(table.name)
    }
    for columns, unique in _index_signatures(table):
        if (columns, unique) not in actual_index_signatures and not (
            unique and columns in actual_unique_signatures
        ):
            issues.append(
                {
                    "kind": "missing_index",
                    "table": table.name,
                    "columns": ",".join(columns),
                }
            )

    for columns in _unique_constraint_signatures(table):
        if (
            columns not in actual_unique_signatures
            and (
                columns,
                True,
            )
            not in actual_index_signatures
        ):
            issues.append(
                {
                    "kind": "missing_unique_constraint",
                    "table": table.name,
                    "columns": ",".join(columns),
                }
            )

    expected_primary_key = _primary_key_signature(table)
    actual_primary_key = tuple(
        inspector.get_pk_constraint(table.name).get("constrained_columns", [])
    )
    if expected_primary_key != actual_primary_key:
        issues.append(
            {
                "kind": "primary_key_mismatch",
                "table": table.name,
                "columns": ",".join(expected_primary_key),
            }
        )

    actual_foreign_keys = {
        (
            tuple(foreign_key["constrained_columns"]),
            foreign_key["referred_table"],
            tuple(foreign_key["referred_columns"]),
        )
        for foreign_key in inspector.get_foreign_keys(table.name)
    }
    for columns, referred_table, referred_columns in _foreign_key_signatures(table):
        if (columns, referred_table, referred_columns) not in actual_foreign_keys:
            issues.append(
                {
                    "kind": "missing_foreign_key",
                    "table": table.name,
                    "columns": ",".join(columns),
                    "referred_table": referred_table,
                }
            )

    return issues


def validate_schema(db: Session) -> list[SchemaIssue]:
    """Return missing or incompatible schema objects without changing the database."""
    inspector = inspect(db.get_bind())
    issues: list[SchemaIssue] = []
    for table in Base.metadata.sorted_tables:
        issues.extend(_validate_table(table, inspector))
    return issues
