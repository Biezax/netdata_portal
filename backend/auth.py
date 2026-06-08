import asyncio
import logging
import ssl
from dataclasses import dataclass

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from ldap3 import AUTO_BIND_NO_TLS, AUTO_BIND_TLS_BEFORE_BIND, BASE, NONE, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from ldap3.utils.conv import escape_filter_chars

from config import config

logger = logging.getLogger(__name__)

SESSION_COOKIE = "nd_session"
PUBLIC_PATHS = {"/health", "/api/auth/login", "/api/auth/logout", "/api/auth/me"}


@dataclass
class AuthUser:
    username: str
    display_name: str


def _build_server(use_ssl: bool) -> Server:
    tls = None
    if use_ssl or config.ldap_start_tls:
        validate = ssl.CERT_REQUIRED if config.ldap_tls_validate else ssl.CERT_NONE
        tls = Tls(validate=validate, ca_certs_file=config.ldap_ca_cert_file or None)
    return Server(
        config.ldap_url,
        use_ssl=use_ssl,
        tls=tls,
        get_info=NONE,
        connect_timeout=config.ldap_connect_timeout,
    )


def _entry_values(entry, attr: str) -> list[str]:
    return [str(value) for value in entry[attr].values] if attr in entry else []


def _entry_value(entry, attr: str, fallback: str) -> str:
    if attr in entry and entry[attr].value:
        return str(entry[attr].value)
    return fallback


def _is_required_group(groups: list[str]) -> bool:
    required_group = config.ldap_required_group.strip().lower()
    return required_group in {group.strip().lower() for group in groups}


def _split_first_dn_component(dn: str) -> tuple[str, str]:
    escaped = False
    for index, char in enumerate(dn):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == ",":
            return dn[:index], dn[index + 1 :]
    return dn, ""


def _is_member_by_group_search(conn: Connection, user_dn: str) -> bool:
    group_dn = config.ldap_required_group.strip()
    rdn, parent_dn = _split_first_dn_component(group_dn)
    member_filter = f"(member={escape_filter_chars(user_dn)})"

    if parent_dn and "=" in rdn:
        attr, value = rdn.split("=", 1)
        search_base = parent_dn
        search_filter = (
            f"(&({attr.strip()}={escape_filter_chars(value.strip())}){member_filter})"
        )
    else:
        search_base = group_dn
        search_filter = member_filter

    conn.search(
        search_base=search_base,
        search_filter=search_filter,
        attributes=[],
    )
    return bool(conn.entries)


def _authenticate_sync(username: str, password: str) -> AuthUser | None:
    use_ssl = config.ldap_url.lower().startswith("ldaps://")
    auto_bind = (
        AUTO_BIND_TLS_BEFORE_BIND if config.ldap_start_tls and not use_ssl else AUTO_BIND_NO_TLS
    )
    server = _build_server(use_ssl)

    # Service or anonymous bind is only used to resolve the user's DN.
    search_conn = Connection(
        server,
        user=config.ldap_bind_dn or None,
        password=config.ldap_bind_password or None,
        auto_bind=auto_bind,
        receive_timeout=config.ldap_connect_timeout,
    )
    try:
        search_filter = config.ldap_user_filter.replace("{username}", escape_filter_chars(username))
        search_conn.search(
            search_base=config.ldap_user_base_dn,
            search_filter=search_filter,
            attributes=[],
        )
        if len(search_conn.entries) != 1:
            logger.info("LDAP lookup returned %d entries", len(search_conn.entries))
            return None
        entry = search_conn.entries[0]
        user_dn = entry.entry_dn
    finally:
        search_conn.unbind()

    # Re-bind as the user before reading group membership.
    try:
        user_conn = Connection(
            server,
            user=user_dn,
            password=password,
            auto_bind=auto_bind,
            receive_timeout=config.ldap_connect_timeout,
        )
    except LDAPException:
        return None
    try:
        user_conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            search_scope=BASE,
            attributes=[config.ldap_display_name_attr, config.ldap_group_attr],
        )
        entry = user_conn.entries[0] if user_conn.entries else None
        groups = _entry_values(entry, config.ldap_group_attr) if entry else []
        display_name = _entry_value(entry, config.ldap_display_name_attr, username) if entry else username

        if not _is_required_group(groups) and not _is_member_by_group_search(user_conn, user_dn):
            logger.info("Authenticated user is not a member of the required group")
            return None
    finally:
        user_conn.unbind()

    return AuthUser(username=username, display_name=display_name)


async def authenticate(username: str, password: str) -> AuthUser | None:
    # Empty password yields an anonymous bind that "succeeds" on most servers; reject up front.
    if not username or not password:
        return None
    try:
        return await asyncio.to_thread(_authenticate_sync, username, password)
    except LDAPException as e:
        logger.warning("LDAP authentication error: %s", e)
        return None


def setup_auth(app: FastAPI) -> None:
    from starlette.middleware.sessions import SessionMiddleware

    if not config.ldap_bind_dn:
        logger.info("LDAP_BIND_DN is empty; initial user lookup uses an anonymous bind")
    if not config.session_cookie_secure:
        logger.warning("SESSION_COOKIE_SECURE is false; enable it when serving over HTTPS")

    @app.post("/api/auth/login")
    async def login(request: Request):
        data = await request.json()
        user = await authenticate(data.get("username", ""), data.get("password", ""))
        if not user:
            return JSONResponse(
                {"error": "Unauthorized", "detail": "Invalid credentials"}, status_code=401
            )
        request.session.clear()
        request.session["user"] = user.username
        request.session["display_name"] = user.display_name
        return {"user": user.username, "display_name": user.display_name}

    @app.post("/api/auth/logout")
    async def logout(request: Request):
        request.session.clear()
        return Response(status_code=204)

    @app.get("/api/auth/me")
    async def me(request: Request):
        user = request.session.get("user")
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return {"user": user, "display_name": request.session.get("display_name", user)}

    @app.middleware("http")
    async def require_auth(request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS or not path.startswith("/api/"):
            return await call_next(request)
        if request.session.get("user"):
            return await call_next(request)
        return JSONResponse(
            {"error": "Unauthorized", "detail": "Authentication required"}, status_code=401
        )

    # Added last so it wraps require_auth: request.session must be populated before the gate runs.
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.session_secret,
        session_cookie=SESSION_COOKIE,
        max_age=config.session_ttl,
        https_only=config.session_cookie_secure,
        same_site=config.session_cookie_samesite,
    )
