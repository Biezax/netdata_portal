from typing import Optional

import httpx


_client: Optional[httpx.AsyncClient] = None


def set_http_client(client: Optional[httpx.AsyncClient]) -> None:
    global _client
    _client = client


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client is not configured")
    return _client
