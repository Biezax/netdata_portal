import os
import asyncio
import logging
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import ValidationError
from models import HostConfig

load_dotenv()
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parent


def _resolve_project_root() -> Path:
    configured_root = os.getenv("PROJECT_ROOT", "")
    if configured_root:
        return Path(configured_root).expanduser().resolve()

    repo_root = BACKEND_DIR.parent
    if (repo_root / "config").exists():
        return repo_root

    logger.warning("Config directory not found under %s; using %s as project root", repo_root, BACKEND_DIR)
    return BACKEND_DIR


PROJECT_ROOT = _resolve_project_root()


def _resolve_hosts_file() -> Path:
    hosts_file = os.getenv("HOSTS_FILE", "config/hosts.txt")
    path = Path(hosts_file).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "on"}


def _read_secret(name: str) -> str:
    value = os.getenv(name, "")
    if value:
        return value

    secret_file = os.getenv(f"{name}_FILE", "")
    if not secret_file:
        return ""

    try:
        return Path(secret_file).expanduser().read_text().strip()
    except OSError as e:
        logger.warning("Could not read secret file from %s: %s", f"{name}_FILE", e)
        return ""


class Config:
    def __init__(self):
        self.hosts: List[HostConfig] = []
        self.alert_poll_interval = int(os.getenv("ALERT_POLL_INTERVAL", "15"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "5"))
        self.connect_timeout = float(os.getenv("CONNECT_TIMEOUT", "2"))
        self.alert_poll_concurrency = max(1, int(os.getenv("ALERT_POLL_CONCURRENCY", "10")))
        self.unreachable_poll_interval = int(os.getenv("UNREACHABLE_POLL_INTERVAL", "60"))
        self.port = int(os.getenv("PORT", "8000"))
        self.netdata_management_enabled = _parse_bool(
            os.getenv("NETDATA_MANAGEMENT_ENABLED", "false")
        )
        self.netdata_management_api_token = _read_secret("NETDATA_MANAGEMENT_API_TOKEN")

        self.auth_enabled = _parse_bool(os.getenv("AUTH_ENABLED", "false"))
        self.ldap_url = os.getenv("LDAP_URL", "")
        self.ldap_start_tls = _parse_bool(os.getenv("LDAP_START_TLS", "false"))
        self.ldap_tls_validate = _parse_bool(os.getenv("LDAP_TLS_VALIDATE", "true"))
        self.ldap_ca_cert_file = os.getenv("LDAP_CA_CERT_FILE", "")
        self.ldap_connect_timeout = int(os.getenv("LDAP_CONNECT_TIMEOUT", "5"))
        self.ldap_bind_dn = os.getenv("LDAP_BIND_DN", "")
        self.ldap_bind_password = _read_secret("LDAP_BIND_PASSWORD")
        self.ldap_user_base_dn = os.getenv("LDAP_USER_BASE_DN", "")
        self.ldap_user_filter = os.getenv("LDAP_USER_FILTER", "(uid={username})")
        self.ldap_display_name_attr = os.getenv("LDAP_DISPLAY_NAME_ATTR", "cn")
        self.ldap_required_group = os.getenv("LDAP_REQUIRED_GROUP", "")
        self.ldap_group_attr = os.getenv("LDAP_GROUP_ATTR", "memberOf")
        self.session_secret = _read_secret("SESSION_SECRET")
        self.session_ttl = int(os.getenv("SESSION_TTL", "28800"))
        self.session_cookie_secure = _parse_bool(os.getenv("SESSION_COOKIE_SECURE", "false"))
        self.session_cookie_samesite = os.getenv("SESSION_COOKIE_SAMESITE", "lax")

        self.hosts_file = _resolve_hosts_file()
        logger.info("Using project root %s and hosts file %s", PROJECT_ROOT, self.hosts_file)
        self._last_mtime = 0.0
        self.load_hosts()

        if self.auth_enabled:
            self._validate_auth_config()

    def _validate_auth_config(self) -> None:
        required = {
            "LDAP_URL": self.ldap_url,
            "LDAP_USER_BASE_DN": self.ldap_user_base_dn,
            "LDAP_REQUIRED_GROUP": self.ldap_required_group,
            "SESSION_SECRET": self.session_secret,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(
                f"AUTH_ENABLED is set but required variables are missing: {', '.join(missing)}"
            )
        if "{username}" not in self.ldap_user_filter:
            raise ValueError("LDAP_USER_FILTER must contain the {username} placeholder")

    @property
    def netdata_management_available(self) -> bool:
        return self.netdata_management_enabled and bool(self.netdata_management_api_token)

    def load_hosts(self) -> None:
        if not self.hosts_file.exists():
            raise ValueError(f"Hosts file not found: {self.hosts_file}")

        lines = self.hosts_file.read_text().splitlines()
        host_urls = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            host_urls.append(line)

        if not host_urls:
            raise ValueError(f"No valid hosts found in {self.hosts_file}")

        loaded_hosts = []
        seen_names = set()
        for url_str in host_urls:
            try:
                from urllib.parse import urlparse

                if "|" in url_str:
                    url_part, display_name = url_str.split("|", 1)
                    url_part = url_part.strip()
                    display_name = display_name.strip()
                else:
                    url_part = url_str
                    parsed = urlparse(url_str)
                    display_name = parsed.netloc or parsed.hostname or "unknown"

                if not display_name:
                    raise ValueError("Display name cannot be empty")
                if display_name in seen_names:
                    raise ValueError(f"Duplicate host display name: {display_name}")

                seen_names.add(display_name)
                loaded_hosts.append(HostConfig(url=url_part, display_name=display_name))
            except ValidationError as e:
                raise ValueError(f"Invalid URL '{url_str}': {e}")

        self.hosts = loaded_hosts
        self._last_mtime = self.hosts_file.stat().st_mtime

    def get_host(self, hostname: str) -> HostConfig | None:
        for host in self.hosts:
            if host.display_name == hostname:
                return host
        return None

    def reload_hosts(self) -> bool:
        try:
            old_hosts = self.hosts
            self.load_hosts()
            logger.info("Config reloaded successfully: %s hosts", len(self.hosts))
            return True
        except Exception as e:
            self.hosts = old_hosts
            logger.error("Config reload failed, keeping old config: %s", e)
            return False

    async def start_config_polling(self):
        logger.info("Config polling started for %s", self.hosts_file)
        while True:
            await asyncio.sleep(5)
            try:
                if not self.hosts_file.exists():
                    continue

                current_mtime = self.hosts_file.stat().st_mtime
                if current_mtime != self._last_mtime:
                    logger.info("%s changed, reloading config", self.hosts_file)
                    self.reload_hosts()
            except Exception as e:
                logger.error("Error checking config file: %s", e)


config = Config()
