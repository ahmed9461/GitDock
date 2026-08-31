# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Implementation status:** P1 is merged into `main` through PR #2. Merge commit: `6f0a93694418c278e400a4c23b84e2f08ac56bdb`. The post-merge `main` GitHub Actions run `33345193470` is green across Python 3.12, Python 3.13, and PostgreSQL 17. The repository is ready to begin P2.1.

## P1 verified foundation

- [x] Python package/application boundaries created.
- [x] Python 3.12 and 3.13 CI support.
- [x] exact direct runtime/development pins.
- [x] PEP 751 transitive/hash runtime locks:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- [x] CI regenerates each lock with `pip lock` and rejects drift.
- [x] typed `GITDOCK_*` configuration with fail-closed validation.
- [x] `.env.example` contains placeholders only; real secrets are ignored/not committed.
- [x] FastAPI factory, `/health`, `/ready`, and Telegram webhook ingress.
- [x] Telegram webhook secret-header validation.
- [x] aiogram polling/webhook-ready bootstrap and owner-only middleware.
- [x] fresh Router factory per Dispatcher lifecycle.
- [x] async SQLAlchemy engine/session baseline.
- [x] initial users/Telegram/GitHub account/installation models.
- [x] Alembic async baseline migration.
- [x] structured JSON logging with secret redaction.
- [x] Ruff format/lint, mypy, pytest, compile, pip-audit, detect-secrets, lock-drift, and PostgreSQL migration gates.

## Verification evidence

### PR verification

PR #2 was merged only after its Pull Request CI run `33345131414` completed successfully.

### Post-merge `main` verification

GitHub Actions run `33345193470`: **green**.

Python 3.12:

- Ruff format: passed
- Ruff lint: passed
- mypy: passed
- pytest: **15 passed**
- compile check: passed
- pip-audit: passed
- detect-secrets: passed
- PEP 751 lock drift: passed

Python 3.13: same configured gates passed; pytest reported **15 passed**.

PostgreSQL 17:

- `alembic upgrade head`: passed
- `alembic downgrade base`: passed
- `alembic upgrade head`: passed

## Important P1 discoveries

- The initial zero-step Actions failures were caused by private-repository Actions quota availability. After the repository was made public, runners executed normally. A zero-step Actions failure must not be misreported as an application test failure.
- CI caught and fixed formatting/import issues, an obsolete mypy ignore, secret-scan false positives, and an aiogram Router lifecycle bug.
- Repository visibility is not a security boundary. Never commit real credentials even while the repository is private.

## Dependency locking policy

Human-maintained inputs:

- `requirements.txt` — exact direct runtime pins
- `requirements-dev.txt` — exact development/test pins

Runtime reproducibility for current Linux targets:

- `pylock.py312-linux.toml`
- `pylock.py313-linux.toml`

Locks use standardized PEP 751 output from `pip lock` and are interpreter/platform-specific.

## Exact next task

**P2.1 — GitHub App authentication foundation.**

Implement and verify, in this order:

1. GitHub App configuration validation.
2. GitHub App JWT generation.
3. installation discovery/binding model.
4. installation access-token provider with expiry-aware refresh.
5. user authorization state/callback scaffold for future user-context operations.
6. encrypted credential/token persistence abstraction.
7. central GitDock capability → GitHub permission/token-context mapper.
8. contract/unit/integration tests for auth, expiry, permissions, and secret redaction.

After P2.1 passes, continue to P2.2 GitHub gateway foundation and then P2.3 read-only Telegram home/repository screens.

## Rules that remain in force

- Use a GitHub App, not a broad long-lived PAT, as the primary credential model.
- Do not start repository write/admin features before their roadmap milestone and permission model.
- Never commit or log real tokens, webhook secrets, client secrets, or private key material.
- PostgreSQL remains the production database; SQLite is development/test only.
- Telegram handlers stay thin; GitHub HTTP details stay behind gateway/service layers.
- A future milestone is not complete until tests and project-control documentation are updated.

## Handoff instruction

Read root `AGENTS.md`, this file, `docs/PROJECT_MEMORY.md`, `docs/ROADMAP.md`, and the P2-relevant architecture/security sections. P1 is complete and merged. Begin from P2.1; do not rebuild P1 or skip directly to write/admin features.
