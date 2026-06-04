import importlib
import sys

import httpx
import pytest


def load_app(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:1|test-host\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("REQUEST_TIMEOUT", "1")

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
