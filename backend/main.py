from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from errors import AggregatorException, error_response
from config import config
from proxy import proxy_request
from alerts import alert_poller
from models import HostStatus
from typing import Dict
import os
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S',
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Netdata Multi-Instance Aggregator")

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
allowed_origins = ["http://localhost:3000"] if ENVIRONMENT == "development" else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting Netdata Aggregator with {len(config.hosts)} configured hosts")
    await alert_poller.start()
    asyncio.create_task(config.start_config_polling())
    logger.info("Netdata Aggregator started successfully")


@app.exception_handler(AggregatorException)
async def aggregator_exception_handler(request: Request, exc: AggregatorException):
    return error_response(exc)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "configured_hosts": len(config.hosts),
        "reachable_hosts": 0,
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
    host_statuses = alert_poller.get_host_statuses()

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


@app.api_route("/api/proxy/{hostname}/{path:path}", methods=["GET", "HEAD", "POST"])
async def proxy_endpoint(hostname: str, path: str, request: Request):
    return await proxy_request(hostname, path, request)
