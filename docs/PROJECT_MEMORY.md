# GitDock — Project Memory

Purpose: durable facts future sessions must remember. This is not a task list.

Last updated: 2026-09-12

## Identity and product direction

- Product: **GitDock**; repository: `ahmed9461/GitDock`.
- Telegram-first GitHub management/control bot.
- v1 user-facing language: Arabic; code/technical identifiers remain English/native.
- v1 boundary: one configured Telegram owner, while services/persistence remain multi-user-ready.

## Canonical architecture

- Python 3.12+; CI verifies Python 3.12 and 3.13.
- aiogram 3.x Telegram UI + FastAPI HTTP ingress.
- httpx behind GitHub auth/gateway boundaries.
- async SQLAlchemy 2.x + Alembic.
- PostgreSQL production; SQLite for portable tests/development only.
- GitHub is source of truth.
- Telegram/HTTP handlers stay thin; auth/token/DB/risk/business rules belong in services/auth/persistence.
- Important confirmations, staged writes, and webhook work are durable when restart safety matters.
- GitHub App installation/user tokens with minimum permissions are preferred over broad long-lived PATs.
- Ordinary feature code uses the canonical `GitHubRestClient`; do not build parallel raw HTTP stacks.

## Verified phase history

### P1 — foundation ✅

- Async app skeleton, owner middleware, persistence/migrations, CI/security/reproducibility foundation.
- Durable invariant: create a fresh aiogram Router for each Dispatcher; never reuse a module-global Router across Dispatcher instances.

### P2 — GitHub App/read core ✅

- GitHub App is primary auth; RS256 App JWT and short-lived installation tokens.
- OAuth + PKCE S256 provides durable authenticated user context when needed.
- Raw OAuth state is not persisted; PKCE verifier/user credentials are encrypted with versioned keys.
- Installation identity is trusted only after App and authenticated-user identities agree and suspension/conflict checks pass.
- `GitHubRestClient` is the canonical REST transport with centralized headers/version/User-Agent, canonical HTTPS target checks, safe errors, bounded GET/HEAD retries, and no blind write retries.
- `repositories_cache` is navigation/context state only, never authorization or source of truth.

### P3 — search and repository administration ✅

- Public search works without installation and is isolated from installed authorization/cache state.
- Opaque active search sessions bind pagination/detail context; stale sessions fail closed.
- Durable user OAuth credentials are encrypted, refresh-aware, and guarded by `credential_generation` against stale concurrency.
- `pending_confirmations` is the general DB-backed one-time confirmation store.
- Local disconnect removes GitDock-local state only and does not claim remote App uninstall.
- Repository administration uses operation-specific credentials, refreshed preconditions, reconciliation, cache synchronization, and safe audit metadata.

### P4.1 — file browser + stale-safe single-file writes ✅

- `file_write_sessions` is restart-safe one-file staging.
- Temporary staged create/update bytes are bounded and scrubbed on consume/cancel/supersede/expiry/prune.
- Create requires target absence; update/delete require exact file SHA; branch HEAD must match staged snapshot.
- `.github/workflows/*` additionally requires `workflows: write`.
- File bodies never enter audit logs.
- Verified baseline: **148 tests**, mypy **87 source files**.

### P4.2 — branch/commit tools ✅

- Branch creation is Tier 1 with persisted preview, exact base SHA/target absence revalidation, repository-scoped `contents: write`, one create-ref request, reconciliation, and audit.
- No normal v1 force-push, force branch update, or branch-delete UI.
- Verified baseline: **165 tests**, mypy **94 source files**.

### P4.3 — clone/setup/run assistant ✅

- Command generation only: GitDock never executes shell commands.
- Fresh clone and update-existing clone are separated from setup/run suggestions.
- Targets: Windows PowerShell, Linux, macOS.
- Evidence-driven baseline detection: Python, Node.js, Docker, Gradle, Maven.
- Public repositories use unauthenticated read-only Contents access; installed/private repositories reuse installation read context.
- README/script content is untrusted; Node script bodies are not copied; generated commands are credential-free.
- Verified baseline: **182 tests**, mypy **100 source files**; all quality/security/migration gates green.

## P4 overall status ✅

P4 repository files, Git tools, and clone/setup/run command generation are delivered and post-merge/governance verified. Do not reopen P4 unless a real regression is found.

## P5 — Webhooks & notification engine

### P5.1 Secure webhook ingestion — implementation verified; delivery closeout pending

Implementation head `e55c6e99001bb657ed2064459e92caca1f2e3481`, push CI `34652564335`:

- **213 tests passed** on Python 3.12 and 3.13;
- Ruff format/lint green on **176 files**;
- mypy clean on **104 source files**;
- compile, audit, secret scan, PEP 751 locks, and PostgreSQL 17 migration round-trip green;
- migration file `0007_github_webhook_deliveries.py`, Alembic revision `0007_webhook_inbox`.

Durable P5.1 facts:

- GitHub webhook ingress is `POST /github/webhook` in the existing FastAPI application.
- It reuses configured `GITDOCK_GITHUB_WEBHOOK_SECRET`; no second secret or webhook stack was introduced.
- Signature verification uses HMAC-SHA256 over the **exact raw HTTP body** and constant-time digest comparison.
- Signature verification happens before event metadata is trusted; missing/malformed/forged signatures fail closed.
- `X-GitHub-Delivery` and `X-GitHub-Event` are bounded/validated after authentication.
- Webhook payload acceptance is bounded to exactly **25,000,000 bytes** by `GITHUB_WEBHOOK_MAX_BODY_BYTES`.
- Successful HTTP acknowledgement occurs only after durable persistence.
- `github_webhook_deliveries.delivery_id` is unique and is the durable idempotency key.
- Exact duplicate ID/event/body is idempotent; no second inbox row/work item is created.
- Same delivery ID with different content is an explicit conflict, not a duplicate.
- Durable states: `pending`, `processing`, `failed`, `processed`.
- `attempt_count`, `processing_started_at`, `next_attempt_at`, `last_error_code`, `processed_at`, and `expires_at` support retry/recovery/retention.
- Processing leases make abandoned `processing` work claimable again after a bounded interval, so a worker crash/restart does not permanently strand accepted work.
- Failure persistence stores only a bounded safe error-code identifier, not raw exception text or payload data.
- Processed raw payloads can be pruned after the retention window.
- Service snapshots normalize persisted timestamps to UTC across SQLite/PostgreSQL behavior.
- Webhook HTTP responses do not echo secrets, signatures, or raw payload content.
- P5.1 does not parse/normalize event-specific business payloads and does not send Telegram notifications. Those belong to P5.2/P5.3.

P5.1 direct regression coverage includes valid/changed-body/forged signatures, signature-before-metadata ordering, duplicate/conflict semantics, route acceptance, oversized-body rejection without persistence, secret-not-configured behavior, restart-safe persistence, processing lease recovery, failure/retry lifecycle, processed pruning, HTTP secrecy, and migration round-trips.

### P5.2 / P5.3 boundary

- P5.2 will normalize authenticated durable deliveries into event-specific domain data.
- P5.3 will apply repository/event preferences and Telegram notification rendering/delivery.
- Duplicate GitHub delivery must never cause duplicate downstream notification work.
- Do not make P5.2 active until P5.1 PR/merge/post-merge/governance closeout completes.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- PEP 751 runtime locks: `pylock.py312-linux.toml`, `pylock.py313-linux.toml`.
- CI regenerates and diffs locks; drift fails the build.
- Never weaken lock/audit/secret checks to obtain green CI.

## GitHub Actions operational memory

- Zero-step hosted-runner failures can be infrastructure/quota issues; inspect runner steps before calling them code failures.
- Legitimate lock drift must be fixed, never bypassed.
- CI push branches include `main`, `feat/**`, `fix/**`, `refactor/**`, and `security/**`.
- Do not bypass PR/branch protections to close a phase.

## Known non-blocking maintenance warnings

- FastAPI/Starlette `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

## GitHub write strategy

- One-file writes: durable staging + branch/file SHA protection + one scoped write + reconciliation + audit.
- Branch create: target/base preview + persisted confirmation + revalidation + scoped write + one create-ref request + reconciliation + audit.
- Repository administration: operation-specific credentials + persisted confirmation + refreshed preconditions + one write + reconciliation + audit.
- Multi-file/ZIP sync remains a future coherent batch commit, review branch by default.
- Never blindly replay uncertain/destructive writes.
- No normal v1 force-push UI.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing current navigation message where practical.
- Use compact inline keyboards and consistent Home/Cancel/Back.
- Long paths and sensitive authority do not belong in callback data.
- Home/start invalidates transient flows where continuing would surprise the user.
- Back/Edit/Cancel after sensitive preview invalidates staged/pending authority.

## Safety memory

- Never expose/commit tokens, keys, client/webhook secrets, OAuth code/state, PKCE verifiers, encryption keys, auth headers, or raw auth response bodies.
- Do not implement arbitrary shell execution as normal bot capability.
- Repository/README/script text is untrusted input.
- No normal v1 force-push/force-update UI.
- High-impact multi-step operations must not depend only on volatile FSM state.
- Audit GitHub writes without secret/file-body material.
- GitHub remains source of truth.
- Stale callbacks/preconditions fail closed.
- Uncertain writes remain uncertain unless reconciliation proves final state.
- Webhook verification must use raw bytes and constant-time cryptographic comparison.
- Do not log webhook secrets, signature values, or unbounded raw webhook bodies.
- Accepted webhook work must be durable before acknowledgement when GitDock claims restart safety.

## Development governance memory

`AGENTS.md` is mandatory. Green tests with stale project state are not Done. Successful work updates relevant control/specification documents and leaves an explicit handoff.

P5.1 implementation is verified, but its delivery closeout is still active. After protected merge + post-merge CI + governance closeout, activate **P5.2 Event normalization**.
