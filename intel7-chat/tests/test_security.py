import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

import app.database as database
import app.main as main


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "chat.db"))
    main.connected_clients.clear()
    main.nickname_registry.clear()
    main.message_timestamps.clear()
    yield
    main.connected_clients.clear()
    main.nickname_registry.clear()
    main.message_timestamps.clear()


def test_ip_suffix_exposes_only_final_two_ipv4_octets():
    assert database.get_ip_suffix("192.168.72.50") == "72.50"
    assert database.get_ip_suffix("not-an-ip") == ""


def test_host_allowlist_accepts_lan_names_and_rejects_public_dns():
    assert main.host_is_allowed("192.168.1.42:8000")
    assert main.host_is_allowed("CLASSROOM-PC:8000")
    assert main.host_is_allowed("classchat.local:8000")
    assert not main.host_is_allowed("evil.example:8000")


def test_recent_messages_return_suffix_but_not_full_ip():
    database.init_db()
    database.save_message("Ronaldo", "hello", ip="192.168.72.50")

    messages = database.get_recent_messages()

    assert messages[0]["ip_suffix"] == "72.50"
    assert "ip" not in messages[0]
    assert "192.168.72.50" not in json.dumps(messages)


def test_http_security_headers_and_api_docs_disabled():
    with TestClient(main.app) as client:
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/", headers={"host": "evil.example"}).status_code == 400


def test_websocket_rejects_cross_origin_connection():
    with TestClient(main.app) as client:
        with pytest.raises(WebSocketDisconnect) as rejected:
            with client.websocket_connect(
                "/ws?nickname=attacker",
                headers={"origin": "http://evil.example"},
            ):
                pass
        assert rejected.value.code == 1008


def test_public_chat_includes_partial_ip(monkeypatch):
    monkeypatch.setattr(main, "get_client_ip", lambda _connection: "192.168.72.50")
    with TestClient(main.app) as client:
        with client.websocket_connect(
            "/ws?nickname=Ronaldo",
            headers={"origin": "http://testserver"},
        ) as websocket:
            websocket.receive_json()  # presence
            websocket.receive_json()  # users
            websocket.send_json({"type": "chat", "content": "hello"})
            message = websocket.receive_json()

        assert message["nickname"] == "Ronaldo"
        assert message["ip_suffix"] == "72.50"
        assert "192.168.72.50" not in json.dumps(message)


def test_rate_limit_uses_a_sliding_window():
    for _ in range(main.RATE_LIMIT_MESSAGES):
        assert main.message_rate_allowed("192.168.1.5", now=100.0)
    assert not main.message_rate_allowed("192.168.1.5", now=100.0)
    assert main.message_rate_allowed(
        "192.168.1.5",
        now=100.0 + main.RATE_LIMIT_WINDOW_SECONDS + 0.01,
    )
