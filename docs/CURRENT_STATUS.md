# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Implementation status:** The P1 foundation is verified complete on `feat/p1-foundation` / PR #1. All required P1 CI gates are green. PR #1 may be marked ready and merged; after merge, verify the `main` push CI before starting P2 feature work.

## P1 verified foundation

- [x] Python package/application boundaries created.
- [x] Python 3.12 and 3.13 are CI-supported.
- [x] Direct runtime/development dependencies exactly pinned.
- [x] PEP 751 transitive/hash lock files committed for Linux/Python 3.12 and 3.13:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- [x] CI regenerates each lock with `pip lock` and fails on drift.
- [x] Typed `GITDOCK_*` configuration with fail-closed owner/token validation.
- [x] `.env.example` contains placeholders only.
- [x] `.gitignore` covers secrets, virtual environments, caches, databases, logs, temporary workspaces, and artifacts.
- [x] FastAPI application factory and lifespan wiring.
- [x] `/health` liveness endpoint with non-secret response.
- [x] `/ready` database readiness endpoint.
- [x] Telegram webhook ingress validates `X-Telegram-Bot-Api-Secret-Token` before update processing.
- [x] aiogram bot/dispatcher bootstrap.
- [x] development polling mode; production polling is refused.
- [x] owner-only middleware for messages and callback queries.
- [x] async SQLAlchemy engine/session baseline.
- [x] initial identity models: users, Telegram accounts, GitHub accounts, GitHub installations.
- [x] Alembic async environment and baseline migration.
- [x] structured JSON logging with secret redaction baseline.
- [x] unit/integration test harness.
- [x] Ruff format/lint, mypy, pytest, compile, pip-audit, detect-secrets, dependency-lock verification, and PostgreSQL migration CI gates.
- [x] current GitHub Actions use Node 24-generation `actions/checkout@v6` and `actions/setup-python@v6`.

## Verification evidence

### Final P1 CI

GitHub Actions run `33344826152`: **green**.

Python 3.12 job:

- Ruff format: passed
- Ruff lint: passed
- mypy: passed
- pytest: **15 passed**
- compile check: passed
- `pip-audit`: passed, no known runtime dependency vulnerabilities reported
- `detect-secrets`: passed
- PEP 751 lock regeneration/diff: passed

Python 3.13 job:

- Ruff format: passed
- Ruff lint: passed
- mypy: passed
- pytest: **15 passed**
- compile check: passed
- `pip-audit`: passed
- `detect-secrets`: passed
- PEP 751 lock regeneration/diff: passed

PostgreSQL 17 job:

- dependency installation: passed
- `alembic upgrade head`: passed
- `alembic downgrade base`: passed
- `alembic upgrade head`: passed

An earlier green run `33344511356` also passed the complete code/security/migration suite before committed lock-drift verification was added.

### Bugs found and fixed by CI during P1

- Ruff formatting inconsistencies in migration/database files.
- Ruff import-order violations.
- obsolete mypy `type: ignore` marker.
- an aiogram lifecycle bug where one global `Router` was reused across multiple `Dispatcher` instances; fixed by using a router factory per dispatcher.
- secret-scan false positives from generated caches/Git metadata and the explicitly test-only PostgreSQL credential; exclusions are limited to generated metadata/lock hashes and the known test credential is explicitly allowlisted.

## Resolved Actions blocker

When the repository was private and the account's included GitHub Actions quota was exhausted, jobs failed before runner steps began. After the repository was made public, hosted runner steps executed normally. The prior zero-step failures were therefore infrastructure/quota-related, not evidence of an application failure.

Repository visibility is an operational choice and must not be treated as an application security boundary. No real credentials may be committed whether the repository is public or private.

## Dependency locking policy

Human-maintained inputs:

- `requirements.txt` — exact direct runtime pins
- `requirements-dev.txt` — exact development/test pins

Reproducible runtime resolution for the current Linux deployment/CI targets:

- `pylock.py312-linux.toml`
- `pylock.py313-linux.toml`

The lock files use the standardized PEP 751 `pylock.toml` format produced by current `pip lock`; they include transitive packages, selected wheels, URLs, and hashes. Because pip lock output is Python/platform-specific, each supported Python/Linux target has its own lock.

## Exact next task

**P2.1 — GitHub App authentication foundation.**

Before repository browsing or writes, implement and verify:

1. GitHub App configuration validation.
2. GitHub App JWT generation.
3. installation discovery/binding model.
4. installation access-token provider with expiry-aware refresh.
5. user authorization state/callback scaffold for future user-context operations.
6. encrypted credential/token persistence abstraction.
7. central GitDock capability → GitHub permission/token-context mapper.
8. contract/unit/integration tests for auth, expiration, permission, and secret-redaction paths.

Then continue to P2.2 GitHub gateway foundation and P2.3 read-only Telegram home/repository screens.

## Rules that remain in force

- Use a GitHub App, not a broad long-lived PAT, as the primary credential model.
- Do not start repository write/admin features before the corresponding roadmap milestone and permission model.
- Never commit or log real tokens, webhook secrets, client secrets, or private key material.
- PostgreSQL remains the production database; SQLite is development/test only.
- Telegram handlers stay thin; GitHub HTTP details stay behind the gateway/service layers.
- A future milestone is not complete until its tests and project-control documentation are updated.

## Handoff instruction

Read root `AGENTS.md`, this file, `docs/PROJECT_MEMORY.md`, `docs/ROADMAP.md`, and the P2-relevant architecture/security sections. Do not rebuild P1. Begin from P2.1 only after PR #1 has been merged and `main` CI is confirmed green.
