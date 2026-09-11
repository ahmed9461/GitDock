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

GitDock is broader than notifications. Planned v1 covers repository search/administration, repository contents/file writes, branches/commits, clone/setup/run command generation, webhooks/notifications, Issues/PRs, Actions, releases, and safe ZIP/project synchronization.

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
- Ordinary feature code never bypasses the canonical `GitHubRestClient` with a parallel raw HTTP stack.

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
- canonical headers/version/User-Agent centralized.
- safe typed response/page/rate metadata.
- absolute API/pagination targets restricted to canonical HTTPS `api.github.com`.
- stable safe error categories; no raw body echo.
- GET/HEAD bounded transient retries; write-like methods no retry by default.
- generic transport does not automatically follow redirects.

### P2.3 — Home + installed repository read ✅

Feature merge `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; closeout `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`.

Durable facts:

- `repositories_cache` is minimal callback/navigation context, never source of truth or authority.
- cache stores no credentials/auth secrets/raw errors.
- repository callbacks use stable numeric repository IDs + compact navigation context.
- selection resolves inside current GitDock user/active installation.
- detail re-fetches GitHub before render.

### P3.1 — public repository search ✅

Feature merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`; closeout `ef2c5f618102063df8166f84b4828243f5efb5c6`.

Durable facts:

- public search works without bound installation.
- search state is separate from installed cache/authorization state.
- sort/filter/pagination + opaque active search sessions.
- stale search sessions fail closed.
- detail resolves from active result context then re-fetches GitHub.
- Home/start clears transient search FSM state.

### P3.2 — durable GitHub user context ✅

Implementation CI `33515291600`; docs CI `33517270731`; PR #12 CI `33527318485`; feature merge `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`; closeout `aeb003cec79d1952dc80a520c03a4eee819872bc`.

Durable facts:

- durable user identity comes from authenticated `GET /user`.
- standalone authorization reuses state + PKCE without reinstalling App.
- access/refresh tokens encrypted before DB persistence; expiry preserved.
- `credential_generation` guards stale refresh/disconnect concurrency.
- `pending_confirmations` is general DB-backed one-time confirmation storage.
- local disconnect removes GitDock-local credentials/bindings/cache/pending state only; it does **not** uninstall/revoke the GitHub App remotely.

### P3.3 — repository administration ✅

Feature chain:

- implementation `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945`;
- docs head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482`;
- PR #14 CI `33891899602`;
- squash merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature main CI `33892100584`.

Durable facts:

- `RepositoryAdminService` owns planning, confirmation, credential selection, refreshed preconditions, reconciliation, cache synchronization, and audit.
- personal/org create uses durable GitHub user OAuth context.
- update/delete uses installation token scoped to selected repository with `administration: write`.
- create Tier 1; update Tier 2; delete Tier 3 + exact typed `owner/name`.
- edit/back/cancel consumes pending confirmation.
- stale/expired/reused/cancelled/wrong-target/wrong-name fail closed.
- no blind write retry; uncertain outcome reconciles remote state.
- unresolved result remains explicit `UNCERTAIN`.
- `audit_log` never stores credentials/tokens/raw upstream auth bodies.

### P4.1 — file browser + stale-safe single-file writes ✅

Final feature-delivery verification chain:

- implementation head `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010` green;
- documentation-synchronized head `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457` green;
- non-draft PR #16 CI `34641248664` green;
- squash merge `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6`;
- post-feature `main` CI `34641411838` green.

Verified P4.1 contract:

- **148 tests** on Python 3.12 and 3.13;
- Ruff format/lint green;
- mypy clean on **87 source files**;
- compile/audit/secrets/PEP 751 locks green;
- PostgreSQL 17 Alembic round-trip through `0006_file_write_sessions`.

Durable P4.1 facts:

- typed GitHub Contents gateway remains on canonical REST transport.
- Arabic `📁 الملفات` supports directory pagination, parent navigation, branch/tag/SHA reads, text preview pages, binary/large fallback, and bounded download.
- long repository paths never travel in callback data; browser callbacks use short server-resolved session/index context.
- create/edit/upload/replace/delete stage a reviewable plan before write.
- `file_write_sessions` is restart-safe staging for one-file writes.
- staging binds user/repository/installation, branch/path, branch-head SHA, expected file SHA, desired blob/content digest, operation, commit message, risk, expiry, and consumed state.
- staged create/update bytes may persist temporarily for at most 15 minutes and are scrubbed on consume/cancel/same-target supersession/expiry/prune.
- create requires target still absent; update/delete require exact expected file SHA; branch HEAD must still match staged snapshot.
- ordinary file writes use repository-scoped `contents: write`; workflow paths additionally require `workflows: write`.
- write call is issued once; uncertain outcomes reconcile remote file state and never blindly replay.
- file audit stores safe metadata only, never file bodies or credentials.
- D-020 records the single-file staged-intent architecture.

### P4.2 — branch/commit tools implementation verified ✅

Implementation verification head `5a4f7aa4eb557e69665a7311f32c8060e38b1518`; CI `34647181024` fully green.

Verified P4.2 contract:

- **165 tests** on Python 3.12 and 3.13;
- Ruff format/lint green on 157 files;
- mypy clean on **94 source files**;
- compile green;
- `pip-audit` reported no known runtime vulnerabilities;
- `detect-secrets` reported no findings;
- PEP 751 runtime locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic round-trip remains green through `0006_file_write_sessions`.

Durable P4.2 facts:

- `GitHubGitToolsGateway` is the typed endpoint boundary for branches, commits, compare, and create-ref on top of `GitHubRestClient`.
- `GitToolsService` owns branch/commit read orchestration plus branch-create confirmation, stale checks, scoped credential selection, uncertain-result reconciliation, and audit.
- repository dashboard `🌿 الفروع` and `📝 Commits` are now real flows.
- branch listing is GitHub-backed; optional search filters the fetched set case-insensitively without turning cache/FSM state into authority.
- recent commits may target the default branch or an explicit branch/tag/SHA ref.
- commit detail is re-fetched from GitHub and exposes safe metadata plus canonical GitHub URL.
- compare uses encoded refs through the canonical REST gateway; Telegram summary is bounded to the first 10 file rows while preserving returned aggregate counts.
- branch creation is Tier 1 and always begins from an explicit target branch + base ref that resolves to a concrete base commit SHA.
- persisted confirmation fingerprint binds repository ID, target branch, base ref, and base SHA.
- confirm consumes authority once, re-resolves repository context, re-resolves base SHA, and rejects changed base as `STALE` before write.
- target branch absence is checked both before preview and immediately before create; GitDock never converts create into force-update/replace.
- missing base or duplicate target performs no write.
- branch creation requests a repository-scoped installation token with `contents: write` and metadata read only for the selected repository.
- create-ref POST is issued once. On uncertain gateway failure, GitDock re-reads the target branch; exact expected SHA may prove applied, otherwise the result remains `UNCERTAIN`.
- branch-create audit records safe target/base/SHA/risk/request/result metadata only; no credentials.
- callbacks remain compact and carry transport context only; server-side service/confirmation state remains authoritative.
- no normal v1 force-push, force branch update, or branch deletion UI exists.
- direct tests cover branch search, known-base create, duplicate target, missing base, stale base, recent commits, commit detail, compare refs, bounded large comparison rendering, callback round-trips, no-replay semantics, and reconciliation.
- intentional Arabic/emoji UI strings retain Ruff `RUF001` only through narrow per-file ignores on the three P4.2 Telegram UI files; the rule remains active elsewhere.
- the compare contract test checks `httpx.URL.raw_path` for `%2F` encoding because `.path` is decoded by httpx; production URL construction did not require a behavior change.

P4.2 still needs its documentation-head CI, PR CI, protected merge, post-merge main CI, and final governance closeout before P4.3 implementation begins.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- PEP 751 runtime locks:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- CI regenerates and diffs each lock; drift fails the build.
- Do not weaken lock/audit/secret checks to obtain green CI.

## GitHub Actions operational memory

- Earlier hosted-runner quota exhaustion caused zero-step failures; a zero-step run is not evidence of a code failure until runner steps are checked.
- On 2026-09-11 dependency caches were disabled; fresh resolution exposed legitimate transitive lock drift, which P4.1 fixed instead of bypassing the lock gate.
- CI push branches include `main`, `feat/**`, `fix/**`, `refactor/**`, and `security/**`; `docs/**` push alone does not trigger CI. Use a CI-enabled branch for governance branches when push-head verification is required.
- Earlier Draft → Ready GraphQL integration requested a nonexistent field; the safe workaround was replacement non-draft PR on the unchanged verified head, never CI bypass.

## Known non-blocking maintenance warnings

- FastAPI/Starlette `TestClient` deprecation toward future `httpx2` direction.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

These are maintenance debt, not hidden failures.

## GitHub write strategy

- Simple one-file writes: Contents API with durable staging and stale branch/file SHA protection.
- Branch create: explicit target/base preview, persisted confirmation, base/target revalidation, repository-scoped `contents: write`, one create-ref request, reconciliation, audit.
- Repository administration: operation-specific credential context + persisted confirmation + refreshed preconditions + one write + reconciliation + audit.
- Multi-file/ZIP sync: future coherent reviewable batch commit, review branch by default.
- Direct default-branch mass replacement is not default.
- `.github/workflows/*` file changes require Workflows capability.
- Never blindly replay uncertain/destructive writes.
- No normal v1 force-push UI.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing current navigation message where practical.
- Use compact inline keyboards and consistent Home/Cancel/Back.
- Long repository paths and sensitive operation authority do not belong in callback data.
- Home/start invalidates transient flows where continuing would surprise the user.
- Back/Edit/Cancel after a sensitive write preview must invalidate staged/pending authority rather than only hiding UI.
- Repository deletion remains exact-name gated Tier 3.
- Long logs/files use pagination or document delivery.

## Safety memory

- Never expose/commit tokens, keys, client/webhook secrets, OAuth code/state, PKCE verifiers, encryption keys, or raw auth response bodies.
- Do not implement arbitrary shell execution as normal bot capability.
- Clone/setup/run generates commands; it does not silently execute repository instructions.
- No normal v1 force-push/force-update UI.
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

P4.2 implementation is verified. Do not begin P4.3 until P4.2 documentation-head CI, non-draft PR CI, protected merge, post-feature `main` CI, and governance closeout are green.

## Next milestone / handoff

**P4.3 — Clone/setup/run assistant** is the exact next implementation item after P4.2 governance completes.

Scope:

- fresh clone commands;
- update-existing-clone commands;
- Python/Node/Docker/Gradle/Maven inference from repository evidence;
- Windows PowerShell, Linux, and macOS variants;
- explicit inference confidence/source;
- no token insertion;
- no arbitrary automatic execution of README/scripts/repository instructions.

## Do not forget later

- Notification preferences are per repository/event type.
- Actions includes status/jobs/steps/logs/artifacts/dispatch/retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
