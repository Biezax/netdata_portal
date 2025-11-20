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


def test_get_alerts_endpoint_exists(client):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data
    assert "total" in data
    assert "by_severity" in data
    assert "unreachable_hosts" in data


def test_alerts_have_severity_counts(client):
    response = client.get("/api/alerts")
    data = response.json()
    assert "critical" in data["by_severity"]
    assert "warning" in data["by_severity"]
    assert "info" in data["by_severity"]
