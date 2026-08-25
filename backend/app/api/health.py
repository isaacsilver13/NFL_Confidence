"""GET /health - unauthenticated, unlimited rate, used for CI/CD and uptime checks."""

from fastapi import APIRouter

from app.core.responses import success

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return success({"status": "healthy"})
