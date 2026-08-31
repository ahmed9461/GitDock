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
- P2.2 stable error translation, rate-limit parsing, canonical-host pagination, and safe retry policy.
- P2.3 typed repository read gateway for installed repositories and repository detail metadata.
- P2.3 minimal `repositories_cache` + Alembic migration `0003` for compact Telegram callback/context resolution.
- P2.3 owner identity service and runtime composition wiring for repository read use cases.
- P2.3 Arabic Telegram home, repository list, filters, repository detail, refresh, stale/error states, and compact versioned callbacks.
- P2.3 working GitHub App setup/OAuth HTTP callback wiring using the existing P2.1 state/PKCE/dual-context binding services.
- P2.3 repository filters for all/private/public/active/archived/source/fork.
- P2.3 contract/integration/UI coverage expanding the suite from 49 to **65 tests**.

### Changed

- Canonical GitHub REST request metadata remains centralized: API `2026-03-10`, `application/vnd.github+json`, and `User-Agent: GitDock/0.1`.
- GitHub HTTP timeout/retry/page-limit constants remain centralized rather than handler-local.
- GitHub pagination/absolute REST targets remain restricted to canonical HTTPS `api.github.com`; the gateway is not a generic URL fetcher.
- P2.2 is now recorded as squash-merged through PR #7 as `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`, with post-merge `main` CI `33409825480` green.
- Repository UI callbacks now carry compact versioned repository IDs plus navigation context rather than arbitrary repository `owner/name` strings.
- Repository list/detail data flows through application services and the P2.2 transport instead of Telegram handlers issuing GitHub HTTP.
- GitHub repository detail is refreshed from GitHub before display; local repository cache is navigation/context state only.
- Runtime dependencies remain unchanged by P2.3; existing PEP 751 locks are still byte-for-byte verified on Python 3.12 and 3.13.

### Fixed

- aiogram Router reuse across multiple Dispatcher instances.
- OAuth authorization-state atomic consumption on SQLite and expired ORM-object access in lifecycle tests.
- P2.1 PEP 751 final-newline drift.
- P2.2 initial Ruff formatting/import ordering and modern Python generic-syntax findings caught by CI before type/test gates.
- P2.3 Ruff formatting/import/Unicode-lint findings without changing the intended Arabic/emoji UI.
- P2.3 FastAPI callback route registration failure by explicitly disabling response-model inference for Response-returning setup/OAuth routes.

### Security

- GitHub App least-privilege authentication remains the primary credential model.
- Raw setup/install `installation_id` remains untrusted until dual app/user-context identity verification.
- OAuth state is one-time/server-side with only SHA-256 digest persisted; PKCE verifier and persisted user credentials are encrypted with versioned keys.
- GitHub gateway errors intentionally omit raw GitHub response bodies and credentials while retaining safe status/request/rate metadata.
- Pagination rejects external hosts, protocol-relative URLs, URL credentials, fragments, and non-canonical targets before network I/O.
- Outbound gateway redirects are not followed automatically.
- GET/HEAD may retry bounded transient failures; write-like methods are never blindly retried by default.
- P2.3 repository callbacks resolve server-side inside the current GitDock user and active installation context; a callback/cache row is not authorization proof by itself.
- `repositories_cache` stores no token/OAuth/PKCE/private-key material and is explicitly non-authoritative.
- Repository detail requests a repository-scoped installation token and re-fetches GitHub before render.
- P2.3 remains Tier 0 read-only and introduces no repository write/admin permission.

### Verification

P1:

- PR #2 CI `33345131414` — green.
- Post-merge `main` CI `33345193470` — green.

P2.1:

- final PR #5 CI `33348768686` — green.
- squash merge commit: `81dfaf406d046205b39980d6a64c681ea3ab18c6`.
- post-merge `main` CI `33348851085` — green.
- Python 3.12/3.13: 37 tests plus format/lint/mypy/compile/audit/secret/lock gates; PostgreSQL 17 migration round trip passed.

P2.2:

- implementation CI `33406986504` — green.
- final PR #7 head CI `33409670775` — green.
- squash merge commit: `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`.
- post-merge `main` CI `33409825480` — green.
- suite at P2.2: 49 tests; Python 3.12/3.13 and PostgreSQL 17 all green.

P2.3 implementation verification:

- implementation head: `a6d57d5a99b58004fab4dbf84b9b6742a9475523`.
- CI run `33423169021` — green on Python 3.12, Python 3.13, and PostgreSQL 17.
- Python 3.12 log confirms **65 passed**; Python 3.13 passed the same configured suite/gates.
- Ruff format/lint, mypy, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff all passed.
- PostgreSQL 17 upgrade -> downgrade -> upgrade including migration `0003` passed.
- `pip-audit` reported no known runtime vulnerabilities.
- P2.3 is implementation-verified but not yet marked complete until documentation-head CI, PR merge, post-merge `main` CI, and final handoff sync succeed.

### Known maintenance warnings

- Green P2.3 CI reports a Starlette/FastAPI `TestClient` deprecation warning for the current `httpx` integration/future `httpx2` direction.
- Green P2.3 CI reports an Alembic deprecation warning because `alembic.ini` does not yet set explicit `path_separator` for `prepend_sys_path`.

These warnings are recorded rather than hidden; they do not currently fail the build.

Operational note: earlier zero-step GitHub Actions failures were caused by exhausted private-repository hosted-runner quota and stopped after the repository became public; they were not application failures.
