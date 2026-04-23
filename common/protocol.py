from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Literal

Resolution = Literal["360p", "480p"]
VALID_RESOLUTIONS = {"360p", "480p"}
MIN_FPS = 3
MAX_FPS = 15


def validate_fps(value: int) -> int:
    if value < MIN_FPS or value > MAX_FPS:
        raise ValueError(f"fps must be between {MIN_FPS} and {MAX_FPS}")
    return value


def validate_resolution(value: str) -> Resolution:
    if value not in VALID_RESOLUTIONS:
        raise ValueError(f"resolution must be one of {sorted(VALID_RESOLUTIONS)}")
    return value  # type: ignore[return-value]


@dataclass(slots=True)
class TimeWindow:
    start: str
    end: str

    @staticmethod
    def _parse_hhmm(value: str) -> time:
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError as exc:
            raise ValueError(f"invalid HH:MM time: {value}") from exc

    def contains(self, current: datetime) -> bool:
        start_time = self._parse_hhmm(self.start)
        end_time = self._parse_hhmm(self.end)
        now_t = current.time()
        if start_time <= end_time:
            return start_time <= now_t < end_time
        return now_t >= start_time or now_t < end_time

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TimeWindow":
        if "start" not in payload or "end" not in payload:
            raise ValueError("time window requires start and end")
        window = cls(start=str(payload["start"]), end=str(payload["end"]))
        # Trigger validation.
        window._parse_hhmm(window.start)
        window._parse_hhmm(window.end)
        return window

    def to_dict(self) -> dict[str, str]:
        return {"start": self.start, "end": self.end}


@dataclass(slots=True)
class ClientDesiredConfig:
    fps: int = 10
    resolution: Resolution = "480p"
    silent: bool = True
    schedule_windows: list[TimeWindow] = field(default_factory=list)
    manual_enabled: bool | None = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def validate(self) -> None:
        self.fps = validate_fps(int(self.fps))
        self.resolution = validate_resolution(str(self.resolution))
        for window in self.schedule_windows:
            if not isinstance(window, TimeWindow):
                raise ValueError("schedule_windows must contain TimeWindow objects")
            # Validate time format.
            window.contains(datetime.now())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClientDesiredConfig":
        windows = [
            TimeWindow.from_dict(item)
            for item in payload.get("schedule_windows", [])
        ]
        config = cls(
            fps=int(payload.get("fps", 10)),
            resolution=validate_resolution(str(payload.get("resolution", "480p"))),
            silent=bool(payload.get("silent", True)),
            schedule_windows=windows,
            manual_enabled=payload.get("manual_enabled"),
            updated_at=str(payload.get("updated_at", datetime.now().isoformat(timespec="seconds"))),
        )
        config.validate()
        return config

    def to_dict(self) -> dict[str, Any]:
        return {
            "fps": self.fps,
            "resolution": self.resolution,
            "silent": self.silent,
            "schedule_windows": [window.to_dict() for window in self.schedule_windows],
            "manual_enabled": self.manual_enabled,
            "updated_at": self.updated_at,
        }


@dataclass(slots=True)
class EffectiveClientConfig:
    fps: int
    resolution: Resolution
    silent: bool
    capture_enabled: bool
    capture_source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fps": self.fps,
            "resolution": self.resolution,
            "silent": self.silent,
            "capture_enabled": self.capture_enabled,
            "capture_source": self.capture_source,
        }


def compute_capture_enabled(config: ClientDesiredConfig, now: datetime | None = None) -> tuple[bool, str]:
    current = now or datetime.now()
    if config.manual_enabled is not None:
        return config.manual_enabled, "manual"

    if not config.schedule_windows:
        return True, "always-on"

    for window in config.schedule_windows:
        if window.contains(current):
            return True, "schedule"
    return False, "schedule"

