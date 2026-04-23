from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile

from server.recon_adapter import LightArmyReconAdapter, ReconRuntimeError
from server.schemas import ConfigPatchRequest, HeartbeatRequest
from server.state import ServerState


def create_app(
    state_file: str | Path = "server\\state.json",
    recon_adapter: LightArmyReconAdapter | None = None,
) -> FastAPI:
    app = FastAPI(title="lar-trans server", version="1.0.0")
    state = ServerState(state_file)
    recon = recon_adapter or LightArmyReconAdapter()
    app.state.server_state = state
    app.state.recon_adapter = recon

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/clients")
    def list_clients() -> dict[str, Any]:
        return {"items": state.list_clients()}

    @app.get("/api/v1/client/{client_id}/config")
    def get_client_config(client_id: str) -> dict[str, Any]:
        return state.get_effective_config(client_id)

    @app.patch("/api/v1/client/{client_id}/config")
    def update_client_config(client_id: str, payload: ConfigPatchRequest) -> dict[str, Any]:
        state.update_config(
            client_id,
            fps=payload.fps,
            resolution=payload.resolution,
            silent=payload.silent,
            schedule_windows=(
                [window.model_dump() for window in payload.schedule_windows]
                if payload.schedule_windows is not None
                else None
            ),
            manual_enabled=payload.manual_enabled if "manual_enabled" in payload.model_fields_set else "__nochange__",
        )
        return state.get_effective_config(client_id)

    @app.post("/api/v1/client/{client_id}/control/start")
    def force_start(client_id: str) -> dict[str, Any]:
        state.set_manual_state(client_id, True)
        return state.get_effective_config(client_id)

    @app.post("/api/v1/client/{client_id}/control/stop")
    def force_stop(client_id: str) -> dict[str, Any]:
        state.set_manual_state(client_id, False)
        return state.get_effective_config(client_id)

    @app.post("/api/v1/client/{client_id}/control/auto")
    def back_to_auto(client_id: str) -> dict[str, Any]:
        state.set_manual_state(client_id, None)
        return state.get_effective_config(client_id)

    @app.post("/api/v1/heartbeat")
    def heartbeat(payload: HeartbeatRequest) -> dict[str, Any]:
        state.record_heartbeat(payload.client_id, payload.stats)
        return state.get_effective_config(payload.client_id)

    @app.post("/api/v1/client/{client_id}/frame")
    async def post_frame(client_id: str, frame: UploadFile = File(...)) -> dict[str, Any]:
        image_bytes = await frame.read()
        try:
            results = recon.process_png_bytes(image_bytes)
        except ReconRuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        state.record_recon_result(
            client_id,
            {
                "result_count": len(results),
                "results": results,
            },
        )
        return {"result_count": len(results), "results": results}

    return app


app = create_app()

