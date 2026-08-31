# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Active item:** P2.1 — GitHub App authentication foundation

**Implementation status:** P1 is merged and verified on `main`. P2.1 implementation is now active on `feat/p2-github-app-auth`. Do not start P2.2/P2.3 or repository write/admin features until P2.1 acceptance is verified through CI and the project-control documents are updated.

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

## P1 verification evidence

PR #2 was merged only after Pull Request CI run `33345131414` completed successfully. Post-merge `main` run `33345193470` was also green on Python 3.12, Python 3.13, and PostgreSQL 17. P1 handoff synchronization was subsequently merged through PR #3 after CI run `33345364226` passed.

## P2.1 implementation target

Implement and verify, in this order:

1. GitHub App configuration validation.
2. GitHub App JWT generation.
3. installation discovery and safe binding primitives.
4. installation access-token provider with expiry-aware refresh.
5. user authorization state/callback scaffold with one-time state and PKCE support.
6. encrypted credential/token persistence abstraction.
7. central GitDock capability → GitHub permission/token-context mapper.
8. contract/unit/integration tests for auth, expiry, permissions, state lifecycle, encryption, and secret redaction.

### Security constraints for P2.1

- Do not trust a raw `installation_id` returned to a setup URL as proof of ownership/association; binding must be based on a verified GitHub installation identity.
- OAuth/user authorization state is opaque, high entropy, user-bound, short-lived, persisted server-side, and one-time use.
- PKCE S256 is used for the user-authorization scaffold.
- GitHub App private key, client secret, installation/user tokens, PKCE verifier, OAuth code, and encryption keys must never be logged or committed.
- Installation access-token handling must not assume a fixed token length or legacy token format.
- P2.1 may provide the secure user-authorization scaffold required for later user-context features, but full P3.2 user-context product flows remain out of scope.

## Dependency locking policy

Human-maintained inputs:

- `requirements.txt` — exact direct runtime pins
- `requirements-dev.txt` — exact development/test pins

Runtime reproducibility for current Linux targets:

- `pylock.py312-linux.toml`
- `pylock.py313-linux.toml`

Locks use standardized PEP 751 output from `pip lock` and are interpreter/platform-specific. Any dependency change in P2.1 requires regenerated committed locks and green drift checks for both supported Python versions before merge.

## Exact next task

Complete **P2.1** on `feat/p2-github-app-auth`, run the full CI suite, update all required project-control documents, and merge through a reviewed/green PR. After that, the next implementation item is **P2.2 — GitHub gateway foundation**.

## Rules that remain in force

- Use a GitHub App, not a broad long-lived PAT, as the primary credential model.
- Do not start repository write/admin features before their roadmap milestone and permission model.
- Never commit or log real tokens, webhook secrets, client secrets, private keys, or credential-encryption keys.
- PostgreSQL remains the production database; SQLite is development/test only.
- Telegram handlers stay thin; GitHub HTTP details stay behind gateway/service layers.
- A milestone is not complete until tests and project-control documentation are updated.

## Handoff instruction

Read root `AGENTS.md`, this file, `docs/PROJECT_MEMORY.md`, `docs/ROADMAP.md`, and the P2-relevant architecture/security/test sections. Continue only P2.1 from this branch until it is verified; do not rebuild P1 or skip ahead.