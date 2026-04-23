from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import cv2

from client.camera import CameraCapture, CaptureSettings
from client.server_api import ServerAPI
from common.protocol import MAX_FPS, MIN_FPS, VALID_RESOLUTIONS


@dataclass(slots=True)
class RuntimeState:
    settings: CaptureSettings
    capture_enabled: bool = True
    capture_source: str = "always-on"


class ClientController:
    def __init__(
        self,
        *,
        client_id: str,
        api: ServerAPI,
        camera: CameraCapture,
        heartbeat_interval: float,
        config_poll_interval: float,
        initial_settings: CaptureSettings,
    ):
        self.client_id = client_id
        self.api = api
        self.camera = camera
        self.heartbeat_interval = heartbeat_interval
        self.config_poll_interval = config_poll_interval
        self.state = RuntimeState(settings=initial_settings)
        self._running = True
        self._frames_sent = 0
        self._last_result_count = 0
        self.log = logging.getLogger("client.controller")

    def stop(self) -> None:
        self._running = False

    def _apply_server_config(self, payload: dict[str, Any] | None) -> None:
        if not payload:
            return
        effective = payload.get("effective_config", {})
        if not effective:
            return

        fps = int(effective.get("fps", self.state.settings.fps))
        if fps < MIN_FPS or fps > MAX_FPS:
            raise ValueError(f"invalid fps from server: {fps}")

        resolution = str(effective.get("resolution", self.state.settings.resolution))
        if resolution not in VALID_RESOLUTIONS:
            raise ValueError(f"invalid resolution from server: {resolution}")

        silent = bool(effective.get("silent", self.state.settings.silent))
        capture_enabled = bool(effective.get("capture_enabled", self.state.capture_enabled))
        capture_source = str(effective.get("capture_source", self.state.capture_source))

        self.state.settings = CaptureSettings(
            fps=fps,
            resolution=resolution,  # type: ignore[arg-type]
            silent=silent,
        )
        self.state.capture_enabled = capture_enabled
        self.state.capture_source = capture_source
        self.log.info(
            "applied config fps=%s resolution=%s silent=%s capture_enabled=%s source=%s",
            fps,
            resolution,
            silent,
            capture_enabled,
            capture_source,
        )

    def run(self) -> None:
        next_heartbeat = 0.0
        next_config_poll = 0.0
        next_frame = 0.0
        network_failures = 0

        self.log.info("client started: id=%s", self.client_id)

        while self._running:
            now = time.monotonic()

            if now >= next_heartbeat:
                heartbeat_payload = self.api.send_heartbeat(
                    self.client_id,
                    {
                        "frames_sent": self._frames_sent,
                        "last_result_count": self._last_result_count,
                    },
                )
                try:
                    self._apply_server_config(heartbeat_payload)
                except ValueError as exc:
                    self.log.error("server config validation failed from heartbeat: %s", exc)
                next_heartbeat = now + self.heartbeat_interval

            if now >= next_config_poll:
                config_payload = self.api.fetch_config(self.client_id)
                try:
                    self._apply_server_config(config_payload)
                except ValueError as exc:
                    self.log.error("server config validation failed from poll: %s", exc)
                next_config_poll = now + self.config_poll_interval

            if not self.state.capture_enabled:
                time.sleep(0.1)
                continue

            if now < next_frame:
                time.sleep(min(0.02, next_frame - now))
                continue

            frame_interval = 1.0 / self.state.settings.fps
            next_frame = now + frame_interval

            try:
                self.camera.apply_settings(self.state.settings)
                image_bytes, frame = self.camera.read_png()
            except RuntimeError as exc:
                self.log.error("camera error: %s", exc)
                self.camera.close()
                time.sleep(1.0)
                continue

            response = self.api.send_frame(self.client_id, image_bytes)
            if response is None:
                network_failures += 1
                backoff = min(10.0, 0.5 * (2 ** min(network_failures, 5)))
                self.log.warning("network unstable, reconnect in %.1fs", backoff)
                time.sleep(backoff)
            else:
                network_failures = 0
                self._frames_sent += 1
                self._last_result_count = int(response.get("result_count", 0))

            if not self.state.settings.silent:
                try:
                    cv2.imshow(f"lar-trans preview ({self.client_id})", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        self.log.info("preview received quit key")
                        self.stop()
                except cv2.error as exc:
                    self.log.warning("preview disabled due to GUI error: %s", exc)
                    self.state.settings = CaptureSettings(
                        fps=self.state.settings.fps,
                        resolution=self.state.settings.resolution,
                        silent=True,
                    )

        self.camera.close()
        try:
            cv2.destroyAllWindows()
        except cv2.error:
            pass
        self.log.info("client stopped")

