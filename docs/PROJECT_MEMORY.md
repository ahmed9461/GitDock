# GitDock — Project Memory

Purpose: durable facts future sessions must remember. This is not a task list.

Last updated: 2026-09-12

## Product and architecture

- Product: **GitDock**; repository: `ahmed9461/GitDock`.
- Telegram-first GitHub management/control bot with Arabic v1 UI.
- Python 3.12+; CI verifies Python 3.12 and 3.13.
- aiogram + FastAPI + async SQLAlchemy/Alembic.
- PostgreSQL is the production database; SQLite is only a portable development/test target.
- GitHub is source of truth for GitHub resources.
- Transport handlers stay thin; workflow/state/risk rules live in services and persistence.
- Important confirmations, staged writes, and accepted webhook work are durable when restart safety matters.

## Verified phase history

- P0 planning/governance ✅
- P1 foundation/quality gates ✅
- P2 GitHub App/auth/read core ✅
- P3 public search + repository administration ✅
- P4 repository files + Git tools + clone/setup/run assistant ✅
- **P5.1 secure webhook ingestion ✅**

P4 final baseline: **182 tests**, mypy **100 source files**.

## Durable pre-P5 invariants

- GitHub App remains the primary GitHub authorization model.
- Repository cache is navigation/context state only, never authority.
- Sensitive multi-step actions use durable server-side confirmation/staging state rather than callback possession.
- GitHub write-like calls are not blindly replayed when outcome is uncertain; reconciliation is preferred.
- File writes and branch creation bind current remote preconditions before mutation.
- No normal v1 force-push/force branch-update capability.
- Clone/setup/run generates commands only and never automatically executes repository instructions.
- Repository/README/script text is untrusted input.

## P5.1 final delivery

Feature-delivery chain:

- implementation head `e55c6e99001bb657ed2064459e92caca1f2e3481` — CI `34652564335` green;
- documentation-synchronized head `49b7b907665a0086b4207ae0b34724ca3fcaaca3` — CI `34654662909` green;
- non-draft PR #22 — PR CI `34654757724` green on unchanged mergeable head;
- protected squash merge `c13c16cf9d2354079294ebf01afbe098635b6247`;
- post-feature `main` CI `34654852954` green.

Verified baseline:

- **213 tests passed** on Python 3.12 and 3.13;
- Ruff format/lint green on **176 files**;
- mypy clean on **104 source files**;
- compile, dependency audit, repository scan, reproducible runtime locks, and PostgreSQL migration round-trip green;
- migration file `0007_github_webhook_deliveries.py`, revision `0007_webhook_inbox`.

Durable P5.1 behavior:

- inbound GitHub webhook endpoint is `POST /github/webhook` in the existing FastAPI application;
- request authenticity is checked against the exact raw request bytes before event metadata is trusted;
- request body acceptance is bounded to exactly **25,000,000 bytes**;
- accepted deliveries are committed durably before HTTP success acknowledgement;
- `github_webhook_deliveries.delivery_id` is the unique durable idempotency key;
- exact duplicate ID/event/body is idempotent; same ID with different content is a conflict;
- durable states are `pending`, `processing`, `failed`, and `processed`;
- attempt/retry state and a processing lease recover abandoned work after process failure/restart;
- processed raw payloads have bounded retention and can be pruned;
- persisted timestamps are normalized to UTC for consistent service behavior;
- normal HTTP responses do not echo private webhook material;
- P5.1 performs no event-specific normalization and sends no Telegram notifications.

## P5.2 — active

**P5.2 Event normalization is the active implementation item.**

It must:

- consume only authenticated durable P5.1 deliveries;
- normalize supported event families into bounded typed/domain event data;
- preserve source delivery identity so retries cannot create duplicate downstream work;
- fail safely on malformed/unsupported event bodies;
- avoid Telegram notification delivery, which belongs to P5.3.

Target event families: push, issues, issue_comment, pull_request, pull_request_review, pull_request_review_comment, workflow_run, release, star, fork, installation, and installation_repositories.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- PEP 751 runtime locks: `pylock.py312-linux.toml`, `pylock.py313-linux.toml`.
- CI regenerates and diffs locks; drift fails the build.
- Never weaken quality/security/reproducibility gates merely to obtain green CI.

## Operations / maintenance memory

- Zero-step hosted-runner failures can be infrastructure/quota problems; inspect job steps before treating them as code failures.
- CI push branches include `main`, `feat/**`, `fix/**`, `refactor/**`, and `security/**`.
- Known non-blocking warnings remain: Starlette/FastAPI TestClient migration toward httpx2, AnyIO BlockingPortal alias deprecation through Starlette, and Alembic path-separator configuration warning.

## Development governance

`AGENTS.md` is mandatory. Green tests with stale project state are not Done. A phase closes only after feature CI, PR CI, protected merge, post-merge `main` CI, and governance handoff.

P5.1 is delivered and post-feature verified. P5.2 is the next active implementation item.
