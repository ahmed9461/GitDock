# Changelog

All notable project changes are recorded here. This repository is pre-v1; entries are organized under `Unreleased` until a release policy is introduced.

## Unreleased

### Added

#### P5.1 — secure webhook ingestion

- Added `POST /github/webhook` to the existing FastAPI ingress.
- Added exact raw-body HMAC-SHA256 verification using the configured GitHub webhook secret.
- Added bounded validation for GitHub delivery ID and event name.
- Added durable `github_webhook_deliveries` inbox with unique delivery identity.
- Added durable `pending`, `processing`, `failed`, and `processed` delivery states.
- Added worker claim state, attempt counting, processing leases, retry scheduling, completion/failure transitions, and processed-payload pruning.
- Added migration file `0007_github_webhook_deliveries.py` with Alembic revision `0007_webhook_inbox` and work/retention indexes.
- Added unit/integration/contract coverage for cryptographic verification, HTTP ingress, durable idempotency, restart survival, retry/lease recovery, retention, secrecy, and migrations.

#### P4 and earlier

- P4.3 clone/setup/run assistant: evidence-driven credential-free OS-specific command generation without automatic execution.
- P4.2 branch/commit tools: typed branch/commit/compare/create-ref flows with stale-safe branch creation.
- P4.1 repository files: Contents browser and restart-safe stale-protected one-file writes.
- P3 and earlier: public search, durable GitHub user authorization, repository administration, GitHub App auth, canonical REST gateway, persistence, owner-only Telegram boundary, and CI/security gates.

### Changed

#### P5.1 ingestion/runtime behavior

- `GITDOCK_GITHUB_WEBHOOK_SECRET` is now consumed by the webhook ingestion service; no parallel secret/config model was introduced.
- Webhook request bodies are read as bounded raw bytes before trusted event processing.
- Payload ceiling is exactly **25,000,000 bytes** (`GITHUB_WEBHOOK_MAX_BODY_BYTES=25_000_000`).
- Successful HTTP acknowledgement is emitted only after durable insert or exact duplicate recognition.
- Exact duplicate delivery ID/event/body is idempotent; reused delivery ID with different content is an explicit conflict.
- Raw payload retention is bounded and processed rows can be pruned.
- Service snapshots normalize persisted timestamps to UTC across SQLite/PostgreSQL behavior.
- Event-specific normalization and Telegram notification remain outside P5.1 and are deferred to P5.2/P5.3.

#### Existing safety baseline

- Repository cache remains navigation state, never authorization.
- File/repository/branch writes use durable reviewed intent, refreshed preconditions, scoped credentials, one write, reconciliation, and safe audit metadata.
- Clone/setup/run remains command generation only; repository/README/script content is untrusted.

### Fixed

#### P5.1 verification

- Corrected Ruff formatting in the new webhook model/service/tests.
- Tightened SQLAlchemy result typing to satisfy strict mypy without weakening type policy.
- Normalized DB timestamp timezone behavior so portable SQLite tests and PostgreSQL production expose consistent UTC snapshots.
- Kept oversized-route testing lightweight while still verifying the endpoint's configured body ceiling behavior.

### Security

#### P5.1

- Missing, malformed, or forged `X-Hub-Signature-256` fails closed before trusted event metadata processing or persistence.
- Signature verification uses HMAC-SHA256 over exact raw request bytes and constant-time comparison.
- Unauthenticated malformed metadata still fails at the authentication boundary first.
- Webhook secrets, signature values, and raw payloads are not echoed in normal HTTP responses.
- Durable deduplication is DB-backed by unique delivery identity rather than volatile process memory.
- Exact duplicate recognition compares event name, SHA-256 digest, byte length, and raw bytes.
- Same delivery ID with different content is rejected as conflict.
- Failed processing stores only a bounded safe error-code identifier rather than arbitrary exception text.
- Abandoned processing work is recoverable through a bounded processing lease.
- Raw webhook payloads are treated as private durable work data with bounded retention, not audit/log content.

#### Existing baseline

- Durable user credentials remain encrypted.
- GitHub App installation binding requires App/user-context identity agreement.
- Generic REST transport restricts canonical GitHub targets and does not blindly replay unsafe writes.
- File bodies never enter audit logs.
- Workflow-file writes additionally require `workflows: write`.
- Normal v1 UI exposes no force-push/force branch-update capability.

### Verification

#### P5.1 implementation head

- head `e55c6e99001bb657ed2064459e92caca1f2e3481`;
- push CI `34652564335` green;
- Python 3.12 and 3.13 quality jobs green;
- **213 tests passed** on both versions;
- mypy clean on **104 source files**;
- Ruff format/lint green on **176 files**;
- compileall green;
- `pip-audit`: no known runtime vulnerabilities;
- `detect-secrets`: no findings;
- PEP 751 runtime locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade green through revision `0007_webhook_inbox`.

P5.1 implementation is verified. Formal delivery remains open until documentation-head CI, non-draft PR CI, protected squash merge, post-feature `main` CI, and governance closeout complete.

#### Earlier baselines

- P4.3: **182 tests**, mypy **100 source files**, all gates green.
- P4.2: **165 tests**, mypy **94 source files**, all gates green.
- P4.1: **148 tests**, mypy **87 source files**, all gates green.

### Maintenance warnings

The following warnings are tracked and non-blocking:

- FastAPI/Starlette `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias surfaced through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.
