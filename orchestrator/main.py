"""OCS Intelligence Inference Orchestrator — FastAPI application."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .auth import verify_api_key
from .config import settings
from .health import WorkerInfo, WorkerState, health_checker
from .proxy import ProxyError, close_client, proxy_blocking, proxy_streaming
from .routing import resolve_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("orchestrator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register workers
    worker_a = WorkerInfo(
        name="group-a",
        base_url=settings.GROUP_A_URL,
        model_alias=settings.GROUP_A_MODEL_ALIAS,
    )
    worker_b = WorkerInfo(
        name="group-b",
        base_url=settings.GROUP_B_URL,
        model_alias=settings.GROUP_B_MODEL_ALIAS,
    )
    health_checker.register(worker_a)
    health_checker.register(worker_b)

    logger.info(
        "Orchestrator starting: A=%s (%s), B=%s (%s)",
        worker_a.base_url,
        worker_a.model_alias,
        worker_b.base_url,
        worker_b.model_alias,
    )

    await health_checker.start()
    yield
    await health_checker.stop()
    await close_client()
    logger.info("Orchestrator stopped")


app = FastAPI(title="OCS Inference Orchestrator", lifespan=lifespan)


# ---------- Health endpoints ----------


@app.get("/healthz")
async def healthz():
    """Process liveness."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz():
    """Ready when at least one worker is healthy."""
    for w in health_checker.workers.values():
        if w.state == WorkerState.HEALTHY:
            return {"status": "ready"}
    return JSONResponse(
        status_code=503, content={"status": "not ready", "detail": "No healthy workers"}
    )


# ---------- OpenAI-compatible API ----------


@app.get("/v1/models", dependencies=[Depends(verify_api_key)])
async def list_models():
    """Return available models in OpenAI format."""
    models = []
    for worker in health_checker.workers.values():
        models.append(
            {
                "id": worker.model_alias,
                "object": "model",
                "created": 0,
                "owned_by": "ocs-intelligence",
                "permission": [],
            }
        )
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
async def chat_completions(request: Request):
    """OpenAI-compatible chat completions — streaming and blocking."""
    body = await request.json()
    model = body.get("model", "")
    is_stream = body.get("stream", False)

    worker = resolve_worker(model)

    async with worker.lock:
        worker.active_requests += 1

    try:
        if is_stream:
            return await _handle_streaming(request, worker, body)
        else:
            return await _handle_blocking(worker, body)
    finally:
        async with worker.lock:
            worker.active_requests = max(0, worker.active_requests - 1)


async def _handle_streaming(
    request: Request, worker: WorkerInfo, body: dict
) -> StreamingResponse:
    """Stream SSE from the worker to the client."""

    async def event_generator():
        try:
            async for chunk in proxy_streaming(worker, "/v1/chat/completions", body):
                if await request.is_disconnected():
                    logger.info("Client disconnected, stopping stream")
                    break
                yield chunk
        except ProxyError as e:
            logger.error("Worker %s error: %d", worker.name, e.status_code)
            yield f'data: {{"error": {{"message": "Worker error", "code": {e.status_code}}}}}\n\n'.encode()
            yield b"data: [DONE]\n\n"
        except Exception:
            logger.exception("Streaming error for worker %s", worker.name)
            yield b'data: {"error": {"message": "Internal error"}}\n\n'
            yield b"data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _handle_blocking(worker: WorkerInfo, body: dict) -> JSONResponse:
    """Non-streaming completion."""
    try:
        status, result = await proxy_blocking(worker, "/v1/chat/completions", body)
        if isinstance(result, dict):
            return JSONResponse(status_code=status, content=result)
        return JSONResponse(status_code=status, content={"raw": result.decode()})
    except ProxyError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": {"message": "Worker error", "code": e.status_code}},
        )
    except Exception:
        logger.exception("Blocking request error for worker %s", worker.name)
        raise HTTPException(status_code=502, detail="Worker communication failed")
