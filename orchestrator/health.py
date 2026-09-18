"""Worker health checking with background polling."""

import asyncio
import enum
import logging
import time

import httpx

from .config import settings

logger = logging.getLogger("orchestrator.health")


class WorkerState(str, enum.Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class WorkerInfo:
    """Tracks a single llama-server worker."""

    def __init__(self, name: str, base_url: str, model_alias: str):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model_alias = model_alias
        self.state = WorkerState.UNKNOWN
        self.last_check: float = 0
        self.active_requests: int = 0
        self.lock = asyncio.Lock()

    @property
    def is_available(self) -> bool:
        return (
            self.state == WorkerState.HEALTHY
            and self.active_requests < settings.QUEUE_CAPACITY_PER_WORKER
        )


class HealthChecker:
    """Background health poller for all workers."""

    def __init__(self):
        self.workers: dict[str, WorkerInfo] = {}
        self._client: httpx.AsyncClient | None = None
        self._task: asyncio.Task | None = None

    def register(self, worker: WorkerInfo) -> None:
        self.workers[worker.name] = worker

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=settings.CONNECT_TIMEOUT, read=5, write=5, pool=5),
        )
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("Health checker started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client:
            await self._client.aclose()
        logger.info("Health checker stopped")

    async def _poll_loop(self) -> None:
        while True:
            for worker in self.workers.values():
                await self._check_worker(worker)
            await asyncio.sleep(settings.HEALTH_INTERVAL)

    async def _check_worker(self, worker: WorkerInfo) -> None:
        try:
            headers = {}
            if settings.WORKER_API_KEY:
                headers["Authorization"] = f"Bearer {settings.WORKER_API_KEY}"
            resp = await self._client.get(
                f"{worker.base_url}/health", headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "")
                if status in ("ok", "no slot available", "loading model"):
                    worker.state = WorkerState.HEALTHY
                else:
                    worker.state = WorkerState.UNHEALTHY
            else:
                worker.state = WorkerState.UNHEALTHY
        except Exception:
            worker.state = WorkerState.UNHEALTHY
        worker.last_check = time.monotonic()

    def get_worker_for_model(self, model: str) -> WorkerInfo | None:
        """Find the worker assigned to a model alias."""
        for worker in self.workers.values():
            if worker.model_alias == model:
                return worker
        return None

    def all_model_aliases(self) -> list[str]:
        return [w.model_alias for w in self.workers.values()]


health_checker = HealthChecker()
