"""Authenticated GitHub webhook ingestion endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gitdock.core.constants import GITHUB_WEBHOOK_PATH
from gitdock.github.webhooks import InvalidWebhookMetadata
from gitdock.services.webhooks import WebhookDeliveryConflict, WebhookPayloadTooLarge

router = APIRouter()


@router.post(GITHUB_WEBHOOK_PATH, response_model=None)
async def github_webhook(request: Request) -> JSONResponse:
    service = request.app.state.runtime_services.webhook_ingestion
    if service is None:
        return _response("webhook ingestion is not configured", 503)

    try:
        body = await _read_bounded_body(request, service.max_payload_bytes)
    except WebhookPayloadTooLarge:
        return _response("webhook payload is too large", 413)

    signature = request.headers.get("X-Hub-Signature-256")
    if not service.verify_signature(body=body, signature=signature):
        return _response("invalid webhook signature", 403)

    try:
        result = await service.ingest(
            delivery_id=request.headers.get("X-GitHub-Delivery") or "",
            event_name=request.headers.get("X-GitHub-Event") or "",
            body=body,
        )
    except InvalidWebhookMetadata:
        return _response("invalid webhook metadata", 400)
    except WebhookPayloadTooLarge:
        return _response("webhook payload is too large", 413)
    except WebhookDeliveryConflict:
        return _response("webhook delivery id conflict", 409)

    status = "duplicate" if result.duplicate else "accepted"
    return JSONResponse({"status": status}, status_code=202)


async def _read_bounded_body(request: Request, max_bytes: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = -1
        if declared_size > max_bytes:
            raise WebhookPayloadTooLarge("GitHub webhook payload exceeds configured limit")

    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > max_bytes:
            raise WebhookPayloadTooLarge("GitHub webhook payload exceeds configured limit")
    return bytes(body)


def _response(detail: str, status_code: int) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status_code)
