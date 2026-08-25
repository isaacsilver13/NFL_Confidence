"""Auth response schemas."""

from app.schemas.base import CamelModel
from app.schemas.user import UserRead


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead


class AccessTokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
