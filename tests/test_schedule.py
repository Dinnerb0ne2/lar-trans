from __future__ import annotations

from datetime import datetime

from common.protocol import ClientDesiredConfig, TimeWindow, compute_capture_enabled


def test_schedule_disabled_outside_window() -> None:
    config = ClientDesiredConfig(
        fps=10,
        resolution="480p",
        silent=True,
        schedule_windows=[TimeWindow(start="08:00", end="12:00")],
    )
    enabled, source = compute_capture_enabled(config, now=datetime(2026, 1, 1, 7, 59))
    assert enabled is False
    assert source == "schedule"


def test_schedule_enabled_inside_window() -> None:
    config = ClientDesiredConfig(
        fps=10,
        resolution="480p",
        silent=True,
        schedule_windows=[TimeWindow(start="08:00", end="12:00")],
    )
    enabled, source = compute_capture_enabled(config, now=datetime(2026, 1, 1, 8, 30))
    assert enabled is True
    assert source == "schedule"


def test_schedule_cross_midnight_window() -> None:
    config = ClientDesiredConfig(
        fps=10,
        resolution="480p",
        silent=True,
        schedule_windows=[TimeWindow(start="22:00", end="06:00")],
    )
    enabled, source = compute_capture_enabled(config, now=datetime(2026, 1, 1, 23, 0))
    assert enabled is True
    assert source == "schedule"


def test_manual_override_wins_over_schedule() -> None:
    config = ClientDesiredConfig(
        fps=10,
        resolution="480p",
        silent=True,
        schedule_windows=[TimeWindow(start="08:00", end="12:00")],
        manual_enabled=False,
    )
    enabled, source = compute_capture_enabled(config, now=datetime(2026, 1, 1, 8, 30))
    assert enabled is False
    assert source == "manual"

