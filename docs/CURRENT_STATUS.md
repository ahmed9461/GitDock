# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Current item:** P2.2 — GitHub gateway foundation — implementation and documentation verified; non-draft PR #7 is the merge target.

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

Implemented on `feat/p2-github-gateway`. Draft PR #6 was used during implementation and documentation closeout; it was closed without merge after its final synchronized head passed CI. Non-draft PR #7 was then opened from the exact same unchanged feature-branch SHA because the known connector Draft→Ready mutation is unreliable.

Implemented scope:

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

Implementation head `ca6c0beb4ea96f661e9e891b04e69228bf6c4de3` passed GitHub Actions run `33406986504`.

The fully documentation-synchronized feature head `d60953bb27951a3ff9019efb101087222a0219af` then passed Draft PR #6 CI run `33409265057` with all configured jobs green.

The same unchanged SHA was opened as non-draft PR #7 and passed its own CI run `33409418512` with all configured jobs green.

Across the verified P2.2 heads:

- Python 3.12: Ruff format/lint, mypy, **49 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff — all passed.
- Python 3.13: the same configured gates — all passed.
- PostgreSQL 17: Alembic upgrade -> downgrade -> upgrade — passed.
- `pip-audit`: no known vulnerabilities found.
- Test suite grew from 37 to 49 tests; 12 contract tests cover gateway headers, pagination, hostile URL rejection, error translation, rate limits, safe retry behavior, and no default write retry.
- P2.2 adds no runtime dependency and no schema migration, so the existing PEP 751 locks remain byte-for-byte valid and PostgreSQL migration coverage remains unchanged.

## P2.2 PR replacement operational fact

The connector's Draft→Ready GraphQL mutation was already known to fail in earlier project work. To avoid repeating a known tooling failure:

1. Draft PR #6 was kept through implementation/documentation verification.
2. Its final synchronized SHA `d60953bb27951a3ff9019efb101087222a0219af` passed run `33409265057`.
3. PR #6 was closed without merge and without changing the feature branch.
4. Non-draft PR #7 was opened from the exact same SHA.
5. PR #7 passed its own run `33409418512` on that unchanged SHA.

No temporary file, no branch-content mutation, and no quality-gate bypass occurred during this replacement.

## Remaining P2.2 closeout

1. Run full CI once more on this handoff-only documentation commit so the exact PR head is verified.
2. Merge PR #7 with `expected_head_sha` matching that final green head.
3. Verify post-merge `main` CI.
4. Synchronize post-merge handoff state if necessary.
5. Only then start **P2.3 — Home + repository read screens** from verified `main`.

## Rules that remain in force

- GitHub App remains the primary credential model; broad long-lived PATs are not introduced.
- A setup/install `installation_id` remains untrusted until dual-context verification.
- GitHub remains source of truth for GitHub resources.
- Telegram handlers stay thin; transport details live in the GitHub gateway.
- Secrets/tokens/private keys/OAuth material are never committed, logged, or rendered to Telegram.
- No repository write/admin feature is pulled forward into P2.2.
- No arbitrary outbound URL support is introduced through pagination or gateway helpers.

## Handoff instruction

Read `AGENTS.md`, `docs/PROJECT_MEMORY.md`, this file, `docs/CONSTANTS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY_MODEL.md`, `docs/BUILD_PROTOCOL.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/TEST_MATRIX.md`. Finish only P2.2 PR/main verification before starting P2.3.
