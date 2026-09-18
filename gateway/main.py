"""OCS Intelligence EC2 admission gateway — FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .auth import verify_api_key
from .config import settings
from .lanes import ClientGone, Lane, LaneFull, lanes
from .proxy import ProxyError, close_client, proxy_blocking, proxy_get, proxy_streaming

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Admission gateway starting: upstream=%s A=%s inflight=%d B=%s inflight=%d waiters=%d",
        settings.UPSTREAM_URL,
        settings.GROUP_A_MODEL_ALIAS,
        settings.GROUP_A_INFLIGHT,
        settings.GROUP_B_MODEL_ALIAS,
        settings.GROUP_B_INFLIGHT,
        settings.MAX_WAITERS_PER_WORKER,
    )
    yield
    await close_client()
    logger.info("Admission gateway stopped")


app = FastAPI(title="OCS Admission Gateway", lifespan=lifespan)


def _lane_full_error() -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={
            "error": {
                "message": "Too many requests. Please retry later.",
                "type": "rate_limit_error",
                "code": "rate_limit_exceeded",
            }
        },
        headers={"Retry-After": "15"},
    )


def _unknown_model_error(model: str) -> HTTPException:
    available = list(lanes.keys())
    return HTTPException(
        status_code=404,
        detail={
            "error": {
                "message": f"Model '{model}' not found. Available models: {available}",
                "type": "invalid_request_error",
                "code": "model_not_found",
            }
        },
    )


@app.get("/healthz")
async def healthz():
    """Gateway process liveness."""
    return {"status": "ok"}


@app.get("/v1/models")
async def list_models(api_key: str = Depends(verify_api_key)):
    """Proxy model list; does not occupy a GPU lane."""
    try:
        status, result = await proxy_get("/v1/models", api_key)
    except Exception:
        logger.exception("Upstream /v1/models failed")
        raise HTTPException(status_code=502, detail="Upstream communication failed")
    if isinstance(result, dict):
        return JSONResponse(status_code=status, content=result)
    return Response(content=result, status_code=status)


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request, api_key: str = Depends(verify_api_key)
):
    """Admit into a per-model lane, then proxy to the rig orchestrator."""
    body = await request.json()
    model = body.get("model", "")
    is_stream = bool(body.get("stream", False))

    lane = lanes.get(model)
    if lane is None:
        raise _unknown_model_error(model)

    try:
        await lane.enter_line()
    except LaneFull:
        raise _lane_full_error()

    if is_stream:
        return await _handle_streaming(request, lane, body, api_key)
    return await _handle_blocking(request, lane, body, api_key)


async def _handle_streaming(
    request: Request, lane: Lane, body: dict, api_key: str
):
    async def event_generator():
        acquired = False
        try:
            async for item in lane.wait_streaming(request):
                if item is None:
                    acquired = True
                    break
                yield item
            async for chunk in proxy_streaming(
                "/v1/chat/completions", body, api_key
            ):
                if await request.is_disconnected():
                    logger.info(
                        "Client disconnected, stopping stream (%s)", lane.name
                    )
                    break
                yield chunk
        except ClientGone:
            logger.info("Client gone while queued or streaming (%s)", lane.name)
            return
        except ProxyError as e:
            logger.error("Upstream error: %d (%s)", e.status_code, lane.name)
            yield (
                f'data: {{"error": {{"message": "Upstream error", '
                f'"code": {e.status_code}}}}}\n\n'
            ).encode()
            yield b"data: [DONE]\n\n"
        except Exception:
            logger.exception("Streaming error (%s)", lane.name)
            yield b'data: {"error": {"message": "Internal error"}}\n\n'
            yield b"data: [DONE]\n\n"
        finally:
            if acquired:
                lane.release()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _handle_blocking(
    request: Request, lane: Lane, body: dict, api_key: str
):
    acquired = False
    try:
        await lane.wait_blocking(request)
        acquired = True
    except ClientGone:
        return Response(status_code=499)

    try:
        status, result = await proxy_blocking(
            "/v1/chat/completions", body, api_key
        )
        if isinstance(result, dict):
            return JSONResponse(status_code=status, content=result)
        return Response(content=result, status_code=status)
    except ProxyError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": {"message": "Upstream error", "code": e.status_code}},
        )
    except Exception:
        logger.exception("Blocking request error (%s)", lane.name)
        raise HTTPException(status_code=502, detail="Upstream communication failed")
    finally:
        if acquired:
            lane.release()
