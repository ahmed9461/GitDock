# GitDock — Current Status / Handoff

Last updated: 2026-09-12

## Project state

**Verified complete:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅
- P2.3 — Home + repository read screens ✅
- P3.1 — GitHub repository search ✅
- P3.2 — durable GitHub user-context authorization/disconnect ✅
- P3.3 — repository create/settings administration ✅
- P4.1 — repository file browser + stale-safe single-file writes ✅
- P4.2 — branch/commit tools ✅
- P4.3 — clone/setup/run assistant ✅
- P4 — Repository contents, Git tools & run-command assistant ✅

**Current phase:** P5 — Webhooks & notification engine.

**Current implementation item:** **P5.1 — Secure webhook ingestion.**

P4 is fully delivered and feature-verified. This branch is governance closeout only; do not reopen P4 unless a real regression is found. New implementation work belongs in a fresh P5.1 feature branch after this closeout is merged.

## P4.3 final delivery chain

- implementation head `fba538e3c6071365361def7d5970ff7b19b5819c` — push CI `34650497474` green;
- documentation-synchronized head `989e826f8e845934b9255a78c91bfeca48f10538` — push CI `34650840434` green;
- non-draft PR #20 on the unchanged head — PR CI `34650940874` green and mergeable;
- protected squash merge `0f0750388a1a919917ba81586fad42ae2ab11336`;
- post-feature `main` CI `34651051039` green.

Verified P4.3 contract:

- Python 3.12 and 3.13;
- **182 tests passed** on both versions;
- Ruff format/lint green on **167 files**;
- mypy clean on **100 source files**;
- compileall green;
- `pip-audit` reported no known runtime vulnerabilities;
- `detect-secrets` reported no findings;
- PEP 751 runtime locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade remains green through `0006_file_write_sessions`.

Known maintenance warnings remain unchanged: Starlette/FastAPI TestClient deprecation toward httpx2, AnyIO `BlockingPortal` alias deprecation through Starlette, and Alembic `prepend_sys_path`/`path_separator` warning. They are not test failures.

## P4.3 delivered behavior

- Repository dashboard and public-search detail expose a real clone/setup/run command assistant.
- Explicit target OS selection: Windows PowerShell, Linux, or macOS.
- Fresh-clone and update-existing-clone commands are separated from setup and run suggestions.
- Bounded evidence-driven inference supports Python, Node.js, Docker, Gradle, and Maven.
- Inferred setup/run suggestions expose confidence and evidence sources.
- Public repositories use unauthenticated read-only Contents access; installed/private repositories reuse existing installation read context.
- P4.3 reuses the canonical `GitHubRestClient`/Contents gateway; there is no parallel HTTP stack.
- Generated commands never contain GitHub tokens or credentials.
- GitDock never executes generated commands automatically.
- README/script text is untrusted and is never copied as arbitrary shell instructions.
- Node script bodies are never copied; only validated script names may produce `npm run <name>` style invocations.
- Python entry-point/script names used in generated commands are constrained to safe identifiers.
- Path/ref material is quoted for the selected shell where applicable.
- Evidence reads are bounded to known root candidates and configured read-size limits.
- Stale public-search callbacks continue to fail closed.
- Output explicitly warns that dependency/build/run commands may execute repository-controlled hooks, build logic, or scripts when the user runs them locally.

## Durable invariants carried forward

- GitHub remains source of truth.
- GitHub App remains the primary credential model.
- Repository cache is navigation/context state, never authorization proof.
- Telegram callbacks are transport only; sensitive authority stays server-side.
- Current remote state and scoped permissions are revalidated before sensitive execution.
- GET/HEAD may use bounded safe retry; write-like GitHub calls are not blindly replayed.
- Uncertain write outcomes remain uncertain unless reconciliation proves final state.
- Repository deletion remains Tier 3 exact-name gated.
- Single-file writes remain stage → preview → confirm → revalidate → scoped token → single write → reconcile → audit.
- Branch creation remains preview → persisted confirmation → base/target revalidation → scoped token → single create-ref → reconcile → audit.
- No normal v1 force-push/force-update UI.
- Repository/README/script text is untrusted input and is never automatically executed.
- Clone/setup/run remains command generation only; GitDock does not provide arbitrary shell execution.
- Webhook verification must use the exact raw HTTP body before JSON parsing.
- Webhook delivery deduplication must be durable and keyed by GitHub delivery identity, not volatile process memory.
- Webhook HTTP acknowledgement must stay fast; durable processing belongs behind the ingestion boundary.

## Active task — P5.1 Secure webhook ingestion

Required scope:

- GitHub webhook endpoint in the existing FastAPI ingress;
- exact raw-body HMAC-SHA256 signature verification using the configured webhook secret;
- reject missing/invalid signatures before trusted event processing;
- capture GitHub delivery ID and event name using bounded validated headers;
- durable webhook/event inbox with unique delivery ID deduplication;
- duplicate deliveries must be idempotent and must not create duplicate downstream work;
- fast HTTP acknowledgement after validation + durable acceptance;
- explicit processing state suitable for retryable worker consumption and restart recovery;
- bounded payload storage/retention policy and no secret/raw-auth overlogging;
- migration + unit/integration/contract coverage for valid signature, forged signature, duplicate delivery, restart-safe persistence, and failure/retry state;
- continue using existing persistence/runtime composition patterns rather than introducing a second service stack.

Before coding, inspect current FastAPI routes, settings/security boundaries, SQLAlchemy/Alembic conventions, and test fixtures. P5.1 is ingestion/durability only; event-specific normalization and Telegram notification UX belong to P5.2/P5.3.
