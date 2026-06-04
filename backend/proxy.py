import httpx
from fastapi import Response, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from urllib.parse import quote, urlsplit
from config import config
from http_client import get_http_client
from errors import (
    HostNotAllowedError,
    GatewayTimeoutError,
    BadGatewayError,
    BadRequestError,
)


async def proxy_request(hostname: str, path: str, request: Request = None) -> Response:
    host_config = config.get_host(hostname)
    if not host_config:
        raise HostNotAllowedError(hostname)

    if ".." in path or path.startswith("/"):
        raise BadRequestError("Path traversal not allowed", hostname)

    if path == "v3":
        return RedirectResponse(
            url=f"/api/proxy/{quote(hostname, safe='')}/v3/",
            status_code=307,
        )

    target_url = f"{str(host_config.url).rstrip('/')}/{path.lstrip('/')}"

    if request and request.query_params:
        target_url = f"{target_url}?{str(request.query_params)}"

    headers = {"User-Agent": "Netdata-Aggregator/1.0"}
    if request:
        for header in ["accept", "accept-language", "content-type"]:
            if header in request.headers:
                headers[header] = request.headers[header]

    try:
        client = get_http_client()
        method = request.method if request else "GET"

        request_kwargs = {"headers": headers}
        if request and method in ["POST", "PUT", "PATCH"]:
            request_kwargs["content"] = await request.body()

        upstream_request = client.build_request(method, target_url, **request_kwargs)
        response = await client.send(upstream_request, stream=True, follow_redirects=False)
        location = response.headers.get("location")
        if location and not _is_allowed_redirect(location, str(host_config.url)):
            await response.aclose()
            return RedirectResponse(
                url=f"/api/proxy/{quote(hostname, safe='')}/v3/",
                status_code=307,
            )

        filtered_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in ["content-encoding", "content-length", "transfer-encoding"]
        }

        return StreamingResponse(
            response.aiter_bytes(),
            status_code=response.status_code,
            headers=filtered_headers,
            background=response.aclose,
        )
    except httpx.TimeoutException:
        raise GatewayTimeoutError(hostname)
    except httpx.ConnectError as e:
        raise BadGatewayError(hostname, f"connection refused: {str(e)}")
    except Exception as e:
        raise BadGatewayError(hostname, str(e))


def _is_allowed_redirect(location: str, upstream_base_url: str) -> bool:
    parsed_location = urlsplit(location)
    if not parsed_location.scheme and not parsed_location.netloc:
        return True

    parsed_base = urlsplit(upstream_base_url)
    return (
        parsed_location.scheme in ["http", "https"]
        and parsed_location.scheme == parsed_base.scheme
        and parsed_location.netloc == parsed_base.netloc
    )
