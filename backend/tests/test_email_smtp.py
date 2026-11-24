"""send_email picks Gmail SMTP when configured, else Resend, else logs."""

import smtplib

import pytest

from app.services import email_service
from app.services.email_service import (  # imported before conftest patches the module attr
    send_email,
)


class FakeSMTP:
    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port, self.calls, self.msg = host, port, [], None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))

    def send_message(self, msg):
        self.msg = msg


@pytest.fixture()
def smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service.settings, "smtp_user", "pool@gmail.com")
    monkeypatch.setattr(email_service.settings, "smtp_password", "app-pass")
    return FakeSMTP


def test_smtp_used_when_password_set_and_resend_skipped(smtp, monkeypatch) -> None:
    monkeypatch.setattr(email_service.settings, "resend_api_key", "re_x")
    monkeypatch.setattr(
        email_service.resend.Emails, "send", lambda *_: pytest.fail("Resend must not be used")
    )
    send_email(to=["a@example.com", "b@example.com"], subject="Hi", html="<p>x</p>")
    (conn,) = smtp.instances
    assert (conn.host, conn.port) == ("smtp.gmail.com", 587)
    assert conn.calls == ["starttls", ("login", "pool@gmail.com", "app-pass")]
    assert conn.msg["To"] == "a@example.com, b@example.com"
    assert "pool@gmail.com" in conn.msg["From"]
    assert conn.msg["Subject"] == "Hi"
    assert "<p>x</p>" in conn.msg.get_body(("html",)).get_content()


def test_single_address_string_still_works(smtp) -> None:
    send_email(to="a@example.com", subject="Hi", html="<p>x</p>")
    assert smtp.instances[0].msg["To"] == "a@example.com"


def test_resend_used_without_smtp_password(monkeypatch) -> None:
    monkeypatch.setattr(email_service.settings, "smtp_password", "")
    monkeypatch.setattr(email_service.settings, "resend_api_key", "re_x")
    sent = []
    monkeypatch.setattr(email_service.resend.Emails, "send", lambda payload: sent.append(payload))
    send_email(to=["a@example.com"], subject="Hi", html="<p>x</p>")
    assert sent[0]["to"] == ["a@example.com"]


def test_nothing_configured_only_logs(monkeypatch) -> None:
    monkeypatch.setattr(email_service.settings, "smtp_password", "")
    monkeypatch.setattr(email_service.settings, "resend_api_key", "")
    send_email(to="a@example.com", subject="Hi", html="<p>x</p>")  # must not raise
