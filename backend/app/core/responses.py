"""Helpers for the standard success/error response envelope used by every endpoint.

Success: {"data": ..., "message": null}
Error:   {"error": {"code": ..., "message": ..., "details": [...]}}
"""

from __future__ import annotations

from typing import Any


def success(data: Any = None, message: str | None = None) -> dict:
    return {"data": data, "message": message}


def error(code: str, message: str, details: list[dict] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or []}}
