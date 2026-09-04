# GitDock — Project Memory

Purpose: durable facts that future sessions must remember. This is not a task list.

Last updated: 2026-09-04

## Identity

- Product name: **GitDock**.
- Repository: `ahmed9461/GitDock`.
- Product type: Telegram-first GitHub management/control bot.
- v1 primary language: Arabic UI; code and technical identifiers remain English/native.
- v1 deployment model: owner-first/single-user with service/persistence boundaries kept multi-user-ready.

## Product intent

GitDock is broader than a notification bot. Planned v1 scope includes repository search and administration, repository contents/file operations, Git/branch/commit tools, GitHub webhooks/notifications, Issues/PRs, GitHub Actions, releases, clone/setup/run command generation, and safe ZIP/project synchronization.

## Canonical implementation direction

- Python 3.12+; CI verifies Python 3.12 and 3.13.
- aiogram 3.x for Telegram.
- FastAPI for HTTP ingress.
- httpx behind canonical GitHub transport/auth boundaries.
- SQLAlchemy 2.x async + Alembic.
- PostgreSQL production; SQLite only for portable development/tests.
- Durable DB-backed event/operation/confirmation state whenever restart safety matters.
- Production deployment remains suitable for systemd.
- Telegram handlers remain thin; OAuth/token/DB/risk rules belong in services/auth/persistence boundaries.
- GitHub remains source of truth; local repository cache is navigation/context only and never proof of authority.

## Verified phase history

### P1 — foundation ✅

P1 was squash-merged through PR #2 as `6f0a93694418c278e400a4c23b84e2f08ac56bdb`; post-merge `main` CI `33345193470` was green.

Foundation includes typed settings, FastAPI health/readiness and Telegram ingress, aiogram polling/webhook bootstrap, owner-only middleware, async SQLAlchemy/Alembic, structured secret-redacting logging, tests, PostgreSQL migration verification, and CI quality/security gates.

Important lifecycle invariant: create a fresh aiogram Router for each Dispatcher; do not reuse a module-global Router across Dispatcher instances.

### P2.1 — GitHub App authentication ✅

P2.1 was squash-merged through PR #5 as `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge `main` CI `33348851085` is green.

Durable auth facts:

- GitHub App is primary auth; do not introduce a broad long-lived PAT as the normal credential model.
- App JWTs use RS256.
- REST API version is pinned to `2026-03-10`.
- Installation access tokens are short-lived and expiry-aware.
- OAuth user authorization uses PKCE S256.
- OAuth state is high entropy, short-lived, user/flow-bound, restart-safe, and one-time use.
- Raw OAuth state is not persisted; only its SHA-256 digest is stored.
- PKCE verifier and persisted GitHub user credentials are encrypted with versioned keys.
- Capability -> GitHub permission/token-context mapping is centralized.
- A setup/install `installation_id` is untrusted candidate data. Binding persists only after the same installation/account identity is independently resolved through GitHub App context and authenticated GitHub user context, matched, and confirmed unsuspended.

### P2.2 — GitHub gateway ✅

P2.2 was squash-merged through PR #7 as `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge `main` CI `33409825480` is green.

Durable gateway facts:

- `GitHubRestClient` is the canonical normal REST transport boundary.
- Telegram handlers and ordinary services must not issue raw GitHub HTTP requests.
- Canonical outbound headers include GitHub media type, API version `2026-03-10`, and `User-Agent: GitDock/0.1`.
- `GitHubResponse[T]` / `GitHubPage[T]` carry safe status/request/pagination/rate-limit metadata.
- Absolute pagination targets are restricted to canonical HTTPS `api.github.com`; unsafe targets fail before network I/O.
- Pagination has repeated-link detection and a configured maximum page count.
- Gateway exceptions expose stable categories and do not echo raw GitHub response bodies.
- GET/HEAD have bounded transient retry by default; write-like methods do not retry by default.
- Redirects are not automatically followed by the generic REST transport.

### P2.3 — Home + installed repository read ✅

P2.3 was squash-merged through PR #8 as `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; post-merge `main` CI `33424799759` is green. Governance closeout PR #9 merged as `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`; post-closeout `main` CI `33444410513` is green.

Durable repository-read facts:

- `repositories_cache` is minimal non-authoritative navigation/callback context, not a shadow GitHub database and never authorization proof.
- Cache contains no access/refresh tokens, OAuth state/code, PKCE material, private keys, or raw GitHub error bodies.
- Repository callbacks use compact stable GitHub repository IDs plus navigation context rather than arbitrary long `owner/name` strings.
- Repository selection resolves server-side inside the current GitDock user and active unsuspended installation.
- Repository detail is re-fetched from GitHub before render.
- P2.3 is Tier 0 read-only and adds no repository write/admin permission.

### P3.1 — public GitHub repository search ✅

Verification chain:

- implementation CI `33453960817` green;
- documentation-head CI `33454438202` green;
- PR #10 CI `33454524953` green;
- squash merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`;
- post-feature `main` CI `33454619065` green;
- governance closeout PR #11 merge `ef2c5f618102063df8166f84b4828243f5efb5c6`;
- post-closeout `main` CI `33454972020` green.

Durable P3.1 facts:

- Public repository search works without a bound GitHub App installation.
- Search uses the canonical `GitHubRestClient`; no parallel raw HTTP client was introduced.
- Search state is distinct from installed repository authorization/cache semantics.
- Search supports stars/update sort, language, minimum stars, owner/org, topic, archive visibility, stable pagination, and compact opaque session IDs.
- Callbacks from older search sessions fail closed after a newer search becomes active.
- Result detail resolves only from active result context and is re-fetched from GitHub before display.
- `/start` and Home clear transient search FSM state.
- Public search results are never inserted into installed `repositories_cache` as authorization context.
- `📥 أوامر التنزيل` remains a placeholder until P4.3.

### P3.2 — durable GitHub user context ✅

Verification chain:

- implementation head `5068b58ec41fb5ac417408d3a535bbb5d66207fc` — CI `33515291600` green;
- documentation-synchronized head `492183bfba311827a965153eff61747bfabf76ed` — CI `33517270731` green;
- PR #12 CI `33527318485` green on unchanged head;
- squash merge `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`;
- post-feature `main` CI `33527484948` green;
- governance closeout PR #13 merged as `aeb003cec79d1952dc80a520c03a4eee819872bc`.

Verified suite at P3.2: **97 tests** plus Ruff format/lint, mypy, compile, `pip-audit`, `detect-secrets`, PEP 751 lock verification, and PostgreSQL 17 Alembic upgrade -> downgrade -> upgrade including `0004_user_auth`.

Durable P3.2 facts:

- GitHub user identity for durable user context comes from authenticated `GET /user`; never infer it from Telegram identity or installation labels.
- Standalone user authorization reuses the P2.1 one-time OAuth state + PKCE S256 machinery and does not require reinstalling the GitHub App.
- Durable GitHub access/refresh credentials use the existing versioned encrypted credential store.
- `credential_generation` is the durable concurrency/version guard; persisting or clearing credentials advances generation.
- Expiry-aware refresh snapshots account ID + generation before network I/O and persists rotated credentials only if durable preconditions still match.
- `pending_confirmations` is the general DB-backed one-time confirmation store. It records user, operation, opaque token digest, target fingerprint, safe payload, risk tier, expiry, consumed state, and timestamps.
- Local-disconnect confirmation fingerprints account identity, credential generation, and ordered current installation IDs.
- Stale, expired, reused, invalid, or cancelled disconnect confirmations remove nothing.
- Home consumes outstanding local-disconnect confirmations so old message buttons cannot retain authority.
- Local disconnect clears GitDock-local encrypted credentials/bindings/cache/pending state only. It does **not** uninstall or revoke the GitHub App remotely.
- Installation binding and durable user OAuth authorization are separate concepts.

### P3.3 — repository create/settings ✅

Feature-delivery verification chain:

- complete implementation head before documentation synchronization: `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945` green;
- final documentation-synchronized feature head: `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482` green;
- non-draft PR #14 CI `33891899602` green on unchanged head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` with `mergeable=true`;
- PR #14 squash merge commit: `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature `main` CI `33892100584` green on Python 3.12, Python 3.13, and PostgreSQL 17.

Verified suite at P3.3: **117 tests** plus Ruff format/lint, mypy, compile, `pip-audit`, `detect-secrets`, PEP 751 lock verification, and PostgreSQL 17 Alembic upgrade -> downgrade -> upgrade including `0005_audit_log`.

Durable P3.3 facts:

- `RepositoryAdminService` is the application boundary for create/update/delete planning, persisted confirmation, credential context, refreshed preconditions, reconciliation, cache synchronization, and audit.
- Typed repository-admin gateway methods remain on top of the canonical REST transport; Telegram handlers do not issue raw GitHub HTTP.
- Personal repository creation uses durable GitHub user OAuth context because GitHub's personal create endpoint is user-context.
- Authorized organization repository creation also uses durable user OAuth context.
- Repository update/delete use installation tokens requested with centralized `administration: write` and scoped to exactly the selected GitHub repository ID.
- Do not replace this split with a broad PAT or broad installation token for convenience.
- Create is Tier 1 confirmation; repository update is Tier 2; delete is Tier 3 plus exact typed current `owner/name` before final confirmation.
- P3.3 reuses `pending_confirmations`; Telegram callback tokens are transport only and never durable authority by themselves.
- Edit/back/cancel consumes pending create/update/delete confirmation so an old Telegram confirm button becomes invalid immediately.
- Stale, expired, reused, cancelled, wrong-target, and wrong-name paths fail closed.
- Update/delete re-fetch current GitHub repository state before mutation and reject stale preconditions.
- Write-like methods remain no-retry by default.
- Potentially uncertain create/update/delete outcomes are reconciled against remote GitHub state instead of replaying the write.
- If reconciliation proves the write applied, result may be recorded as applied/reconciled. If it cannot prove final state, `RepositoryAdminState.UNCERTAIN` remains explicit.
- Migration `0005_audit_log` adds durable repository-administration audit records.
- Audit may contain safe operation/status/repository/request/reconciliation metadata but never credentials, OAuth/PKCE material, private keys, client secrets, or raw upstream auth/error bodies.
- Applied update refreshes local repository cache; confirmed applied delete removes the deleted repository cache row.
- Telegram has a real Arabic repository-create wizard and repository-settings screen with centralized callbacks/keyboards/renderers/FSM/router layers.
- Visibility change and archive/unarchive are not one-tap writes; they pass through Tier 2 preview/confirmation.
- Delete remains visually isolated and exact-name gated.
- Organization creation is verified at gateway/service level; the current personal create wizard does not silently invent organization selection UI.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- Runtime transitive/hash locks are PEP 751 files generated by `pip lock`:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- CI regenerates and diffs each target lock; drift fails the build.
- P3.3 introduced no runtime dependency drift.

## GitHub Actions operational memory

The repository was initially private during P1 and the account's included private-repository Actions quota was exhausted, causing jobs to fail before any runner step. The repository was changed to public and Actions then ran normally.

Do not diagnose a zero-step Actions failure as code failure without checking whether a runner step actually started.

Known connector issue: the connector's Draft -> Ready GraphQL path has previously failed because it requested nonexistent `Repository.fullDatabaseId`. Safe prior workaround: close the verified Draft without merging, open a non-draft replacement from the same unchanged branch, and require final-head CI before merge. Never bypass CI merely to work around connector behavior.

## Known non-blocking maintenance warnings

As of P3.3 verification:

- FastAPI/Starlette `TestClient` emits a deprecation warning about the existing `httpx` integration/future `httpx2` direction.
- Starlette test-client usage surfaces AnyIO's deprecated `anyio.abc.BlockingPortal` alias.
- Alembic emits a deprecation warning because `alembic.ini` has no explicit `path_separator` for `prepend_sys_path` handling.

These warnings do not fail tests, but must remain recorded maintenance debt.

## GitHub write strategy

- Simple single-file writes may use Contents API with current-SHA conflict protection.
- Multi-file/ZIP sync uses a reviewable coherent batch commit, normally on a review branch followed by optional PR.
- Direct default-branch mass replacement is not the default.
- `.github/workflows/*` requires the appropriate Workflows capability.
- Never blindly retry destructive/non-idempotent writes after an uncertain result; reconcile remote state first.
- P3.3 establishes the concrete repository-admin precedent: select the least-privileged credential context per operation, persist confirmation, refresh preconditions, issue the write once, reconcile uncertainty, then audit.

## Webhook strategy

- GitHub webhooks drive immediate notifications.
- Verify `X-Hub-Signature-256` using HMAC-SHA256 before processing.
- Deduplicate by GitHub delivery ID.
- Persist accepted events before asynchronous processing.
- Keep ingress fast; enrichment/rendering happens after durable acceptance.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing the existing navigation message when practical.
- Use inline keyboards; normally no more than two primary action buttons per row.
- Keep Home / Cancel / Back consistent.
- Home/start must invalidate transient input flows where continuing them would surprise the user.
- High-impact operations require persisted explicit confirmation; repository deletion additionally requires exact current repository name.
- After a write preview exists, Back/Edit/Cancel must invalidate pending confirmation rather than merely hide the screen.
- Sensitive local account disconnect also uses persisted explicit confirmation even though it changes GitDock-local state rather than deleting a GitHub repository.
- Long logs/files use pagination or document delivery.

## Safety memory

- Never expose or commit tokens, private keys, client/webhook secrets, OAuth codes, PKCE verifiers, credential-encryption keys, or raw auth response bodies.
- Do not implement arbitrary shell execution as a normal bot capability.
- Clone/setup/run generates commands and never silently executes repository-controlled instructions.
- No normal v1 force-push UI.
- High-impact multi-step operations must not depend only on volatile in-memory FSM state.
- Audit GitHub writes without secret material.
- GitHub remains source of truth for GitHub resources.
- Do not turn pagination/download helpers into arbitrary outbound URL fetchers.
- A stale Telegram callback must fail closed when server-side authorization/preconditions have changed.
- An uncertain GitHub write must remain uncertain unless remote reconciliation proves final state.

## Development governance memory

`AGENTS.md` is mandatory. A feature with green tests but stale project state is not Done. Successful work updates, as applicable:

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_MEMORY.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- affected architecture/security/constants/decision/test/UX docs.

P3.3 feature delivery is merged and post-merge verified. This `docs/p3-3-closeout` branch records the final governance facts. After this closeout PR itself is green, squash-merged, and post-closeout `main` CI is green, do not reopen P3.3 implementation work unless a real regression is found.

## Next milestone / handoff

After P3.3 governance closeout merges, the exact next implementation item is **P4.1 — File browser**.

P4.1 scope starts with:

- repository directory navigation;
- text preview/pagination;
- binary/large-file metadata fallback;
- branch/ref selection;
- create file;
- update/replace file;
- delete file;
- stale SHA protection;
- special permission handling for `.github/workflows/*`.

P4.1 must preserve the existing write-safety precedent: current remote state is authoritative, writes use explicit preview/confirmation where risk requires it, stale SHA/preconditions fail closed, and workflow-file writes require the correct Workflows capability.

## Do not forget later

- Generate fresh-clone and existing-clone update commands under P4.3.
- Run/setup commands derive from repository evidence and label uncertainty.
- Notification preferences are per repository and event type.
- Actions support includes status, jobs/steps/logs/artifacts, dispatch, retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
