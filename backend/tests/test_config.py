import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ["NETDATA_HOSTS"] = "http://test-host:19999"


def test_config_loads_from_env():
    from config import config
    assert len(config.hosts) > 0
    assert config.alert_poll_interval == 15
    assert config.request_timeout == 5


def test_config_reload_preserves_on_error():
    from config import config
    old_hosts = config.hosts
    os.environ["NETDATA_HOSTS"] = "invalid-url-without-scheme"
    result = config.reload_hosts()
    assert result is False
    assert config.hosts == old_hosts
