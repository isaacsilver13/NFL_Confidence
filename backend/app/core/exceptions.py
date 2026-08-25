"""Application-level exceptions mapped to the standard error response envelope."""

from __future__ import annotations


class AppError(Exception):
    """Base exception for all expected, user-facing application errors.

    Raised from services and caught by a FastAPI exception handler that converts
    it into the standard `{"error": {"code", "message", "details"}}` envelope.
    """

    status_code: int = 400
    code: str = "APP_ERROR"

    def __init__(self, message: str, details: list[dict] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ValidationError(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
