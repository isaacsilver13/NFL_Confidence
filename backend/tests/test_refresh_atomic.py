from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import auth_service


def _exercise_rotation(engine):
    unique = uuid4().hex
    with Session(engine) as session:
        user = User(google_id=unique, email=f"{unique}@example.test", display_name="Fixture")
        session.add(user)
        session.flush()
        user_id = user.id
        raw = auth_service.issue_tokens(session, user).refresh_token
    barrier = Barrier(2)

    def rotate(_):
        with Session(engine) as session:
            barrier.wait(timeout=10)
            try:
                return auth_service.refresh_session(session, raw).refresh_token
            except UnauthorizedError:
                return None

    try:
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(rotate, range(2)))
        assert sum(result is not None for result in results) == 1
        with Session(engine) as session:
            count = session.scalar(
                select(func.count())
                .select_from(RefreshToken)
                .where(RefreshToken.user_id == user_id)
            )
            assert count == 2  # consumed original plus exactly one replacement
            with pytest.raises(UnauthorizedError):
                auth_service.refresh_session(session, raw)
    finally:
        with engine.begin() as connection:
            connection.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
            connection.execute(delete(User).where(User.id == user_id))


def test_concurrent_refresh_on_isolated_sqlite(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'refresh.db'}", connect_args={"timeout": 15})
    User.__table__.create(engine)
    RefreshToken.__table__.create(engine)
    try:
        _exercise_rotation(engine)
    finally:
        engine.dispose()


def test_concurrent_refresh_on_postgres(db_engine):
    # CI's db_engine fixture creates its own disposable schema, never public.
    _exercise_rotation(db_engine)


def test_failed_issuance_rolls_back_consumption(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'rollback.db'}")
    User.__table__.create(engine)
    RefreshToken.__table__.create(engine)
    try:
        with Session(engine) as session:
            user = User(google_id=uuid4().hex, email="fixture@example.test", display_name="Fixture")
            session.add(user)
            session.flush()
            raw = auth_service.issue_tokens(session, user).refresh_token
        with monkeypatch.context() as patch:

            def fail_issuance(db, user):
                raise RuntimeError("fixture issuance failure")

            patch.setattr(auth_service, "issue_tokens", fail_issuance)
            with pytest.raises(RuntimeError, match="fixture issuance failure"):
                with Session(engine) as session:
                    auth_service.refresh_session(session, raw)
        with Session(engine) as session:
            replacement = auth_service.refresh_session(session, raw)
            assert replacement.refresh_token != raw
    finally:
        engine.dispose()


def test_jwt_migration_preserves_hs256_claims_and_rejects_bad_tokens():
    import base64
    import hashlib
    import hmac
    import json
    import time

    from app.auth import jwt as tokens

    def legacy_token(payload, *, key=None, algorithm="HS256"):
        def encode(value):
            return base64.urlsafe_b64encode(json.dumps(value).encode()).rstrip(b"=")

        signing_input = encode({"alg": algorithm, "typ": "JWT"}) + b"." + encode(payload)
        signature = hmac.new(
            (key or tokens.settings.jwt_secret).encode(), signing_input, hashlib.sha256
        ).digest()
        return (signing_input + b"." + base64.urlsafe_b64encode(signature).rstrip(b"=")).decode()

    payload = {
        "sub": str(uuid4()),
        "type": "access",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
    }
    assert tokens.decode_access_token(legacy_token(payload)) == payload
    for forged in (
        legacy_token(payload, key="independent-wrong-key-fixture-only"),
        legacy_token(payload, algorithm="HS384"),
    ):
        with pytest.raises(tokens.InvalidTokenError):
            tokens.decode_access_token(forged)
    for invalid in ({**payload, "exp": 1}, {**payload, "type": "refresh"}):
        with pytest.raises(tokens.InvalidTokenError):
            tokens.decode_access_token(legacy_token(invalid))
    with pytest.raises(tokens.InvalidTokenError):
        tokens.decode_access_token("invalid.signature.fixture")
