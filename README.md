# GitDock

GitDock is a Telegram-first GitHub control center. It is designed to let a user inspect, search, manage, update, and monitor GitHub repositories without needing to keep the GitHub website open for routine work.

## Product direction

GitDock is not only a notification bot. The target product includes:

- Repository discovery, creation, rename, visibility/settings management, and safe deletion.
- Repository dashboard: metadata, branches, commits, releases, issues, pull requests, workflows, and activity.
- File browser with view/create/edit/replace/delete flows.
- Safe ZIP/project synchronization with diff preview and a single reviewed commit/PR.
- GitHub Actions status, logs, artifacts, retry, and manual workflow dispatch.
- GitHub search with stars, forks, language, license, activity, and filters.
- Immediate Telegram notifications from GitHub webhooks with per-repository preferences.
- Generated clone/update/setup/run commands for Windows, Linux, and macOS based on repository contents.
- Strong confirmation gates for destructive operations.

## Verified foundation

P1 establishes the tested runtime foundation:

- Python 3.12 and 3.13 CI targets.
- aiogram 3.x Telegram bootstrap with owner-only middleware.
- FastAPI `/health`, `/ready`, and Telegram webhook ingress.
- Async SQLAlchemy 2.x + Alembic.
- PostgreSQL production baseline; SQLite only for portable local development/tests.
- Structured logging with secret redaction.
- Ruff, mypy, pytest, compile, pip-audit, detect-secrets, and PostgreSQL migration gates.
- PEP 751 runtime locks for Python 3.12/3.13 Linux with CI drift verification.

Final P1 verification: GitHub Actions run `33344826152` passed both Python quality jobs and the PostgreSQL 17 migration round trip.

## Architecture baseline

- Python 3.12+
- aiogram 3.x
- FastAPI for Telegram/GitHub webhook ingress and OAuth callbacks
- httpx for GitHub REST/GraphQL clients
- SQLAlchemy 2.x async + Alembic
- PostgreSQL in production
- GitHub App authentication; avoid long-lived broad PATs
- Persistent database-backed webhook inbox/job processing for restart safety

## Project governance

Before changing code, read the project control files in this order:

1. `AGENTS.md`
2. `docs/PROJECT_MASTER_PLAN.md`
3. `docs/PROJECT_MEMORY.md`
4. `docs/CURRENT_STATUS.md`
5. `docs/CONSTANTS.md`
6. `docs/ARCHITECTURE.md`
7. `docs/UI_UX_SPEC.md`
8. `docs/SECURITY_MODEL.md`
9. `docs/BUILD_PROTOCOL.md`
10. `docs/ROADMAP.md`
11. `docs/DECISIONS.md`
12. `docs/TEST_MATRIX.md`
13. `.github/PULL_REQUEST_TEMPLATE.md`

The files above are part of the product, not optional notes. A successful implementation that does not update the relevant status/memory/roadmap/changelog documentation is not considered complete.

## Current state

- P0 planning/governance foundation: **complete**.
- P1 project skeleton & quality gates: **verified complete**.
- Current implementation target after P1 merge verification: **P2.1 — GitHub App authentication foundation**.

See `docs/CURRENT_STATUS.md` for the exact handoff point, verification evidence, and next task.
