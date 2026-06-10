import asyncio
import importlib
import sys
from datetime import datetime, timedelta, timezone

import httpx
import pytest


def load_app(monkeypatch, tmp_path, hosts="http://127.0.0.1:1|test-host\n"):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text(hosts)
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
async def test_get_alerts_endpoint_exists(app):
    async with make_client(app) as client:
        response = await client.get("/api/alerts")

    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total" in data
    assert "by_severity" in data
    assert "unreachable_hosts" in data


@pytest.mark.asyncio
async def test_alerts_have_severity_counts(app):
    async with make_client(app) as client:
        response = await client.get("/api/alerts")

    data = response.json()
    assert "critical" in data["by_severity"]
    assert "warning" in data["by_severity"]
    assert "info" in data["by_severity"]


class FakeAlarmsClient:
    def __init__(self):
        self.calls = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def get(self, url):
        self.calls.append(url)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        self.in_flight -= 1
        return httpx.Response(200, json={"alarms": {}}, request=httpx.Request("GET", url))


@pytest.mark.asyncio
async def test_poll_alerts_skips_recently_unreachable_host(monkeypatch, tmp_path):
    load_app(monkeypatch, tmp_path)
    import alerts
    from models import HostStatus

    status = HostStatus(
        hostname="test-host",
        reachable=False,
        last_check=datetime.now(timezone.utc),
        alert_count=0,
    )
    alerts.alert_poller.host_statuses["test-host"] = status
    fake_client = FakeAlarmsClient()
    monkeypatch.setattr(alerts, "get_http_client", lambda: fake_client)

    await alerts.alert_poller.poll_alerts()

    assert fake_client.calls == []
    assert alerts.alert_poller.host_statuses["test-host"] is status


@pytest.mark.asyncio
async def test_poll_alerts_retries_unreachable_host_after_interval(monkeypatch, tmp_path):
    load_app(monkeypatch, tmp_path)
    import alerts
    from models import HostStatus

    alerts.alert_poller.host_statuses["test-host"] = HostStatus(
        hostname="test-host",
        reachable=False,
        last_check=datetime.now(timezone.utc) - timedelta(seconds=120),
        alert_count=0,
    )
    fake_client = FakeAlarmsClient()
    monkeypatch.setattr(alerts, "get_http_client", lambda: fake_client)

    await alerts.alert_poller.poll_alerts()

    assert fake_client.calls == ["http://127.0.0.1:1/api/v1/alarms"]
    assert alerts.alert_poller.host_statuses["test-host"].reachable is True


@pytest.mark.asyncio
async def test_poll_alerts_caps_concurrency(monkeypatch, tmp_path):
    monkeypatch.setenv("ALERT_POLL_CONCURRENCY", "2")
    hosts = "".join(f"http://127.0.0.1:{port}|host-{port}\n" for port in range(1, 6))
    load_app(monkeypatch, tmp_path, hosts=hosts)
    import alerts

    fake_client = FakeAlarmsClient()
    monkeypatch.setattr(alerts, "get_http_client", lambda: fake_client)

    await alerts.alert_poller.poll_alerts()

    assert len(fake_client.calls) == 5
    assert fake_client.max_in_flight == 2
