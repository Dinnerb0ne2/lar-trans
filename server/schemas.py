from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TimeWindowModel(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class ConfigPatchRequest(BaseModel):
    fps: int | None = Field(default=None, ge=3, le=15)
    resolution: Literal["360p", "480p"] | None = None
    silent: bool | None = None
    schedule_windows: list[TimeWindowModel] | None = None
    manual_enabled: bool | None = None


class HeartbeatRequest(BaseModel):
    client_id: str = Field(min_length=1)
    stats: dict[str, Any] = Field(default_factory=dict)

