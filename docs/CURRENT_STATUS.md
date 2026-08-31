# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Current item:** P2.2 — GitHub gateway foundation — implementation verified; documentation/PR closeout in progress on `feat/p2-github-gateway`.

**Next item after verified P2.2 merge and `main` CI:** P2.3 — Home + repository read screens.

## P2.1 final verification

P2.1 was squash-merged through PR #5 into `main` as commit `81dfaf406d046205b39980d6a64c681ea3ab18c6`.

Verification evidence:

- PR #5 final-head CI run `33348768686` — green.
- Post-merge `main` CI run `33348851085` — green.
- Python 3.12: Ruff format/lint, mypy, 37 pytest tests, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff — passed.
- Python 3.13: same gates and 37 tests — passed.
- PostgreSQL 17: Alembic upgrade -> downgrade -> upgrade — passed.

The earlier PR #4 draft was closed without merge only because the connector's ready-for-review GraphQL mutation failed internally; no quality gate was bypassed.

## P2.2 verified implementation

Implemented on `feat/p2-github-gateway` in Draft PR #6:

- [x] typed `GitHubRestClient` transport wrapper.
- [x] canonical REST headers: GitHub media type, REST API version `2026-03-10`, and `GitDock/0.1` User-Agent.
- [x] parser-driven typed `GitHubResponse[T]` / `GitHubPage[T]` boundary.
- [x] pagination helper with validated `next` / `prev` / `first` / `last` links.
- [x] async page iterator with repeated-link detection and a configured maximum page limit.
- [x] canonical GitHub API target validation; external, credentialed, protocol-relative, fragment-bearing, or non-HTTPS pagination targets are rejected before network I/O.
- [x] stable GitDock error categories for authentication, permission, not-found, conflict, validation, rate-limit, transient, and unexpected failures.
- [x] transport exceptions contain safe status/request/rate metadata but never raw GitHub response bodies.
- [x] GitHub rate-limit metadata capture including resource, limit, remaining, used, reset time, and `Retry-After`.
- [x] bounded exponential backoff with jitter for transient safe requests.
- [x] GET/HEAD retry safely by default; write-like methods do **not** retry by default.
- [x] an explicit `RetryMode.SAFE` escape hatch exists only for a higher layer that has positively classified a non-read operation as retry-safe.
- [x] redirects are not followed by the gateway transport.
- [x] HTTPX MockTransport contract fixture/tests added.

### P2.2 security/architecture invariants

- Telegram/application handlers must not call raw GitHub HTTP endpoints; they consume gateway/service interfaces.
- Absolute transport/pagination targets are restricted to canonical HTTPS `api.github.com`; the gateway is not a generic URL fetcher.
- Authentication headers are constructed from `SecretStr` only at the outbound transport boundary.
- Raw GitHub error bodies are intentionally not copied into raised errors or user-facing text.
- Blind retries of writes are prohibited. A write/non-read operation requires explicit retry-safe classification by the caller before retry can occur.
- GitHub remains source of truth; transport metadata is contextual information, not locally authoritative resource state.

## P2.2 verification evidence

Implementation head `ca6c0beb4ea96f661e9e891b04e69228bf6c4de3` passed GitHub Actions run `33406986504`:

- Python 3.12: Ruff format/lint, mypy, **49 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff — all passed.
- Python 3.13: the same configured gates — all passed.
- PostgreSQL 17: Alembic upgrade -> downgrade -> upgrade — passed.
- `pip-audit`: no known vulnerabilities found.
- Test suite grew from 37 to 49 tests; 12 contract tests cover gateway headers, pagination, hostile URL rejection, error translation, rate limits, safe retry behavior, and no default write retry.
- P2.2 adds no runtime dependency and no schema migration, so the existing PEP 751 locks remain byte-for-byte valid and PostgreSQL migration coverage remains unchanged.

This run verifies the implementation before documentation closeout. A new full CI run is still required on the exact documentation-synchronized head before PR merge.

## Remaining P2.2 closeout

1. Synchronize durable project memory, roadmap, changelog, constants, architecture/security/test/decision documentation.
2. Require full green CI on the exact synchronized PR head.
3. Convert/replace Draft PR #6 with a non-draft PR if the known connector ready-for-review mutation fails again; do not merge a Draft.
4. Merge only with `expected_head_sha` matching the verified final head.
5. Verify post-merge `main` CI.
6. Synchronize post-merge handoff state if necessary.
7. Only then start **P2.3 — Home + repository read screens** from verified `main`.

## Rules that remain in force

- GitHub App remains the primary credential model; broad long-lived PATs are not introduced.
- A setup/install `installation_id` remains untrusted until dual-context verification.
- GitHub remains source of truth for GitHub resources.
- Telegram handlers stay thin; transport details live in the GitHub gateway.
- Secrets/tokens/private keys/OAuth material are never committed, logged, or rendered to Telegram.
- No repository write/admin feature is pulled forward into P2.2.
- No arbitrary outbound URL support is introduced through pagination or gateway helpers.

## Handoff instruction

Read `AGENTS.md`, `docs/PROJECT_MEMORY.md`, this file, `docs/CONSTANTS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY_MODEL.md`, `docs/BUILD_PROTOCOL.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/TEST_MATRIX.md`. Finish only P2.2 documentation/PR/main verification before starting P2.3.