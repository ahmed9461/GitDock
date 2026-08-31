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

GitDock is broader than a GitHub notification bot. Planned product scope includes repository creation/settings, file operations, Git/branch/commit tools, Issues/PRs, GitHub Actions, releases, GitHub search, clone/run command generation, webhook notifications, and safe ZIP/project synchronization.

## Canonical implementation direction

- Python 3.12+; CI currently verifies Python 3.12 and 3.13.
- aiogram 3.x for Telegram.
- FastAPI for HTTP ingress: Telegram webhook, GitHub App webhooks/OAuth callbacks, health/readiness.
- httpx for outbound GitHub HTTP calls.
- SQLAlchemy 2.x async + Alembic.
- PostgreSQL in production.
- SQLite is allowed only for portable local development/tests.
- Durable DB-backed webhook/event processing is preferred over an in-memory-only queue.
- Production deployment should remain suitable for systemd.

## P1 verified foundation

P1 was implemented on `feat/p1-foundation`, verified through Pull Request CI, and squash-merged into `main` through **PR #2**.

- P1 merge commit on `main`: `6f0a93694418c278e400a4c23b84e2f08ac56bdb`
- PR #2 verification run: `33345131414` — green
- post-merge `main` run: `33345193470` — green

Verified runtime pins selected on 2026-08-31 include:

- aiogram 3.31.0
- FastAPI 0.141.1
- HTTPX 0.28.1
- SQLAlchemy 2.0.52
- Alembic 1.19.1
- asyncpg 0.31.0
- pydantic-settings 2.15.0
- Uvicorn 0.52.4

P1 foundation contains:

- typed `GITDOCK_*` settings with production-safety validation;
- FastAPI factory with `/health`, `/ready`, and Telegram webhook ingress;
- aiogram development polling and production webhook-ready wiring;
- owner-only message/callback middleware;
- async SQLAlchemy engine/session baseline;
- initial users/Telegram/GitHub account/installation models and Alembic migration;
- structured JSON logging with secret redaction baseline;
- test harness and CI quality/security gates;
- PostgreSQL 17 migration upgrade/downgrade/re-upgrade validation.

Post-merge `main` validation run `33345193470` verified:

- Python 3.12: Ruff format/lint, mypy, 15 pytest tests, compile, pip-audit, detect-secrets, PEP 751 lock drift check — all passed.
- Python 3.13: same gates — all passed.
- PostgreSQL 17 Alembic upgrade -> downgrade -> upgrade — passed.

Important P1 defect caught by tests: a module-global aiogram Router could not be attached to multiple Dispatcher instances. The correct design is a router factory returning a fresh Router per Dispatcher. Preserve that lifecycle rule for future routers/tests.

PR #1 was the original verified draft. The connector's ready-for-review mutation failed internally, so PR #1 was closed without merge and the exact same verified head was opened as non-draft PR #2. No code or quality gate was bypassed.

## P2.1 GitHub App authentication foundation

P2.1 was implemented on `feat/p2-github-app-auth` in **PR #4**. The implementation head passed full CI run `33348203305` before documentation closeout.

Durable implementation facts:

- grouped GitHub App settings fail closed when only part of the auth configuration is supplied;
- GitHub App JWTs are RS256, short-lived, and use the configured GitHub App client ID as issuer;
- the GitHub REST API version used by the auth layer is pinned to `2026-03-10`;
- installation access tokens are created on demand, permission/repository scoped when requested, cached only while sufficiently valid, and refreshed near expiry;
- OAuth user authorization uses PKCE S256;
- authorization state is high entropy, server-side, user/flow-bound, short-lived, restart-safe, and one-time use;
- raw authorization state is not stored: only a SHA-256 digest is persisted;
- the PKCE verifier is encrypted before persistence and tagged with an encryption-key version;
- encrypted GitHub user access/refresh credential storage supports key versioning and stores access/refresh expiry metadata;
- capability-to-GitHub-permission/token-context mapping is centralized rather than scattered through handlers;
- auth error/log redaction covers tokens, OAuth codes, state, PKCE verifiers, client secrets, and authorization headers;
- the P2.1 schema is exercised by Alembic upgrade -> downgrade -> upgrade on PostgreSQL 17.

### Critical installation-binding invariant

A raw `installation_id` returned through GitHub's setup/install redirect is **untrusted candidate data**. It must never be treated as proof that the current GitDock user owns/controls that installation.

The P2.1 binding flow is intentionally two-stage:

1. receive the setup/install candidate installation ID;
2. perform GitHub user authorization with one-time state + PKCE;
3. resolve the installation through GitHub App authentication context;
4. resolve the same installation through the authenticated user context;
5. compare installation/account identity;
6. persist the binding only when both contexts match and the installation is not suspended.

Preserve this rule in future callback/gateway/UI work. Do not simplify the flow to “trust installation_id from query string.”

The user access token used to prove installation access in the binding flow is not persisted merely because it was used for that proof. Persist user credentials only when a feature genuinely requires durable user-context authorization, using the encrypted credential store.

### P2.1 verification evidence

CI run `33348203305` verified the implementation head:

- Python 3.12: Ruff format/lint, mypy, **37 pytest tests**, compile, pip-audit, detect-secrets, and PEP 751 lock regeneration/diff — green.
- Python 3.13: same gates, including **37 pytest tests** — green.
- PostgreSQL 17: Alembic upgrade -> downgrade to base -> upgrade to head — green.
- `pip-audit`: no known vulnerabilities found for the pinned runtime requirements in that run.

P2.1 adds exact runtime pins:

- PyJWT 2.13.0
- cryptography 50.0.1

Their transitive selections are captured in the Python 3.12/3.13 Linux PEP 751 locks and verified byte-for-byte by CI.

## Dependency reproducibility decision

- `requirements.txt` is the human-maintained exact direct runtime dependency input.
- `requirements-dev.txt` is the human-maintained exact development/test dependency input.
- Runtime transitive/hash locking uses standardized PEP 751 lock files generated by `pip lock`.
- Current Linux CI/deployment locks:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- CI regenerates the lock for each Python version and diffs it against the committed file; dependency drift fails the build.
- Lock output is Python/platform-specific, so do not assume one Linux/Python lock is portable to another target.

## GitHub Actions operational memory

The repository was initially private after P1 implementation began. The account's included GitHub Actions quota had been exhausted, causing hosted jobs to fail before any runner step. The user changed the repository to public, after which hosted Actions ran normally and the full suite became green.

Do not misdiagnose a zero-step Actions failure as a code failure. Inspect whether any runner step actually started. Repository visibility is not an application security boundary; real secrets must never enter the repository regardless of visibility.

## GitHub authentication decision

Primary authentication is a **GitHub App**, not a broad long-lived PAT.

Expected contexts:

- installation access tokens for repository-scoped operations on repositories granted to the app;
- GitHub App user access tokens only for operations requiring authenticated-user context, such as creating a personal repository or other user-level interactions when required.

Permissions follow least privilege and are introduced incrementally by milestone. Do not request Administration/Workflows write permissions merely for convenience.

## GitHub write strategy

- Simple single-file operations may use the Contents API with current-SHA conflict protection.
- Multi-file/ZIP synchronization uses a reviewable batch strategy and one coherent commit where practical.
- Default mass update target is a review branch, then optional PR.
- Direct mass replacement of the default branch is not the default.
- Editing `.github/workflows/*` requires the appropriate Workflows capability in addition to content access.

## Webhook strategy

- GitHub webhooks are the source for immediate notifications.
- Verify `X-Hub-Signature-256` using HMAC-SHA256 before processing.
- Deduplicate using GitHub delivery ID.
- Persist accepted events before asynchronous processing so restart does not silently lose them.
- Keep ingress fast; enrichment/rendering happens after durable acceptance.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing the existing navigation message when practical.
- Use inline keyboards.
- Default to no more than two primary action buttons per row.
- Navigation actions remain consistent: Home / Cancel / Back according to context.
- Destructive actions are visually isolated.
- Tier 2/3 actions use explicit confirmation; repository deletion requires exact repository name plus final confirmation.
- Long logs/files use pagination/document delivery instead of flooding chat.

## Safety memory

- Never expose full tokens/secrets in Telegram or logs.
- Never commit secrets.
- Do not implement arbitrary shell execution as a normal bot capability.
- Clone/setup/run generates commands; it does not silently execute repository instructions.
- No normal v1 force-push UI.
- High-impact multi-step operations must not depend only on volatile in-memory FSM state.
- Audit user-triggered GitHub writes without secret material.
- GitHub remains the source of truth for GitHub resources; local repository metadata is cache/preferences only.
- Never trust setup/OAuth callback query parameters as authorization proof by themselves; validate server-side state and GitHub identities.

## Development governance memory

`AGENTS.md` is mandatory. Every successful implementation task updates relevant state/control documentation in the same change set. At minimum:

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_MEMORY.md` when durable facts changed
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- affected architecture/security/UX/decision/test documents

A green test run with stale project state documentation is not Done.

## Current implementation fact

As of 2026-08-31:

- P0 planning/governance is complete.
- P1 project skeleton & quality gates are merged into `main` and verified green after merge.
- P2.1 GitHub App authentication foundation implementation is verified green in PR #4; documentation/merge closeout is the only remaining work before moving on.
- P2.1 implementation verification run: `33348203305`.
- The exact next implementation task **after PR #4 is merged and `main` is verified** is **P2.2 — GitHub gateway foundation**.

## Do not forget later

- Search results should show stars, forks, language, license where available, archived state, and recency.
- Generate both fresh-clone and existing-clone update commands.
- Run/setup instructions must derive from actual repository evidence and label uncertainty.
- Notification preferences must be per repository and per event type.
- GitHub Actions support should include run status, jobs/steps/logs/artifacts, dispatch, and retry where permissions allow.
- ZIP sync must show added/modified/deleted/unchanged counts and review before write.
- Every risky action needs explicit target context: repository, branch/ref, path/PR/workflow, and consequence.
