"""Model-to-worker routing logic."""

from fastapi import HTTPException

from .health import WorkerInfo, health_checker


def resolve_worker(model: str) -> WorkerInfo:
    """Find the healthy worker for a given model name.

    Raises 404 if the model is unknown, 503 if the worker is unhealthy,
    429 if the worker queue is full.
    """
    worker = health_checker.get_worker_for_model(model)
    if worker is None:
        available = health_checker.all_model_aliases()
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Model '{model}' not found. Available models: {available}",
                    "type": "invalid_request_error",
                    "code": "model_not_found",
                }
            },
        )
    if not worker.is_available:
        from .config import settings

        if worker.active_requests >= settings.QUEUE_CAPACITY_PER_WORKER:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "message": "Too many requests. Please retry later.",
                        "type": "rate_limit_error",
                        "code": "rate_limit_exceeded",
                    }
                },
                headers={"Retry-After": "5"},
            )
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": f"Worker for model '{model}' is currently unavailable.",
                    "type": "server_error",
                    "code": "worker_unavailable",
                }
            },
        )
    return worker
