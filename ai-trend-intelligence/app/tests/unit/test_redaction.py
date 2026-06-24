"""Unit tests: secret redaction processor (T070, SC-011, FR-027)."""
from __future__ import annotations

import pytest


def test_redact_known_secret_key():
    from trend_intel.core.logging import redact_secrets
    event = {"openrouter_api_key": "sk-or-realkey123", "msg": "test"}
    result = redact_secrets(None, "info", event)
    assert result["openrouter_api_key"] == "[REDACTED]"


def test_redact_bearer_token_in_value():
    from trend_intel.core.logging import redact_secrets
    event = {"message": "Authorization: Bearer sk-or-abc123def456"}
    result = redact_secrets(None, "info", event)
    assert "sk-or-abc123def456" not in result["message"]
    assert "[REDACTED]" in result["message"]


def test_redact_sk_or_pattern_in_value():
    from trend_intel.core.logging import redact_secrets
    event = {"detail": "error with key sk-or-v1-abcdefghij"}
    result = redact_secrets(None, "info", event)
    assert "sk-or-v1-abcdefghij" not in result["detail"]


def test_redact_nested_dict():
    from trend_intel.core.logging import redact_secrets
    event = {"nested": {"openrouter_api_key": "sk-or-secret"}}
    result = redact_secrets(None, "info", event)
    assert result["nested"]["openrouter_api_key"] == "[REDACTED]"


def test_benign_fields_unchanged():
    from trend_intel.core.logging import redact_secrets
    event = {"run_id": "abc-123", "status": "succeeded"}
    result = redact_secrets(None, "info", event)
    assert result["run_id"] == "abc-123"
    assert result["status"] == "succeeded"


def test_postgres_password_redacted():
    from trend_intel.core.logging import redact_secrets
    event = {"postgres_password": "supersecret"}
    result = redact_secrets(None, "info", event)
    assert result["postgres_password"] == "[REDACTED]"
