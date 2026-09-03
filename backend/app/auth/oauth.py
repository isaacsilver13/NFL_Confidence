"""Google OAuth client registration (Authlib).

The client is only registered when GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET are set.
In local development without real Google credentials, `is_google_oauth_configured()`
returns False and the API exposes a dev-only fallback login endpoint instead
(see app/api/auth.py).
"""

from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings

settings = get_settings()

oauth = OAuth()

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
            "timeout": settings.google_oauth_timeout_seconds,
        },
    )


def is_google_oauth_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)
