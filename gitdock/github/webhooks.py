"""Pure GitHub webhook signature and metadata validation helpers."""

from __future__ import annotations

import hashlib
import hmac
import re

_SIGNATURE_PREFIX = "sha256="
_SHA256_HEX_LENGTH = 64
_DELIVERY_ID_RE = re.compile(r"^[A-Za-z0-9-]{1,128}$")
_EVENT_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


class InvalidWebhookMetadata(ValueError):
    """Raised when bounded GitHub webhook transport metadata is invalid."""


def verify_webhook_signature(*, secret: str, body: bytes, signature: str | None) -> bool:
    """Verify GitHub's SHA-256 webhook signature over the exact raw request body."""

    if not secret or signature is None:
        return False
    if not signature.startswith(_SIGNATURE_PREFIX):
        return False
    supplied_digest = signature[len(_SIGNATURE_PREFIX) :]
    if len(supplied_digest) != _SHA256_HEX_LENGTH:
        return False
    try:
        bytes.fromhex(supplied_digest)
    except ValueError:
        return False

    expected_digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(
        f"{_SIGNATURE_PREFIX}{expected_digest}",
        f"{_SIGNATURE_PREFIX}{supplied_digest.lower()}",
    )


def validate_delivery_id(value: str | None) -> str:
    """Return a bounded delivery identifier or raise a safe validation error."""

    if value is None or _DELIVERY_ID_RE.fullmatch(value) is None:
        raise InvalidWebhookMetadata("invalid GitHub delivery id")
    return value


def validate_event_name(value: str | None) -> str:
    """Return a bounded event name or raise a safe validation error."""

    if value is None or _EVENT_NAME_RE.fullmatch(value) is None:
        raise InvalidWebhookMetadata("invalid GitHub event name")
    return value
