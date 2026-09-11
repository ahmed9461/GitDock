# GitDock — Test Matrix

Last updated: 2026-09-12

Purpose: acceptance and regression matrix for GitDock. A checked item means direct automated coverage or an explicitly verified CI gate exists. Unchecked items remain future roadmap work.

## Universal quality gates

Every implementation-bearing branch/PR must pass:

- [x] Python 3.12 CI.
- [x] Python 3.13 CI.
- [x] `ruff format --check .`.
- [x] `ruff check .`.
- [x] `mypy gitdock` strict configuration.
- [x] `pytest`.
- [x] `python -m compileall -q gitdock`.
- [x] `pip-audit -r requirements.txt`.
- [x] `detect-secrets` scan.
- [x] PEP 751 runtime-lock regeneration/diff for each supported Python version.
- [x] PostgreSQL 17 Alembic upgrade → downgrade → upgrade.

Latest verified implementation head: `e55c6e99001bb657ed2064459e92caca1f2e3481`, CI `34652564335`:

- **213 tests passed** on Python 3.12 and 3.13.
- mypy clean on **104 source files**.
- Ruff reported **176 files already formatted** and lint clean.
- `pip-audit`: no known runtime vulnerabilities.
- secret scan: no findings.
- PEP 751 locks reproduced byte-for-byte.
- PostgreSQL migration round-trip passed through `0007_github_webhook_inbox`.

Known warning-only debt:

- Starlette/FastAPI TestClient deprecation toward httpx2.
- AnyIO `BlockingPortal` alias deprecation through Starlette.
- Alembic `prepend_sys_path` warning because `path_separator` is not explicit.

## P1 — foundation

- [x] settings validation/fail-closed startup behavior.
- [x] health/readiness routes.
- [x] Telegram owner middleware.
- [x] polling/webhook bootstrap.
- [x] fresh Router per Dispatcher regression.
- [x] async DB foundation and migration smoke coverage.
- [x] redaction tests.

## P2 — GitHub App auth/gateway/read core

- [x] App JWT, installation-token lifecycle, OAuth state, PKCE S256, encrypted durable credential abstraction.
- [x] installation identity validation under App and authenticated-user contexts.
- [x] canonical GitHub API headers/version/User-Agent and safe error/rate metadata.
- [x] hostile pagination/redirect/host rejection and loop/page guards.
- [x] GET/HEAD bounded retry; write-like methods no retry by default.
- [x] installed repository list/detail/cache isolation and current-GitHub re-fetch where required.

## P3 — search and repository administration

- [x] public search without installation, query/filter/sort/page validation, opaque active sessions, stale-session rejection.
- [x] durable encrypted user OAuth context, refresh/rotation, credential-generation concurrency guard.
- [x] restart-safe pending confirmations and safe local disconnect.
- [x] repository personal/org create, settings/rename/visibility/archive/default branch, Tier 3 delete.
- [x] scoped permissions, refreshed preconditions, cancellation/stale safety, uncertain-result reconciliation, safe audit rows.

## P4.1 — file browser and stale-safe one-file writes

- [x] directory listing, parent navigation, branch/tag/SHA reads.
- [x] UTF-8 preview, binary/large fallback, bounded download.
- [x] create/upload/edit/replace/delete and review/diff.
- [x] durable staging with TTL/content digest/Git blob validation and content scrubbing.
- [x] target absence/file SHA/branch-head exact preconditions.
- [x] repository-scoped `contents: write`; workflow files additionally require `workflows: write`.
- [x] one write request; uncertain result reconciles instead of replay.
- [x] audit excludes body bytes/credentials.

## P4.2 — branch/commit tools

- [x] branch list/search, recent commits/detail, compare refs.
- [x] branch-create preview binds target/base/base SHA in persisted confirmation.
- [x] target absence and exact base SHA rechecked at confirmation time.
- [x] repository-scoped `contents: write` requested only at execution.
- [x] one create-ref POST; uncertain outcome reconciles by reading target ref.
- [x] no normal v1 force-push/force-update/branch-delete action.

## P4.3 — clone/setup/run assistant

- [x] fresh clone commands.
- [x] update-existing-clone commands.
- [x] project stack inference from bounded repository evidence.
- [x] Windows PowerShell, Linux, macOS commands.
- [x] shell-aware path/ref quoting.
- [x] confidence/source labeling.
- [x] no credential/token insertion.
- [x] no automatic execution of repository/README/script instructions.
- [x] malicious Node script bodies are never copied into generated commands.
- [x] public unauthenticated evidence reads and installed/private authorized reads.
- [x] stale public-search sessions fail closed.

## P5.1 — secure webhook ingestion — implementation verified

### Signature/authentication boundary

- [x] HMAC-SHA256 verification over exact raw HTTP body.
- [x] changed body invalidates an otherwise valid signature.
- [x] missing signature rejected.
- [x] malformed signature rejected.
- [x] forged signature rejected.
- [x] constant-time standard-library digest comparison used.
- [x] authentication occurs before delivery/event metadata is trusted.

### Metadata/body limits

- [x] bounded valid `X-GitHub-Delivery` accepted.
- [x] missing/empty/overlong/unsafe delivery IDs rejected.
- [x] bounded valid `X-GitHub-Event` accepted.
- [x] missing/empty/overlong/unsafe event names rejected.
- [x] payload ceiling is 25 MiB.
- [x] oversized body is rejected without durable persistence.

### Durable acceptance/idempotency

- [x] valid signed endpoint request returns 202 only after durable insert.
- [x] accepted inbox item survives a fresh service instance/restart boundary.
- [x] delivery ID has DB uniqueness protection.
- [x] exact duplicate delivery/event/body is idempotent and does not create a second inbox row.
- [x] same delivery ID with different content returns conflict instead of silently deduplicating.
- [x] duplicate route response contains status only and does not echo private payload data.

### Worker/retry/restart state

- [x] pending delivery can be claimed as processing.
- [x] attempt count increments when claimed.
- [x] processing delivery can be marked processed.
- [x] processing delivery can be marked failed with bounded safe error code.
- [x] failed delivery becomes claimable after retry delay.
- [x] stale processing lease becomes claimable again after crash/abandonment.
- [x] service snapshots normalize timezone behavior across SQLite/PostgreSQL.
- [x] processed raw payload is pruneable after retention expiry.

### HTTP/runtime/config integration

- [x] route is part of existing FastAPI ingress.
- [x] route reuses `GITDOCK_GITHUB_WEBHOOK_SECRET`.
- [x] route returns 503 when webhook secret is not configured.
- [x] response does not expose webhook secret/signature/raw body.
- [x] ingestion service composes from existing DB session factory; no parallel persistence stack.
- [x] event-specific normalization and Telegram notification are not performed in P5.1.

### Schema/contracts

- [x] `0007_github_webhook_inbox` creates durable inbox table and work/retention indexes.
- [x] migration upgrade/downgrade/re-upgrade covered on SQLite and PostgreSQL CI.
- [x] HTTP contract coverage verifies status/body secrecy and signature failure behavior.
- [x] unit/integration/contract suites run on Python 3.12 and 3.13.

## P5.2 — event normalization — future

- [ ] push.
- [ ] issues.
- [ ] issue_comment.
- [ ] pull_request.
- [ ] pull_request_review.
- [ ] pull_request_review_comment.
- [ ] workflow_run.
- [ ] release.
- [ ] star.
- [ ] fork.
- [ ] installation/install-repository changes.

## P5.3 — notification UX/preferences — future

- [ ] repository/event preference storage.
- [ ] mute repository.
- [ ] Telegram event renderers/deep actions.
- [ ] duplicate GitHub delivery produces no duplicate Telegram message.

## P6–P10 — future

Issues/PRs, Actions/releases, safe ZIP/project synchronization, production hardening, and post-v1 expansion remain unchecked roadmap work.

## Matrix rule

Do not check a row because a nearby behavior “probably covers it.” Add direct regression coverage where the row is material to acceptance or safety. Do not weaken CI gates to obtain green status.
