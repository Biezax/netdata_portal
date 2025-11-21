import os
import asyncio
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from pydantic import ValidationError
from models import HostConfig

load_dotenv()


class Config:
    def __init__(self):
        self.hosts: List[HostConfig] = []
        self.alert_poll_interval = int(os.getenv("ALERT_POLL_INTERVAL", "15"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "5"))
        self.port = int(os.getenv("PORT", "8000"))
        self.hosts_file = Path("config/hosts.txt")
        self._last_mtime = 0.0
        self.load_hosts()

    def load_hosts(self) -> None:
        if not self.hosts_file.exists():
            raise ValueError(f"Hosts file not found: {self.hosts_file}")

        lines = self.hosts_file.read_text().strip().split("\n")
        host_urls = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            host_urls.append(line)

        if not host_urls:
            raise ValueError(f"No valid hosts found in {self.hosts_file}")

        self.hosts = []
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
                    display_name = parsed.hostname or parsed.netloc or "unknown"

                self.hosts.append(
                    HostConfig(url=url_part, display_name=display_name)
                )
            except ValidationError as e:
                raise ValueError(f"Invalid URL '{url_str}': {e}")

        self._last_mtime = self.hosts_file.stat().st_mtime

    def reload_hosts(self) -> bool:
        try:
            old_hosts = self.hosts
            self.load_hosts()
            print(f"Config reloaded successfully: {len(self.hosts)} hosts")
            return True
        except Exception as e:
            self.hosts = old_hosts
            print(f"Config reload failed, keeping old config: {e}")
            return False

    async def start_config_polling(self):
        print(f"Config polling started for {self.hosts_file}")
        while True:
            await asyncio.sleep(5)
            try:
                if not self.hosts_file.exists():
                    continue

                current_mtime = self.hosts_file.stat().st_mtime
                if current_mtime != self._last_mtime:
                    print(f"{self.hosts_file} changed, reloading config...")
                    self.reload_hosts()
            except Exception as e:
                print(f"Error checking config file: {e}")


config = Config()
