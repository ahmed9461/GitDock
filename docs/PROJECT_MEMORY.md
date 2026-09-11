# GitDock — Project Memory

Purpose: durable facts that future sessions must remember. This is not a task list.

Last updated: 2026-09-11

## Identity

- Product: **GitDock**.
- Repository: `ahmed9461/GitDock`.
- Telegram-first GitHub management/control bot.
- v1 user-facing language: Arabic; code/technical identifiers remain English/native.
- v1 boundary: one configured Telegram owner, with services/persistence kept multi-user-ready.

## Product intent

GitDock is broader than notifications. Planned v1 covers repository search/administration, repository contents/file writes, branches/commits, webhooks/notifications, Issues/PRs, Actions, releases, clone/setup/run command generation, and safe ZIP/project synchronization.

## Canonical architecture direction

- Python 3.12+; CI verifies 3.12 and 3.13.
- aiogram 3.x Telegram layer.
- FastAPI HTTP ingress.
- httpx behind GitHub auth/gateway boundaries.
- async SQLAlchemy 2.x + Alembic.
- PostgreSQL production; SQLite only for portable tests/development.
- GitHub remains source of truth.
- Telegram handlers remain thin; OAuth/token/DB/risk rules belong in services/auth/persistence.
- Important multi-step confirmation/write/event state is durable when restart safety matters.
- No broad long-lived PAT as normal credential model.

## Verified phase history

### P1 — foundation ✅

Merged through PR #2; post-merge main CI `33345193470` green.

Durable invariant: create a fresh aiogram Router for each Dispatcher; do not reuse a module-global Router across Dispatcher instances.

### P2.1 — GitHub App authentication ✅

Merge `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge CI `33348851085` green.

Durable facts:

- GitHub App primary auth.
- RS256 App JWT.
- REST API version `2026-03-10`.
- short-lived expiry-aware installation tokens.
- OAuth with PKCE S256.
- raw OAuth state never persisted; SHA-256 digest only.
- PKCE verifier and durable user credentials encrypted with versioned keys.
- capability → permission/token-context mapping centralized.
- setup/install `installation_id` is untrusted until App + authenticated-user identities independently match and suspension/ownership checks pass.

### P2.2 — GitHub gateway ✅

Merge `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge CI `33409825480` green.

Durable facts:

- `GitHubRestClient` is canonical REST transport.
- ordinary services/Telegram handlers do not issue raw GitHub HTTP.
- canonical headers/version/User-Agent centralized.
- safe typed response/page/rate metadata.
- absolute API/pagination targets restricted to canonical HTTPS `api.github.com`.
- stable safe error categories; no raw body echo.
- GET/HEAD bounded transient retries; writes no retry by default.
- generic transport does not automatically follow redirects.

### P2.3 — Home + installed repository read ✅

Feature merge `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; closeout `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`.

Durable facts:

- `repositories_cache` is minimal callback/navigation context, never source of truth or authority.
- cache stores no credentials/auth secrets/raw errors.
- repository callbacks use stable numeric repository IDs + compact navigation context.
- selection resolves inside current GitDock user/active installation.
- detail re-fetches GitHub before render.
- P2.3 is Tier 0 read-only.

### P3.1 — public repository search ✅

Feature merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`; closeout `ef2c5f618102063df8166f84b4828243f5efb5c6`.

Durable facts:

- public search works without bound installation.
- canonical REST transport reused.
- search state is separate from installed cache/authorization state.
- sort/filter/pagination + opaque active search sessions.
- stale search sessions fail closed.
- detail resolves from active result context then re-fetches GitHub.
- Home/start clears transient search FSM state.
- `📥 أوامر التنزيل` remains P4.3 work.

### P3.2 — durable GitHub user context ✅

Implementation CI `33515291600`; docs CI `33517270731`; PR #12 CI `33527318485`; feature merge `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`; closeout `aeb003cec79d1952dc80a520c03a4eee819872bc`.

Verified suite at P3.2: 97 tests plus all quality/security/lock/PostgreSQL gates.

Durable facts:

- durable user identity comes from authenticated `GET /user`.
- standalone authorization reuses P2.1 one-time state + PKCE.
- durable access/refresh credentials use versioned encrypted store.
- `credential_generation` guards stale refresh/disconnect concurrency.
- `pending_confirmations` is general DB-backed one-time confirmation storage.
- local-disconnect target binds account/generation/installations.
- stale/expired/reused/cancelled confirmation does nothing.
- Home invalidates outstanding disconnect authority.
- local disconnect removes GitDock-local credentials/bindings/cache/pending state only; it does **not** uninstall/revoke the GitHub App remotely.
- installation binding and durable user authorization remain separate concepts.

### P3.3 — repository administration ✅

Feature chain:

- implementation `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945`;
- docs head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482`;
- PR #14 CI `33891899602`;
- squash merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature main CI `33892100584`.

Verified suite at P3.3: 117 tests, mypy 72 source files, migration `0005_audit_log`, all gates green.

Durable facts:

- `RepositoryAdminService` owns create/update/delete planning, confirmation, credential selection, refreshed preconditions, reconciliation, cache synchronization, and audit.
- personal/org create uses durable GitHub user OAuth context.
- update/delete uses installation token scoped to selected repository with `administration: write`.
- create Tier 1; update Tier 2; delete Tier 3 + exact typed `owner/name`.
- edit/back/cancel consumes pending confirmation.
- stale/expired/reused/cancelled/wrong-target/wrong-name fail closed.
- sensitive update/delete re-fetch current repository state.
- no blind write retry; uncertain outcome reconciles remote state.
- unresolved result remains explicit `UNCERTAIN`.
- `audit_log` never stores credentials/tokens/raw upstream auth bodies.
- current Telegram create wizard defaults to personal account; org create support exists at gateway/service boundary rather than a fake UI selector.

### P4.1 — file browser + stale-safe single-file writes ✅

Final feature-delivery verification chain:

- implementation head `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010` green;
- documentation-synchronized head `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457` green;
- non-draft PR #16 CI `34641248664` green on unchanged mergeable head;
- squash merge `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6` with expected-head protection;
- post-feature `main` CI `34641411838` green.

Verified P4.1 contract:

- **148 tests** on Python 3.12 and 3.13;
- Ruff format/lint green;
- mypy clean on **87 source files**;
- compile green;
- `pip-audit` no known runtime vulnerabilities;
- `detect-secrets` no findings;
- PEP 751 locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade through `0006_file_write_sessions`.

Durable P4.1 facts:

- typed GitHub Contents gateway remains on canonical REST transport.
- real Arabic `📁 الملفات` flow supports directory pagination, parent navigation, branch/tag/SHA read selection, text preview pages, binary/large fallback, and bounded download.
- long repository paths do not travel in callback data; browser callbacks use short server-resolved session/index context.
- create/edit/upload/replace/delete never write directly from the initial UI action; they stage a reviewable plan.
- `file_write_sessions` is restart-safe staging for one-file writes.
- staging binds user, installation/repository, repository full name/default branch, operation, branch, path, branch-head SHA, expected file SHA, desired Git blob SHA/content digest, commit message, risk tier, expiry, and consumed state.
- staged create/update body bytes may be persisted temporarily for at most **15 minutes** so explicit review survives restart.
- staged `content_bytes` is cleared on consume, cancel, same-target supersession, expiry cleanup/prune, or integrity-failure consumption.
- staged content is not audit data.
- on consume, content digest + Git blob SHA integrity are recomputed before execution.
- a newer staging for the same user/repository/branch/path supersedes the older staging and clears its stored content; regression coverage is explicit.
- before any write, GitDock re-resolves repository context and requires the staged repository full name/default branch, current branch HEAD, and current file presence/SHA preconditions still match.
- create requires target still absent; update/delete require exact expected file SHA.
- archived repositories are rejected for writes.
- ordinary file writes use repository-scoped `contents: write`; `.github/workflows/*` additionally requires `workflows: write`.
- create/update on default branch are Tier 2; non-default create/update Tier 1; delete Tier 2.
- GitHub write call is issued once; uncertain create/update/delete outcomes reconcile remote file state and never blindly replay PUT/DELETE.
- response SHA mismatch remains `UNCERTAIN`.
- file audit stores branch/path/expected SHA/desired blob SHA/risk/workflow/request/commit/reconciliation metadata only; never file bodies or credentials.
- migration `0006_file_write_sessions` is in the verified PostgreSQL chain.
- Actions dependency-cache removal exposed normal transitive resolver drift (`anyio 4.15.1`, `multidict 6.8.0`); runtime locks were refreshed while direct pins remained unchanged and then verified byte-for-byte.
- D-020 records the single-file staged-intent architecture.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- PEP 751 runtime locks:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- CI regenerates and diffs each lock; drift fails the build.
- Do not weaken lock/audit/secret checks to obtain green CI.

## GitHub Actions operational memory

Earlier private-repository hosted-runner quota exhaustion caused zero-step failures; do not diagnose a zero-step run as code failure without checking whether runner steps began.

On 2026-09-11 `main` commit `c5d8b10557deda0bb2c268bf28adb9eed0151e64` disabled dependency caches. Fresh resolution then exposed legitimate transitive lock drift, which P4.1 fixed rather than bypassing the lock gate.

Workflow push branches currently include `main`, `feat/**`, `fix/**`, `refactor/**`, and `security/**`; `docs/**` push alone does not trigger CI. Use a CI-enabled branch name for governance branches when push-head CI is required.

Known connector caveat from earlier phases: Draft → Ready GraphQL path previously requested nonexistent `Repository.fullDatabaseId`. Safe workaround was replacement non-draft PR on unchanged verified head, never CI bypass.

## Known non-blocking maintenance warnings

- FastAPI/Starlette `TestClient` deprecation toward future `httpx2` direction.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

These are maintenance debt, not hidden failures.

## GitHub write strategy

- Simple one-file writes: Contents API with durable staging and stale branch/file SHA protection.
- Repository administration: operation-specific credential context + persisted confirmation + refreshed preconditions + one write + reconciliation + audit.
- Multi-file/ZIP sync: future coherent reviewable batch commit, review branch by default.
- Direct default-branch mass replacement is not default.
- `.github/workflows/*` file changes require Workflows capability.
- Never blindly replay uncertain/destructive writes.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing current navigation message where practical.
- Use compact inline keyboards and consistent Home/Cancel/Back.
- Long repository paths do not belong in callback data.
- Home/start invalidates transient flows where continuing would surprise the user.
- High-impact/sensitive authority is server-side, expiring, and one-time where required.
- Back/Edit/Cancel after a write preview must invalidate staged/pending authority rather than only hiding UI.
- Repository deletion remains exact-name gated Tier 3.
- Long logs/files use pagination or document delivery.

## Safety memory

- Never expose/commit tokens, keys, client/webhook secrets, OAuth code/state, PKCE verifiers, encryption keys, or raw auth response bodies.
- Do not implement arbitrary shell execution as normal bot capability.
- Clone/setup/run generates commands; it does not silently execute repository instructions.
- No normal v1 force-push UI.
- High-impact multi-step operations must not depend only on volatile FSM state.
- Audit GitHub writes without secret/file-body material.
- GitHub remains source of truth.
- Pagination/download helpers must not become arbitrary outbound URL fetchers.
- Stale callbacks/preconditions fail closed.
- Uncertain writes remain uncertain unless reconciliation proves final state.

## Development governance memory

`AGENTS.md` is mandatory. Green tests with stale project state are not Done. Successful work updates, as applicable:

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_MEMORY.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- affected architecture/security/constants/decision/test/UX docs.

P4.1 feature delivery is merged and post-feature `main` verified. This closeout records P4.1 as complete. Once the closeout PR itself is green, squash-merged, and post-closeout `main` CI is green, the exact implementation task is P4.2.

## Next milestone / handoff

**P4.2 — Branch/commit tools** is next after this closeout lands.

Scope:

- list branches;
- search/filter branches where useful;
- create branch from explicit known base ref/SHA;
- recent commits;
- commit detail and safe diff summary;
- compare refs;
- compact Telegram callback/navigation context;
- stale-safe branch-create preconditions and explicit target/base preview where appropriate;
- preserve no-force-push v1 policy.

## Do not forget later

- P4.3 generates fresh-clone and existing-clone update commands by OS and labels inference confidence.
- Notification preferences are per repository/event type.
- Actions includes status/jobs/steps/logs/artifacts/dispatch/retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
