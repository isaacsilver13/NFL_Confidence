import uuid

from starlette.requests import Request

from app.auth.jwt import create_access_token
from app.core.limiter import user_rate_key


def _request(authorization: str | None = None) -> Request:
    headers = [(b"authorization", authorization.encode())] if authorization else []
    return Request({"type": "http", "headers": headers, "client": ("203.0.113.7", 1234)})


def test_valid_bearer_token_keys_by_user() -> None:
    user_id = uuid.uuid4()
    token, _ = create_access_token(user_id)
    assert user_rate_key(_request(f"Bearer {token}")) == f"user:{user_id}"


def test_missing_authorization_falls_back_to_client_ip() -> None:
    assert user_rate_key(_request()) == "203.0.113.7"


def test_garbage_bearer_token_falls_back_to_client_ip() -> None:
    assert user_rate_key(_request("Bearer not-a-jwt")) == "203.0.113.7"
