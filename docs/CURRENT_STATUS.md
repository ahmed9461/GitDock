# GitDock — Current Status / Handoff

Last updated: 2026-09-12

## Project state

**Verified complete:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2 — GitHub App connection & read-only core ✅
- P3 — Search & repository administration ✅
- P4 — Repository contents, Git tools & run-command assistant ✅

**Current phase:** P5 — Webhooks & notification engine.

**Current implementation item:** **P5.1 — Secure webhook ingestion.**

P5.1 implementation is feature-verified on branch `feat/p5-1-webhook-ingestion`, but delivery closeout is still pending. Do not start P5.2 until documentation-head CI, non-draft PR CI, protected squash merge, post-feature `main` CI, and governance closeout are complete.

## P5.1 implementation verification

- implementation head: `e55c6e99001bb657ed2064459e92caca1f2e3481`;
- push CI: `34652564335` — green;
- Python 3.12 and 3.13 quality jobs green;
- **213 tests passed** on both versions;
- Ruff format/lint green on **176 files**;
- mypy clean on **104 source files**;
- compileall green;
- `pip-audit`: no known runtime vulnerabilities;
- `detect-secrets`: no findings;
- PEP 751 runtime locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade green through revision `0007_webhook_inbox` in `0007_github_webhook_deliveries.py`.

Known maintenance warnings remain unchanged: Starlette/FastAPI TestClient deprecation toward httpx2, AnyIO `BlockingPortal` alias deprecation through Starlette, and Alembic `prepend_sys_path`/`path_separator` warning. They are not test failures.

## P5.1 delivered implementation behavior

- `POST /github/webhook` lives in the existing FastAPI ingress; no second web service stack was introduced.
- The configured `GITDOCK_GITHUB_WEBHOOK_SECRET` is reused; no parallel secret/config model was added.
- Request body is read as bounded raw bytes before trusted processing.
- `X-Hub-Signature-256` is verified with HMAC-SHA256 over the exact raw body using constant-time digest comparison.
- Missing, malformed, or forged signatures fail closed before trusted event metadata processing or persistence.
- `X-GitHub-Delivery` and `X-GitHub-Event` are validated with bounded fail-closed syntax after authentication.
- Payload acceptance is bounded to **25,000,000 bytes**.
- Accepted deliveries are persisted durably before the endpoint returns HTTP 202.
- `github_webhook_deliveries.delivery_id` is unique and is the durable idempotency key.
- Exact duplicate delivery/content returns `202 {"status":"duplicate"}` without creating a second inbox item.
- Reuse of the same delivery ID with different event/content fails with HTTP 409 instead of being silently deduplicated.
- Durable states are `pending`, `processing`, `failed`, and `processed`.
- Worker-facing claim state increments attempt count and supports retry after failure.
- A processing lease allows abandoned `processing` work to become claimable again after a bounded interval, enabling restart/crash recovery.
- Failure state stores only a bounded safe error-code identifier, not exception text or raw payload content.
- Processed raw payloads have bounded retention and can be pruned after expiry.
- Service snapshots normalize DB timestamps to UTC across SQLite/PostgreSQL differences.
- HTTP responses do not echo webhook secrets, signatures, delivery payloads, or private event bodies.
- P5.1 intentionally does **not** normalize event-specific payloads or send Telegram notifications; those belong to P5.2/P5.3.

## Direct P5.1 regression coverage

- valid raw-body HMAC verification;
- changed-body signature rejection;
- missing/malformed/forged signature rejection;
- signature verification occurs before trusted metadata handling;
- bounded delivery/event header validation;
- valid endpoint acceptance;
- exact duplicate idempotency;
- delivery-ID conflict on different content;
- oversized payload rejection without persistence;
- endpoint unavailable when webhook secret is not configured;
- durable delivery survives a fresh service instance;
- pending → processing → processed lifecycle;
- processing lease recovery after simulated crash/abandonment;
- processing → failed → retry claim lifecycle;
- processed retention pruning;
- HTTP contract does not expose payload/secret material;
- Alembic SQLite and PostgreSQL round-trip includes the webhook inbox table.

## Durable invariants carried forward

- GitHub remains source of truth for GitHub resources.
- GitHub App remains the primary credential model.
- Repository cache is navigation/context state, never authorization proof.
- Telegram callbacks are transport only; sensitive authority stays server-side.
- Current remote state and scoped permissions are revalidated before sensitive execution.
- GET/HEAD may use bounded safe retry; write-like GitHub calls are not blindly replayed.
- Uncertain write outcomes remain uncertain unless reconciliation proves final state.
- Repository/README/script text is untrusted input and is never automatically executed.
- Clone/setup/run remains command generation only.
- Webhook verification always uses exact raw HTTP bytes before event trust.
- Webhook delivery deduplication is durable and keyed by GitHub delivery identity, never process memory.
- Webhook acknowledgement occurs only after signature validation and durable acceptance.
- Event normalization/Telegram delivery is downstream of the ingestion boundary.

## Active delivery task — close P5.1

Remaining required chain:

1. synchronize affected governance/specification documents on this feature branch;
2. run CI on the documentation-synchronized feature head;
3. compare against `main` and verify expected scope / behind=0;
4. open a non-draft P5.1 PR;
5. require PR CI green and unchanged mergeable head;
6. protected squash merge;
7. require post-feature `main` CI green;
8. use a governance-only closeout branch to mark P5.1 fully complete and activate **P5.2 — Event normalization**;
9. merge that closeout through the same protected CI/PR path and verify final `main` CI.

Until that chain is complete, **P5.2 is not active implementation work**.
