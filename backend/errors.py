from fastapi.responses import JSONResponse, HTMLResponse
from typing import Optional
from html import escape


class AggregatorException(Exception):
    def __init__(self, status_code: int, error: str, detail: str, host: Optional[str] = None):
        self.status_code = status_code
        self.error = error
        self.detail = detail
        self.host = host


class HostNotAllowedError(AggregatorException):
    def __init__(self, hostname: str):
        super().__init__(
            status_code=403,
            error="HostNotAllowed",
            detail=f"Hostname '{hostname}' not in configured hosts",
            host=hostname,
        )


class GatewayTimeoutError(AggregatorException):
    def __init__(self, hostname: str):
        super().__init__(
            status_code=504,
            error="GatewayTimeout",
            detail=f"{hostname} did not respond within timeout",
            host=hostname,
        )


class BadGatewayError(AggregatorException):
    def __init__(self, hostname: str, reason: str):
        super().__init__(
            status_code=502,
            error="BadGateway",
            detail=f"Could not connect to {hostname}: {reason}",
            host=hostname,
        )


class ManagementForbiddenError(AggregatorException):
    def __init__(self, hostname: str, status_code: int):
        if status_code in (401, 403):
            detail = (
                "Netdata management API rejected the request. Check the management "
                "API token and Netdata allow management from settings."
            )
        else:
            detail = (
                f"Netdata health management is unavailable on this host (HTTP {status_code}). "
                "The host may not expose the management API."
            )
        super().__init__(
            status_code=403,
            error="ManagementForbidden",
            detail=detail,
            host=hostname,
        )
        self.upstream_status_code = status_code


class BadRequestError(AggregatorException):
    def __init__(self, detail: str, host: Optional[str] = None):
        super().__init__(
            status_code=400,
            error="BadRequest",
            detail=detail,
            host=host,
        )


def error_response(exc: AggregatorException, html: bool = False):
    if not html:
        return JSONResponse(
            content={"error": exc.error, "detail": exc.detail, "host": exc.host},
            status_code=exc.status_code,
        )

    host = escape(exc.host or "")
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Netdata Unavailable</title>
        <style>
            body {{
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: #1a1d23;
                color: #c8d0e0;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }}
            .error-container {{
                text-align: center;
                padding: 2rem;
            }}
            .error-icon {{
                font-size: 4rem;
                margin-bottom: 1rem;
            }}
            .error-title {{
                font-size: 1.5rem;
                font-weight: 600;
                color: #ff4f4f;
                margin-bottom: 0.5rem;
            }}
            .error-message {{
                font-size: 1rem;
                color: #8892a6;
                margin-bottom: 1rem;
            }}
            .error-host {{
                font-size: 0.875rem;
                color: #5f6b7c;
                font-family: monospace;
            }}
        </style>
    </head>
    <body>
        <div class="error-container">
            <div class="error-icon">!</div>
            <div class="error-title">Netdata Unavailable</div>
            <div class="error-message">Could not connect to this host</div>
            <div class="error-host">{host}</div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=exc.status_code)
