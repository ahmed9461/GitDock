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
- P2.1 GitHub App authentication foundation with grouped fail-closed configuration validation.
- Short-lived RS256 GitHub App JWT issuer and version-pinned GitHub auth HTTP client.
- GitHub App installation discovery plus installation access-token creation with permission/repository scoping.
- Expiry-aware installation access-token cache/refresh provider.
- OAuth user-authorization foundation with PKCE S256 and restart-safe one-time state.
- Durable GitHub authorization-state model/migration storing only a SHA-256 state digest and encrypted PKCE verifier.
- Two-stage installation candidate -> authenticated-user verification -> verified installation binding flow.
- Versioned authenticated encryption abstraction for GitHub user access/refresh credentials, including access/refresh expiry metadata.
- Central GitDock capability -> GitHub permission/token-context mapping.
- P2.1 unit/integration coverage expanding the suite from 15 to 37 tests.

### Changed

- GitHub Actions workflow uses Node 24-generation `actions/checkout@v6` and `actions/setup-python@v6`.
- `docs/BUILD_PROTOCOL.md` contains concrete bootstrap, quality, secret-scan, PostgreSQL migration, PEP 751 lock-generation, and lock-drift commands.
- Project handoff/roadmap state records P2.1 implementation as verified, with P2.2 GitHub gateway foundation as the next implementation item only after replacement PR #5 merge/main verification.
- Runtime dependencies add exact pins `PyJWT==2.13.0` and `cryptography==50.0.1`.
- Python 3.12/3.13 Linux PEP 751 runtime locks were regenerated to include the P2.1 crypto/JWT dependency graph and verified byte-for-byte by CI.
- Secret scanning ignores generated Git/cache metadata and PEP 751 lock entropy while retaining explicit scanning for project source; the known PostgreSQL CI-only credential is narrowly allowlisted in the workflow.

### Fixed

- Ruff formatting inconsistencies in database/migration files.
- Ruff import-order violations.
- Obsolete mypy ignore marker.
- aiogram Router reuse across multiple Dispatcher instances, which caused integration tests to fail after the first app creation.
- OAuth authorization-state atomic consumption on SQLite by disabling ORM in-memory session evaluation for the `UPDATE ... RETURNING` statement; PostgreSQL behavior remains the production reference.
- Integration state-lifecycle test access to expired ORM objects after rollback.
- P2.1 lock-drift mismatch caused solely by missing final newline in regenerated PEP 751 lock files.

### Security

- Established least-privilege GitHub App authentication as the primary credential model.
- A raw GitHub setup/install `installation_id` is explicitly treated as untrusted candidate data; binding requires the installation/account identity to match in both GitHub App and authenticated-user contexts before persistence.
- OAuth state is high-entropy, user/flow-bound, short-lived, one-time, and server-side; only its SHA-256 digest is persisted.
- PKCE uses S256 and the verifier is encrypted at rest with key-version metadata.
- GitHub user credential storage uses authenticated encryption with rotation-aware key versions; tokens are not stored merely because they were used for installation proof.
- GitHub auth errors and structured logs redact tokens, authorization headers, OAuth codes, state, PKCE verifiers, and client secrets.
- Installation token parsing does not assume legacy token length/format.
- Established HMAC-SHA256 GitHub webhook verification and delivery deduplication requirements for the later GitHub webhook milestone.
- Established exact-name + final confirmation requirement for repository deletion.
- Established safe archive extraction and reviewed batch-update policy for ZIP/project synchronization.
- Added Telegram webhook secret-header validation and owner-only ingress middleware to the P1 runtime foundation.
- Added structured secret redaction, dependency auditing, repository secret scanning, and reproducible lock verification to CI.

### Verification

P1 was squash-merged into `main` through PR #2 as commit `6f0a93694418c278e400a4c23b84e2f08ac56bdb`.

- PR #2 CI run `33345131414`: passed all Python 3.12, Python 3.13, and PostgreSQL 17 jobs.
- Post-merge `main` CI run `33345193470`: passed all configured checks.
- Python 3.12 and 3.13 each passed Ruff format/lint, mypy, 15 pytest tests, compile validation, pip-audit, detect-secrets, and PEP 751 lock-drift verification.
- PostgreSQL 17 migration round trip passed: upgrade -> downgrade -> upgrade.

P2.1 verification history:

- Draft PR #4 implementation CI run `33348203305`: all configured Python 3.12, Python 3.13, and PostgreSQL 17 jobs passed.
- Draft PR #4 documentation-synchronized CI run `33348487790`: all configured jobs passed again.
- Python 3.12 and 3.13 each passed Ruff format/lint, mypy, **37 pytest tests**, compile validation, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff.
- PostgreSQL 17 migration round trip passed: upgrade -> downgrade -> upgrade.
- `pip-audit` reported no known vulnerabilities for the pinned runtime requirements in the verification runs.
- PR #4 was closed without merge only because the connector's draft-to-ready GraphQL mutation failed internally; replacement PR #5 was opened non-draft from the same feature branch.
- A temporary empty `.tmp` file created during the PR-replacement workflow was immediately removed. Because those create/delete commits moved the branch SHA, PR #5 requires its own green final-head CI before merge; earlier green runs remain supporting evidence only.

The earlier GitHub Actions zero-step failures were resolved after the repository became public when private-repository included Actions quota had been exhausted; they were infrastructure/quota failures rather than application-test failures.
