"""Per-model admission lanes: bounded waiters + in-flight semaphore.

FIFO is preserved by starting a single ``Semaphore.acquire()`` task and
waiting on it. Timing out that acquire and retrying would cancel it and
send the client to the back of the line.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Protocol

from .config import settings


class Disconnectable(Protocol):
    async def is_disconnected(self) -> bool: ...


class LaneFull(Exception):
    """Waiting line is at MAX_WAITERS_PER_WORKER."""


class ClientGone(Exception):
    """Client disconnected while waiting or while holding a slot."""


async def _cancel_acquire(sem: asyncio.Semaphore, task: asyncio.Task) -> None:
    """Cancel an in-flight acquire, releasing the semaphore if it was granted."""
    if task.done():
        if not task.cancelled() and task.exception() is None:
            sem.release()
        return
    task.cancel()
    try:
        await task
        sem.release()
    except asyncio.CancelledError:
        pass


class Lane:
    """One wait line + in-flight cap for a single model alias."""

    def __init__(self, name: str, inflight: int, max_waiters: int):
        self.name = name
        self.inflight_limit = inflight
        self.max_waiters = max_waiters
        self._sem = asyncio.Semaphore(inflight)
        self._waiting = 0
        self._in_flight = 0
        self._lock = asyncio.Lock()

    @property
    def waiting(self) -> int:
        return self._waiting

    @property
    def occupancy(self) -> int:
        return self._waiting + self._in_flight

    @property
    def capacity(self) -> int:
        return self.inflight_limit + self.max_waiters

    async def enter_line(self) -> None:
        """Occupy a waiter slot or raise LaneFull. Pair with wait_*()."""
        async with self._lock:
            if self.occupancy >= self.capacity:
                raise LaneFull()
            self._waiting += 1

    async def _leave_line(self) -> None:
        async with self._lock:
            if self._waiting > 0:
                self._waiting -= 1

    def _mark_in_flight(self) -> None:
        self._in_flight += 1

    async def _acquire(
        self, request: Disconnectable, emit_keepalive: bool
    ) -> AsyncIterator[bytes]:
        """Precondition: enter_line() succeeded.

        Yields SSE keepalives while queued. On return, caller holds the
        in-flight slot and must ``release()``. Always leaves the waiter line.
        """
        acquire_task = asyncio.create_task(self._sem.acquire())
        acquired = False
        try:
            while not acquire_task.done():
                if await request.is_disconnected():
                    raise ClientGone()
                await asyncio.wait(
                    {acquire_task}, timeout=settings.KEEPALIVE_INTERVAL
                )
                if acquire_task.done():
                    break
                if emit_keepalive:
                    yield b": queued\n\n"
            acquire_task.result()
            acquired = True
            self._mark_in_flight()
        except BaseException:
            if not acquired:
                await _cancel_acquire(self._sem, acquire_task)
            raise
        finally:
            await self._leave_line()

    def release(self) -> None:
        if self._in_flight > 0:
            self._in_flight -= 1
        self._sem.release()

    async def wait_blocking(self, request: Disconnectable) -> None:
        """Wait until holding an in-flight slot. Caller must ``release()``."""
        async for _ in self._acquire(request, emit_keepalive=False):
            pass

    async def wait_streaming(
        self, request: Disconnectable
    ) -> AsyncIterator[bytes | None]:
        """Yield keepalives, then ``None`` once the in-flight slot is held."""
        async for chunk in self._acquire(request, emit_keepalive=True):
            yield chunk
        yield None


def _lanes() -> dict[str, Lane]:
    return {
        settings.GROUP_A_MODEL_ALIAS: Lane(
            settings.GROUP_A_MODEL_ALIAS,
            settings.GROUP_A_INFLIGHT,
            settings.MAX_WAITERS_PER_WORKER,
        ),
        settings.GROUP_B_MODEL_ALIAS: Lane(
            settings.GROUP_B_MODEL_ALIAS,
            settings.GROUP_B_INFLIGHT,
            settings.MAX_WAITERS_PER_WORKER,
        ),
    }


lanes: dict[str, Lane] = _lanes()
