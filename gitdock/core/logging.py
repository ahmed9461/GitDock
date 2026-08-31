"""Structured logging with mandatory secret redaction."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from gitdock.security.redaction import redact_text, redact_value


class RedactingJsonFormatter(logging.Formatter):
    """Small JSON formatter that never emits raw known secret patterns."""

    def format(self, record: logging.LogRecord) -> str:
        message = redact_text(record.getMessage())
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }
        context = getattr(record, "context", None)
        if context is not None:
            payload["context"] = redact_value(context)
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger once for application startup."""

    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingJsonFormatter())
    root.addHandler(handler)
    root.setLevel(level.upper())
