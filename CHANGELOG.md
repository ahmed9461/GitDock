# Changelog

All meaningful changes to GitDock are recorded here.

The project follows an `Unreleased` section during active development. Versioning/release policy will be finalized before the first tagged release.

## Unreleased

### Added

- Initial GitDock product definition and repository governance.
- Root `AGENTS.md` with mandatory pre-flight, Definition of Done, and post-success documentation protocol.
- Master plan covering repository management, search, file operations, Issues/PRs, Actions, notifications, command generation, and safe ZIP/project synchronization.
- Durable project memory and current handoff state.
- Canonical constants, callback/risk conventions, and GitHub capability groups.
- Async Python/FastAPI/aiogram/PostgreSQL baseline architecture.
- Arabic-first Telegram UI/UX screen and interaction specification.
- Security model for GitHub App credentials, webhook validation, destructive confirmations, archive safety, stale-state protection, and audit logging.
- Build/development protocol.
- Phased implementation roadmap.
- Architectural/product decision log.
- Comprehensive test matrix and live-smoke expectations.
- P1 application foundation on `feat/p1-foundation`: typed configuration, FastAPI health/readiness, aiogram polling/webhook bootstrap, owner authorization middleware, async SQLAlchemy persistence baseline, Alembic migration, structured redacting logs, and initial tests.
- Exact direct runtime/development dependency pins for the P1 foundation.
- GitHub Actions CI definition for Ruff, mypy, pytest, compile validation, dependency audit, secret scan, and PostgreSQL migration round-trip.
- Draft PR #1 for P1 foundation review; it remains unmerged until required checks actually execute and pass.

### Changed

- `docs/BUILD_PROTOCOL.md` now contains concrete environment bootstrap, quality-check, secret-scan, and migration-validation commands.
- Project handoff state now distinguishes implemented-but-unverified P1 work from verified completion.

### Security

- Established least-privilege GitHub App authentication as the primary credential model.
- Established HMAC-SHA256 GitHub webhook verification and delivery deduplication requirements.
- Established exact-name + final confirmation requirement for repository deletion.
- Established safe archive extraction and reviewed batch-update policy for ZIP/project synchronization.
- Added Telegram webhook secret-header validation and owner-only ingress middleware to the P1 runtime foundation.
- Added structured secret redaction baseline and CI secret/dependency scanning gates.

### Known verification blocker

- GitHub Actions runs `33343624229` and `33343758121` failed before any job step started and exposed no job logs through the connected API. P1 is therefore not marked complete or merged; see `docs/CURRENT_STATUS.md` for the exact handoff.