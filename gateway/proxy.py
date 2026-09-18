"""HTTP proxy from the EC2 gateway to the rig orchestrator."""

import logging
from collections.abc import AsyncIterator

import httpx

from .config import settings

logger = logging.getLogger("gateway.proxy")

_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=settings.CONNECT_TIMEOUT,
                read=settings.UPSTREAM_TIMEOUT,
                write=30,
                pool=10,
            ),
            limits=httpx.Limits(
                max_connections=40,
                max_keepalive_connections=10,
            ),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


async def proxy_streaming(
    path: str, body: dict, api_key: str
) -> AsyncIterator[bytes]:
    client = await get_client()
    url = f"{settings.UPSTREAM_URL}{path}"
    async with client.stream(
        "POST", url, json=body, headers=_auth_headers(api_key)
    ) as resp:
        if resp.status_code != 200:
            error_body = await resp.aread()
            raise ProxyError(resp.status_code, error_body)
        async for chunk in resp.aiter_bytes():
            yield chunk


async def proxy_blocking(
    path: str, body: dict, api_key: str
) -> tuple[int, dict | bytes]:
    client = await get_client()
    url = f"{settings.UPSTREAM_URL}{path}"
    resp = await client.post(url, json=body, headers=_auth_headers(api_key))
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.status_code, resp.json()
    return resp.status_code, resp.content


async def proxy_get(path: str, api_key: str) -> tuple[int, dict | bytes]:
    client = await get_client()
    url = f"{settings.UPSTREAM_URL}{path}"
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = await client.get(url, headers=headers)
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.status_code, resp.json()
    return resp.status_code, resp.content


class ProxyError(Exception):
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Upstream returned {status_code}")
