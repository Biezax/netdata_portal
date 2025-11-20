import asyncio
import httpx
from datetime import datetime
from typing import List, Dict
from models import Alert, AlertSeverity, HostStatus
from config import config


class AlertPoller:
    def __init__(self):
        self.alerts: List[Alert] = []
        self.host_statuses: Dict[str, HostStatus] = {}
        self._polling_task = None

    async def start(self):
        if self._polling_task is None:
            self._polling_task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        while True:
            await self.poll_alerts()
            await asyncio.sleep(config.alert_poll_interval)

    async def poll_alerts(self):
        tasks = [self._fetch_host_alerts(host) for host in config.hosts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_alerts = []
        for result in results:
            if isinstance(result, list):
                all_alerts.extend(result)

        self.alerts = self._sort_alerts(all_alerts)

    async def _fetch_host_alerts(self, host) -> List[Alert]:
        hostname = host.display_name
        alerts_url = f"{str(host.url).rstrip('/')}/api/v1/alarms"

        try:
            async with httpx.AsyncClient(timeout=config.request_timeout) as client:
                response = await client.get(alerts_url)
                response.raise_for_status()

                data = response.json()
                alarms = data.get("alarms", {})

                self.host_statuses[hostname] = HostStatus(
                    hostname=hostname,
                    reachable=True,
                    last_check=datetime.now(),
                    error_message=None,
                    alert_count=len(alarms),
                )

                return self._parse_netdata_alarms(hostname, alarms)

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as e:
            error_msg = f"Connection timeout" if isinstance(e, httpx.TimeoutException) else "Connection error"
            self.host_statuses[hostname] = HostStatus(
                hostname=hostname,
                reachable=False,
                last_check=datetime.now(),
                error_message=error_msg,
                alert_count=0,
            )
            return []

    def _parse_netdata_alarms(self, hostname: str, alarms: dict) -> List[Alert]:
        alerts = []
        for alert_id, alarm_data in alarms.items():
            if alarm_data.get("status") == "CLEAR":
                continue

            severity = self._map_severity(alarm_data.get("status", "INFO"))
            timestamp = datetime.fromtimestamp(alarm_data.get("updated", 0))

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
