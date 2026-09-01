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
- P2.2 typed `GitHubResponse[T]`, `GitHubPage[T]`, `GitHubRateLimit`, validated pagination metadata, safe error translation, canonical-host pagination, and safe retry policy.
- P2.3 typed installed-repository read gateway/model, minimal `repositories_cache` migration `0003`, owner identity service, runtime composition, Arabic Home/list/filter/detail UI, compact callbacks, and setup/OAuth callback wiring.
- P2.3 repository filters for all/private/public/active/archived/source/fork and verified suite growth to **65 tests**.
- P3.1 typed public GitHub repository-search gateway/model over the canonical REST transport.
- P3.1 validated search service with stars/update sorting, language/min-stars/owner/topic/archive filters, stable pagination, Arabic search UI, opaque active-session callbacks, stale-session rejection, and GitHub detail re-fetch.
- P3.1 public search remains usable without a bound installation and keeps public discovery state separate from installed `repositories_cache`; verified suite grew to **83 tests**.
- P3.2 authenticated GitHub user identity resolution through `GET /user` for durable user-context authorization.
- P3.2 expiry-aware durable user access-token lifecycle with encrypted access/refresh storage and refresh-token rotation.
- P3.2 `credential_generation` concurrency guard so stale refresh/disconnect work cannot overwrite or delete newer authorization state.
- P3.2 general DB-backed `pending_confirmations` model/service with opaque one-time confirmation tokens, expiry, target fingerprint, payload, risk tier, and consumed state.
- P3.2 Alembic migration `0004_user_auth` for credential-generation and durable confirmation state.
- P3.2 Arabic `👤 حساب GitHub` screen with activate/re-authorize, refresh, and isolated `🔌 قطع الربط المحلي` confirmation flow.
- P3.2 legacy-installation local disconnect support for P2.3 bindings that predate durable user-token persistence.
- P3.2 integration coverage for standalone OAuth state/PKCE -> GitHub identity -> encrypted durable credentials without reinstalling the GitHub App.
- P3.2 service/UI/security coverage expanding the suite from 83 to **97 tests**.

### Changed

- Canonical GitHub REST request metadata remains centralized: API `2026-03-10`, `application/vnd.github+json`, and `User-Agent: GitDock/0.1`.
- GitHub HTTP timeout/retry/page-limit constants remain centralized rather than handler-local.
- GitHub pagination/absolute REST targets remain restricted to canonical HTTPS `api.github.com`; the gateway is not a generic URL fetcher.
- Repository UI callbacks carry compact versioned repository IDs plus navigation context rather than arbitrary repository `owner/name` strings.
- Repository list/detail data flows through application services and the P2.2 transport instead of Telegram handlers issuing GitHub HTTP.
- GitHub repository detail is refreshed from GitHub before display; local repository cache is navigation/context state only.
- Public search discovery uses its own Tier 0 ephemeral session/result context instead of treating search results as installed repository cache/authorization context.
- P3.1 search detail exposes **📥 أوامر التنزيل** only as a safe placeholder; actual clone/update/setup/run command generation remains P4.3.
- P3.2 OAuth completion may now persist durable GitHub user credentials when the flow is the explicit durable user-authorization use case; the existing installation-binding trust checks remain unchanged.
- Connected Home now exposes `👤 حساب GitHub` as a real account-management entry point.
- Returning Home invalidates outstanding local-disconnect confirmations so old Telegram messages cannot retain active destructive authorization.
- GitHub installation binding and durable GitHub user authorization remain explicitly separate states in service/UI semantics.
- Runtime dependencies remain unchanged by P3.1/P3.2; existing PEP 751 locks remain byte-for-byte verified on Python 3.12 and 3.13.

### Fixed

- aiogram Router reuse across multiple Dispatcher instances.
- OAuth authorization-state atomic consumption on SQLite and expired ORM-object access in lifecycle tests.
- P2.1 PEP 751 final-newline drift.
- P2.2 initial Ruff formatting/import ordering and modern Python generic-syntax findings caught by CI before type/test gates.
- P2.3 Ruff formatting/import/Unicode-lint findings without changing intended Arabic/emoji UI.
- P2.3 FastAPI callback route registration failure by explicitly disabling response-model inference for Response-returning setup/OAuth routes.
- P3.1 Ruff formatting and unused-import findings caught by branch CI before final verification.
- Search Home/start navigation clears transient FSM state so abandoned query/filter input cannot be interpreted after returning to the main menu.
- P3.1 navigation tests model aiogram async child methods correctly rather than failing on non-awaitable mock attributes.
- P3.2 initial Alembic migration failure caused by revision identifier `0004_user_authorization_lifecycle` exceeding Alembic's default `alembic_version.version_num` length. The revision was correctly shortened to `0004_user_auth` instead of widening Alembic's internal version table for an unnecessarily long label.
- P3.2 Ruff formatting, one E501 lint finding, and one mypy variable-shadowing inference issue were corrected at their source while preserving the intended auth behavior.

### Security

- GitHub App least-privilege authentication remains the primary credential model.
- Raw setup/install `installation_id` remains untrusted until dual App/user-context identity verification.
- OAuth state remains one-time/server-side with only SHA-256 digest persisted; PKCE verifier and persisted user credentials are encrypted with versioned keys.
- GitHub gateway errors omit raw GitHub response bodies and credentials while retaining safe status/request/rate metadata.
- Pagination rejects external hosts, protocol-relative URLs, URL credentials, fragments, and non-canonical targets before network I/O; outbound gateway redirects are not followed automatically.
- GET/HEAD may retry bounded transient failures; write-like methods are never blindly retried by default.
- P2.3 repository callbacks resolve server-side inside the current GitDock user and active installation context; cache existence is not authorization proof.
- `repositories_cache` stores no token/OAuth/PKCE/private-key material and is explicitly non-authoritative.
- P3.1 public search uses opaque active session IDs and does not insert public results into installed authorization/cache context.
- P3.2 durable access/refresh credentials use the existing versioned encrypted credential store; token material is never placed in Telegram callback data or user-facing copy.
- P3.2 refresh snapshots `credential_generation` before external refresh and persists the rotated credential pair only if the current durable generation/preconditions still match.
- P3.2 local-disconnect confirmation is DB-backed, one-time, expiring, and bound to GitDock user + operation + account identity + credential generation + current installation IDs.
- Reauthorization or installation-set change makes an older disconnect confirmation stale; stale, cancelled, reused, or invalid confirmation removes nothing.
- Local disconnect clears only GitDock-local credentials/bindings/cache/pending state and explicitly **does not uninstall or revoke the GitHub App remotely**.
- P3.2 introduces no repository write/admin capability and does not expand the GitHub App to a broad permission model.

### Verification

P1:

- PR #2 CI `33345131414` — green.
- Post-merge `main` CI `33345193470` — green.

P2.1:

- final PR #5 CI `33348768686` — green.
- squash merge `81dfaf406d046205b39980d6a64c681ea3ab18c6`.
- post-merge `main` CI `33348851085` — green.
- Python 3.12/3.13: 37 tests plus format/lint/mypy/compile/audit/secret/lock gates; PostgreSQL 17 migration round trip passed.

P2.2:

- implementation CI `33406986504` — green.
- final PR #7 head CI `33409670775` — green.
- squash merge `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`.
- post-merge `main` CI `33409825480` — green.
- suite at P2.2: 49 tests; Python 3.12/3.13 and PostgreSQL 17 green.

P2.3:

- implementation CI `33423169021` — green.
- documentation-head CI `33424505117` — green.
- PR #8 CI `33424652835` — green.
- squash merge `939d218d76fd87f3ba6cf0a80a89b4a816aac557`.
- post-merge `main` CI `33424799759` — green.
- governance closeout PR #9 merge `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`; post-closeout `main` CI `33444410513` — green.
- Python 3.12/3.13 passed Ruff format/lint, mypy, **65 tests**, compile, audit, secret scan, locks; PostgreSQL migration round trip passed.

P3.1:

- implementation CI `33453960817` — green.
- documentation-head CI `33454438202` — green.
- PR #10 CI `33454524953` — green.
- squash merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`.
- post-feature `main` CI `33454619065` — green.
- governance closeout PR #11 merge `ef2c5f618102063df8166f84b4828243f5efb5c6`; post-closeout `main` CI `33454972020` — green.
- suite at P3.1: **83 tests**, all configured Python 3.12/3.13 and PostgreSQL gates green.

P3.2 pre-merge implementation:

- foundation validation head `2faed69d8333c019ec1f307583434d598d2c5c4e` — CI `33459209919` fully green before UI wiring;
- complete implementation head before documentation synchronization `5068b58ec41fb5ac417408d3a535bbb5d66207fc` — CI **`33515291600` fully green**;
- Python 3.12: Ruff format/lint, mypy, **97 tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock verification passed;
- Python 3.13: the same configured quality/security/lock gates passed;
- PostgreSQL 17 Alembic upgrade -> downgrade -> upgrade including migration `0004_user_auth` passed;
- `pip-audit` reported no known runtime vulnerabilities;
- no secret-scan findings and no PEP 751 lock drift;
- P3.2 remains pre-merge until documentation-head CI, non-draft PR, squash merge, post-merge `main` CI, and governance closeout are recorded.

### Known maintenance warnings

- Green P3.2 verification continues to report a Starlette/FastAPI `TestClient` deprecation warning for the current `httpx` integration/future `httpx2` direction.
- Green P3.2 verification continues to report Alembic's `path_separator` deprecation warning because `alembic.ini` does not explicitly set `path_separator` for `prepend_sys_path`.

These warnings are recorded rather than hidden; they do not currently fail the build.

Operational note: earlier zero-step GitHub Actions failures were caused by exhausted private-repository hosted-runner quota and stopped after the repository became public; they were not application failures.
