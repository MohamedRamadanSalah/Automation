"""Shared utilities."""
from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC time as timezone-naive datetime (matches TIMESTAMP columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
