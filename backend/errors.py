from fastapi import HTTPException
from fastapi.responses import JSONResponse
from typing import Optional


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


def error_response(exc: AggregatorException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "detail": exc.detail, "host": exc.host},
    )
