from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from common.protocol import ClientDesiredConfig, TimeWindow
from server.schedule import build_effective_config


class ServerState:
    def __init__(self, state_file: str | Path):
        self._state_file = Path(state_file)
        self._lock = threading.Lock()
        self._clients: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        payload = json.loads(self._state_file.read_text(encoding="utf-8"))
        clients = payload.get("clients", {})
        for client_id, data in clients.items():
            config = ClientDesiredConfig.from_dict(data.get("desired_config", {}))
            self._clients[client_id] = {
                "desired_config": config,
                "last_heartbeat": data.get("last_heartbeat"),
                "last_stats": data.get("last_stats", {}),
                "last_recon_result": data.get("last_recon_result"),
            }

    def _dump(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"clients": {}}
        for client_id, data in self._clients.items():
            payload["clients"][client_id] = {
                "desired_config": data["desired_config"].to_dict(),
                "last_heartbeat": data.get("last_heartbeat"),
                "last_stats": data.get("last_stats", {}),
                "last_recon_result": data.get("last_recon_result"),
            }
        self._state_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _get_or_create_config_unlocked(self, client_id: str) -> ClientDesiredConfig:
        if client_id not in self._clients:
            config = ClientDesiredConfig()
            config.validate()
            self._clients[client_id] = {
                "desired_config": config,
                "last_heartbeat": None,
                "last_stats": {},
                "last_recon_result": None,
            }
            self._dump()
        return self._clients[client_id]["desired_config"]

    def get_or_create_config(self, client_id: str) -> ClientDesiredConfig:
        with self._lock:
            return self._get_or_create_config_unlocked(client_id)

    def get_effective_config(self, client_id: str) -> dict[str, Any]:
        with self._lock:
            config = self._get_or_create_config_unlocked(client_id)
            effective = build_effective_config(config)
            return {
                "client_id": client_id,
                "desired_config": config.to_dict(),
                "effective_config": effective.to_dict(),
                "server_time": datetime.now().isoformat(timespec="seconds"),
            }

    def update_config(
        self,
        client_id: str,
        *,
        fps: int | None = None,
        resolution: str | None = None,
        silent: bool | None = None,
        schedule_windows: list[dict[str, str]] | None = None,
        manual_enabled: bool | None | str = "__nochange__",
    ) -> ClientDesiredConfig:
        with self._lock:
            config = self._get_or_create_config_unlocked(client_id)
            if fps is not None:
                config.fps = fps
            if resolution is not None:
                config.resolution = resolution  # type: ignore[assignment]
            if silent is not None:
                config.silent = silent
            if schedule_windows is not None:
                config.schedule_windows = [TimeWindow.from_dict(item) for item in schedule_windows]
            if manual_enabled != "__nochange__":
                config.manual_enabled = manual_enabled  # type: ignore[assignment]
            config.updated_at = datetime.now().isoformat(timespec="seconds")
            config.validate()
            self._dump()
            return config

    def set_manual_state(self, client_id: str, manual_enabled: bool | None) -> ClientDesiredConfig:
        return self.update_config(client_id, manual_enabled=manual_enabled)

    def record_heartbeat(self, client_id: str, stats: dict[str, Any]) -> None:
        with self._lock:
            self._get_or_create_config_unlocked(client_id)
            self._clients[client_id]["last_heartbeat"] = datetime.now().isoformat(timespec="seconds")
            self._clients[client_id]["last_stats"] = stats
            self._dump()

    def record_recon_result(self, client_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            self._get_or_create_config_unlocked(client_id)
            self._clients[client_id]["last_recon_result"] = result
            self._dump()

    def list_clients(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = []
            for client_id, data in self._clients.items():
                effective = build_effective_config(data["desired_config"]).to_dict()
                rows.append(
                    {
                        "client_id": client_id,
                        "desired_config": data["desired_config"].to_dict(),
                        "effective_config": effective,
                        "last_heartbeat": data.get("last_heartbeat"),
                        "last_stats": data.get("last_stats", {}),
                    }
                )
            rows.sort(key=lambda item: item["client_id"])
            return rows

