# GitDock — Project Memory

Purpose: durable facts that future sessions must remember. This is not a task list.

Last updated: 2026-08-31

## Identity

- Product name: **GitDock**.
- Repository: `ahmed9461/GitDock`.
- Product type: Telegram-first GitHub management/control bot.
- v1 primary language: Arabic UI; code and technical identifiers in English.
- v1 deployment model: owner-first/single-user, designed so multi-user support can be added without rewriting core services.

## Product intent

GitDock is deliberately broader than a GitHub notification bot. The planned product includes repository creation/settings, file operations, Git/branch/commit tools, Issues/PRs, GitHub Actions, releases, GitHub search, clone/run command generation, webhook notifications, and safe ZIP/project synchronization.

## Canonical implementation direction

- Python 3.12+.
- aiogram 3.x for Telegram.
- FastAPI for HTTP ingress (Telegram webhook in production + GitHub App webhooks + health endpoints).
- httpx for outbound GitHub HTTP calls.
- SQLAlchemy 2.x async and Alembic.
- PostgreSQL production database.
- SQLite is allowed for local development/tests only; code should not depend on SQLite-specific behavior.
- Persistent DB-backed event inbox/job processing is preferred over an in-memory queue for webhook reliability across restarts.
- Production process should be suitable for systemd deployment.

## P1 foundation implementation memory

P1.1 implementation exists on branch `feat/p1-foundation` and draft PR #1. It is deliberately not merged while quality gates are unverified.

Current direct runtime pins selected on 2026-08-31:

- aiogram 3.31.0
- FastAPI 0.141.1
- HTTPX 0.28.1
- SQLAlchemy 2.0.52
- Alembic 1.19.1
- asyncpg 0.31.0
- pydantic-settings 2.15.0
- Uvicorn 0.52.4

The feature branch currently contains:

- typed `GITDOCK_*` settings and production-safety validation;
- FastAPI factory with `/health`, `/ready`, and Telegram webhook ingress;
- aiogram development polling and production webhook-ready dispatcher wiring;
- owner-only message/callback middleware;
- async SQLAlchemy engine/session baseline;
- initial identity/account models and Alembic migration;
- JSON structured logging and secret redaction baseline;
- unit/integration test scaffolding;
- Ruff/mypy/pytest/pip-audit/detect-secrets/compile CI checks;
- PostgreSQL migration round-trip CI job.

Do not describe P1 as complete yet. Two GitHub Actions runs (`33343624229` and `33343758121`) failed before any job step started; jobs exposed no steps and logs were unavailable through the connected API. The code therefore has not received the required full CI verification. Local compile passed and eight targeted config/redaction tests passed, but the local execution environment could not install missing aiogram/aiosqlite/Ruff/mypy packages because it could not reach PyPI.

Direct requirements are exactly pinned, but a complete transitive/hash lock has not yet been generated. This remains part of finishing the P1 quality baseline.

## GitHub authentication decision

Primary authentication is a **GitHub App**, not a broad long-lived PAT.

Expected contexts:

- Installation access tokens for repository-level operations on installed repositories.
- GitHub App user access tokens for user-context operations that require the authenticated user, including creating a repository for the authenticated user and other user-level actions when required.

Permissions follow least privilege and should be introduced by feature milestone. Do not request every permission at once merely for convenience.

## GitHub write strategy

- Simple single-file operations may use the Contents API.
- Multi-file/ZIP synchronization should use a reviewable batch strategy and produce one coherent commit where practical.
- Default for mass updates is a new review branch, then optional PR.
- Do not default to direct mass replacement on the default branch.
- Editing `.github/workflows/*` requires the appropriate Workflows permission in addition to content access.

## Webhook strategy

- GitHub webhooks are the source for immediate notifications.
- Verify `X-Hub-Signature-256` using HMAC-SHA256 before processing.
- Deduplicate using the GitHub delivery identifier.
- Persist accepted events before asynchronous processing so a restart does not silently lose them.
- Keep webhook ingress fast; heavy rendering/API enrichment happens after durable acceptance.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing the existing navigation message when practical.
- Use inline keyboards.
- Default to no more than two primary action buttons per row.
- Navigation actions remain consistent: Home / Cancel / Back according to context.
- Destructive actions are visually separated.
- High-impact actions always have a confirmation screen.
- Repository deletion requires the strongest confirmation: exact repository name plus final confirm.
- Messages are concise and information-dense; long logs/files use pagination/document delivery instead of flooding chat.

## Safety memory

- Never expose full tokens/secrets in Telegram or logs.
- Never commit secrets.
- Do not implement arbitrary shell execution as a normal bot capability.
- Clone/setup/run feature generates commands; it does not silently execute commands on the user's device.
- No force-push UI in normal v1.
- High-impact multi-step operations must not rely only on volatile in-memory FSM state.
- Audit user-triggered GitHub writes without storing secret material.

## Development governance memory

`AGENTS.md` is mandatory. Every successful coding task must update relevant state/control documentation in the same change set. At minimum, successful implementation work updates:

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_MEMORY.md` if durable knowledge changed
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- other affected control docs

A green test run with stale project state documentation is not considered Done. A failed/partial build must leave the blocker and safe handoff state documented instead of falsely marking roadmap items complete.

## Current implementation fact

As of 2026-08-31:

- P0 planning/governance foundation is complete.
- P1.1 foundation code has started and exists on `feat/p1-foundation` / draft PR #1.
- P1.1 is **not verified complete** because GitHub-hosted CI has not begun runner steps successfully.
- The exact next task is to resolve the GitHub Actions pre-run blocker, run all configured gates, fix any real code failures found, finalize dependency locking, then merge P1 through PR.

## Do not forget later

- Search results should display useful repository quality/context signals such as stars, forks, language, license where available, archived state, and recency.
- The bot should generate both fresh-clone and existing-clone update commands.
- Run/setup instructions should be inferred from actual repository files and labeled when inference is uncertain.
- Notification settings must be per repository and per event type.
- GitHub Actions should support run status, jobs/steps/logs/artifacts, manual dispatch, and retry flows where API permissions support them.
- ZIP sync must show added/modified/deleted/unchanged counts and provide review before write.
- Every risky action needs clear target context: repository, branch/ref, path/PR/workflow, and consequence.
