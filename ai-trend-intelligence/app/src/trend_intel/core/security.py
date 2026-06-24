"""Optional API-key dependency for mutating endpoints (FR-027)."""
from __future__ import annotations

from fastapi import Header, HTTPException, status

from trend_intel.config import get_settings


async def require_api_key(x_api_key: str = Header(default="")) -> None:
    """FastAPI dependency — no-op when API_KEY env is blank."""
    settings = get_settings()
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key.")
