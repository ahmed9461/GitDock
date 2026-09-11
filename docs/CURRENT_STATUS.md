# GitDock — Current Status / Handoff

Last updated: 2026-09-12

## Project state

**Verified complete:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2 — GitHub App connection & read-only core ✅
- P3 — Search & repository administration ✅
- P4 — Repository contents, Git tools & run-command assistant ✅
- **P5.1 — Secure webhook ingestion ✅**

**Current phase:** P5 — Webhooks & notification engine.

**Current implementation item:** **P5.2 — Event normalization.**

P5.1 implementation, protected feature delivery, and post-feature `main` verification are complete. This governance-only closeout activates P5.2 after its own closeout PR/final `main` CI completes; no P5.1 implementation work remains unless a real regression is found.

## P5.1 final delivery chain

- implementation head: `e55c6e99001bb657ed2064459e92caca1f2e3481`;
- implementation push CI: `34652564335` — green;
- documentation-synchronized feature head: `49b7b907665a0086b4207ae0b34724ca3fcaaca3`;
- documentation-head push CI: `34654662909` — green;
- non-draft PR **#22** — PR CI `34654757724` green and mergeable on unchanged head;
- protected squash merge: `c13c16cf9d2354079294ebf01afbe098635b6247`;
- post-feature `main` CI: `34654852954` — green.

Verified contract on Python 3.12 and 3.13:

- **213 tests passed**;
- Ruff format/lint green on **176 files**;
- mypy clean on **104 source files**;
- compileall green;
- `pip-audit`: no known runtime vulnerabilities;
- `detect-secrets`: no findings;
- PEP 751 runtime locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade green through revision `0007_webhook_inbox` in `0007_github_webhook_deliveries.py`.

Known maintenance warnings remain unchanged: Starlette/FastAPI TestClient deprecation toward httpx2, AnyIO `BlockingPortal` alias deprecation through Starlette, and Alembic `prepend_sys_path`/`path_separator` warning. They are not test failures.

## P5.1 delivered behavior

- `POST /github/webhook` lives in the existing FastAPI ingress.
- Reuses `GITDOCK_GITHUB_WEBHOOK_SECRET`; no parallel secret/config or HTTP stack.
- Reads bounded raw request bytes and verifies `X-Hub-Signature-256` with HMAC-SHA256 over the exact body using constant-time comparison.
- Missing, malformed, or forged signatures fail closed before trusted event metadata processing/persistence.
- `X-GitHub-Delivery` and `X-GitHub-Event` are bounded/validated only after authentication.
- Payload acceptance is bounded to exactly **25,000,000 bytes**.
- Accepted deliveries are persisted durably before HTTP 202 acknowledgement.
- `github_webhook_deliveries.delivery_id` is the unique durable idempotency key.
- Exact duplicate delivery/event/body is idempotent; same ID with different content is an explicit conflict.
- Durable states: `pending`, `processing`, `failed`, `processed`.
- Attempt counts, retry timing, processing lease recovery, safe failure codes, UTC-normalized snapshots, processed-payload retention/pruning are implemented.
- Responses do not echo webhook secrets, signatures, or raw payloads.
- P5.1 deliberately performs no event-specific normalization and no Telegram notification delivery.

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
- Downstream normalization/notification must consume authenticated durable deliveries and preserve delivery idempotency.

## Active task — P5.2 Event normalization

P5.2 scope from the roadmap:

- normalize authenticated durable webhook deliveries for `push`;
- `issues`;
- `issue_comment`;
- `pull_request`;
- `pull_request_review`;
- `pull_request_review_comment`;
- `workflow_run`;
- `release`;
- `star`;
- `fork`;
- installation / installation-repository changes.

P5.2 must remain downstream of P5.1 authentication/durable-ingestion boundaries. It must not re-trust external request metadata, create duplicate downstream work for the same delivery, or send Telegram notifications yet; preference/rendering/delivery belongs to P5.3.
