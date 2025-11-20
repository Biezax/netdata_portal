import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["NETDATA_HOSTS"] = "http://test-host:19999"


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_proxy_with_invalid_hostname_returns_403(client):
    response = client.get("/api/proxy/malicious-host/v3/")
    assert response.status_code == 403
    assert "HostNotAllowed" in response.json()["error"]


def test_proxy_rejects_path_traversal(client):
    response = client.get("/api/proxy/test-host/../etc/passwd")
    assert response.status_code == 502
    assert "Path traversal not allowed" in response.json()["detail"]


def test_get_hosts_returns_configured_hosts(client):
    response = client.get("/api/hosts")
    assert response.status_code == 200
    data = response.json()
    assert "hosts" in data
    assert data["total"] == 1
    assert data["hosts"][0]["name"] == "test-host"
