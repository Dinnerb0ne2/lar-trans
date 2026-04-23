from __future__ import annotations

import argparse

import uvicorn

from server.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="lar-trans server")
    parser.add_argument("--host", default="0.0.0.0", help="bind host")
    parser.add_argument("--port", default=8000, type=int, help="bind port")
    parser.add_argument("--state-file", default="server\\state.json", help="state persistence file")
    args = parser.parse_args()

    app = create_app(state_file=args.state_file)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

