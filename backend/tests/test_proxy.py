import importlib
import sys
from datetime import datetime, timezone

import httpx
import pytest


def load_app(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:1|test-host\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("REQUEST_TIMEOUT", "1")
    monkeypatch.setenv("AUTH_ENABLED", "false")

    for module_name in ["main", "alerts", "proxy", "notifications", "config", "http_client"]:
        sys.modules.pop(module_name, None)

    return importlib.import_module("main").app


@pytest.fixture
def app(monkeypatch, tmp_path):
    return load_app(monkeypatch, tmp_path)


def make_client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


@pytest.mark.asyncio
async def test_proxy_with_invalid_hostname_returns_403_json(app):
    async with make_client(app) as client:
        response = await client.get("/api/proxy/malicious-host/v3/")

    assert response.status_code == 403
    assert response.json()["error"] == "HostNotAllowed"


@pytest.mark.asyncio
async def test_proxy_rejects_path_traversal(app):
    async with make_client(app) as client:
        response = await client.get("/api/proxy/test-host/%2E%2E/etc/passwd")

    assert response.status_code == 400
    assert response.json()["detail"] == "Path traversal not allowed"


@pytest.mark.asyncio
async def test_proxy_redirects_dashboard_without_trailing_slash(app):
    async with make_client(app) as client:
        response = await client.get("/api/proxy/test-host/v3", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/api/proxy/test-host/v3/"


@pytest.mark.asyncio
async def test_proxy_does_not_follow_upstream_redirects(app, monkeypatch):
    import proxy

    class UpstreamResponse:
        status_code = 302
        headers = {"location": "/relative-path"}

        async def aiter_bytes(self):
            yield b""

        async def aclose(self):
            pass

    class FakeClient:
        follow_redirects = None
        stream = None

        def build_request(self, method, target_url, **kwargs):
            return object()

        async def send(self, request, stream, follow_redirects):
            self.stream = stream
            self.follow_redirects = follow_redirects
            return UpstreamResponse()

    fake_client = FakeClient()
    monkeypatch.setattr(proxy, "get_http_client", lambda: fake_client)

    response = await proxy.proxy_request("test-host", "api/v1/data")

    assert response.status_code == 302
    assert fake_client.stream is True
    assert fake_client.follow_redirects is False


@pytest.mark.asyncio
async def test_proxy_redirects_external_upstream_redirects_to_dashboard(app, monkeypatch):
    import proxy

    class UpstreamResponse:
        status_code = 302
        headers = {"location": "https://app.netdata.cloud/"}
        closed = False

        async def aiter_bytes(self):
            yield b""

        async def aclose(self):
            self.closed = True

    class FakeClient:
        follow_redirects = None
        response = UpstreamResponse()

        def build_request(self, method, target_url, **kwargs):
            return object()

        async def send(self, request, stream, follow_redirects):
            self.follow_redirects = follow_redirects
            return self.response

    fake_client = FakeClient()
    monkeypatch.setattr(proxy, "get_http_client", lambda: fake_client)

    async with make_client(app) as client:
        response = await client.get("/api/proxy/test-host/api/v1/data")

    assert response.status_code == 307
    assert response.headers["location"] == "/api/proxy/test-host/v3/"
    assert fake_client.follow_redirects is False
    assert fake_client.response.closed is True


@pytest.mark.asyncio
async def test_get_hosts_returns_configured_hosts(app):
    from alerts import alert_poller
    from models import Alert, AlertSeverity

    alert_poller.alerts = [
        Alert(
            source_host="test-host",
            alert_id="crit",
            name="Critical",
            severity=AlertSeverity.CRITICAL,
            status="CRITICAL",
            timestamp=datetime.now(timezone.utc),
            message="critical alert",
        ),
        Alert(
            source_host="test-host",
            alert_id="warn",
            name="Warning",
            severity=AlertSeverity.WARNING,
            status="WARNING",
            timestamp=datetime.now(timezone.utc),
            message="warning alert",
        ),
    ]

    async with make_client(app) as client:
        response = await client.get("/api/hosts")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["hosts"][0]["name"] == "test-host"
    assert data["hosts"][0]["status"]["critical_count"] == 1
    assert data["hosts"][0]["status"]["warning_count"] == 1
