from __future__ import annotations

from datetime import datetime

from common.protocol import ClientDesiredConfig, EffectiveClientConfig, compute_capture_enabled


def build_effective_config(config: ClientDesiredConfig, now: datetime | None = None) -> EffectiveClientConfig:
    capture_enabled, capture_source = compute_capture_enabled(config, now=now)
    return EffectiveClientConfig(
        fps=config.fps,
        resolution=config.resolution,
        silent=config.silent,
        capture_enabled=capture_enabled,
        capture_source=capture_source,
    )

