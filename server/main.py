from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from server.app import create_app


DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "state_file": "server/state.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="lar-trans server")
    parser.add_argument("--config", "-c", default="server/config.json", help="path to JSON config (default: server/config.json)")
    return parser.parse_args()


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
    # sanitize types
    try:
        cfg["port"] = int(cfg.get("port", cfg["port"]))
    except Exception:
        cfg["port"] = DEFAULT_CONFIG["port"]
    cfg["host"] = str(cfg.get("host", cfg["host"]))
    cfg["state_file"] = str(cfg.get("state_file", cfg["state_file"]))
    return cfg


def main() -> None:
    args = parse_args()
    cfg = build_config(args)

    app = create_app(state_file=cfg["state_file"])
    uvicorn.run(app, host=cfg["host"], port=cfg["port"]) 


if __name__ == "__main__":
    main()

