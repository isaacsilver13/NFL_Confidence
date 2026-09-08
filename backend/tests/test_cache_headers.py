"""Tests for the API cache policy."""


def test_api_success_responses_are_private_and_non_storable(client) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "private, no-store"
    assert {value.strip().lower() for value in response.headers["Vary"].split(",")} >= {
        "authorization",
        "cookie",
    }


def test_api_error_responses_are_private_and_non_storable(client) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "private, no-store"
