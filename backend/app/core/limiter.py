"""Shared slowapi rate limiter instance.

Kept separate from app.main so route modules can import it for `@limiter.limit(...)`
decorators without causing a circular import with the FastAPI app factory.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth.jwt import InvalidTokenError, decode_access_token

limiter = Limiter(key_func=get_remote_address)


def user_rate_key(request: Request) -> str:
    """Rate-limit key: the Bearer token's user id, falling back to the client IP.

    Per-user keys keep users behind a shared IP (household, office, Fly proxy) from
    sharing one bucket.
    """
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() == "bearer" and token:
        try:
            return f"user:{decode_access_token(token).get('sub', '')}"
        except InvalidTokenError:
            pass
    return get_remote_address(request)
