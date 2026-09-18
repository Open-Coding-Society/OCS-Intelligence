"""API key authentication."""

from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import settings

_bearer = HTTPBearer(auto_error=False)


async def verify_api_key(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """Validate the Bearer token against configured public API keys."""
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Missing or invalid authorization")
    if not settings.PUBLIC_API_KEYS:
        # No keys configured — allow all (dev mode)
        return creds.credentials
    if creds.credentials not in settings.PUBLIC_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return creds.credentials
