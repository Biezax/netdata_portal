import importlib
import sys
from datetime import datetime, timezone

import httpx
import pytest


def load_app(monkeypatch, tmp_path, enabled=False, token=""):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:19999|test-host\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("REQUEST_TIMEOUT", "1")
    monkeypatch.setenv("NETDATA_MANAGEMENT_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("NETDATA_MANAGEMENT_API_TOKEN", token)
    monkeypatch.delenv("NETDATA_MANAGEMENT_API_TOKEN_FILE", raising=False)

    for module_name in ["main", "alerts", "proxy", "notifications", "config", "http_client"]:
        sys.modules.pop(module_name, None)

    return importlib.import_module("main").app


def make_client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


class FakeManagementClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def get(self, url, params, headers):
        self.calls.append({"url": url, "params": params, "headers": headers})
        body = self.responses.pop(0)
        if isinstance(body, httpx.Response):
            return body
        return httpx.Response(200, text=body, request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_notifications_disabled_returns_503(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "ManagementDisabled"
    assert data["host"] == "test-host"


@pytest.mark.asyncio
async def test_notifications_enabled_with_empty_token_returns_503(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="")

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 503
    assert response.json()["error"] == "ManagementDisabled"


@pytest.mark.asyncio
async def test_notifications_invalid_hostname_returns_whitelist_error(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/unknown-host/notifications")

    assert response.status_code == 403
    assert response.json()["error"] == "HostNotAllowed"


@pytest.mark.asyncio
async def test_notifications_list_returns_raw_and_parsed_status(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    seed_host_status(reachable=True)
    raw = '{"all": true, "type": "SILENCE", "silencers": []}'
    fake_client = FakeManagementClient([raw])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 200
    assert response.json() == {"state": "silenced", "silenced": True, "raw": raw}
    assert fake_client.calls[0]["url"] == "http://127.0.0.1:19999/api/v1/manage/health"
    assert fake_client.calls[0]["params"] == {"cmd": "LIST"}
    assert fake_client.calls[0]["headers"] == {"X-Auth-Token": "secret-token"}
    assert "secret-token" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            '{"all": false, "type": "SILENCE", "silencers": [{"context": "load"}]}',
            {"state": "partial", "silenced": None},
        ),
        (
            '{"all": true, "type": "DISABLE", "silencers": []}',
            {"state": "disabled", "silenced": None},
        ),
    ],
)
async def test_notifications_list_parses_non_default_active_states(
    monkeypatch,
    tmp_path,
    raw,
    expected,
):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    seed_host_status(reachable=True)
    fake_client = FakeManagementClient([raw])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 200
    assert response.json() == {**expected, "raw": raw}


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_notifications_maps_upstream_auth_errors_to_management_forbidden(
    monkeypatch,
    tmp_path,
    status_code,
):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    seed_host_status(reachable=True)
    request = httpx.Request("GET", "http://127.0.0.1:19999/api/v1/manage/health")
    fake_client = FakeManagementClient([httpx.Response(status_code, request=request)])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 403
    data = response.json()
    assert data["error"] == "ManagementForbidden"
    assert "management API token" in data["detail"]


def seed_host_status(reachable):
    import alerts
    from models import HostStatus

    alerts.alert_poller.host_statuses["test-host"] = HostStatus(
        hostname="test-host",
        reachable=reachable,
        last_check=datetime.now(timezone.utc),
        alert_count=0,
    )


@pytest.mark.asyncio
async def test_notifications_unreachable_host_short_circuits(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    seed_host_status(reachable=False)
    fake_client = FakeManagementClient([])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 200
    assert response.json() == {
        "state": "unavailable",
        "silenced": None,
        "raw": "",
        "message": "Host is unreachable",
        "retryable": True,
    }
    assert fake_client.calls == []


@pytest.mark.asyncio
async def test_notifications_unchecked_host_short_circuits(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    fake_client = FakeManagementClient([])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 200
    assert response.json() == {
        "state": "unknown",
        "silenced": None,
        "raw": "",
        "message": "Host reachability is not checked yet",
        "retryable": True,
    }
    assert fake_client.calls == []


@pytest.mark.asyncio
async def test_notifications_management_disabled_wins_over_unreachable(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path)

    seed_host_status(reachable=False)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 503
    assert response.json()["error"] == "ManagementDisabled"


@pytest.mark.asyncio
async def test_notifications_reachable_host_uses_live_status(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    seed_host_status(reachable=True)
    raw = '{"all": false, "type": null, "silencers": []}'
    fake_client = FakeManagementClient([raw])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.get("/api/hosts/test-host/notifications")

    assert response.status_code == 200
    assert response.json() == {"state": "enabled", "silenced": False, "raw": raw}
    assert len(fake_client.calls) == 1


@pytest.mark.asyncio
async def test_notifications_silence_sends_command_header_and_refreshes(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    fake_client = FakeManagementClient([
        "All alarm notifications are silenced",
        '{"all": true, "type": "SILENCE", "silencers": []}',
    ])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.post("/api/hosts/test-host/notifications/silence")

    assert response.status_code == 200
    assert response.json()["state"] == "silenced"
    assert [call["params"] for call in fake_client.calls] == [{"cmd": "SILENCE ALL"}, {"cmd": "LIST"}]
    assert all(call["headers"] == {"X-Auth-Token": "secret-token"} for call in fake_client.calls)


@pytest.mark.asyncio
async def test_notifications_reset_sends_command_header_and_refreshes(monkeypatch, tmp_path):
    app = load_app(monkeypatch, tmp_path, enabled=True, token="secret-token")
    import notifications

    fake_client = FakeManagementClient([
        "All health checks and notifications are enabled",
        '{"all": false, "type": "SILENCE", "silencers": []}',
    ])
    monkeypatch.setattr(notifications, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.post("/api/hosts/test-host/notifications/reset")

    assert response.status_code == 200
    assert response.json() == {
        "state": "enabled",
        "silenced": False,
        "raw": '{"all": false, "type": "SILENCE", "silencers": []}',
    }
    assert [call["params"] for call in fake_client.calls] == [{"cmd": "RESET"}, {"cmd": "LIST"}]
    assert all(call["headers"] == {"X-Auth-Token": "secret-token"} for call in fake_client.calls)
