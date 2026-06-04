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

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
        self.port = int(os.getenv("PORT", "8000"))
        self.netdata_management_enabled = _parse_bool(
            os.getenv("NETDATA_MANAGEMENT_ENABLED", "false")
        )
        self.netdata_management_api_token = _read_secret("NETDATA_MANAGEMENT_API_TOKEN")
        self.hosts_file = _resolve_hosts_file()
        self._last_mtime = 0.0
        self.load_hosts()

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
