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
- httpx behind the canonical GitHub REST gateway.
- SQLAlchemy 2.x async + Alembic.
- PostgreSQL production; SQLite only for portable development/tests.
- Durable DB-backed event/operation state when restart safety matters.
- Production deployment remains suitable for systemd.

## Verified phase history

### P1 — foundation

P1 was squash-merged through PR #2 as `6f0a93694418c278e400a4c23b84e2f08ac56bdb`; post-merge `main` CI `33345193470` was green.

Foundation includes typed settings, FastAPI health/readiness and Telegram ingress, aiogram polling/webhook bootstrap, owner-only middleware, async SQLAlchemy/Alembic, structured secret-redacting logging, tests, PostgreSQL migration verification, and CI quality/security gates.

Important lifecycle invariant: create a fresh aiogram Router for each Dispatcher; do not reuse a module-global Router across Dispatcher instances.

### P2.1 — GitHub App authentication

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

### P2.2 — GitHub gateway

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

### P2.3 — Home + installed repository read

P2.3 was squash-merged through non-draft PR #8 as `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; post-merge `main` CI `33424799759` is green. Governance closeout PR #9 merged as `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`; post-closeout `main` CI `33444410513` is green.

Durable repository-read facts:

- GitHub remains source of truth.
- `repositories_cache` is minimal non-authoritative navigation/callback context, not a shadow GitHub database and never authorization proof.
- Cache contains no access/refresh tokens, OAuth state/code, PKCE material, private keys, or raw GitHub error bodies.
- Repository callbacks use compact stable GitHub repository IDs plus navigation context rather than arbitrary long `owner/name` strings.
- Repository selection resolves server-side inside the current GitDock user and active unsuspended installation.
- Repository detail is re-fetched from GitHub before render.
- P2.3 is Tier 0 read-only and adds no repository write/admin permission.

## P3.1 — public GitHub repository search

P3.1 implementation is verified on branch `feat/p3-1-github-search`; final PR/merge/main-CI closeout is still required before marking the milestone fully merged complete.

Verified implementation head:

`4a4f00d50e886ab494e2a83f2c649cd64b7398b2`

Implementation CI:

`33453960817` — green on Python 3.12, Python 3.13, and PostgreSQL 17 with **83 tests**, Ruff format/lint, mypy, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff all passing.

Durable P3.1 facts:

- Public repository search works without a bound GitHub App installation.
- Search uses the canonical `GitHubRestClient`; no parallel raw HTTP client was introduced.
- Search models/service are distinct from installed repository read/cache semantics.
- Query/filter construction is validated and supports stars/update sort, language, min-stars, `user:`/`org:` scope, topic, and archive visibility.
- Search displays typed stars/forks/language/license/default-branch/topics/archive/update metadata.
- Search uses stable application pagination (`SEARCH_PAGE_SIZE`).
- Public result/session context is ephemeral FSM state because it is Tier 0 and authorizes no write.
- Every search session has an opaque compact session ID; callbacks from older sessions fail closed after a newer search becomes active.
- Result detail can only resolve from the active result context and is then re-fetched from GitHub before display.
- `/start` and Home clear transient search FSM state so abandoned input cannot be interpreted later.
- Public search results are never inserted into installed `repositories_cache` as authorization context.
- Search introduces no repository write/admin permission.
- Search detail currently shows **📥 أوامر التنزيل** only as a placeholder. Actual clone/update/setup/run command generation remains P4.3 and must not be described as implemented in P3.1.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- Runtime transitive/hash locks are PEP 751 files generated by `pip lock`:
  - `pylock.py312-linux.toml`
  - `pylock.py313-linux.toml`
- CI regenerates and diffs each target lock; drift fails the build.

## GitHub Actions operational memory

The repository was initially private during P1 and the account's included private-repository Actions quota was exhausted, causing jobs to fail before any runner step. The repository was changed to public and Actions then ran normally.

Do not diagnose a zero-step Actions failure as code failure without checking whether a runner step actually started.

Known connector issue: the connector's Draft -> Ready GraphQL path has previously failed because it requested nonexistent `Repository.fullDatabaseId`. Safe prior workaround: close the verified Draft without merging, open a non-draft replacement from the same unchanged branch, and require final-head CI before merge. Never bypass CI merely to work around connector behavior.

## Known non-blocking maintenance warnings

As of P3.1 implementation CI `33453960817`:

- FastAPI/Starlette `TestClient` emits a deprecation warning about the existing `httpx` integration/future `httpx2` direction.
- Alembic emits a deprecation warning because `alembic.ini` has no explicit `path_separator` for `prepend_sys_path` handling.

These warnings do not fail tests, but must remain recorded maintenance debt.

## GitHub write strategy

- Simple single-file writes may use Contents API with current-SHA conflict protection.
- Multi-file/ZIP sync uses a reviewable coherent batch commit, normally on a review branch followed by optional PR.
- Direct default-branch mass replacement is not the default.
- `.github/workflows/*` requires the appropriate Workflows capability.
- Never blindly retry destructive/non-idempotent writes after an uncertain result; reconcile remote state first.

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
- Long logs/files use pagination or document delivery.

## Safety memory

- Never expose or commit tokens, private keys, client/webhook secrets, OAuth codes, PKCE verifiers, or credential-encryption keys.
- Do not implement arbitrary shell execution as a normal bot capability.
- Clone/setup/run generates commands and never silently executes repository-controlled instructions.
- No normal v1 force-push UI.
- High-impact multi-step operations must not depend only on volatile in-memory FSM state.
- Audit GitHub writes without secret material.
- GitHub remains source of truth for GitHub resources.
- Do not turn pagination/download helpers into arbitrary outbound URL fetchers.

## Development governance memory

`AGENTS.md` is mandatory. A feature with green tests but stale project state is not Done. Successful work updates, as applicable:

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_MEMORY.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- affected architecture/security/constants/decision/test/UX docs.

P3.1 is currently at the documentation-synchronization / PR-closeout boundary. Do not start P3.2 until the feature branch has final green CI, a non-draft PR is merged from the unchanged green head, post-merge `main` CI is green, and governance closeout records the exact final facts.

## Next milestone after P3.1 closeout

**P3.2 — user-context authorization/disconnect support.** Reuse the P2.1 secure one-time-state/PKCE/encryption foundation; do not duplicate auth machinery.

## Do not forget later

- Generate fresh-clone and existing-clone update commands under P4.3.
- Run/setup commands derive from repository evidence and label uncertainty.
- Notification preferences are per repository and event type.
- Actions support includes status, jobs/steps/logs/artifacts, dispatch, retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
