# GitDock — Project Memory

Purpose: durable facts future sessions must remember. This is not a task list.

Last updated: 2026-09-12

## Identity and product direction

- Product: **GitDock**.
- Repository: `ahmed9461/GitDock`.
- Telegram-first GitHub management/control bot.
- v1 user-facing language: Arabic; code/technical identifiers remain English/native.
- v1 boundary: one configured Telegram owner, while services/persistence remain multi-user-ready.
- Planned v1 covers repository search/administration, repository contents/file writes, branches/commits, clone/setup/run command generation, webhooks/notifications, Issues/PRs, Actions, releases, and safe ZIP/project synchronization.

## Canonical architecture

- Python 3.12+; CI verifies Python 3.12 and 3.13.
- aiogram 3.x Telegram UI.
- FastAPI HTTP ingress.
- httpx behind GitHub auth/gateway boundaries.
- async SQLAlchemy 2.x + Alembic.
- PostgreSQL production; SQLite only for portable tests/development.
- GitHub is source of truth.
- Telegram handlers stay thin; auth/token/DB/risk/business rules belong in services/auth/persistence.
- Important multi-step confirmation/write/event state is durable when restart safety matters.
- GitHub App installation/user tokens with minimum permissions are preferred over broad long-lived PATs.
- Ordinary feature code must use the canonical `GitHubRestClient`; do not build a parallel raw HTTP stack.

## Verified phase history

### P1 — foundation ✅

Merged through PR #2; post-merge main CI `33345193470` green.

Durable invariant: create a fresh aiogram Router for each Dispatcher; never reuse a module-global Router across Dispatcher instances.

### P2.1 — GitHub App authentication ✅

Merge `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge CI `33348851085` green.

Durable facts:

- GitHub App primary auth;
- RS256 App JWT;
- REST API version `2026-03-10`;
- short-lived expiry-aware installation tokens;
- OAuth + PKCE S256;
- raw OAuth state never persisted, SHA-256 digest only;
- PKCE verifier and durable user credentials encrypted with versioned keys;
- capability → permission/token-context mapping centralized;
- setup/install `installation_id` remains untrusted until App + authenticated-user identities independently match and ownership/suspension checks pass.

### P2.2 — GitHub gateway ✅

Merge `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge CI `33409825480` green.

Durable facts:

- `GitHubRestClient` is the canonical REST transport;
- canonical headers/version/User-Agent are centralized;
- absolute API/pagination targets are restricted to canonical HTTPS `api.github.com`;
- stable safe error categories never echo raw upstream bodies;
- GET/HEAD use bounded transient retries;
- write-like methods do not retry by default;
- generic transport does not automatically follow redirects.

### P2.3 — Home + installed repository read ✅

Feature merge `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; closeout `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`.

Durable facts:

- `repositories_cache` is navigation/context state only, never source of truth or authorization;
- cache stores no credentials/auth secrets/raw errors;
- repository callbacks use stable numeric repository IDs + compact navigation context;
- repository selection resolves inside the current GitDock user/active installation;
- detail re-fetches GitHub before render.

### P3.1 — public repository search ✅

Feature merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`; closeout `ef2c5f618102063df8166f84b4828243f5efb5c6`.

Durable facts:

- public search works without a bound installation;
- search state is isolated from installed cache/authorization state;
- sort/filter/pagination use opaque active search sessions;
- stale search sessions fail closed;
- detail resolves from active result context then re-fetches GitHub;
- Home/start clears transient search FSM state.

### P3.2 — durable GitHub user context ✅

Implementation CI `33515291600`; docs CI `33517270731`; PR #12 CI `33527318485`; feature merge `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`; closeout `aeb003cec79d1952dc80a520c03a4eee819872bc`.

Durable facts:

- durable user identity comes from authenticated `GET /user`;
- standalone authorization reuses state + PKCE without reinstalling the App;
- access/refresh tokens are encrypted before DB persistence;
- `credential_generation` guards stale refresh/disconnect concurrency;
- `pending_confirmations` is a general DB-backed one-time confirmation store;
- local disconnect removes only GitDock-local credentials/bindings/cache/pending state and does **not** uninstall/revoke the GitHub App remotely.

### P3.3 — repository administration ✅

Verification chain:

- implementation `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945`;
- docs head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482`;
- PR #14 CI `33891899602`;
- feature merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature main CI `33892100584`.

Durable facts:

- `RepositoryAdminService` owns planning, confirmation, credential selection, refreshed preconditions, reconciliation, cache synchronization, and audit;
- personal/org create uses durable GitHub user OAuth context;
- update/delete uses installation token scoped to selected repository with `administration: write`;
- create Tier 1; update Tier 2; delete Tier 3 + exact typed `owner/name`;
- edit/back/cancel consumes pending confirmation;
- stale/expired/reused/cancelled/wrong-target/wrong-name fail closed;
- no blind write retry; uncertain outcome reconciles remote state;
- unresolved result remains explicit `UNCERTAIN`;
- `audit_log` never stores credentials/tokens/raw upstream auth bodies.

### P4.1 — file browser + stale-safe single-file writes ✅

Final delivery chain:

- implementation head `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010` green;
- documentation-synchronized head `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457` green;
- non-draft PR #16 CI `34641248664` green;
- squash merge `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6`;
- post-feature `main` CI `34641411838` green;
- governance closeout `d113872e703b005f4c3c8e2b1da8fc2597e8ecd7`.

Verified contract: **148 tests** on Python 3.12/3.13, Ruff green, mypy clean on **87 source files**, compile/audit/secrets/PEP 751 locks green, PostgreSQL 17 migration round-trip through `0006_file_write_sessions`.

Durable facts:

- typed GitHub Contents gateway remains on canonical REST transport;
- Arabic `📁 الملفات` supports directory pagination, parent navigation, branch/tag/SHA reads, text preview pages, binary/large fallback, and bounded download;
- long repository paths never travel in callback data;
- create/edit/upload/replace/delete stage a reviewable plan before write;
- `file_write_sessions` is restart-safe one-file staging;
- staging binds user/repository/installation, branch/path, branch-head SHA, expected file SHA, desired blob/content digest, operation, commit message, risk, expiry, and consumed state;
- temporary staged create/update bytes survive for at most 15 minutes and are scrubbed on consume/cancel/supersede/expiry/prune;
- create requires target absence; update/delete require exact expected file SHA; branch HEAD must match staged snapshot;
- ordinary writes use repository-scoped `contents: write`; workflow paths additionally require `workflows: write`;
- write is issued once; uncertain outcomes reconcile remote file state and never blindly replay;
- file audit stores safe metadata only, never bodies or credentials;
- D-020 records the single-file staged-intent lifecycle.

### P4.2 — branch/commit tools ✅

Final feature-delivery chain:

- implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518` — CI `34647181024` green;
- documentation-synchronized feature head `73e48dfced65d72d0d27e9defc4c3e107527107f` — push CI `34647866083` green;
- non-draft PR #18 CI `34648080794` green on the unchanged mergeable head;
- protected squash merge `b4e7dcd9de5db1e958e831508443d3fa1445213d`;
- post-feature `main` CI `34648224733` green.

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

- `GitHubGitToolsGateway` is the typed endpoint boundary for branches, commits, compare, and create-ref on top of `GitHubRestClient`;
- `GitToolsService` owns branch/commit read orchestration plus branch-create confirmation, stale checks, scoped credential selection, uncertain-result reconciliation, and audit;
- repository dashboard `🌿 الفروع` and `📝 Commits` are real flows;
- branch listing is GitHub-backed; optional search filters fetched names case-insensitively without making cache/FSM state authoritative;
- recent commits may target default branch or explicit branch/tag/SHA ref;
- commit detail is re-fetched from GitHub and exposes safe metadata + canonical GitHub URL;
- compare refs are path-component encoded through the canonical gateway; Telegram output is bounded to the first 10 file rows while preserving aggregate counts;
- branch creation is Tier 1 and begins from explicit target branch + base ref resolving to a concrete base SHA;
- confirmation fingerprint binds repository ID, target branch, base ref, and base SHA;
- confirm consumes authority once, re-resolves repository context/base SHA, and rejects changed base as `STALE` before write;
- target absence is checked before preview and immediately before create; GitDock never turns create into force-update/replace;
- missing base or duplicate target performs no write;
- branch create requests a repository-scoped installation token with `contents: write` + metadata read only for the selected repository;
- create-ref POST is issued once; uncertain failure reconciles by reading target branch, with exact expected SHA required to prove `APPLIED`;
- unresolved results remain `UNCERTAIN`;
- branch-create audit stores safe target/base/SHA/risk/request/result metadata only;
- callbacks remain compact transport context only;
- no normal v1 force-push, force branch update, or branch-delete UI exists.

### P4.3 — clone/setup/run assistant — implementation verified; delivery closeout pending

Implementation verification head `fba538e3c6071365361def7d5970ff7b19b5819c`; CI `34650497474` green.

Verified implementation contract:

- **182 tests** on Python 3.12 and 3.13;
- Ruff format/lint green on **167 files**;
- mypy clean on **100 source files**;
- compile green;
- `pip-audit` reported no known runtime vulnerabilities;
- `detect-secrets` reported no findings;
- PEP 751 runtime locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic round-trip remains green through `0006_file_write_sessions`.

Durable P4.3 facts:

- `RunAssistantService` is the orchestration boundary for collecting bounded repository evidence and building an OS-specific command plan;
- `gitdock.domain.run_assistant` is the pure inference/command-generation layer and is testable without Telegram or live GitHub;
- the assistant generates commands only and never executes shell commands;
- fresh-clone and update-existing-clone flows are rendered separately from setup and run suggestions;
- target OS is explicit: Windows PowerShell, Linux, or macOS;
- baseline stack inference supports Python, Node.js, Docker, Gradle, and Maven from known repository files;
- inference exposes confidence and evidence sources rather than presenting guesses as fact;
- public repository evidence reads use the existing Contents gateway without Authorization; installed/private repositories use the current installation read context;
- P4.3 extends read-only Contents access only; write methods keep their existing token/permission requirements;
- public-search command generation remains bound to the active opaque search session and stale sessions fail closed;
- repository dashboard and public search detail both expose real command-assistant entry points using compact callbacks;
- README is untrusted evidence: its shell snippets are never copied or automatically executed;
- Node script bodies from `package.json` are not copied into output; only safe script names may produce `npm run <name>` style invocations;
- Python entry-point/script names used in generated commands are constrained to safe identifiers;
- generated clone/update commands use target-OS-aware quoting for repository path/branch material where applicable;
- generated output never contains GitHub tokens, credentials, OAuth material, or installation secrets;
- evidence collection is bounded to known root candidates and bounded file reads; P4.3 is not an arbitrary repository crawler;
- output warns that dependency/setup/run commands may execute repository-controlled hooks, build logic, or scripts when the user chooses to run them locally;
- direct unit/integration/contract tests cover stack inference, OS variants, quoting, malicious script bodies, public unauthenticated evidence reads, installed/private service reads, UI callback compactness, and renderer safety.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- PEP 751 runtime locks: `pylock.py312-linux.toml`, `pylock.py313-linux.toml`.
- CI regenerates and diffs each lock; drift fails the build.
- Never weaken lock/audit/secret checks to obtain green CI.

## GitHub Actions operational memory

- Earlier hosted-runner quota exhaustion caused zero-step failures; zero-step run is not evidence of code failure until runner steps are inspected.
- Cache-disabled resolution previously exposed legitimate transitive lock drift; it was fixed rather than bypassing the lock gate.
- CI push branches include `main`, `feat/**`, `fix/**`, `refactor/**`, and `security/**`; `docs/**` push alone does not trigger CI, so governance branches that require push verification use `feat/**`.
- Earlier Draft → Ready GraphQL integration requested a nonexistent field; the safe workaround was a replacement non-draft PR on the unchanged verified head, never CI bypass.

## Known non-blocking maintenance warnings

- FastAPI/Starlette `TestClient` deprecation toward future `httpx2` direction.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

These are maintenance debt, not hidden failures.

## GitHub write strategy

- One-file writes: Contents API + durable staging + branch/file SHA protection + one write + reconciliation + audit.
- Branch create: explicit target/base preview + persisted confirmation + base/target revalidation + repository-scoped `contents: write` + one create-ref request + reconciliation + audit.
- Repository administration: operation-specific credential context + persisted confirmation + refreshed preconditions + one write + reconciliation + audit.
- Multi-file/ZIP sync remains a future coherent reviewable batch commit, review branch by default.
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
- Back/Edit/Cancel after sensitive preview invalidates staged/pending authority rather than only hiding UI.
- Repository deletion remains exact-name gated Tier 3.
- Long logs/files use pagination or document delivery.

## Safety memory

- Never expose/commit tokens, keys, client/webhook secrets, OAuth code/state, PKCE verifiers, encryption keys, or raw auth response bodies.
- Do not implement arbitrary shell execution as normal bot capability.
- Clone/setup/run generates commands only; it does not silently execute repository instructions.
- Repository/README/script text is untrusted input.
- Generated setup/run commands may invoke repository-controlled hooks/build logic when the user runs them; the UI must say so.
- No normal v1 force-push/force-update UI.
- High-impact multi-step operations must not depend only on volatile FSM state.
- Audit GitHub writes without secret/file-body material.
- GitHub remains source of truth.
- Pagination/download helpers must not become arbitrary outbound URL fetchers.
- Stale callbacks/preconditions fail closed.
- Uncertain writes remain uncertain unless reconciliation proves final state.

## Development governance memory

`AGENTS.md` is mandatory. Green tests with stale project state are not Done. Successful work updates the relevant control documentation and leaves an explicit handoff.

P4.3 implementation and push verification are complete, but P4.3 is **not yet delivery-complete** until docs-head CI, PR CI/mergeability, protected squash merge, post-merge `main` CI, and final governance closeout all succeed.

## Active milestone / handoff

**P4.3 — delivery closeout**

Remaining work:

- verify the documentation-synchronized feature head;
- open a non-draft PR and require green PR CI + mergeability;
- squash merge without bypassing protections;
- verify `main` after merge;
- close governance and only then mark P4 complete / P5.1 active.

## Do not forget later

- Notification preferences are per repository/event type.
- Actions includes status/jobs/steps/logs/artifacts/dispatch/retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
