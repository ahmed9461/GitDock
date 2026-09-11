from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gitdock.http.routes.webhooks import router
from gitdock.services.webhooks import WebhookIngestResult


class _WebhookService:
    def __init__(self, *, max_payload_bytes: int = 1024) -> None:
        self.max_payload_bytes = max_payload_bytes
        self.verified_body: bytes | None = None
        self.ingested: tuple[str, str, bytes] | None = None

    def verify_signature(self, *, body: bytes, signature: str | None) -> bool:
        self.verified_body = body
        return signature == "sha256=contract-signature"

    async def ingest(
        self,
        *,
        delivery_id: str,
        event_name: str,
        body: bytes,
    ) -> WebhookIngestResult:
        self.ingested = (delivery_id, event_name, body)
        return WebhookIngestResult(delivery_id=delivery_id, duplicate=False)


def _app(service: _WebhookService) -> FastAPI:
    app = FastAPI()
    app.state.runtime_services = SimpleNamespace(webhook_ingestion=service)
    app.include_router(router)
    return app


def test_webhook_http_contract_preserves_exact_raw_bytes_for_signature_and_ingest() -> None:
    service = _WebhookService()
    body = b'{"spacing":  true}\n'

    with TestClient(_app(service)) as client:
        response = client.post(
            "/github/webhook",
            headers={
                "X-Hub-Signature-256": "sha256=contract-signature",
                "X-GitHub-Delivery": "contract-delivery-1",
                "X-GitHub-Event": "push",
                "Content-Type": "application/json",
            },
            content=body,
        )

    assert response.status_code == 202
    assert response.json() == {"status": "accepted"}
    assert service.verified_body == body
    assert service.ingested == ("contract-delivery-1", "push", body)


def test_webhook_http_contract_enforces_body_limit_before_authentication() -> None:
    service = _WebhookService(max_payload_bytes=4)

    with TestClient(_app(service)) as client:
        response = client.post(
            "/github/webhook",
            headers={
                "X-Hub-Signature-256": "sha256=contract-signature",
                "X-GitHub-Delivery": "contract-delivery-2",
                "X-GitHub-Event": "push",
            },
            content=b"12345",
        )

    assert response.status_code == 413
    assert service.verified_body is None
    assert service.ingested is None
