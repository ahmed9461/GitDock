# Changelog

All meaningful changes to GitDock are recorded here.

The project follows an `Unreleased` section during active development. Versioning/release policy will be finalized before the first tagged release.

## Unreleased

### Added

- Initial GitDock product definition and repository governance.
- Root `AGENTS.md` with mandatory pre-flight, Definition of Done, and post-success documentation protocol.
- Master plan plus durable memory/current-state/constants/architecture/UI/security/roadmap/decision/test documentation.
- P1 async Python application foundation: typed settings, FastAPI health/readiness + Telegram ingress, aiogram polling/webhook bootstrap, owner-only middleware, async SQLAlchemy/Alembic, structured redacting logging, tests, and CI.
- PEP 751 Linux runtime locks for Python 3.12 and 3.13 with CI byte-for-byte drift verification.
- P2.1 GitHub App authentication foundation: fail-closed settings, RS256 App JWT, installation token provider/cache, OAuth + PKCE S256, hashed one-time state, encrypted PKCE/user credentials, dual-context installation binding, and central capability/permission mapping.
- P2.2 typed `GitHubRestClient` as the canonical REST transport boundary.
- P2.2 typed `GitHubResponse[T]`, `GitHubPage[T]`, `GitHubRateLimit`, and validated pagination metadata models.
- P2.2 stable error translation for authentication, permission, not-found, conflict/precondition, validation, rate-limit, transient, and unexpected failures.
- P2.2 GitHub rate-limit parsing for resource/limit/remaining/used/reset and `Retry-After`.
- P2.2 validated pagination iterator with canonical-host checks, repeated-link detection, and maximum-page guard.
- P2.2 bounded exponential backoff with jitter for retry-safe transient requests; write-like methods default to no retry.
- P2.2 HTTPX MockTransport fixture/contract coverage expanding the suite from 37 to 49 tests.

### Changed

- Canonical GitHub REST request metadata is now centralized: API `2026-03-10`, `application/vnd.github+json`, and `User-Agent: GitDock/0.1`.
- GitHub HTTP timeout/retry/page-limit constants are centralized rather than handler-local.
- GitHub pagination/absolute REST targets are restricted to canonical HTTPS `api.github.com`; the gateway is not a generic URL fetcher.
- Runtime dependencies include exact pins `PyJWT==2.13.0` and `cryptography==50.0.1` from P2.1; P2.2 adds no runtime dependency and does not alter the existing PEP 751 locks.
- Project state now records P2.1 as merged/post-merge verified and P2.2 as implementation-verified pending documentation/final-head PR closeout.

### Fixed

- aiogram Router reuse across multiple Dispatcher instances.
- OAuth authorization-state atomic consumption on SQLite and expired ORM-object access in lifecycle tests.
- P2.1 PEP 751 final-newline drift.
- P2.2 initial Ruff formatting/import ordering and modern Python generic-syntax findings caught by CI before type/test gates.

### Security

- GitHub App least-privilege authentication remains the primary credential model.
- Raw setup/install `installation_id` remains untrusted until dual app/user-context identity verification.
- OAuth state is one-time/server-side with only SHA-256 digest persisted; PKCE verifier and persisted user credentials are encrypted with versioned keys.
- GitHub gateway errors intentionally omit raw GitHub response bodies and credentials while retaining safe status/request/rate metadata.
- Pagination rejects external hosts, protocol-relative URLs, URL credentials, fragments, and non-canonical targets before network I/O.
- Outbound gateway redirects are not followed automatically.
- GET/HEAD may retry bounded transient failures; write-like methods are never blindly retried by default.
- Structured secret redaction, dependency auditing, secret scanning, and reproducible lock verification remain CI gates.

### Verification

P1:

- PR #2 CI `33345131414` — green.
- Post-merge `main` CI `33345193470` — green.

P2.1:

- final PR #5 CI `33348768686` — green.
- squash merge commit: `81dfaf406d046205b39980d6a64c681ea3ab18c6`.
- post-merge `main` CI `33348851085` — green.
- Python 3.12/3.13: 37 tests plus format/lint/mypy/compile/audit/secret/lock gates; PostgreSQL 17 migration round trip passed.

P2.2 implementation verification:

- implementation head `ca6c0beb4ea96f661e9e891b04e69228bf6c4de3`.
- PR #6 CI run `33406986504` — green on Python 3.12, Python 3.13, and PostgreSQL 17.
- Python 3.12 log confirms **49 passed**; the 12 new contract tests all passed.
- Both Python jobs passed Ruff format/lint, mypy, pytest, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff.
- PostgreSQL 17 upgrade -> downgrade -> upgrade passed.
- `pip-audit` reported no known runtime vulnerabilities.
- This is pre-documentation verification; final-head CI is still required after all P2.2 documentation is synchronized.

Operational note: earlier zero-step GitHub Actions failures were caused by exhausted private-repository hosted-runner quota and stopped after the repository became public; they were not application failures.