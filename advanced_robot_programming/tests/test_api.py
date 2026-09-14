import time

from fastapi.testclient import TestClient

from workcell.app import create_app
from workcell.config import Settings


def ready(client):
    for _ in range(200):
        status = client.get("/api/status").json()
        if status["initialized"] and not status["pending"]:
            return status
        time.sleep(0.01)
    raise AssertionError(status)


def test_api_requires_token_and_returns_accepted_not_completed():
    app = create_app(Settings(database=":memory:"))
    with TestClient(app) as client:
        ready(client)
        assert client.get("/").status_code == 200
        assert client.post("/api/commands", json={"action": "enable"}).status_code == 403
        headers = {"X-Workcell-Token": app.state.token}
        result = client.post("/api/commands", json={"action": "enable"}, headers=headers)
        assert result.status_code == 202
        assert result.json()["status"] == "accepted"
        ready(client)
        app.state.cell.scenario.delay = 0.15
        assert (
            client.post("/api/commands", json={"action": "start"}, headers=headers).status_code
            == 202
        )
        assert (
            client.post("/api/commands", json={"action": "start"}, headers=headers).status_code
            == 409
        )
        start = time.monotonic()
        assert client.get("/api/status").status_code == 200
        assert time.monotonic() - start < 0.3
        assert client.get("/api/frame").headers["content-type"] == "image/jpeg"
        assert (
            client.post("/api/commands", json={"action": "stop"}, headers=headers).status_code
            == 202
        )
        assert ready(client)["state"] == "FAULT"


def test_recovery_requires_inspection_note():
    app = create_app(Settings(database=":memory:"))
    with TestClient(app) as client:
        ready(client)
        headers = {"X-Workcell-Token": app.state.token}
        for action in ("reset", "replace_pallet", "reconcile"):
            assert (
                client.post("/api/commands", json={"action": action}, headers=headers).status_code
                == 422
            )


def test_bad_host_is_rejected():
    app = create_app(Settings(database=":memory:"))
    with TestClient(app) as client:
        assert client.get("/", headers={"Host": "untrusted.example"}).status_code == 400


def test_camera_failure_does_not_serve_stale_preview():
    app = create_app(Settings(database=":memory:"))
    with TestClient(app) as client:
        ready(client)
        assert client.get("/api/frame").status_code == 200
        app.state.cell.scenario.configure(fault="camera_disconnect")
        assert client.get("/api/frame").status_code == 503
