from __future__ import annotations

import argparse
import logging
import signal
import socket
from typing import Callable
import json
from pathlib import Path

from client.camera import CameraCapture, CaptureSettings
from client.controller import ClientController
from client.logging_utils import setup_logging
from client.server_api import ServerAPI
from common.protocol import MAX_FPS, MIN_FPS, VALID_RESOLUTIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="lar-trans raspberry-pi monitor client")
    parser.add_argument("--config", "-c", default="client/config.json", help="path to JSON config (default: client/config.json)")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging (overrides config)")
    return parser.parse_args()


DEFAULT_CONFIG = {
    "server_url": "http://127.0.0.1:8000",
    "client_id": socket.gethostname(),
    "camera_index": 0,
    "fps": 10,
    "resolution": "480p",
    "silent": False,
    "heartbeat_interval": 10.0,
    "config_poll_interval": 3.0,
    "connect_timeout": 3.0,
    "read_timeout": 20.0,
    "verbose": False,
}


def load_json_config(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def build_config(args: argparse.Namespace) -> dict:
    cfg = {**DEFAULT_CONFIG}
    file_cfg = load_json_config(args.config)
    if file_cfg:
        cfg.update(file_cfg)
    if args.verbose:
        cfg["verbose"] = True
    # sanitize values
    try:
        cfg["fps"] = int(cfg.get("fps", cfg["fps"]))
    except Exception:
        cfg["fps"] = DEFAULT_CONFIG["fps"]
    if cfg["fps"] < MIN_FPS or cfg["fps"] > MAX_FPS:
        cfg["fps"] = DEFAULT_CONFIG["fps"]
    cfg["heartbeat_interval"] = float(cfg.get("heartbeat_interval", cfg["heartbeat_interval"]))
    cfg["config_poll_interval"] = float(cfg.get("config_poll_interval", cfg["config_poll_interval"]))
    if cfg["config_poll_interval"] <= 0 or cfg["heartbeat_interval"] <= 0:
        cfg["heartbeat_interval"] = DEFAULT_CONFIG["heartbeat_interval"]
        cfg["config_poll_interval"] = DEFAULT_CONFIG["config_poll_interval"]
    resolution = str(cfg.get("resolution", cfg["resolution"]))
    if resolution not in VALID_RESOLUTIONS:
        cfg["resolution"] = DEFAULT_CONFIG["resolution"]
    return cfg


def _register_signal_handlers(stop_fn: Callable[[], None], log: logging.Logger) -> None:
    def _handler(signum: int, frame: object) -> None:
        log.info("received signal=%s, shutting down", signum)
        stop_fn()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def main() -> None:
    args = parse_args()
    cfg = build_config(args)
    setup_logging(cfg.get("verbose", False))
    log = logging.getLogger("client.main")

    api = ServerAPI(
        base_url=cfg.get("server_url"),
        connect_timeout=cfg.get("connect_timeout"),
        read_timeout=cfg.get("read_timeout"),
    )
    camera = CameraCapture(int(cfg.get("camera_index", 0)))
    controller = ClientController(
        client_id=str(cfg.get("client_id")),
        api=api,
        camera=camera,
        heartbeat_interval=float(cfg.get("heartbeat_interval")),
        config_poll_interval=float(cfg.get("config_poll_interval")),
        initial_settings=CaptureSettings(
            fps=int(cfg.get("fps")),
            resolution=str(cfg.get("resolution")),
            silent=bool(cfg.get("silent")),
        ),
    )
    _register_signal_handlers(controller.stop, log)

    try:
        controller.run()
    finally:
        camera.close()


if __name__ == "__main__":
    main()

