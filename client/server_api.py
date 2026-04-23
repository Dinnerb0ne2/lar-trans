from __future__ import annotations

import logging
from typing import Any

import requests


class ServerAPI:
    def __init__(self, base_url: str, connect_timeout: float, read_timeout: float):
        self.base_url = base_url.rstrip("/")
        self.timeout = (connect_timeout, read_timeout)
        self.session = requests.Session()
        self.log = logging.getLogger("client.server_api")

    def send_heartbeat(self, client_id: str, stats: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self.base_url}/api/v1/heartbeat"
        payload = {"client_id": client_id, "stats": stats}
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            self.log.warning("heartbeat failed: %s", exc)
            return None

    def fetch_config(self, client_id: str) -> dict[str, Any] | None:
        url = f"{self.base_url}/api/v1/client/{client_id}/config"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            self.log.warning("fetch config failed: %s", exc)
            return None

    def send_frame(self, client_id: str, image_bytes: bytes) -> dict[str, Any] | None:
        url = f"{self.base_url}/api/v1/client/{client_id}/frame"
        files = {"frame": ("frame.png", image_bytes, "image/png")}
        try:
            response = self.session.post(url, files=files, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            self.log.warning("frame upload failed: %s", exc)
            return None

