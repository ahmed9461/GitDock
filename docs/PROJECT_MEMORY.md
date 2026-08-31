# GitDock — Project Memory

Purpose: durable facts that future sessions must remember. This is not a task list.

Last updated: 2026-08-31

## Identity

- Product name: **GitDock**.
- Repository: `ahmed9461/GitDock`.
- Product type: Telegram-first GitHub management/control bot.
- v1 primary language: Arabic UI; code and technical identifiers in English.
- v1 deployment model: owner-first/single-user, designed so multi-user support can be added without rewriting core services.

## Product intent

GitDock is broader than a GitHub notification bot. Planned scope includes repository creation/settings, file operations, Git/branch/commit tools, Issues/PRs, GitHub Actions, releases, GitHub search, clone/run command generation, webhook notifications, and safe ZIP/project synchronization.

## Canonical implementation direction

- Python 3.12+; CI verifies Python 3.12 and 3.13.
- aiogram 3.x for Telegram.
- FastAPI for HTTP ingress.
- httpx for outbound GitHub HTTP.
- SQLAlchemy 2.x async + Alembic.
- PostgreSQL in production; SQLite only for portable development/tests.
- Durable DB-backed event/operation state when restart safety matters.
- Production deployment remains suitable for systemd.

## P1 verified foundation

P1 was squash-merged through PR #2 as `6f0a93694418c278e400a4c23b84e2f08ac56bdb`; post-merge `main` CI run `33345193470` was green.

Foundation includes typed settings, FastAPI health/readiness and Telegram webhook ingress, aiogram polling/webhook bootstrap, owner-only middleware, async SQLAlchemy/Alembic, structured secret-redacting logging, tests, PostgreSQL migration verification, and CI quality/security gates.

Important lifecycle rule caught by P1 tests: create a fresh aiogram Router for each Dispatcher; do not reuse a module-global Router across Dispatcher instances.

## P2.1 GitHub App authentication foundation

P2.1 was squash-merged through PR #5 as commit `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge `main` CI `33348851085` is green.

Durable auth facts:

- GitHub App is primary auth; do not introduce a broad long-lived PAT as the normal credential model.
- App JWTs use RS256 and configured GitHub App identity.
- REST API version is pinned to `2026-03-10`.
- Installation access tokens are short-lived and expiry-aware.
- OAuth user authorization uses PKCE S256.
- OAuth state is high entropy, short-lived, user/flow-bound, restart-safe, and one-time use.
- Raw OAuth state is not persisted; only its SHA-256 digest is stored.
- PKCE verifier and persisted GitHub user credentials are encrypted with versioned keys.
- Capability -> GitHub permission/token-context mapping is centralized.

### Critical installation-binding invariant

A setup/install `installation_id` is **untrusted candidate data**, not authorization proof. Binding is persisted only after the same installation/account identity is independently resolved through GitHub App context and authenticated GitHub user context, matched, and confirmed unsuspended.

Do not simplify this to trusting a callback query parameter.

## P2.2 GitHub gateway foundation

P2.2 was squash-merged through PR #7 into `main` as commit `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge `main` CI `33409825480` is green.

Durable gateway facts:

- `GitHubRestClient` is the canonical REST transport boundary.
- Telegram handlers and normal application services must not issue raw GitHub HTTP requests.
- Canonical outbound REST headers include GitHub media type, API version `2026-03-10`, and `User-Agent: GitDock/0.1`.
- Payload parsing is caller-supplied at the gateway boundary.
- `GitHubResponse[T]` and `GitHubPage[T]` carry safe request/status/pagination/rate-limit metadata.
- Pagination links are accepted only when they resolve to canonical HTTPS `api.github.com`; unsafe targets are rejected before network I/O.
- Pagination iteration has repeated-next-link detection and a configured max-page safety bound.
- The gateway is not a generic URL fetcher.
- Stable error categories cover authentication, permission, not-found, conflict/precondition, validation, rate-limit, transient, and unexpected failures.
- Gateway exceptions intentionally omit raw GitHub response bodies.
- GET/HEAD are retry-safe by default for bounded transient conditions.
- Write-like methods do **not** retry by default; explicit safe retry requires higher-level idempotency reasoning.
- Redirects are not automatically followed by the REST gateway.

P2.2 added 12 contract tests, growing the suite from 37 to 49 tests before P2.3.

## P2.3 home + repository read — verified complete

P2.3 was squash-merged through non-draft PR #8 into `main` as commit:

`939d218d76fd87f3ba6cf0a80a89b4a816aac557`

Verification chain:

- implementation-head CI `33423169021` — green;
- documentation-synchronized branch-head CI `33424505117` — green;
- PR #8 CI `33424652835` — green;
- post-merge `main` CI `33424799759` — green.

Final verified facts:

- Python 3.12 and 3.13 each pass Ruff format/lint, mypy, **65 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff.
- PostgreSQL 17 upgrade -> downgrade -> upgrade passes with Alembic migration `0003`.
- `pip-audit` reports no known runtime vulnerabilities.
- The working Telegram/FastAPI runtime now includes GitHub App installation/setup + OAuth callback wiring through the P2.1 secure state/PKCE/dual-context binding flow.
- Home, installed repository list, pagination, filtering, repository detail, refresh, stale/error states, and Arabic renderers/keyboards are implemented.

### Durable repository-read invariants

- GitHub remains the source of truth for repositories.
- `repositories_cache` is a **minimal non-authoritative callback/context cache**, not a shadow repository database.
- Cache stores only safe non-secret repository metadata/context needed for compact Telegram navigation and server-side repository resolution.
- Never store installation/user access tokens, OAuth codes/state, PKCE material, private keys, or raw GitHub error bodies in repository cache rows.
- Telegram repository callbacks are compact and versioned. They use stable GitHub repository ID plus navigation context instead of arbitrary long `owner/name` values.
- Callback resolution must be scoped to the current GitDock user and a currently bound, unsuspended GitHub installation.
- A repository detail view must be re-fetched from GitHub before render. A GitHub not-found result removes stale local cache state.
- A cache hit is never authorization proof by itself.
- Repository read flows request only metadata/read capabilities; P2.3 adds no repository write/admin behavior.
- Repository listing supports all/private/public/active/archived/source/fork filters and stable application-level pagination.
- Future P3/P4/P6/P7 features must extend these services/gateways rather than bypass the P2.2 transport or make cache authoritative.

### Working GitHub connection UI

- Telegram can create the short-lived GitHub installation/setup session.
- GitHub setup callback continues into OAuth/PKCE verification.
- OAuth callback completes the existing dual-context binding flow.
- Success/error HTML pages never display tokens, OAuth codes, PKCE material, or raw upstream error bodies.
- FastAPI GitHub callback routes explicitly disable response-model inference for Response subclasses; do not regress to a union annotation that FastAPI tries to model with Pydantic.

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

Known connector issue: the connector's Draft -> Ready GraphQL path has failed because it requested nonexistent `Repository.fullDatabaseId`. Safe prior workaround: close the verified Draft without merging, open a non-draft replacement from the same branch, and require new final-head CI before merge. Never bypass CI or merge a Draft merely to work around the connector.

## Known non-blocking maintenance warnings

As of P2.3 verified CI:

- FastAPI/Starlette `TestClient` emits a deprecation warning about the existing `httpx` integration and future `httpx2` direction.
- Alembic emits a deprecation warning because `alembic.ini` has no explicit `path_separator` for `prepend_sys_path` handling.

These warnings do not currently fail tests, but future maintenance should resolve them deliberately rather than forgetting them.

## GitHub write strategy

- Simple single-file writes may use Contents API with current-SHA conflict protection.
- Multi-file/ZIP sync uses a reviewable coherent batch commit, normally on a review branch followed by optional PR.
- Direct default-branch mass replacement is not the default.
- `.github/workflows/*` requires the appropriate Workflows capability.
- Never blindly retry a destructive/non-idempotent write after an uncertain result; reconcile remote state first.

## Webhook strategy

- GitHub webhooks drive immediate notifications.
- Verify `X-Hub-Signature-256` using HMAC-SHA256 before parsing/processing.
- Deduplicate by GitHub delivery ID.
- Persist accepted events before asynchronous processing.
- Keep ingress fast; enrichment/rendering happens after durable acceptance.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing the existing navigation message when practical.
- Use inline keyboards; normally no more than two primary action buttons per row.
- Keep Home / Cancel / Back consistent.
- Destructive actions are isolated and Tier 2/3 actions require persisted explicit confirmation.
- Repository deletion additionally requires exact repository name plus final confirmation.
- Long logs/files use pagination or document delivery.

## Safety memory

- Never expose or commit tokens, private keys, client/webhook secrets, OAuth codes, PKCE verifiers, or credential-encryption keys.
- Do not implement arbitrary shell execution as a normal bot capability.
- Clone/setup/run generates commands and never silently executes repository-controlled instructions.
- No normal v1 force-push UI.
- High-impact multi-step operations must not depend only on volatile in-memory FSM state.
- Audit GitHub writes without secret material.
- GitHub remains source of truth for GitHub resources; local GitHub metadata is cache/preferences/operation state only.
- Do not turn GitHub pagination/download helpers into arbitrary outbound URL fetchers.

## Development governance memory

`AGENTS.md` is mandatory. A feature with green tests but stale project state is not Done. Successful work updates, as applicable:

- `docs/CURRENT_STATUS.md`
- `docs/PROJECT_MEMORY.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- affected architecture/security/constants/decision/test/UX docs.

## Current implementation fact

As of 2026-08-31:

- P0 complete.
- P1 merged and post-merge verified.
- P2.1 merged as `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge CI `33348851085` green.
- P2.2 merged as `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge CI `33409825480` green.
- P2.3 merged as `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; post-merge CI `33424799759` green; suite is 65 tests.
- The next implementation milestone is **P3.1 — GitHub repository search**.

## P3.1 durable boundary reminders

- Search is read-only; do not request repository write/admin permission.
- Build on `GitHubRestClient`; no raw GitHub HTTP in Telegram handlers/services.
- Public search results are not installed-repository authorization context and must not be inserted into `repositories_cache` as though installed.
- Normalize search results to typed models and keep callbacks compact/versioned.
- Search detail may reuse read-only rendering/model concepts but must preserve installed-vs-public provenance.
- Repository creation/settings/deletion remain P3.3, not P3.1.

## Do not forget later

- Search results: stars, forks, language, license, archived state, recency.
- Generate fresh-clone and existing-clone update commands.
- Run/setup commands derive from repository evidence and label uncertainty.
- Notification preferences are per repository and event type.
- Actions support includes status, jobs/steps/logs/artifacts, dispatch, retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
