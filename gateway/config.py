"""Configuration from environment variables."""

import os


class Settings:
    UPSTREAM_URL: str = os.environ.get(
        "UPSTREAM_URL", "http://100.75.123.203:9000"
    ).rstrip("/")
    PUBLIC_API_KEYS: list[str] = [
        k.strip()
        for k in os.environ.get("PUBLIC_API_KEYS", "").split(",")
        if k.strip()
    ]
    GROUP_A_MODEL_ALIAS: str = os.environ.get("GROUP_A_MODEL_ALIAS", "qwen3.8:27b")
    GROUP_B_MODEL_ALIAS: str = os.environ.get("GROUP_B_MODEL_ALIAS", "qwen2.5:0.5b")
    GROUP_A_INFLIGHT: int = int(os.environ.get("GROUP_A_INFLIGHT", "1"))
    GROUP_B_INFLIGHT: int = int(os.environ.get("GROUP_B_INFLIGHT", "2"))
    MAX_WAITERS_PER_WORKER: int = int(os.environ.get("MAX_WAITERS_PER_WORKER", "4"))
    KEEPALIVE_INTERVAL: float = float(
        os.environ.get("KEEPALIVE_INTERVAL_SECONDS", "15")
    )
    CONNECT_TIMEOUT: float = float(os.environ.get("CONNECT_TIMEOUT_SECONDS", "5"))
    UPSTREAM_TIMEOUT: float = float(
        os.environ.get("UPSTREAM_TIMEOUT_SECONDS", "3600")
    )


settings = Settings()
