"""User-facing response schemas."""

import uuid

from app.schemas.base import CamelModel


class UserRead(CamelModel):
    id: uuid.UUID
    display_name: str
    email: str
    avatar_url: str | None
