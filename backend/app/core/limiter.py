"""Shared slowapi rate limiter instance.

Kept separate from app.main so route modules can import it for `@limiter.limit(...)`
decorators without causing a circular import with the FastAPI app factory.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
