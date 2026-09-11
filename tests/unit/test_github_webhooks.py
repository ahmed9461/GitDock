from __future__ import annotations

import hashlib
import hmac

import pytest

from gitdock.github.webhooks import (
    InvalidWebhookMetadata,
    validate_delivery_id,
    validate_event_name,
    verify_webhook_signature,
)


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_webhook_signature_verifies_exact_raw_body() -> None:
    secret = "unit-test-webhook-key"
    body = b'{"action":"opened","value":1}'

    assert verify_webhook_signature(
        secret=secret,
        body=body,
        signature=_signature(secret, body),
    )
    assert not verify_webhook_signature(
        secret=secret,
        body=body + b"\n",
        signature=_signature(secret, body),
    )


@pytest.mark.parametrize(
    "signature",
    [
        None,
        "",
        "sha1=abc",
        "sha256=abc",
        "sha256=" + ("z" * 64),
    ],
)
def test_webhook_signature_rejects_missing_or_malformed_values(signature: str | None) -> None:
    assert not verify_webhook_signature(
        secret="unit-test-webhook-key",
        body=b"{}",
        signature=signature,
    )


def test_webhook_signature_accepts_hex_case_without_weakening_comparison() -> None:
    secret = "unit-test-webhook-key"
    body = b"raw-body"
    signature = _signature(secret, body)
    assert verify_webhook_signature(
        secret=secret,
        body=body,
        signature=signature.upper().replace("SHA256=", "sha256="),
    )


def test_webhook_signature_requires_non_empty_secret() -> None:
    assert not verify_webhook_signature(secret="", body=b"{}", signature="sha256=" + ("0" * 64))


def test_webhook_metadata_validation_accepts_bounded_github_headers() -> None:
    assert validate_delivery_id("4a5c0e22-1234-5678-abcd-1234567890ef") == (
        "4a5c0e22-1234-5678-abcd-1234567890ef"
    )
    assert validate_event_name("pull_request_review") == "pull_request_review"


@pytest.mark.parametrize("value", [None, "", "spaces are invalid", "x" * 129, "bad/slash"])
def test_webhook_delivery_id_validation_fails_closed(value: str | None) -> None:
    with pytest.raises(InvalidWebhookMetadata):
        validate_delivery_id(value)


@pytest.mark.parametrize("value", [None, "", "bad event", "x" * 129, "bad/slash"])
def test_webhook_event_name_validation_fails_closed(value: str | None) -> None:
    with pytest.raises(InvalidWebhookMetadata):
        validate_event_name(value)
