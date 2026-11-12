"""Request schemas for client-reported usage events."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ClientAction = Literal["session_start", "page_view", "section_open", "heartbeat"]

SECTIONS = {"leaderboard", "breakdown", "standings", "profile"}
DEVICES = {"phone", "desktop"}
MAX_PATH_LENGTH = 200

# Required metadata key per action. Anything else is rejected so free text and PII never land
# in audit_log.
_REQUIRED_KEY: dict[str, str] = {
    "session_start": "device",
    "page_view": "path",
    "heartbeat": "path",
    "section_open": "section",
}


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ClientAction
    metadata: dict[str, str] | None = None

    @model_validator(mode="after")
    def _validate_metadata(self) -> "EventIn":
        key = _REQUIRED_KEY[self.action]
        if not self.metadata or set(self.metadata) != {key}:
            raise ValueError(f"{self.action} requires exactly the metadata key '{key}'")
        value = self.metadata[key]
        if key == "path":
            if not value.startswith("/") or "?" in value or "#" in value:
                raise ValueError("path must be an absolute path without query string or hash")
            if len(value) > MAX_PATH_LENGTH:
                raise ValueError("path is too long")
        elif key == "section" and value not in SECTIONS:
            raise ValueError("unknown section")
        elif key == "device" and value not in DEVICES:
            raise ValueError("unknown device")
        return self


class EventsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[EventIn] = Field(min_length=1, max_length=20)
