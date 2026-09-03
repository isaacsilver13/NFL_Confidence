"""Application configuration loaded from environment variables (.env for local dev)."""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_DEFAULT_JWT_SECRET = "dev-only-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "local"
    enable_scheduler: bool = True

    database_url: str = (
        "postgresql+psycopg://nfl_confidence:nfl_confidence@localhost:5432/nfl_confidence"
    )

    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_timeout_seconds: float = 8.0

    jwt_secret: str = _INSECURE_DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30

    resend_api_key: str = ""
    email_from: str = "noreply@nfl-confidence-pool.local"

    nfl_api_key: str = ""
    nfl_api_base_url: str = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
    nfl_api_timeout_seconds: float = 10.0

    app_url: str = "http://127.0.0.1:5173"
    cors_origins: str = "http://127.0.0.1:5173"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_postgres_driver(cls, value: object) -> object:
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return "postgresql+psycopg://" + value.removeprefix("postgres://")
            if value.startswith("postgresql://"):
                return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @model_validator(mode="after")
    def _reject_insecure_secret_outside_local(self) -> "Settings":
        if self.environment != "local" and self.jwt_secret == _INSECURE_DEFAULT_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a real secret outside local")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_local(self) -> bool:
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
