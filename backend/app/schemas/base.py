"""Shared Pydantic base classes.

All API response schemas use camelCase field names (to match the frontend/API
spec) while models/business logic use snake_case Python attribute names.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base schema that serializes snake_case attributes as camelCase JSON."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
