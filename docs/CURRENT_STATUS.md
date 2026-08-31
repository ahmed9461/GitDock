# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phase:** P0 — Planning and governance foundation ✅

**Current phase:** P1 — Project skeleton & quality gates

**Active item:** P1.1 — Application skeleton and quality baseline

**Implementation status:** P1.1 is implemented on `feat/p1-foundation` and exposed through draft PR #1, but it is **not verified complete and must not be merged yet** because the required GitHub Actions checks have not executed successfully.

## P1.1 implementation present on the feature branch

- [x] Python package/application boundaries created.
- [x] Current direct dependency versions selected and exactly pinned in `requirements.txt` / `requirements-dev.txt`.
- [x] Typed `GITDOCK_*` configuration with fail-closed owner/token validation.
- [x] `.env.example` with placeholders only.
- [x] `.gitignore` for secrets, environments, caches, DB files, logs, workspaces, and artifacts.
- [x] FastAPI application factory and lifespan wiring.
- [x] `/health` endpoint with non-secret liveness response.
- [x] `/ready` endpoint with database readiness check.
- [x] Telegram webhook endpoint with `X-Telegram-Bot-Api-Secret-Token` validation before update processing.
- [x] aiogram bot/dispatcher bootstrap.
- [x] development polling mode; polling is refused in production mode.
- [x] owner-only Telegram middleware on messages and callback queries.
- [x] async SQLAlchemy engine/session baseline.
- [x] initial identity models: users, Telegram accounts, GitHub accounts, GitHub installations.
- [x] Alembic async environment + initial upgrade/downgrade migration.
- [x] structured JSON logging baseline with secret redaction.
- [x] unit/integration test scaffolding.
- [x] Ruff, mypy, pytest, pip-audit, detect-secrets and compile checks configured in CI.
- [x] PostgreSQL 17 migration round-trip CI job configured.
- [x] draft PR #1 opened from `feat/p1-foundation` to `main`.

Items above mean "implementation exists", not "acceptance verified".

## Dependency state

Direct dependencies are exact-pinned for reproducibility at the project boundary. Current selected runtime pins include:

- aiogram 3.31.0
- FastAPI 0.141.1
- HTTPX 0.28.1
- SQLAlchemy 2.0.52
- Alembic 1.19.1
- asyncpg 0.31.0
- pydantic-settings 2.15.0
- Uvicorn 0.52.4

Development tooling is also exactly pinned in `requirements-dev.txt`.

A fully resolved/hash-locked transitive dependency artifact has **not** been generated yet. Do not describe the current requirements files as a complete transitive lock. Finalize that strategy before declaring P1 quality gates fully complete.

## Verification performed in this implementation session

Local execution environment:

- `python -m compileall` over the generated project: **passed**.
- targeted config + redaction tests using packages already available in the execution environment: **8 passed**.
- the local environment did not contain aiogram, aiosqlite, Ruff, or mypy and could not reach PyPI, so the complete dependency-backed suite could not be executed locally.

GitHub Actions:

- CI run `33343624229`: **failure before any job step executed**.
- CI run `33343758121`: **failure before any job step executed**.
- Both runs created the expected three jobs (`quality` on Python 3.12, `quality` on Python 3.13, and `postgres-migration`).
- All jobs returned `steps = null` / no step summaries and no downloadable job logs were available through the connected GitHub API; log requests returned `BlobNotFound`.
- Because no checkout/install/test step started, these runs do **not** establish a code/test failure. They also do **not** establish a green build.

## Current blocker

Determine why GitHub-hosted Actions jobs for this private repository are failing before runner steps begin (repository/account Actions availability, billing/spending policy, runner allocation, or another GitHub-side pre-run condition). Do not weaken or delete quality gates to work around this.

## Exact next task

1. Resolve/identify the GitHub Actions pre-run failure.
2. Re-run CI until actual steps execute.
3. Fix any real Ruff/mypy/pytest/Alembic/pip-audit/detect-secrets failures revealed by that run.
4. Generate/finalize the selected transitive dependency lock strategy.
5. Run/verify PostgreSQL migration upgrade -> downgrade -> upgrade.
6. Only after all required P1 checks are green: update Roadmap/Memory/Changelog as verified, mark PR #1 ready, and merge through PR.

## Rules that remain in force

- Do not start GitHub repository write features while P1 foundation is unverified.
- Do not merge draft PR #1 while the required checks have not run green.
- Do not interpret a zero-step GitHub Actions failure as a passing or failing application test.
- Do not commit real tokens/secrets.
- PostgreSQL remains the production target; SQLite is development/test only.

## Handoff instruction

Read root `AGENTS.md`, then this file and the P1 branch/PR. Continue from the CI pre-run blocker; do not rebuild the foundation from scratch and do not skip directly to P2 until P1 acceptance is verified.