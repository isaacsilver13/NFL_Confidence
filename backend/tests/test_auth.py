"""Tests for Google OAuth, JWT access tokens, refresh rotation, and logout."""

import asyncio
from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from authlib.integrations.base_client.errors import OAuthError
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api import auth
from app.api.auth import _run_google_request
from app.core.exceptions import UnauthorizedError
from app.models.user import User


async def _slow_google_operation() -> None:
    await asyncio.sleep(1)


async def _provider_error_operation() -> None:
    raise OAuthError("provider unavailable")


async def _timeout_operation() -> None:
    raise asyncio.TimeoutError


async def test_google_request_timeout_is_mapped_to_unauthorized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.auth.settings.google_oauth_timeout_seconds", 0.01)

    with pytest.raises(UnauthorizedError, match="Google sign-in is temporarily unavailable"):
        await _run_google_request(_slow_google_operation())


@pytest.mark.parametrize("operation", [_timeout_operation, _provider_error_operation])
async def test_google_request_provider_failures_are_mapped_to_unauthorized(
    operation: Callable[[], Awaitable[None]],
) -> None:
    with pytest.raises(UnauthorizedError, match="Google sign-in is temporarily unavailable"):
        await _run_google_request(operation())


def test_dev_login_returns_access_token_and_user(client: TestClient) -> None:
    response = client.post("/api/v1/auth/dev-login")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["accessToken"]
    assert body["tokenType"] == "bearer"
    assert body["expiresIn"] > 0
    assert body["user"]["email"] == "dev@localhost"
    assert "refresh_token" in response.cookies


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_returns_current_user_with_valid_token(client: TestClient) -> None:
    login = client.post("/api/v1/auth/dev-login")
    access_token = login.json()["data"]["accessToken"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "dev@localhost"


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


def test_refresh_rotates_the_refresh_token(client: TestClient) -> None:
    client.post("/api/v1/auth/dev-login")
    old_refresh_cookie = client.cookies.get("refresh_token")

    refreshed = client.post("/api/v1/auth/refresh")

    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["accessToken"]
    new_refresh_cookie = client.cookies.get("refresh_token")
    assert new_refresh_cookie != old_refresh_cookie

    # The old refresh token was revoked by rotation, so reusing it must fail.
    assert old_refresh_cookie is not None
    client.cookies.set("refresh_token", old_refresh_cookie)
    reuse_attempt = client.post("/api/v1/auth/refresh")
    assert reuse_attempt.status_code == 401


def test_refresh_without_cookie_is_unauthorized(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    login = client.post("/api/v1/auth/dev-login")
    access_token = login.json()["data"]["accessToken"]
    refresh_token = client.cookies.get("refresh_token")

    logout_response = client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout_response.status_code == 204

    assert refresh_token is not None
    client.cookies.set("refresh_token", refresh_token)
    reuse_attempt = client.post("/api/v1/auth/refresh")
    assert reuse_attempt.status_code == 401


def test_logout_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 401


def test_google_login_returns_401_when_not_configured(client: TestClient) -> None:
    response = client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert response.status_code == 401


def test_google_login_uses_configured_redirect_url(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google_login(monkeypatch)
    redirect_url = "https://nfl-confidence-web.fly.dev/api/v1/auth/google/callback"
    monkeypatch.setattr(auth.settings, "google_oauth_redirect_url", redirect_url)

    response = client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert response.status_code == 307
    provider = auth.oauth.google
    provider.authorize_redirect.assert_awaited_once()
    assert provider.authorize_redirect.await_args.args[1] == redirect_url


def test_google_login_uses_request_url_when_redirect_url_is_unconfigured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google_login(monkeypatch)
    monkeypatch.setattr(auth.settings, "google_oauth_redirect_url", "")

    response = client.get("/api/v1/auth/google/login", follow_redirects=False)

    assert response.status_code == 307
    provider = auth.oauth.google
    provider.authorize_redirect.assert_awaited_once()
    assert provider.authorize_redirect.await_args.args[1] == (
        "http://testserver/api/v1/auth/google/callback"
    )


def _mock_google_login(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth.settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(auth.settings, "google_client_secret", "test-client-secret")
    monkeypatch.setattr("app.auth.oauth.settings.google_client_id", "test-client-id")
    monkeypatch.setattr("app.auth.oauth.settings.google_client_secret", "test-client-secret")
    authorize_redirect = AsyncMock(return_value=auth.RedirectResponse("https://accounts.google.com"))
    monkeypatch.setattr(
        auth.oauth,
        "google",
        SimpleNamespace(authorize_redirect=authorize_redirect),
        raising=False,
    )


def _mock_google_callback(monkeypatch: pytest.MonkeyPatch, userinfo: dict[str, str] | None) -> None:
    monkeypatch.setattr(auth.settings, "google_client_id", "test-client-id")
    monkeypatch.setattr(auth.settings, "google_client_secret", "test-client-secret")
    monkeypatch.setattr("app.auth.oauth.settings.google_client_id", "test-client-id")
    monkeypatch.setattr("app.auth.oauth.settings.google_client_secret", "test-client-secret")
    authorize_access_token = AsyncMock(return_value={"userinfo": userinfo})
    monkeypatch.setattr(
        auth.oauth,
        "google",
        SimpleNamespace(authorize_access_token=authorize_access_token),
        raising=False,
    )


def test_google_callback_creates_user_and_redirects(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock_google_callback(
        monkeypatch,
        {
            "sub": "google-user-123",
            "email": "user@example.com",
            "name": "Google User",
            "picture": "https://example.com/avatar.png",
        },
    )
    monkeypatch.setattr(auth.settings, "environment", "production")

    response = client.get(
        "/api/v1/auth/google/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == auth.settings.app_url
    cookie = response.headers["set-cookie"].lower()
    assert "refresh_token=" in cookie
    assert "path=/api/v1/auth" in cookie
    assert "secure" in cookie
    assert "httponly" in cookie
    assert "samesite=none" in cookie


@pytest.mark.parametrize(
    "userinfo",
    [{"email": "user@example.com"}, {"sub": "google-user-123"}, None],
)
def test_google_callback_rejects_incomplete_userinfo(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    userinfo: dict[str, str] | None,
) -> None:
    _mock_google_callback(monkeypatch, userinfo)

    response = client.get(
        "/api/v1/auth/google/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_google_callback_rejects_email_already_linked_to_another_account(
    client: TestClient,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_session.add(
        User(
            google_id="different-google-user",
            email="user@example.com",
            display_name="Existing User",
        )
    )
    db_session.flush()
    _mock_google_callback(
        monkeypatch,
        {"sub": "google-user-123", "email": "user@example.com"},
    )

    response = client.get(
        "/api/v1/auth/google/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


def test_google_user_creation_retries_after_google_id_race(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    raced_user = User(
        google_id="google-user-123",
        email="user@example.com",
        display_name="Google User",
    )
    get_by_google_id = iter([None, raced_user])
    monkeypatch.setattr(
        "app.services.auth_service.user_repository.get_by_google_id",
        lambda _db, _google_id: next(get_by_google_id),
    )
    monkeypatch.setattr(
        "app.services.auth_service.user_repository.get_by_email",
        lambda _db, _email: None,
    )
    monkeypatch.setattr(
        "app.services.auth_service.user_repository.create",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(IntegrityError("duplicate", {}, None)),
    )

    user = auth.auth_service.get_or_create_google_user(
        db_session,
        google_id="google-user-123",
        email="user@example.com",
        display_name="Google User",
        avatar_url=None,
    )

    assert user is raced_user
