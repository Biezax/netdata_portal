import importlib
import sys

import httpx
import pytest


def load_auth_app(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:1|test-host\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("REQUEST_TIMEOUT", "1")
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("LDAP_URL", "ldap://localhost:389")
    monkeypatch.setenv("LDAP_USER_BASE_DN", "ou=people,dc=example,dc=com")
    monkeypatch.setenv("LDAP_REQUIRED_GROUP", "cn=admins,ou=groups,dc=example,dc=com")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    for module_name in ["main", "alerts", "proxy", "notifications", "config", "http_client", "auth"]:
        sys.modules.pop(module_name, None)

    main = importlib.import_module("main")
    return main.app, sys.modules["auth"]


def make_client(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    )


# --- LDAP bind unit tests -------------------------------------------------

class _FakeAttr:
    def __init__(self, values):
        self.values = list(values)
        self.value = values[0] if values else None


class _FakeEntry:
    entry_dn = "uid=alice,ou=people,dc=example,dc=com"

    def __init__(self, attrs):
        self._attrs = attrs

    def __contains__(self, key):
        return key in self._attrs

    def __getitem__(self, key):
        return _FakeAttr(self._attrs[key])


def _fake_connection_factory(groups):
    captured = {}

    class _FakeConnection:
        def __init__(self, server, user=None, password=None, **kwargs):
            self.entries = []

        def search(self, search_base, search_filter, attributes):
            captured["filter"] = search_filter
            self.entries = [_FakeEntry({"cn": ["Alice"], "memberOf": list(groups)})]

        def unbind(self):
            pass

    return _FakeConnection, captured


@pytest.mark.asyncio
async def test_empty_password_is_rejected(monkeypatch, tmp_path):
    _, auth = load_auth_app(monkeypatch, tmp_path)
    assert await auth.authenticate("alice", "") is None
    assert await auth.authenticate("", "secret") is None


@pytest.mark.asyncio
async def test_username_is_escaped_in_filter(monkeypatch, tmp_path):
    _, auth = load_auth_app(monkeypatch, tmp_path)
    conn, captured = _fake_connection_factory(["cn=admins,ou=groups,dc=example,dc=com"])
    monkeypatch.setattr(auth, "Server", lambda *a, **k: object())
    monkeypatch.setattr(auth, "Connection", conn)

    user = await auth.authenticate("alice*)(uid=*", "secret")

    assert user is not None
    # The injected * ) ( must all be escaped, leaving no raw filter metacharacters.
    assert "\\2a" in captured["filter"]  # *
    assert "\\28" in captured["filter"]  # (
    assert "\\29" in captured["filter"]  # )
    assert "*)(" not in captured["filter"]


@pytest.mark.asyncio
async def test_user_outside_required_group_is_denied(monkeypatch, tmp_path):
    _, auth = load_auth_app(monkeypatch, tmp_path)
    conn, _ = _fake_connection_factory(["cn=others,ou=groups,dc=example,dc=com"])
    monkeypatch.setattr(auth, "Server", lambda *a, **k: object())
    monkeypatch.setattr(auth, "Connection", conn)

    assert await auth.authenticate("alice", "secret") is None


# --- Endpoint / session gate tests ---------------------------------------

@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(monkeypatch, tmp_path):
    app, _ = load_auth_app(monkeypatch, tmp_path)
    async with make_client(app) as client:
        assert (await client.get("/api/hosts")).status_code == 401
        assert (await client.get("/health")).status_code == 200
        # Auto docs / schema must not be exposed when auth is enabled.
        assert (await client.get("/openapi.json")).status_code == 404
        assert (await client.get("/docs")).status_code == 404


@pytest.mark.asyncio
async def test_login_logout_flow(monkeypatch, tmp_path):
    app, auth = load_auth_app(monkeypatch, tmp_path)

    async def fake_authenticate(username, password):
        if password == "good":
            return auth.AuthUser(username=username, display_name="Tester")
        return None

    monkeypatch.setattr(auth, "authenticate", fake_authenticate)

    async with make_client(app) as client:
        assert (await client.post("/api/auth/login", json={"username": "u", "password": "bad"})).status_code == 401

        ok = await client.post("/api/auth/login", json={"username": "u", "password": "good"})
        assert ok.status_code == 200
        assert ok.json()["user"] == "u"

        assert (await client.get("/api/hosts")).status_code == 200
        assert (await client.get("/api/auth/me")).json()["user"] == "u"

        assert (await client.post("/api/auth/logout")).status_code == 204
        assert (await client.get("/api/hosts")).status_code == 401


def test_missing_config_fails_fast(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:1|test-host\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.delenv("LDAP_URL", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)

    sys.modules.pop("config", None)
    with pytest.raises(ValueError, match="AUTH_ENABLED"):
        importlib.import_module("config")


@pytest.mark.asyncio
async def test_auth_disabled_leaves_api_open(monkeypatch, tmp_path):
    hosts_file = tmp_path / "hosts.txt"
    hosts_file.write_text("http://127.0.0.1:1|test-host\n")
    monkeypatch.setenv("HOSTS_FILE", str(hosts_file))
    monkeypatch.delenv("AUTH_ENABLED", raising=False)

    for module_name in ["main", "alerts", "proxy", "notifications", "config", "http_client", "auth"]:
        sys.modules.pop(module_name, None)
    app = importlib.import_module("main").app

    async with make_client(app) as client:
        assert (await client.get("/api/hosts")).status_code == 200
        assert (await client.get("/api/auth/me")).status_code == 404


@pytest.mark.asyncio
async def test_ambiguous_lookup_is_denied(monkeypatch, tmp_path):
    _, auth = load_auth_app(monkeypatch, tmp_path)

    class _MultiConnection:
        def __init__(self, *args, **kwargs):
            self.entries = []

        def search(self, search_base, search_filter, attributes):
            entry = _FakeEntry({"cn": ["A"], "memberOf": ["cn=admins,ou=groups,dc=example,dc=com"]})
            self.entries = [entry, entry]

        def unbind(self):
            pass

    monkeypatch.setattr(auth, "Server", lambda *a, **k: object())
    monkeypatch.setattr(auth, "Connection", _MultiConnection)

    assert await auth.authenticate("alice", "secret") is None
