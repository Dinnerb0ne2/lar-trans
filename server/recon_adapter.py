from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any


class ReconRuntimeError(RuntimeError):
    pass


class LightArmyReconAdapter:
    """Adapter that calls LightArmyRecon without modifying the original project."""

    def __init__(
        self,
        light_army_root: str | Path = "..\\LightArmyRecon",
        conf_threshold: float = 0.5,
        sim_threshold: float = 0.5,
    ):
        self.light_army_root = Path(light_army_root).resolve()
        self.src_dir = self.light_army_root / "src"
        self.detector_model = self.light_army_root / "models" / "yolov8n.pt"
        self.db_path = self.light_army_root / "data" / "face_database.pkl"
        self.conf_threshold = conf_threshold
        self.sim_threshold = sim_threshold
        self._monitor: Any | None = None
        self._lock = threading.Lock()

    def _ensure_monitor(self) -> Any:
        if self._monitor is not None:
            return self._monitor

        if not self.src_dir.exists():
            raise ReconRuntimeError(f"LightArmyRecon src not found: {self.src_dir}")

        if str(self.src_dir) not in sys.path:
            sys.path.insert(0, str(self.src_dir))

        main_file = self.src_dir / "main.py"
        spec = importlib.util.spec_from_file_location("lightarmyrecon_main", str(main_file))
        if spec is None or spec.loader is None:
            raise ReconRuntimeError(f"cannot load module from {main_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        if not hasattr(module, "SilentFaceMonitor"):
            raise ReconRuntimeError("SilentFaceMonitor was not found in LightArmyRecon src/main.py")

        monitor_cls = module.SilentFaceMonitor
        self._monitor = monitor_cls(
            detector_model=str(self.detector_model),
            db_path=str(self.db_path),
            conf_threshold=self.conf_threshold,
            sim_threshold=self.sim_threshold,
        )
        return self._monitor

    @staticmethod
    def _normalize_results(results: Any) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in results or []:
            bbox = item.get("bbox", ())
            normalized.append(
                {
                    "bbox": [int(x) for x in bbox],
                    "name": str(item.get("name", "Unknown")),
                    "similarity": float(item.get("similarity", 0.0)),
                }
            )
        return normalized

    def process_png_bytes(self, image_bytes: bytes) -> list[dict[str, Any]]:
        if not image_bytes:
            raise ReconRuntimeError("empty frame payload")

        monitor = self._ensure_monitor()
        with self._lock:
            temp_path = ""
            try:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    temp_file.write(image_bytes)
                    temp_path = temp_file.name
                results = monitor.process_image(temp_path)
                return self._normalize_results(results)
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)

