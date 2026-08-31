"""Secret redaction helpers for logs and diagnostic text."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:bearer\s+)?[^\s,;]+"),
    re.compile(
        r"(?i)((?:access_token|refresh_token|client_secret|webhook_secret|bot_token|oauth_code|token)"
        r"\s*[:=]\s*)[^\s,;]+"
    ),
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.DOTALL),
)

_SENSITIVE_KEYS = {
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "client_secret",
    "webhook_secret",
    "telegram_bot_token",
    "oauth_code",
    "private_key",
}


def redact_text(value: str) -> str:
    """Redact common credential forms from a string."""

    result = value
    for pattern in _PATTERNS:
        result = pattern.sub(
            lambda match: f"{match.group(1)}{REDACTED}" if match.lastindex else REDACTED,
            result,
        )
    return result


def redact_value(value: Any, key: str | None = None) -> Any:
    """Recursively redact sensitive values while preserving log structure."""

    if key is not None and key.lower() in _SENSITIVE_KEYS:
        return REDACTED
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {str(k): redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value
