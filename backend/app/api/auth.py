"""Authentication routes: Google OAuth login/callback, token refresh, logout, current user.

Routes stay thin: validate request -> call service -> return response.
The refresh token is delivered as an httpOnly, Secure, SameSite=Lax cookie scoped to
/api/v1/auth; the access token is returned in the JSON body for the SPA to hold in memory
and send as `Authorization: Bearer <token>`.
"""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

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


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_refresh_token,
        httponly=True,
        secure=not settings.is_local,
        samesite="lax",
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
    redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", name="google_callback")
@limiter.limit("30/hour")
async def google_callback(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> dict:
    if not is_google_oauth_configured():
        raise UnauthorizedError("Google OAuth is not configured in this environment.")

    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}

    user = auth_service.get_or_create_google_user(
        db,
        google_id=userinfo["sub"],
        email=userinfo["email"],
        display_name=userinfo.get("name") or userinfo["email"],
        avatar_url=userinfo.get("picture"),
    )
    issued = auth_service.issue_tokens(db, user)
    _set_refresh_cookie(response, issued.refresh_token)

    return success(
        TokenResponse(
            access_token=issued.access_token,
            expires_in=issued.expires_in,
            user=UserRead.model_validate(user),
        ).model_dump(by_alias=True)
    )


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
