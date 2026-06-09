import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict
from models import Alert, AlertSeverity, HostStatus
from config import config
from http_client import get_http_client


class AlertPoller:
    def __init__(self):
        self.alerts: List[Alert] = []
        self.host_statuses: Dict[str, HostStatus] = {}
        self._polling_task = None

    async def start(self):
        if self._polling_task is None:
            self._polling_task = asyncio.create_task(self._poll_loop())

    async def stop(self):
        if self._polling_task is not None:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                pass
            self._polling_task = None

    async def _poll_loop(self):
        while True:
            await self.poll_alerts()
            await asyncio.sleep(config.alert_poll_interval)

    async def poll_alerts(self):
        current_hosts = {host.display_name for host in config.hosts}
        self.host_statuses = {
            hostname: status
            for hostname, status in self.host_statuses.items()
            if hostname in current_hosts
        }

        now = datetime.now(timezone.utc)
        hosts_to_poll = [host for host in config.hosts if self._should_poll(host.display_name, now)]

        # Cap concurrent fetches: each dead host pins a connect attempt and a
        # getaddrinfo executor thread, so unbounded gather over a dirty
        # inventory starves DNS/connections for healthy hosts too.
        semaphore = asyncio.Semaphore(config.alert_poll_concurrency)

        async def fetch_limited(host):
            async with semaphore:
                return await self._fetch_host_alerts(host)

        tasks = [fetch_limited(host) for host in hosts_to_poll]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_alerts = []
        for result in results:
            if isinstance(result, list):
                all_alerts.extend(result)

        self.alerts = self._sort_alerts(all_alerts)

    def _should_poll(self, hostname: str, now: datetime) -> bool:
        # Unreachable hosts keep their stale status and are retried at the
        # slower unreachable_poll_interval; _mark_unreachable refreshes
        # last_check on every real attempt, so the backoff window slides.
        status = self.host_statuses.get(hostname)
        if status is None or status.reachable or status.last_check is None:
            return True
        return (now - status.last_check).total_seconds() >= config.unreachable_poll_interval

    async def _fetch_host_alerts(self, host) -> List[Alert]:
        hostname = host.display_name
        alerts_url = f"{str(host.url).rstrip('/')}/api/v1/alarms"

        try:
            client = get_http_client()
            response = await client.get(alerts_url)
            response.raise_for_status()

            data = response.json()
            alarms = data.get("alarms", {})
            if not isinstance(alarms, dict):
                raise ValueError("Netdata alarms payload is malformed")

            self.host_statuses[hostname] = HostStatus(
                hostname=hostname,
                reachable=True,
                last_check=datetime.now(timezone.utc),
                error_message=None,
                alert_count=len(alarms),
            )

            return self._parse_netdata_alarms(hostname, alarms)

        except httpx.TimeoutException:
            self._mark_unreachable(hostname, "Connection timeout")
            return []
        except (httpx.HTTPError, ValueError, TypeError):
            self._mark_unreachable(hostname, "Connection error")
            return []

    def _parse_netdata_alarms(self, hostname: str, alarms: dict) -> List[Alert]:
        alerts = []
        for alert_id, alarm_data in alarms.items():
            if not isinstance(alarm_data, dict):
                continue

            if alarm_data.get("status") == "CLEAR":
                continue

            severity = self._map_severity(alarm_data.get("status", "INFO"))
            timestamp = datetime.fromtimestamp(alarm_data.get("updated", 0), tz=timezone.utc)

            alerts.append(
                Alert(
                    source_host=hostname,
                    alert_id=alert_id,
                    name=alarm_data.get("name", alert_id),
                    severity=severity,
                    status=alarm_data.get("status", "UNKNOWN"),
                    timestamp=timestamp,
                    value=alarm_data.get("value"),
                    message=alarm_data.get("info", "No details available"),
                )
            )

        return alerts

    def _mark_unreachable(self, hostname: str, error_message: str) -> None:
        self.host_statuses[hostname] = HostStatus(
            hostname=hostname,
            reachable=False,
            last_check=datetime.now(timezone.utc),
            error_message=error_message,
            alert_count=0,
        )

    def _map_severity(self, status: str) -> AlertSeverity:
        status_upper = status.upper()
        if status_upper == "CRITICAL":
            return AlertSeverity.CRITICAL
        elif status_upper == "WARNING":
            return AlertSeverity.WARNING
        else:
            return AlertSeverity.INFO

    def _sort_alerts(self, alerts: List[Alert]) -> List[Alert]:
        return sorted(alerts, key=lambda a: (a.severity.priority(), -a.timestamp.timestamp()))

    def get_alerts(self) -> List[Alert]:
        return self.alerts

    def get_host_statuses(self) -> Dict[str, HostStatus]:
        return self.host_statuses


alert_poller = AlertPoller()
