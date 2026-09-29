"""Internal endpoints called by infrastructure, not by users."""

import hmac
import logging

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.responses import error, success
from app.jobs import tick

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)


@router.post("/tick", response_model=None)
def run_scheduled_tick(authorization: str | None = Header(default=None)) -> dict | JSONResponse:
    """Run whichever scheduled jobs are due. Called by the GitHub Actions cron.

    Auth is a shared secret (`TICK_TOKEN`), separate from user JWTs, because the
    caller is a cron with no user. With no token configured the endpoint is
    disabled rather than open.
    """
    expected = get_settings().tick_token
    if not expected:
        return JSONResponse(
            status_code=503,
            content=error("TICK_DISABLED", "Scheduled ticks are not configured."),
        )

    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(
        supplied.strip().encode(), expected.encode()
    ):
        logger.warning("Rejected tick request with a missing or invalid token")
        return JSONResponse(
            status_code=401,
            content=error("UNAUTHORIZED", "Invalid or missing tick token."),
        )

    return success(tick.run_tick())
