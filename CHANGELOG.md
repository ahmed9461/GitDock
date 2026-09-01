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
- P3.1 typed public GitHub repository-search gateway/model over the canonical REST transport.
- P3.1 search service with validated query construction, stars/update sorting, language/min-stars/owner/topic/archive filters, and stable pagination.
- P3.1 Arabic Telegram search prompt/results/filter/detail screens plus `/search` entry point.
- P3.1 compact opaque search-session callbacks, active-session rejection of stale search buttons, and current-result detail resolution followed by GitHub re-fetch.
- P3.1 search remains usable without a bound GitHub installation and keeps public discovery state separate from installed `repositories_cache`.
- P3.1 navigation coverage that clears transient search FSM state on `/start` and Home.
- P3.1 contract/service/UI/session/navigation coverage expanding the suite from 65 to **83 tests**.

### Changed

- Canonical GitHub REST request metadata remains centralized: API `2026-03-10`, `application/vnd.github+json`, and `User-Agent: GitDock/0.1`.
- GitHub HTTP timeout/retry/page-limit constants remain centralized rather than handler-local.
- GitHub pagination/absolute REST targets remain restricted to canonical HTTPS `api.github.com`; the gateway is not a generic URL fetcher.
- P2.2 is recorded as squash-merged through PR #7 as `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`, with post-merge `main` CI `33409825480` green.
- P2.3 is recorded as squash-merged through PR #8 as `939d218d76fd87f3ba6cf0a80a89b4a816aac557`, with post-merge `main` CI `33424799759` green.
- Repository UI callbacks carry compact versioned repository IDs plus navigation context rather than arbitrary repository `owner/name` strings.
- Repository list/detail data flows through application services and the P2.2 transport instead of Telegram handlers issuing GitHub HTTP.
- GitHub repository detail is refreshed from GitHub before display; local repository cache is navigation/context state only.
- Public search discovery uses its own Tier 0 ephemeral session/result context instead of treating search results as installed repository cache/authorization context.
- P3.1 search detail exposes **📥 أوامر التنزيل** only as a safe placeholder; actual clone/update/setup/run command generation remains P4.3.
- Runtime dependencies remain unchanged by P3.1; existing PEP 751 locks remain byte-for-byte verified on Python 3.12 and 3.13.

### Fixed

- aiogram Router reuse across multiple Dispatcher instances.
- OAuth authorization-state atomic consumption on SQLite and expired ORM-object access in lifecycle tests.
- P2.1 PEP 751 final-newline drift.
- P2.2 initial Ruff formatting/import ordering and modern Python generic-syntax findings caught by CI before type/test gates.
- P2.3 Ruff formatting/import/Unicode-lint findings without changing the intended Arabic/emoji UI.
- P2.3 FastAPI callback route registration failure by explicitly disabling response-model inference for Response-returning setup/OAuth routes.
- P3.1 Ruff formatting and unused-import findings caught by branch CI before final verification.
- Search Home/start navigation now clears transient FSM state so abandoned query/filter input cannot be interpreted after returning to the main menu.
- P3.1 navigation tests now model aiogram async child methods correctly rather than failing on non-awaitable mock attributes.

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
- P3.1 public search uses opaque session IDs and active-session/result-context checks so stale search callbacks fail closed.
- P3.1 public search results are not inserted into installed `repositories_cache` and do not grant installation/repository authorization.
- P3.1 remains Tier 0 read-only and introduces no repository write/admin permission.

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

P2.3:

- implementation-head CI `33423169021` — green.
- documentation-synchronized branch-head CI `33424505117` — green.
- PR #8 CI `33424652835` — green.
- squash merge commit: `939d218d76fd87f3ba6cf0a80a89b4a816aac557`.
- post-merge `main` CI `33424799759` — green.
- governance closeout PR #9 merged as `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`; post-closeout `main` CI `33444410513` — green.
- Python 3.12 and 3.13 each passed Ruff format/lint, mypy, **65 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff.
- PostgreSQL 17 upgrade -> downgrade -> upgrade including migration `0003` passed.

P3.1:

- implementation head `4a4f00d50e886ab494e2a83f2c649cd64b7398b2` — CI `33453960817` green.
- final documentation-synchronized feature head `14e149ea307871abd8406ffc6212fe062ead9098` — branch CI `33454438202` green.
- non-draft PR #10 CI `33454524953` — green and mergeable on the unchanged head.
- squash merge commit: `d822338fcc1546418ed2100cc9534cdc71a6bcbe`.
- post-merge `main` CI `33454619065` — green.
- Python 3.12 and 3.13 each passed Ruff format/lint, mypy, **83 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff.
- PostgreSQL 17 Alembic upgrade -> downgrade -> upgrade passed.
- `pip-audit` reported no known runtime vulnerabilities.
- P3.1 feature delivery is verified complete; the small `docs/p3-1-closeout` PR records the final governance facts before P3.2 begins.

### Known maintenance warnings

- Green P3.1 verification continues to report a Starlette/FastAPI `TestClient` deprecation warning for the current `httpx` integration/future `httpx2` direction.
- Green P3.1 verification continues to report an Alembic deprecation warning because `alembic.ini` does not yet set explicit `path_separator` for `prepend_sys_path`.

These warnings are recorded rather than hidden; they do not currently fail the build.

Operational note: earlier zero-step GitHub Actions failures were caused by exhausted private-repository hosted-runner quota and stopped after the repository became public; they were not application failures.
