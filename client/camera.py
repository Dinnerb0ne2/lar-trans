from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

Resolution = Literal["360p", "480p"]


@dataclass(slots=True)
class CaptureSettings:
    fps: int
    resolution: Resolution
    silent: bool


def _resolution_to_size(resolution: Resolution) -> tuple[int, int]:
    if resolution == "360p":
        return (640, 360)
    return (640, 480)


class CameraCapture:
    def __init__(self, camera_index: int):
        self._camera_index = camera_index
        self._cap: cv2.VideoCapture | None = None
        self._current_resolution: Resolution | None = None
        self._current_fps: int | None = None

    def open(self) -> None:
        if self._cap is not None and self._cap.isOpened():
            return
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"cannot open camera index={self._camera_index}")
        self._cap = cap

    def apply_settings(self, settings: CaptureSettings) -> None:
        self.open()
        assert self._cap is not None
        if settings.resolution != self._current_resolution:
            width, height = _resolution_to_size(settings.resolution)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self._current_resolution = settings.resolution
        if settings.fps != self._current_fps:
            self._cap.set(cv2.CAP_PROP_FPS, settings.fps)
            self._current_fps = settings.fps

    def read_png(self) -> tuple[bytes, np.ndarray]:
        self.open()
        assert self._cap is not None
        ok, frame = self._cap.read()
        if not ok:
            raise RuntimeError("camera read failed")
        encoded, buf = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        if not encoded:
            raise RuntimeError("png encode failed")
        return buf.tobytes(), frame

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

