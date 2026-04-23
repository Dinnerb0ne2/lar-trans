from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from server.app import create_app


class DummyReconAdapter:
    def process_png_bytes(self, image_bytes: bytes):
        assert image_bytes.startswith(b"\x89PNG")
        return [{"bbox": [0, 0, 10, 10], "name": "Unknown", "similarity": 0.0}]


def test_client_config_and_control_flow(tmp_path: Path) -> None:
    app = create_app(state_file=tmp_path / "state.json", recon_adapter=DummyReconAdapter())
    client = TestClient(app)

    response = client.get("/api/v1/client/c1/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["effective_config"]["capture_enabled"] is True
    assert payload["effective_config"]["capture_source"] == "always-on"

    response = client.patch(
        "/api/v1/client/c1/config",
        json={
            "fps": 12,
            "resolution": "360p",
            "schedule_windows": [{"start": "08:00", "end": "08:30"}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["desired_config"]["fps"] == 12
    assert payload["desired_config"]["resolution"] == "360p"

    stop_resp = client.post("/api/v1/client/c1/control/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["effective_config"]["capture_enabled"] is False
    assert stop_resp.json()["effective_config"]["capture_source"] == "manual"

    auto_resp = client.post("/api/v1/client/c1/control/auto")
    assert auto_resp.status_code == 200
    assert auto_resp.json()["desired_config"]["manual_enabled"] is None


def test_heartbeat_and_frame_endpoint(tmp_path: Path) -> None:
    app = create_app(state_file=tmp_path / "state.json", recon_adapter=DummyReconAdapter())
    client = TestClient(app)

    hb = client.post("/api/v1/heartbeat", json={"client_id": "pi-a", "stats": {"frames_sent": 5}})
    assert hb.status_code == 200
    assert hb.json()["client_id"] == "pi-a"

    png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01\xe2!\xbc3"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    frame_resp = client.post(
        "/api/v1/client/pi-a/frame",
        files={"frame": ("f.png", png, "image/png")},
    )
    assert frame_resp.status_code == 200
    assert frame_resp.json()["result_count"] == 1

