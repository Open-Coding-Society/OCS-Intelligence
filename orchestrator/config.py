"""Configuration from environment variables."""

import os


class Settings:
    GROUP_A_URL: str = os.environ.get("GROUP_A_URL", "http://127.0.0.1:8081")
    GROUP_B_URL: str = os.environ.get("GROUP_B_URL", "http://127.0.0.1:8082")
    GROUP_A_MODEL_ALIAS: str = os.environ.get("GROUP_A_MODEL_ALIAS", "qwen3.8:27b")
    GROUP_B_MODEL_ALIAS: str = os.environ.get("GROUP_B_MODEL_ALIAS", "qwen2.5:0.5b")
    WORKER_API_KEY: str = os.environ.get("WORKER_API_KEY", "")
    PUBLIC_API_KEYS: list[str] = [
        k.strip()
        for k in os.environ.get("PUBLIC_API_KEYS", "").split(",")
        if k.strip()
    ]
    QUEUE_CAPACITY_PER_WORKER: int = int(
        os.environ.get("QUEUE_CAPACITY_PER_WORKER", "16")
    )
    CONNECT_TIMEOUT: float = float(os.environ.get("CONNECT_TIMEOUT_SECONDS", "5"))
    RESPONSE_TIMEOUT: float = float(
        os.environ.get("RESPONSE_HEADER_TIMEOUT_SECONDS", "600")
    )
    STREAM_IDLE_TIMEOUT: float = float(
        os.environ.get("STREAM_IDLE_TIMEOUT_SECONDS", "300")
    )
    HEALTH_INTERVAL: float = float(os.environ.get("HEALTH_INTERVAL_SECONDS", "5"))


settings = Settings()
