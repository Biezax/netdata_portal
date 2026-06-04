import importlib
import sys

import pytest


@pytest.fixture
def config_module(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:19999\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.delenv("NETDATA_MANAGEMENT_API_TOKEN", raising=False)
    monkeypatch.delenv("NETDATA_MANAGEMENT_API_TOKEN_FILE", raising=False)

    sys.modules.pop("config", None)
    module = importlib.import_module("config")
    return module, hosts_file


def test_config_loads_from_hosts_file(config_module):
    module, _ = config_module
    assert len(module.config.hosts) == 1
    assert module.config.hosts[0].display_name == "127.0.0.1:19999"
    assert module.config.alert_poll_interval == 15
    assert module.config.request_timeout == 5
    assert module.config.netdata_management_available is False


@pytest.mark.parametrize("value", ["true", "1", "yes", "on"])
def test_config_parses_management_enabled_true_values(monkeypatch, tmp_path, value):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:19999\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("NETDATA_MANAGEMENT_ENABLED", value)
    monkeypatch.setenv("NETDATA_MANAGEMENT_API_TOKEN", "secret-token")

    sys.modules.pop("config", None)
    module = importlib.import_module("config")

    assert module.config.netdata_management_available is True


def test_config_requires_management_token(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:19999\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("NETDATA_MANAGEMENT_ENABLED", "true")
    monkeypatch.setenv("NETDATA_MANAGEMENT_API_TOKEN", "")
    monkeypatch.delenv("NETDATA_MANAGEMENT_API_TOKEN_FILE", raising=False)

    sys.modules.pop("config", None)
    module = importlib.import_module("config")

    assert module.config.netdata_management_available is False


def test_config_reads_management_token_from_file(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    token_file = tmp_path / "token"
    hosts_file.write_text("http://127.0.0.1:19999\n")
    token_file.write_text("secret-token\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("NETDATA_MANAGEMENT_ENABLED", "true")
    monkeypatch.setenv("NETDATA_MANAGEMENT_API_TOKEN", "")
    monkeypatch.setenv("NETDATA_MANAGEMENT_API_TOKEN_FILE", str(token_file))

    sys.modules.pop("config", None)
    module = importlib.import_module("config")

    assert module.config.netdata_management_available is True
    assert module.config.netdata_management_api_token == "secret-token"


def test_config_reload_preserves_on_error(config_module):
    module, hosts_file = config_module
    old_hosts = module.config.hosts
    hosts_file.write_text("invalid-url-without-scheme\n")

    result = module.config.reload_hosts()

    assert result is False
    assert module.config.hosts == old_hosts


def test_config_rejects_duplicate_display_names(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text(
        "http://127.0.0.1:19999|same\n"
        "http://127.0.0.1:29999|same\n"
    )
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))

    sys.modules.pop("config", None)
    with pytest.raises(ValueError, match="Duplicate host display name"):
        importlib.import_module("config")
