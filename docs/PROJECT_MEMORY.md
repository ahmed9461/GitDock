# GitDock — Project Memory

Purpose: durable facts that future sessions must remember. This is not a task list.

Last updated: 2026-09-01

## Identity

- Product name: **GitDock**.
- Repository: `ahmed9461/GitDock`.
- Product type: Telegram-first GitHub management/control bot.
- v1 primary language: Arabic UI; code and technical identifiers remain English/native.
- v1 deployment model: owner-first/single-user with service/persistence boundaries kept multi-user-ready.

## Product intent

GitDock is broader than a notification bot. Planned scope includes repository search and administration, file operations, Git/branch/commit tools, Issues/PRs, GitHub Actions, releases, clone/setup/run command generation, webhook notifications, and safe ZIP/project synchronization.

## Canonical implementation direction

- Python 3.12+; CI verifies Python 3.12 and 3.13.
- aiogram 3.x for Telegram.
- FastAPI for HTTP ingress.
- httpx behind canonical GitHub transport/auth boundaries.
- SQLAlchemy 2.x async + Alembic.
- PostgreSQL production; SQLite only for portable development/tests.
- Durable DB-backed event/operation/confirmation state when restart safety matters.
- Production deployment remains suitable for systemd.
- Telegram handlers remain thin; OAuth/token/DB rules belong in services/auth/persistence boundaries.

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

Critical installation-binding invariant: a setup/install `installation_id` is untrusted candidate data. Binding is persisted only after the same installation/account identity is independently resolved through GitHub App context and authenticated GitHub user context, matched, and confirmed unsuspended.

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

- GitHub remains source of truth.
- `repositories_cache` is minimal non-authoritative navigation/callback context, not a shadow GitHub database and never authorization proof.
- Cache contains no access/refresh tokens, OAuth state/code, PKCE material, private keys, or raw GitHub error bodies.
- Repository callbacks use compact stable GitHub repository IDs plus navigation context rather than arbitrary long `owner/name` strings.
- Repository selection resolves server-side inside the current GitDock user and active unsuspended installation.
- Repository detail is re-fetched from GitHub before render.
- P2.3 is Tier 0 read-only and adds no repository write/admin permission.

### P3.1 — public GitHub repository search ✅

P3.1 feature delivery and governance are verified complete.

Verification chain:

- implementation head `4a4f00d50e886ab494e2a83f2c649cd64b7398b2` — CI `33453960817` green;
- documentation-synchronized feature head `14e149ea307871abd8406ffc6212fe062ead9098` — branch CI `33454438202` green;
- non-draft PR #10 — PR CI `33454524953` green and mergeable on unchanged head;
- squash merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`;
- post-feature `main` CI `33454619065` green;
- governance closeout PR #11 merged as `ef2c5f618102063df8166f84b4828243f5efb5c6`;
- post-closeout `main` CI `33454972020` green.

Durable P3.1 facts:

- Public repository search works without a bound GitHub App installation.
- Search uses the canonical `GitHubRestClient`; no parallel raw HTTP client was introduced.
- Search models/service are distinct from installed repository read/cache semantics.
- Query/filter construction is validated and supports stars/update sort, language, min-stars, `user:`/`org:` scope, topic, and archive visibility.
- Search displays typed stars/forks/language/license/default-branch/topics/archive/update metadata.
- Search uses stable application pagination (`SEARCH_PAGE_SIZE`).
- Public result/session context is ephemeral FSM state because it is Tier 0 and authorizes no write.
- Every search session has an opaque compact session ID; callbacks from older sessions fail closed after a newer search becomes active.
- Result detail can only resolve from active result context and is then re-fetched from GitHub before display.
- `/start` and Home clear transient search FSM state so abandoned input cannot be interpreted later.
- Public search results are never inserted into installed `repositories_cache` as authorization context.
- Search introduces no repository write/admin permission.
- Search detail shows **📥 أوامر التنزيل** only as a placeholder. Actual clone/update/setup/run command generation remains P4.3.

### P3.2 — durable GitHub user context — implementation pre-merge verified

P3.2 implementation is complete on `feat/p3-2-user-authorization`, but it is not yet recorded as fully merged/closed.

Pre-merge verified implementation head:

- commit `5068b58ec41fb5ac417408d3a535bbb5d66207fc`;
- branch CI `33515291600` — green;
- Python 3.12 and Python 3.13 each pass format, lint, mypy, **97 tests**, compile, dependency audit, secret scan, and PEP 751 lock regeneration/diff;
- PostgreSQL 17 Alembic upgrade -> downgrade -> upgrade passes including `0004_user_auth`;
- no known runtime vulnerabilities, secret findings, or lock drift.

Durable P3.2 facts:

- GitHub user identity for durable user context comes from authenticated `GET /user`; do not infer it from Telegram identity or installation labels.
- Standalone user authorization reuses the P2.1 one-time OAuth state + PKCE S256 machinery. Reauthorizing user context does not require reinstalling the GitHub App.
- The OAuth completion path can persist durable user access/refresh credentials through `GitHubUserCredentialStore` after identity verification.
- P3.2 uses the existing versioned authenticated-encryption abstraction; it does not introduce custom crypto or a second credential store.
- Access/refresh expiry metadata remains separate from ciphertext.
- `credential_generation` is a durable concurrency/version guard on GitHub user credentials. Persisting or clearing credentials advances the generation.
- Expiry-aware refresh snapshots account ID + credential generation before network I/O. A rotated access/refresh pair is persisted only if the current row still belongs to the same GitDock user, remains authorized, and has the same generation. Concurrent reconnect/disconnect therefore causes the stale refresh to fail closed.
- Refresh tokens are treated as rotating one-use credentials; the newly returned refresh token replaces the old one only after the generation precondition succeeds.
- `pending_confirmations` is the general DB-backed one-time confirmation store introduced in P3.2. It records user, operation, opaque token digest, target fingerprint, payload, risk tier, expiry, consumed state, and timestamps without putting secrets in Telegram callback data.
- GitHub local-disconnect confirmation fingerprints account DB ID, GitHub user ID, current `credential_generation`, and the ordered current installation IDs. A confirmation becomes stale if any of those authorization preconditions changed.
- Stale, expired/invalid, reused, or explicitly cancelled disconnect confirmations never claim deletion and never remove current authorization state.
- Returning Home consumes outstanding GitHub disconnect confirmations so buttons left in older messages cannot remain active destructive authority.
- P2.3 legacy state is supported: a GitDock user with installation binding(s) but no durable UAT may still remove the local binding safely.
- P3.2 local disconnect clears encrypted GitHub user credentials, deletes local installation bindings and repository cache, and invalidates relevant unconsumed local OAuth/confirmation state.
- **Local disconnect does not uninstall or revoke the GitHub App on GitHub.** UI copy must keep this distinction explicit.
- Installation binding and durable user OAuth authorization remain separate concepts. Later code must not treat the existence of one as proof of the other.
- Connected Home has a real `👤 حساب GitHub` entry. The account UI separates user authorization from installation count, allows activate/re-authorize, refresh, and isolated local disconnect confirmation.
- P3.2 adds no repository-create/settings/delete behavior and no broad new GitHub App permission. P3.3 owns those writes.
- P3.1 public search remains usable independently of installation/user authorization.
- The initial Alembic revision identifier `0004_user_authorization_lifecycle` exceeded Alembic's default 32-character `alembic_version.version_num` column. The correct root fix was to use short revision ID `0004_user_auth`, not to widen Alembic's internal table merely for an unnecessarily long revision label.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- Runtime transitive/hash locks are PEP 751 files generated by `pip lock`:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- CI regenerates and diffs each target lock; drift fails the build.
- P3.2 introduces no runtime dependency drift.

## GitHub Actions operational memory

The repository was initially private during P1 and the account's included private-repository Actions quota was exhausted, causing jobs to fail before any runner step. The repository was changed to public and Actions then ran normally.

Do not diagnose a zero-step Actions failure as code failure without checking whether a runner step actually started.

Known connector issue: the connector's Draft -> Ready GraphQL path has previously failed because it requested nonexistent `Repository.fullDatabaseId`. Safe prior workaround: close the verified Draft without merging, open a non-draft replacement from the same unchanged branch, and require final-head CI before merge. Never bypass CI merely to work around connector behavior.

## Known non-blocking maintenance warnings

As of P3.2 pre-merge verification:

- FastAPI/Starlette `TestClient` emits a deprecation warning about the existing `httpx` integration/future `httpx2` direction.
- Alembic emits a deprecation warning because `alembic.ini` has no explicit `path_separator` for `prepend_sys_path` handling.

These warnings do not fail tests, but must remain recorded maintenance debt.

## GitHub write strategy

- Simple single-file writes may use Contents API with current-SHA conflict protection.
- Multi-file/ZIP sync uses a reviewable coherent batch commit, normally on a review branch followed by optional PR.
- Direct default-branch mass replacement is not the default.
- `.github/workflows/*` requires the appropriate Workflows capability.
- Never blindly retry destructive/non-idempotent writes after an uncertain result; reconcile remote state first.
- Later repository administration must use P3.2 user context only where GitHub actually requires user context and still pass capability/permission/precondition checks.

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
- Destructive Tier 2/3 actions require persisted explicit confirmation; repository deletion additionally requires exact repository name.
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

## Development governance memory

`AGENTS.md` is mandatory. A feature with green tests but stale project state is not Done. Successful work updates, as applicable:

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_MEMORY.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- affected architecture/security/constants/decision/test/UX docs.

P3.2 implementation is pre-merge green. Finish the synchronized documentation head, non-draft PR, unchanged-head PR CI, squash merge, post-merge `main` CI, and small governance closeout before marking P3.2 fully verified complete.

## Next milestone

After P3.2 closeout: **P3.3 — repository create/settings**.

P3.3 must reuse the P3.2 user-context lifecycle and the existing central capability/permission model. It must not introduce one-tap dangerous writes, broad PATs, or handler-local GitHub writes.

## Do not forget later

- Generate fresh-clone and existing-clone update commands under P4.3.
- Run/setup commands derive from repository evidence and label uncertainty.
- Notification preferences are per repository and event type.
- Actions support includes status, jobs/steps/logs/artifacts, dispatch, retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
