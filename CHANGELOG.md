# Changelog

All meaningful changes to GitDock are recorded here.

The project follows an `Unreleased` section during active development. Versioning/release policy will be finalized before the first tagged release.

## Unreleased

### Added

- Initial GitDock product definition and repository governance.
- Root `AGENTS.md` with mandatory pre-flight, Definition of Done, and post-success documentation protocol.
- Master plan covering repository management, search, file operations, Issues/PRs, Actions, notifications, command generation, and safe ZIP/project synchronization.
- Durable project memory, current handoff state, canonical constants, architecture, Arabic-first UI/UX specification, security model, roadmap, decision log, test matrix, and PR checklist.
- P1 async Python application foundation with typed `GITDOCK_*` configuration and production safety validation.
- FastAPI application factory with `/health`, `/ready`, lifespan wiring, and Telegram webhook ingress.
- Telegram webhook `X-Telegram-Bot-Api-Secret-Token` validation.
- aiogram development polling bootstrap and production webhook-ready dispatcher wiring.
- Owner-only Telegram middleware for messages and callback queries.
- Fresh aiogram Router factory per Dispatcher lifecycle.
- Async SQLAlchemy engine/session baseline and initial users/Telegram/GitHub account/installation models.
- Alembic async migration environment and baseline identity migration.
- Structured JSON logging with secret redaction baseline.
- Exact direct runtime/development dependency pins.
- PEP 751 Linux runtime locks for Python 3.12 and 3.13 with transitive package wheels and hashes.
- GitHub Actions CI for Python 3.12/3.13 with Ruff formatting/lint, mypy, pytest, compile validation, pip-audit, detect-secrets, and PEP 751 lock-drift verification.
- PostgreSQL 17 migration CI round trip: upgrade -> downgrade -> upgrade.

### Changed

- GitHub Actions workflow uses Node 24-generation `actions/checkout@v6` and `actions/setup-python@v6`.
- `docs/BUILD_PROTOCOL.md` now contains concrete bootstrap, quality, secret-scan, PostgreSQL migration, PEP 751 lock-generation, and lock-drift commands.
- Project handoff/roadmap state now records P1 as verified complete and P2 GitHub App authentication as the next implementation phase.
- Secret scanning ignores generated Git/cache metadata and PEP 751 lock entropy while retaining explicit scanning for project source; the known PostgreSQL CI-only credential is narrowly allowlisted in the workflow.

### Fixed

- Ruff formatting inconsistencies in database/migration files.
- Ruff import-order violations.
- Obsolete mypy ignore marker.
- aiogram Router reuse across multiple Dispatcher instances, which caused integration tests to fail after the first app creation.

### Security

- Established least-privilege GitHub App authentication as the primary credential model.
- Established HMAC-SHA256 GitHub webhook verification and delivery deduplication requirements for the later GitHub webhook milestone.
- Established exact-name + final confirmation requirement for repository deletion.
- Established safe archive extraction and reviewed batch-update policy for ZIP/project synchronization.
- Added Telegram webhook secret-header validation and owner-only ingress middleware to the P1 runtime foundation.
- Added structured secret redaction, dependency auditing, repository secret scanning, and reproducible lock verification to CI.

### Verification

P1 final verification on GitHub Actions run `33344826152`:

- Python 3.12 quality job: passed all configured checks; pytest reported 15 passed.
- Python 3.13 quality job: passed all configured checks; pytest reported 15 passed.
- PostgreSQL 17 migration round trip: passed.
- PEP 751 committed lock regeneration/diff: passed for both Python versions.

The earlier GitHub Actions zero-step failures were resolved after the repository became public when private-repository included Actions quota had been exhausted; they were infrastructure/quota failures rather than application-test failures.
