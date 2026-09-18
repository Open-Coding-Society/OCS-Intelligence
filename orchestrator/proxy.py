"""Streaming proxy to llama-server workers."""

import logging
from collections.abc import AsyncIterator

import httpx

from .config import settings
from .health import WorkerInfo

logger = logging.getLogger("orchestrator.proxy")

# Shared HTTP client — created once, reused for all requests
_client: httpx.AsyncClient | None = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=settings.CONNECT_TIMEOUT,
                read=settings.STREAM_IDLE_TIMEOUT,
                write=30,
                pool=10,
            ),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
            ),
        )
    return _client


async def close_client() -> None:
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


async def proxy_streaming(
    worker: WorkerInfo,
    path: str,
    body: dict,
) -> AsyncIterator[bytes]:
    """Stream SSE response from a worker, yielding raw bytes."""
    client = await get_client()
    url = f"{worker.base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if settings.WORKER_API_KEY:
        headers["Authorization"] = f"Bearer {settings.WORKER_API_KEY}"

    async with client.stream(
        "POST",
        url,
        json=body,
        headers=headers,
    ) as resp:
        if resp.status_code != 200:
            error_body = await resp.aread()
            raise ProxyError(resp.status_code, error_body)
        async for chunk in resp.aiter_bytes():
            yield chunk


async def proxy_blocking(
    worker: WorkerInfo,
    path: str,
    body: dict,
) -> tuple[int, dict | bytes]:
    """Non-streaming proxy to a worker. Returns (status_code, response_body)."""
    client = await get_client()
    url = f"{worker.base_url}{path}"
    headers = {"Content-Type": "application/json"}
    if settings.WORKER_API_KEY:
        headers["Authorization"] = f"Bearer {settings.WORKER_API_KEY}"

    resp = await client.post(url, json=body, headers=headers)
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.status_code, resp.json()
    return resp.status_code, resp.content


async def proxy_get(
    worker: WorkerInfo,
    path: str,
) -> tuple[int, dict | bytes]:
    """GET proxy to a worker."""
    client = await get_client()
    url = f"{worker.base_url}{path}"
    headers = {}
    if settings.WORKER_API_KEY:
        headers["Authorization"] = f"Bearer {settings.WORKER_API_KEY}"

    resp = await client.get(url, headers=headers)
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.status_code, resp.json()
    return resp.status_code, resp.content


class ProxyError(Exception):
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Worker returned {status_code}")
