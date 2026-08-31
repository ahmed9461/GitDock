# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Current item:** P2.1 — GitHub App authentication foundation — implementation verified; documentation/PR closeout in progress.

**Next implementation item after merge:** P2.2 — GitHub gateway foundation.

P2.1 implementation on `feat/p2-github-app-auth` passed the full configured CI suite in run `33348203305`. Do not start P2.2/P2.3 or repository write/admin features until PR #4 is merged and the merged `main` state is verified.

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

## P2.1 verified implementation

- [x] grouped GitHub App configuration validation with fail-closed partial configuration handling.
- [x] short-lived RS256 GitHub App JWT generation using the configured client ID as issuer.
- [x] GitHub App installation discovery and safe installation identity parsing.
- [x] installation access-token creation with permission/repository scoping and expiry-aware cache refresh.
- [x] GitHub OAuth user-authorization scaffold with PKCE S256.
- [x] restart-safe one-time authorization state persisted server-side as SHA-256 digest only.
- [x] encrypted PKCE verifier persistence with encryption-key version metadata.
- [x] two-stage installation candidate -> OAuth/user verification -> verified binding flow.
- [x] encrypted GitHub user access/refresh credential persistence abstraction with access/refresh expiry metadata and key rotation support.
- [x] central GitDock capability -> GitHub permission/token-context mapper.
- [x] secret redaction coverage for GitHub auth material.
- [x] Alembic migration for durable GitHub authorization state and refresh-token expiry metadata.
- [x] unit/integration coverage expanded to 37 tests.

### P2.1 security invariants

- A raw `installation_id` returned through GitHub's setup/install flow is **untrusted candidate data**, not proof of ownership. GitDock binds only after the same installation identity is verified from both GitHub App authentication context and authenticated GitHub user context.
- OAuth state is opaque, high entropy, user-bound, short-lived, server-side, and one-time use.
- The raw OAuth state is not persisted; only its SHA-256 digest is stored.
- PKCE uses S256; the verifier is encrypted at rest and never logged.
- GitHub App private key, client secret, installation/user tokens, OAuth code, PKCE verifier, and credential-encryption keys must never be logged or committed.
- Installation access-token handling does not assume a fixed token length or legacy token format.
- GitHub user credential persistence uses authenticated encryption and versioned keys; the binding flow does not persist a user token merely because it was used to prove installation access.

## P2.1 verification evidence

Pre-closeout PR CI run `33348203305` passed all configured jobs:

- Python 3.12: Ruff format, Ruff lint, mypy, **37 pytest tests**, compile validation, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff — all passed.
- Python 3.13: the same gates, including **37 pytest tests** and PEP 751 lock regeneration/diff — all passed.
- PostgreSQL 17: Alembic upgrade -> downgrade to base -> upgrade to head — passed.
- `pip-audit` reported no known vulnerabilities for the pinned runtime requirements in this verification run.

The P2.1 dependency set adds exact runtime pins for `PyJWT==2.13.0` and `cryptography==50.0.1`; the Python 3.12 and 3.13 Linux PEP 751 locks were regenerated and verified byte-for-byte by CI.

## Dependency locking policy

Human-maintained inputs:

- `requirements.txt` — exact direct runtime pins
- `requirements-dev.txt` — exact development/test pins

Runtime reproducibility for current Linux targets:

- `pylock.py312-linux.toml`
- `pylock.py313-linux.toml`

Locks use standardized PEP 751 output from `pip lock` and are interpreter/platform-specific. Any dependency change requires regenerated committed locks and green drift checks for both supported Python versions before merge.

## Exact next task

1. Finish P2.1 project-control documentation synchronization in PR #4.
2. Require a green CI run for that exact documentation-synchronized head.
3. Mark PR #4 ready and merge only while the verified head is unchanged.
4. Verify the merged `main` CI state.
5. Then start **P2.2 — GitHub gateway foundation** on a new branch from verified `main`.

## Rules that remain in force

- Use a GitHub App, not a broad long-lived PAT, as the primary credential model.
- Do not start repository write/admin features before their roadmap milestone and permission model.
- Never commit or log real tokens, webhook secrets, client secrets, private keys, OAuth codes, PKCE verifiers, or credential-encryption keys.
- PostgreSQL remains the production database; SQLite is development/test only.
- Telegram handlers stay thin; GitHub HTTP details stay behind gateway/service layers.
- A milestone is not complete until tests and project-control documentation are updated.

## Handoff instruction

Read root `AGENTS.md`, this file, `docs/PROJECT_MEMORY.md`, `docs/ROADMAP.md`, `docs/SECURITY_MODEL.md`, `docs/TEST_MATRIX.md`, and the P2-relevant architecture sections. Complete only the PR #4 closeout/merge before starting P2.2; do not rebuild P1 or skip ahead.
