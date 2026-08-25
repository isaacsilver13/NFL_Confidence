"""Tests for Google-OAuth-free dev login, JWT access tokens, refresh rotation, and logout."""

from fastapi.testclient import TestClient


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
