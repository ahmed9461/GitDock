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
- P2.2 typed `GitHubRestClient`, typed response/page/rate models, safe error translation, canonical-host pagination, and safe retry policy.
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
- P3.3 typed repository-administration gateway/service for personal and authorized organization creation, repository settings updates, archive/unarchive, visibility changes, default-branch changes, and deletion.
- P3.3 durable `audit_log` persistence plus Alembic migration `0005_audit_log` for repository-administration write outcomes.
- P3.3 remote-state reconciliation for uncertain create/update/delete outcomes so write-like GitHub calls are not blindly retried or mislabeled.
- P3.3 Arabic Telegram repository-creation wizard and repository-settings UX with centralized renderers, keyboards, callbacks, FSM states, and thin router handlers.
- P3.3 one-time server-side confirmation cancellation so edit/back/cancel consumes pending authority and old Telegram buttons cannot execute later.
- P3.3 organization-create, reconciliation, confirmation-cancellation, gateway/service, deletion-negative-path, and Telegram UI coverage expanding the suite from 97 to **117 tests**.
- P4.1 typed GitHub Contents gateway and file-browser/read/write services for directory browsing, file preview, ref selection, bounded download, create/update/replace/delete, stale-write protection, reconciliation, and audit.
- P4.1 real Arabic Telegram `📁 الملفات` UX with directory/file pagination, branch/ref input, create/edit/upload/replace/download/delete flows, diff/preview, and compact short-session callbacks.
- P4.1 durable `file_write_sessions` staging plus Alembic migration `0006_file_write_sessions`; staged content survives restart briefly for reviewed writes and is scrubbed when authority is consumed, cancelled, superseded, expired, or pruned.
- P4.1 explicit same-path staging supersession regression coverage; full suite is now **148 tests**.
- P4.1 D-020 decision documenting the stage → preview → confirm → revalidate → scoped-token → single-write → reconcile → audit lifecycle.

### Changed

- Canonical GitHub REST request metadata remains centralized: API `2026-03-10`, `application/vnd.github+json`, and `User-Agent: GitDock/0.1`.
- GitHub HTTP timeout/retry/page-limit constants remain centralized rather than handler-local.
- GitHub pagination/absolute REST targets remain restricted to canonical HTTPS `api.github.com`; the gateway is not a generic URL fetcher.
- Repository UI callbacks carry compact versioned repository IDs plus navigation context rather than arbitrary repository `owner/name` strings.
- Repository list/detail data flows through application services and the P2.2 transport instead of Telegram handlers issuing GitHub HTTP.
- GitHub repository detail is refreshed from GitHub before display; local repository cache is navigation/context state only.
- Public search discovery uses its own Tier 0 ephemeral session/result context instead of treating search results as installed repository cache/authorization context.
- P3.1 search detail exposes `📥 أوامر التنزيل` only as a safe placeholder; actual clone/update/setup/run command generation remains P4.3.
- P3.2 OAuth completion may persist durable GitHub user credentials when the flow is the explicit durable user-authorization use case; existing installation-binding trust checks remain unchanged.
- Connected Home exposes `👤 حساب GitHub` as a real account-management entry point.
- Returning Home invalidates outstanding local-disconnect confirmations so old Telegram messages cannot retain active destructive authorization.
- GitHub installation binding and durable GitHub user authorization remain explicitly separate states in service/UI semantics.
- P3.3 runtime composition reuses the established confirmation service, durable user-token provider, repository read/cache service, and GitHub REST transport instead of creating parallel auth or persistence stacks.
- P3.3 personal/organization repository creation uses durable GitHub user OAuth context; repository update/delete uses a repository-scoped installation token requesting `administration: write` only for the selected repository.
- P3.3 sensitive write previews and Telegram buttons are transport/UI only; execution remains bound to persisted server-side confirmation and refreshed repository preconditions.
- P3.3 write-like GitHub operations remain no-retry by default; uncertain outcomes reconcile remote state before GitDock reports final applied/failed/uncertain state.
- P4.1 reads use repository-scoped `contents: read`; ordinary writes use `contents: write`; writes under `.github/workflows/` additionally require `workflows: write`.
- P4.1 repository paths stay in server/FSM context instead of Telegram callback data; callbacks transport short browse session IDs, indexes, and opaque confirmation tokens.
- P4.1 staged file bytes are temporary restart-safety data, not audit data; the 15-minute staging lifecycle scrubs content on consume/cancel/supersede/expiry/prune.
- Runtime locks were refreshed for current cache-disabled CI resolution: transitive `anyio` moved to `4.15.1` and `multidict` to `6.8.0`; direct runtime pins remain unchanged.

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
- P3.2 initial Alembic migration failure caused by revision identifier `0004_user_authorization_lifecycle` exceeding Alembic's default `alembic_version.version_num` length; revision shortened to `0004_user_auth`.
- P3.2 Ruff formatting, one E501 lint finding, and one mypy variable-shadowing inference issue were corrected at source.
- P3.3 branch CI formatting/Unicode/unused-context findings were corrected at source without weakening gates.
- P3.3 update-message router no longer keeps unused navigation variables after token-aware confirmation cancellation made them unnecessary.
- P4.1 Telegram formatting/lint/type findings were corrected at source, including a real `message.bot` guard and typed reply markup rather than broad ignores.
- P4.1 runtime-lock drift exposed after Actions dependency caches were disabled was reconciled and both PEP 751 files again match fresh `pip lock` output byte-for-byte.
- P4.1 final lock-file newline mismatch was fixed instead of weakening byte-for-byte lock verification.

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
- P3.2 refresh snapshots `credential_generation` before external refresh and persists rotated credentials only if current durable generation/preconditions still match.
- P3.2 local-disconnect confirmation is DB-backed, one-time, expiring, and bound to GitDock user + operation + account identity + credential generation + current installation IDs.
- Reauthorization/install-set change makes an older disconnect confirmation stale; stale/cancelled/reused/invalid confirmation removes nothing.
- Local disconnect clears only GitDock-local credentials/bindings/cache/pending state and does **not** uninstall/revoke the GitHub App remotely.
- P3.3 creation/update/deletion all require persisted server-side confirmation; update is Tier 2 and delete is Tier 3 with exact typed `owner/name` validation.
- P3.3 repository update/delete installation credentials are scoped to selected repository and `administration: write`; create uses the required narrower durable user-context path.
- P3.3 audit records omit credentials/tokens/raw upstream auth bodies; uncertain writes reconcile instead of replaying.
- P4.1 validates repository paths/refs before GitHub calls and binds write staging to user, repository/installation, branch, branch head, path, expected file SHA, desired blob/content digest, operation, risk, and expiry.
- P4.1 staged file body bytes may exist temporarily in `file_write_sessions` for up to 15 minutes; content is cleared on consume/cancel/same-target supersession/expiry/prune and never copied into audit metadata.
- P4.1 create requires target absence; update/delete require exact current expected file SHA; branch HEAD must still match the staged snapshot.
- P4.1 ordinary writes use repository-scoped `contents: write`; workflow paths additionally require `workflows: write`.
- P4.1 write-like GitHub requests are issued once and uncertain outcomes reconcile remote state rather than blindly replaying.

### Verification

P1:

- PR #2 CI `33345131414` — green.
- Post-merge `main` CI `33345193470` — green.

P2.1:

- final PR #5 CI `33348768686` — green.
- squash merge `81dfaf406d046205b39980d6a64c681ea3ab18c6`.
- post-merge `main` CI `33348851085` — green.

P2.2:

- implementation CI `33406986504` — green.
- final PR #7 head CI `33409670775` — green.
- squash merge `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`.
- post-merge `main` CI `33409825480` — green.

P2.3:

- implementation CI `33423169021` — green.
- documentation-head CI `33424505117` — green.
- PR #8 CI `33424652835` — green.
- squash merge `939d218d76fd87f3ba6cf0a80a89b4a816aac557`.
- post-merge `main` CI `33424799759` — green.
- governance closeout merge `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`; post-closeout CI `33444410513` — green.

P3.1:

- implementation CI `33453960817` — green.
- documentation-head CI `33454438202` — green.
- PR #10 CI `33454524953` — green.
- squash merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`.
- post-feature `main` CI `33454619065` — green.
- governance closeout merge `ef2c5f618102063df8166f84b4828243f5efb5c6`; post-closeout CI `33454972020` — green.

P3.2:

- implementation `5068b58ec41fb5ac417408d3a535bbb5d66207fc` — CI `33515291600` green;
- docs head `492183bfba311827a965153eff61747bfabf76ed` — CI `33517270731` green;
- PR #12 CI `33527318485` green;
- squash merge `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`;
- post-feature `main` CI `33527484948` green;
- governance closeout `aeb003cec79d1952dc80a520c03a4eee819872bc`.

P3.3:

- implementation `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945` green;
- docs head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482` green;
- PR #14 CI `33891899602` green;
- squash merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature `main` CI `33892100584` green;
- suite: **117 tests**, mypy 72 source files, migration `0005_audit_log`, audit/secrets/locks green.

P4.1:

- implementation head `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010` green;
- documentation-synchronized head `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457` green;
- non-draft PR #16 CI `34641248664` — green on unchanged `mergeable=true` head;
- squash merge commit `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6` with expected-head protection;
- post-feature `main` CI `34641411838` — green;
- Python 3.12 and 3.13 each passed Ruff format/lint, mypy, **148 tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff;
- mypy clean on **87 source files**;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade including `0006_file_write_sessions` passed;
- `pip-audit` reported no known runtime vulnerabilities;
- no secret-scan findings and no PEP 751 lock drift;
- governance closeout records P4.1 ✅ and hands implementation to P4.2.

### Known maintenance warnings

- Green verification reports a Starlette/FastAPI `TestClient` deprecation warning for current `httpx` integration/future `httpx2` direction.
- Starlette tests surface AnyIO's deprecated `anyio.abc.BlockingPortal` alias.
- Alembic reports the `path_separator` warning because `alembic.ini` does not explicitly set it for `prepend_sys_path`.

These warnings are recorded rather than hidden and do not currently fail the build.

Operational note: `main` intentionally disabled GitHub Actions dependency caches on 2026-09-11 (`c5d8b10557deda0bb2c268bf28adb9eed0151e64`). Fresh resolver output exposed transitive runtime-lock drift, which P4.1 refreshed and reverified rather than bypassing the lock gate.
