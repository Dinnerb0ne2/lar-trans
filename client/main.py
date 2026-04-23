from __future__ import annotations

import argparse
import logging
import signal
import socket
from typing import Callable

from client.camera import CameraCapture, CaptureSettings
from client.controller import ClientController
from client.logging_utils import setup_logging
from client.server_api import ServerAPI
from common.protocol import MAX_FPS, MIN_FPS, VALID_RESOLUTIONS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="lar-trans raspberry-pi monitor client")
    parser.add_argument("--server-url", default="http://127.0.0.1:8000", help="server base url")
    parser.add_argument("--client-id", default=socket.gethostname(), help="client id")
    parser.add_argument("--camera-index", type=int, default=0, help="usb camera index")
    parser.add_argument("--fps", type=int, default=10, help=f"capture fps ({MIN_FPS}-{MAX_FPS})")
    parser.add_argument("--resolution", choices=sorted(VALID_RESOLUTIONS), default="480p", help="capture resolution")
    parser.add_argument("--silent", action="store_true", help="run in silent mode (no preview window)")
    parser.add_argument("--heartbeat-interval", type=float, default=10.0, help="seconds between heartbeats")
    parser.add_argument("--config-poll-interval", type=float, default=3.0, help="seconds between config pulls")
    parser.add_argument("--connect-timeout", type=float, default=3.0, help="http connect timeout in seconds")
    parser.add_argument("--read-timeout", type=float, default=20.0, help="http read timeout in seconds")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    args = parser.parse_args()

    if args.fps < MIN_FPS or args.fps > MAX_FPS:
        parser.error(f"--fps must be between {MIN_FPS} and {MAX_FPS}")
    if args.heartbeat_interval <= 0 or args.config_poll_interval <= 0:
        parser.error("interval values must be > 0")
    return args


def _register_signal_handlers(stop_fn: Callable[[], None], log: logging.Logger) -> None:
    def _handler(signum: int, frame: object) -> None:
        log.info("received signal=%s, shutting down", signum)
        stop_fn()

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    log = logging.getLogger("client.main")

    api = ServerAPI(
        base_url=args.server_url,
        connect_timeout=args.connect_timeout,
        read_timeout=args.read_timeout,
    )
    camera = CameraCapture(args.camera_index)
    controller = ClientController(
        client_id=args.client_id,
        api=api,
        camera=camera,
        heartbeat_interval=args.heartbeat_interval,
        config_poll_interval=args.config_poll_interval,
        initial_settings=CaptureSettings(
            fps=args.fps,
            resolution=args.resolution,
            silent=args.silent,
        ),
    )
    _register_signal_handlers(controller.stop, log)

    try:
        controller.run()
    finally:
        camera.close()


if __name__ == "__main__":
    main()

