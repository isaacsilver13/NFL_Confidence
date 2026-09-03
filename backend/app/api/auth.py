"""Authentication routes: Google OAuth login/callback, token refresh, logout, current user.

Routes stay thin: validate request -> call service -> return response.
The refresh token is delivered as an httpOnly, Secure cookie scoped to
/api/v1/auth; the access token is returned in the JSON body for the SPA to hold in memory
and send as `Authorization: Bearer <token>`.
"""

import asyncio
import logging
from collections.abc import Awaitable, Mapping
from typing import TypeVar

import httpx
from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.auth.dependencies import get_current_user
from app.auth.oauth import is_google_oauth_configured, oauth
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.limiter import limiter
from app.core.responses import success
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AccessTokenResponse, TokenResponse
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

settings = get_settings()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"
_GoogleResult = TypeVar("_GoogleResult")
logger = logging.getLogger(__name__)


def _extract_google_userinfo(token: object) -> tuple[str, str, str, str | None]:
    if not isinstance(token, Mapping):
        raise UnauthorizedError("Google sign-in returned an invalid response. Please try again.")

    userinfo = token.get("userinfo")
    if not isinstance(userinfo, Mapping):
        raise UnauthorizedError(
            "Google sign-in did not return the required account information. Please try again."
        )

    google_id = userinfo.get("sub")
    email = userinfo.get("email")
    if not isinstance(google_id, str) or not google_id.strip():
        raise UnauthorizedError(
            "Google sign-in did not return the required account information. Please try again."
        )
    if not isinstance(email, str) or not email.strip():
        raise UnauthorizedError(
            "Google sign-in did not return the required account information. Please try again."
        )

    display_name = userinfo.get("name")
    picture = userinfo.get("picture")
    return (
        google_id,
        email,
        display_name if isinstance(display_name, str) and display_name.strip() else email,
        picture if isinstance(picture, str) and picture.strip() else None,
    )


async def _run_google_request(operation: Awaitable[_GoogleResult]) -> _GoogleResult:
    try:
        return await asyncio.wait_for(operation, timeout=settings.google_oauth_timeout_seconds)
    except (asyncio.TimeoutError, httpx.HTTPError, OAuthError) as exc:
        raise UnauthorizedError(
            "Google sign-in is temporarily unavailable. Please try again."
        ) from exc


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=not settings.is_local,
        samesite="lax" if settings.is_local else "none",  # cross-site frontend/backend in prod
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.get("/google/login")
@limiter.limit("30/hour")
async def google_login(request: Request) -> Response:
    if not is_google_oauth_configured():
        raise UnauthorizedError(
            "Google OAuth is not configured in this environment. Use /auth/dev-login instead."
        )
    redirect_uri = settings.google_oauth_redirect_url or str(request.url_for("google_callback"))
    return await _run_google_request(oauth.google.authorize_redirect(request, redirect_uri))


@router.get("/google/callback", name="google_callback")
@limiter.limit("30/hour")
async def google_callback(request: Request, db: Session = Depends(get_db)) -> RedirectResponse:
    if not is_google_oauth_configured():
        raise UnauthorizedError("Google OAuth is not configured in this environment.")

    try:
        token = await _run_google_request(oauth.google.authorize_access_token(request))
    except UnauthorizedError as exc:
        logger.warning(
            "Google OAuth token exchange failed: %s",
            type(exc.__cause__ or exc).__name__,
        )
        raise

    try:
        google_id, email, display_name, avatar_url = _extract_google_userinfo(token)
    except UnauthorizedError:
        logger.warning("Google OAuth response did not contain required user claims")
        raise

    try:
        user = auth_service.get_or_create_google_user(
            db,
            google_id=google_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        issued = auth_service.issue_tokens(db, user)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Google OAuth callback database operation failed: %s", type(exc).__name__)
        raise UnauthorizedError("Google sign-in could not be completed. Please try again.") from exc

    redirect = RedirectResponse(url=settings.app_url, status_code=303)
    _set_refresh_cookie(redirect, issued.refresh_token)
    return redirect


@router.post("/dev-login")
@limiter.limit("30/hour")
def dev_login(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    """Local-only login bypass for development when Google OAuth credentials aren't set."""
    if is_google_oauth_configured() or not settings.is_local:
        raise UnauthorizedError("Dev login is only available in local development.")

    user = auth_service.get_or_create_dev_user(db)
    issued = auth_service.issue_tokens(db, user)
    _set_refresh_cookie(response, issued.refresh_token)

    return success(
        TokenResponse(
            access_token=issued.access_token,
            expires_in=issued.expires_in,
            user=UserRead.model_validate(user),
        ).model_dump(by_alias=True)
    )


@router.post("/refresh")
@limiter.limit("30/hour")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise UnauthorizedError("Missing refresh token")

    issued = auth_service.refresh_session(db, raw_refresh_token)
    _set_refresh_cookie(response, issued.refresh_token)

    return success(
        AccessTokenResponse(
            access_token=issued.access_token, expires_in=issued.expires_in
        ).model_dump(by_alias=True)
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh_token:
        auth_service.logout(db, user_id=current_user.id, raw_refresh_token=raw_refresh_token)
    _clear_refresh_cookie(response)


@router.get("/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    return success(UserRead.model_validate(current_user).model_dump(by_alias=True))
