from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from fastapi import FastAPI, Request
import httpx
from errors import AggregatorException, error_response
from config import config
from proxy import proxy_request
from alerts import alert_poller
from notifications import get_notification_status, reset_notifications, silence_notifications
from models import HostStatus
from http_client import set_http_client
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S',
)

logger = logging.getLogger(__name__)
startup_time = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Netdata Aggregator with %s configured hosts", len(config.hosts))
    config_task = None
    async with httpx.AsyncClient(timeout=config.request_timeout, follow_redirects=False) as client:
        set_http_client(client)
        await alert_poller.start()
        config_task = asyncio.create_task(config.start_config_polling())
        logger.info("Netdata Aggregator started successfully")
        try:
            yield
        finally:
            await alert_poller.stop()
            if config_task:
                config_task.cancel()
                with suppress(asyncio.CancelledError):
                    await config_task
            set_http_client(None)


# Auto docs are served outside /api/, so the auth gate would leave them public; disable
# them (and the OpenAPI schema) entirely when auth is on.
app = FastAPI(
    title="Netdata Multi-Instance Aggregator",
    lifespan=lifespan,
    docs_url=None if config.auth_enabled else "/docs",
    redoc_url=None if config.auth_enabled else "/redoc",
    openapi_url=None if config.auth_enabled else "/openapi.json",
)

# Keep after any other add_middleware calls: setup_auth adds SessionMiddleware, which must
# wrap the auth gate so request.session is decoded before the gate runs.
if config.auth_enabled:
    from auth import setup_auth

    setup_auth(app)


@app.exception_handler(AggregatorException)
async def aggregator_exception_handler(request: Request, exc: AggregatorException):
    wants_html = (
        request.url.path.startswith("/api/proxy/")
        and "text/html" in request.headers.get("accept", "")
    )
    return error_response(exc, html=wants_html)


@app.get("/health")
async def health_check():
    host_names = {host.display_name for host in config.hosts}
    host_statuses = alert_poller.get_host_statuses()
    reachable_hosts = sum(
        1
        for hostname in host_names
        if host_statuses.get(hostname) and host_statuses[hostname].reachable
    )

    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": int((datetime.now(timezone.utc) - startup_time).total_seconds()),
        "configured_hosts": len(config.hosts),
        "reachable_hosts": reachable_hosts,
    }


@app.get("/api/hosts")
async def get_hosts():
    hosts_list = []
    host_statuses = alert_poller.get_host_statuses()

    for host in config.hosts:
        status = host_statuses.get(
            host.display_name,
            HostStatus(hostname=host.display_name, reachable=False, alert_count=0),
        )
        hosts_list.append({
            "name": host.display_name,
            "url": str(host.url),
            "status": {
                "reachable": status.reachable,
                "last_check": status.last_check.isoformat() if status.last_check else None,
                "alert_count": status.alert_count,
                "error_message": status.error_message,
            },
        })

    healthy_count = sum(1 for h in hosts_list if h["status"]["reachable"])
    return {"hosts": hosts_list, "total": len(hosts_list), "healthy": healthy_count}


@app.get("/api/alerts")
async def get_alerts():
    alerts = alert_poller.get_alerts()
    host_names = {host.display_name for host in config.hosts}
    host_statuses = {
        hostname: status
        for hostname, status in alert_poller.get_host_statuses().items()
        if hostname in host_names
    }

    alerts_data = [
        {
            "source_host": alert.source_host,
            "alert_id": alert.alert_id,
            "name": alert.name,
            "severity": alert.severity.value,
            "status": alert.status,
            "timestamp": alert.timestamp.isoformat(),
            "value": alert.value,
            "message": alert.message,
        }
        for alert in alerts
    ]

    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for alert in alerts:
        severity_counts[alert.severity.value] += 1

    unreachable_hosts = [
        hostname for hostname, status in host_statuses.items() if not status.reachable
    ]

    return {
        "alerts": alerts_data,
        "total": len(alerts_data),
        "by_severity": severity_counts,
        "unreachable_hosts": unreachable_hosts,
    }


@app.get("/api/hosts/{hostname}/notifications")
async def host_notification_status(hostname: str):
    return await get_notification_status(hostname)


@app.post("/api/hosts/{hostname}/notifications/silence")
async def host_notification_silence(hostname: str):
    return await silence_notifications(hostname)


@app.post("/api/hosts/{hostname}/notifications/reset")
async def host_notification_reset(hostname: str):
    return await reset_notifications(hostname)


@app.api_route("/api/proxy/{hostname}/{path:path}", methods=["GET", "HEAD", "POST"])
async def proxy_endpoint(hostname: str, path: str, request: Request):
    return await proxy_request(hostname, path, request)
