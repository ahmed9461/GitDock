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

P2.1 was squash-merged through PR #5 as commit `81dfaf406d046205b39980d6a64c681ea3ab18c6`.

- PR #5 final-head CI: `33348768686` — green.
- Post-merge `main` CI: `33348851085` — green.
- Python 3.12/3.13 each passed 37 tests plus format/lint/mypy/compile/audit/secret/lock checks.
- PostgreSQL 17 migration round trip passed.

Durable auth facts:

- GitHub App is primary auth; do not introduce a broad long-lived PAT as the normal credential model.
- App JWTs use RS256 and configured GitHub App client ID issuer.
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

P2.2 is implemented on `feat/p2-github-gateway` in PR #6. Implementation head `ca6c0beb4ea96f661e9e891b04e69228bf6c4de3` passed CI run `33406986504`; documentation closeout/final-head CI and merge are still required before P2.3 starts.

Durable gateway facts:

- `GitHubRestClient` is the canonical REST transport boundary.
- Telegram handlers and normal application services must not issue raw GitHub HTTP requests.
- Canonical outbound REST headers include GitHub media type, API version `2026-03-10`, and `User-Agent: GitDock/0.1`.
- Payload parsing is caller-supplied at the gateway boundary; successful results carry typed data plus safe transport metadata.
- `GitHubResponse[T]` and `GitHubPage[T]` carry request ID, status, pagination, and rate-limit metadata.
- Pagination links are accepted only when they resolve to canonical HTTPS `api.github.com`; protocol-relative, credentialed, fragmented, external-host, or other unsafe targets are rejected before network I/O.
- Pagination iteration has repeated-next-link detection and a configured max-page safety bound.
- The gateway is not a generic URL fetcher.
- Stable error categories cover authentication, permission, not-found, conflict/precondition, validation, rate-limit, transient, and unexpected failures.
- Gateway exceptions intentionally omit raw GitHub response bodies. Preserve safe status/request-id/rate metadata only.
- Rate-limit metadata captures resource, limit, remaining, used, reset timestamp, and `Retry-After` where present.
- GET/HEAD are retry-safe by default for bounded transient transport/5xx conditions.
- Write-like methods do **not** retry by default. A non-read operation may use `RetryMode.SAFE` only when a higher layer has positively established retry/idempotency safety for that specific operation.
- Redirects are not automatically followed by the REST gateway.
- HTTP timeouts/retry/page limits are centralized constants, not handler-local magic numbers.

P2.2 contract verification adds 12 tests, growing the suite from 37 to **49 tests**. CI run `33406986504` passed on Python 3.12 and 3.13, plus PostgreSQL 17. It also passed `pip-audit`, `detect-secrets`, compile, and byte-for-byte PEP 751 lock verification. No runtime dependency or DB schema change was needed for P2.2.

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

Known connector issue: the connector's `markPullRequestReadyForReview` GraphQL mutation has failed because it requested nonexistent `Repository.fullDatabaseId`. Previous safe workaround was to close the verified Draft without merging, open a non-draft replacement from the same branch, and require new final-head CI before merge. Never bypass CI or merge a Draft merely to work around the connector.

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
- P2.1 merged as `81dfaf406d046205b39980d6a64c681ea3ab18c6` and post-merge CI `33348851085` is green.
- P2.2 implementation is green in CI run `33406986504`; PR #6 remains Draft while documentation/final-head verification is completed.
- The next implementation task **after P2.2 merge and post-merge `main` verification** is **P2.3 — Home + repository read screens**.

## Do not forget later

- Search results: stars, forks, language, license, archived state, recency.
- Generate fresh-clone and existing-clone update commands.
- Run/setup commands derive from repository evidence and label uncertainty.
- Notification preferences are per repository and event type.
- Actions support includes status, jobs/steps/logs/artifacts, dispatch, retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.