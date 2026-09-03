"""FastAPI application entry point.

Wires together CORS, rate limiting, the standard error envelope, and API routers.
Routes must stay thin: validate request -> call service -> return response.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.sessions import SessionMiddleware

from app.api.auth import router as auth_router
from app.api.games import router as games_router
from app.api.health import router as health_router
from app.api.jobs import router as jobs_router
from app.api.leaderboard import router as leaderboard_router
from app.api.league import router as league_router
from app.api.picks import router as picks_router
from app.api.session import router as session_router
from app.api.weeks import router as weeks_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.limiter import limiter
from app.core.responses import error
from app.jobs.scheduler import create_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI):
    scheduler = create_scheduler() if settings.enable_scheduler else None
    if scheduler is not None:
        scheduler.start()
    application.state.scheduler = scheduler
    application.state.scheduler_enabled = settings.enable_scheduler
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(title="NFL Confidence Pool API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Required by Authlib to store the OAuth `state`/nonce between the /google/login
# redirect and the /google/callback request.
app.add_middleware(SessionMiddleware, secret_key=settings.jwt_secret, same_site="lax")


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error(exc.code, exc.message, exc.details),
    )


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(league_router, prefix="/api/v1")
app.include_router(games_router, prefix="/api/v1")
app.include_router(weeks_router, prefix="/api/v1")
app.include_router(picks_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(leaderboard_router, prefix="/api/v1")
app.include_router(jobs_router)
