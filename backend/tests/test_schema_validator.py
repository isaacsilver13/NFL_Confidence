from types import SimpleNamespace

from sqlalchemy import (
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.sql.sqltypes import Enum

from app.db import schema_validator
from app.db.schema_validator import _type_matches, _validate_table

metadata = MetaData()
parents = Table("parents", metadata, Column("id", Integer, primary_key=True))
children = Table(
    "children",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("parent_id", Integer, ForeignKey("parents.id"), nullable=False),
    Column("name", String(20), nullable=False),
    UniqueConstraint("name", name="uq_children_name"),
)
Index("ix_children_name", children.c.name)


class TableInspector:
    def __init__(self, table: Table):
        self.table = table
        self.columns = {
            column.name: {
                "name": column.name,
                "type": column.type,
                "nullable": column.nullable,
            }
            for column in table.columns
        }
        self.indexes = [
            {"column_names": list(index.columns.keys()), "unique": index.unique}
            for index in table.indexes
        ]
        self.unique_constraints = [
            {"column_names": list(constraint.columns.keys())}
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        ]
        self.primary_key = {"constrained_columns": list(table.primary_key.columns.keys())}
        self.foreign_keys = [
            {
                "constrained_columns": list(constraint.columns.keys()),
                "referred_table": constraint.elements[0].column.table.name,
                "referred_columns": [element.column.name for element in constraint.elements],
            }
            for constraint in table.constraints
            if isinstance(constraint, ForeignKeyConstraint)
        ]

    def has_table(self, table_name: str) -> bool:
        return table_name == self.table.name

    def get_columns(self, table_name: str):
        return list(self.columns.values())

    def get_indexes(self, table_name: str):
        return self.indexes

    def get_unique_constraints(self, table_name: str):
        return self.unique_constraints

    def get_pk_constraint(self, table_name: str):
        return self.primary_key

    def get_foreign_keys(self, table_name: str):
        return self.foreign_keys


def test_validate_table_accepts_matching_schema() -> None:
    assert _validate_table(children, TableInspector(children)) == []


def test_validate_table_reports_missing_column_index_and_constraints() -> None:
    inspector = TableInspector(children)
    inspector.columns.pop("name")
    inspector.indexes = []
    inspector.unique_constraints = []
    inspector.foreign_keys = []

    issue_kinds = {issue["kind"] for issue in _validate_table(children, inspector)}

    assert issue_kinds == {
        "missing_column",
        "missing_index",
        "missing_unique_constraint",
        "missing_foreign_key",
    }


def test_validate_table_reports_type_nullability_and_primary_key_mismatches() -> None:
    inspector = TableInspector(children)
    inspector.columns["name"]["type"] = Integer()
    inspector.columns["name"]["nullable"] = True
    inspector.primary_key = {"constrained_columns": ["name"]}

    issue_kinds = {issue["kind"] for issue in _validate_table(children, inspector)}

    assert issue_kinds == {
        "column_type_mismatch",
        "column_nullability_mismatch",
        "primary_key_mismatch",
    }


def test_type_matches_postgresql_enum_labels() -> None:
    expected = Enum("pending", "complete", name="job_status")
    matching = Enum("pending", "complete", name="job_status")
    different = Enum("pending", "failed", name="job_status")

    assert _type_matches(expected, matching)
    assert not _type_matches(expected, different)
    assert not _type_matches(expected, String())


def test_validate_schema_checks_tables_registered_by_models(monkeypatch) -> None:
    model_metadata = MetaData()
    Table("unapplied_model_table", model_metadata, Column("id", Integer, primary_key=True))
    monkeypatch.setattr(schema_validator, "Base", SimpleNamespace(metadata=model_metadata))

    class EmptyInspector:
        def has_table(self, table_name: str) -> bool:
            return False

    class FakeSession:
        def get_bind(self):
            return object()

    monkeypatch.setattr(schema_validator, "inspect", lambda _bind: EmptyInspector())

    issues = schema_validator.validate_schema(FakeSession())

    assert issues == [{"kind": "missing_table", "table": "unapplied_model_table"}]
