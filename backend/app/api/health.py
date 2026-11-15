"""Unauthenticated liveness and readiness probes."""

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import desc, func, select, text
from sqlalchemy.orm import Session

from app.core.responses import error, success
from app.db.schema_validator import validate_schema
from app.db.session import get_db
from app.jobs import tick
from app.models.job_execution import JobExecution
from app.models.nfl_game import NflGame
from app.models.pick import Pick

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

# A clean schema check is reused this long: reflecting the whole schema on every readiness probe
# kept Neon's compute awake. Drift is never cached, so it keeps reporting until it is fixed.
SCHEMA_RECHECK_SECONDS = 600
_schema_valid_until = 0.0


@router.get("/health")
def health_check() -> dict:
    return success({"status": "healthy"})


@router.get("/health/metrics")
def metrics(db: Session = Depends(get_db)) -> dict:
    """Aggregate counts and timestamps for the AIsaac dashboard. No users, picks or scores."""

    last_pick, last_sync, picks, games = db.execute(
        select(
            select(func.max(Pick.submitted_at)).scalar_subquery(),
            select(func.max(NflGame.last_synced)).scalar_subquery(),
            select(func.count(Pick.id)).scalar_subquery(),
            select(func.count(NflGame.id)).scalar_subquery(),
        )
    ).one()
    return success(
        {
            "last_activity_at": last_pick.isoformat() if last_pick else None,
            "data_freshness_at": last_sync.isoformat() if last_sync else None,
            "picks_total": picks,
            "games_total": games,
        }
    )


@router.get("/health/ready", response_model=None)
def readiness_check(db: Session = Depends(get_db)) -> dict | JSONResponse:
    """Report whether dependencies needed to serve production traffic are ready."""

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Readiness check failed because the database is unavailable")
        return JSONResponse(
            status_code=503,
            content=error("SERVICE_UNAVAILABLE", "The application is not ready."),
        )

    global _schema_valid_until
    try:
        schema_issues = [] if time.monotonic() < _schema_valid_until else validate_schema(db)
    except Exception:
        logger.exception("Readiness check failed because schema validation could not run")
        return JSONResponse(
            status_code=503,
            content=error("SERVICE_UNAVAILABLE", "The application is not ready."),
        )
    if schema_issues:
        logger.error("Readiness check detected database schema drift: %s", schema_issues)
        return JSONResponse(
            status_code=503,
            content=error(
                "SCHEMA_DRIFT",
                "The database schema does not match the application.",
                schema_issues,
            ),
        )

    if _schema_valid_until <= time.monotonic():
        _schema_valid_until = time.monotonic() + SCHEMA_RECHECK_SECONDS
    return success(
        {
            "status": "ready",
            "database": "healthy",
            "schema": "valid",
            "scheduler": "external",
        }
    )


@router.get("/health/jobs")
def job_status(db: Session = Depends(get_db)) -> dict:
    """Last run and status of every scheduled job. Unauthenticated, so no error text: commissioners
    see errors at /api/v1/admin/jobs/status."""
    status: dict[str, dict[str, object]] = {}
    for job_name in tick.JOB_FUNCTIONS:
        latest = db.execute(
            select(JobExecution)
            .where(JobExecution.job_name == job_name)
            .order_by(desc(JobExecution.started_at))
            .limit(1)
        ).scalar_one_or_none()
        if latest is None:
            status[job_name] = {"status": "never_run"}
            continue
        age_minutes = (datetime.now(timezone.utc) - latest.started_at).total_seconds() / 60
        status[job_name] = {
            "last_run": latest.started_at.isoformat(),
            "status": latest.status,
            "result_count": latest.result_count,
            "age_minutes": round(age_minutes, 1),
        }
    return success(status)
