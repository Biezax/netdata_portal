import httpx
from typing import Optional
from fastapi import Response, Request
from fastapi.responses import StreamingResponse
from config import config
from errors import HostNotAllowedError, GatewayTimeoutError, BadGatewayError


async def proxy_request(hostname: str, path: str, request: Request = None) -> Response:
    host_config = _validate_hostname(hostname)
    if not host_config:
        raise HostNotAllowedError(hostname)

    if ".." in path or path.startswith("/"):
        raise BadGatewayError(hostname, "Path traversal not allowed")

    target_url = f"{str(host_config.url).rstrip('/')}/{path.lstrip('/')}"

    if request and request.query_params:
        target_url = f"{target_url}?{str(request.query_params)}"

    headers = {
        "Accept": "*/*",
        "User-Agent": "Netdata-Aggregator/1.0",
    }

    try:
        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            method = request.method if request else "GET"

            request_kwargs = {
                "method": method,
                "url": target_url,
                "headers": headers,
                "follow_redirects": True,
            }

            if request and method in ["POST", "PUT", "PATCH"]:
                request_kwargs["content"] = await request.body()

            response = await client.request(**request_kwargs)

            # Remove content-encoding headers to avoid double-decoding
            filtered_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in ['content-encoding', 'content-length', 'transfer-encoding']
            }

            return StreamingResponse(
                iter([response.content]),
                status_code=response.status_code,
                headers=filtered_headers,
            )
    except httpx.TimeoutException:
        raise GatewayTimeoutError(hostname)
    except httpx.ConnectError as e:
        raise BadGatewayError(hostname, f"connection refused: {str(e)}")
    except Exception as e:
        raise BadGatewayError(hostname, str(e))


def _validate_hostname(hostname: str) -> Optional:
    for host in config.hosts:
        if host.display_name == hostname:
            return host
    return None
