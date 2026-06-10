import json
from typing import Any

import httpx

from alerts import alert_poller
from config import config
from errors import (
    AggregatorException,
    BadGatewayError,
    GatewayTimeoutError,
    HostNotAllowedError,
    ManagementForbiddenError,
)
from http_client import get_http_client


LIST_CMD = "LIST"
SILENCE_ALL_CMD = "SILENCE ALL"
RESET_CMD = "RESET"


async def get_notification_status(hostname: str) -> dict[str, Any]:
    host = _get_host(hostname)
    _ensure_management_available(hostname)
    # Unknown/unreachable hosts answer from the alert poller cache instead of
    # spending a live management request on hosts that are not ready to answer.
    status = alert_poller.host_statuses.get(hostname)
    if status is None:
        return {
            "state": "unknown",
            "silenced": None,
            "raw": "",
            "message": "Host reachability is not checked yet",
            "retryable": True,
        }
    if not status.reachable:
        return {
            "state": "unavailable",
            "silenced": None,
            "raw": "",
            "message": "Host is unreachable",
            "retryable": True,
        }
    raw = await _call_management_api(hostname, str(host.url), LIST_CMD)
    return _parse_list_response(raw)


async def silence_notifications(hostname: str) -> dict[str, Any]:
    host = _get_host(hostname)
    _ensure_management_available(hostname)
    await _call_management_api(hostname, str(host.url), SILENCE_ALL_CMD)
    raw = await _call_management_api(hostname, str(host.url), LIST_CMD)
    return _parse_list_response(raw)


async def reset_notifications(hostname: str) -> dict[str, Any]:
    host = _get_host(hostname)
    _ensure_management_available(hostname)
    await _call_management_api(hostname, str(host.url), RESET_CMD)
    raw = await _call_management_api(hostname, str(host.url), LIST_CMD)
    return _parse_list_response(raw)


def _ensure_management_available(hostname: str) -> None:
    if not config.netdata_management_available:
        raise AggregatorException(
            503,
            "ManagementDisabled",
            "Netdata management API is disabled",
            host=hostname,
        )


def _get_host(hostname: str):
    host = config.get_host(hostname)
    if not host:
        raise HostNotAllowedError(hostname)
    return host


async def _call_management_api(hostname: str, host_url: str, command: str) -> str:
    target_url = f"{host_url.rstrip('/')}/api/v1/manage/health"
    try:
        response = await get_http_client().get(
            target_url,
            params={"cmd": command},
            headers={"X-Auth-Token": config.netdata_management_api_token},
        )
        response.raise_for_status()
        return response.text
    except httpx.TimeoutException:
        raise GatewayTimeoutError(hostname)
    except httpx.HTTPStatusError as e:
        status_code = e.response.status_code
        # 4xx from the management API are permission/availability problems
        # (403 bad token, 451/404 when the host doesn't expose health management);
        # they won't change on retry, so surface them as terminal forbidden.
        if 400 <= status_code < 500 and status_code not in {408, 429}:
            raise ManagementForbiddenError(hostname, status_code)
        raise BadGatewayError(hostname, f"management API returned {status_code}")
    except httpx.HTTPError as e:
        raise BadGatewayError(hostname, str(e))


def _parse_list_response(raw: str) -> dict[str, Any]:
    state = "unknown"
    silenced = None

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        all_alerts = data.get("all")
        silence_type = data.get("type")
        silencers = data.get("silencers")

        if all_alerts is False and silencers == []:
            state = "enabled"
            silenced = False
        elif silence_type == "SILENCE":
            state = "silenced" if all_alerts is True else "partial"
            silenced = True if all_alerts is True else None
        elif silence_type == "DISABLE":
            state = "disabled"
            silenced = None

    return {"state": state, "silenced": silenced, "raw": raw}
