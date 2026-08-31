# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Current item:** P2.2 — GitHub gateway foundation — active on `feat/p2-github-gateway`.

**Next item after verified P2.2 merge:** P2.3 — Home + repository read screens.

## P2.1 final verification

P2.1 was squash-merged through PR #5 into `main` as commit `81dfaf406d046205b39980d6a64c681ea3ab18c6`.

Verification evidence:

- PR #5 final-head CI run `33348768686` — green.
- Post-merge `main` CI run `33348851085` — green.
- Python 3.12: Ruff format/lint, mypy, 37 pytest tests, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff — passed.
- Python 3.13: same gates and 37 tests — passed.
- PostgreSQL 17: Alembic upgrade -> downgrade -> upgrade — passed.

The earlier PR #4 draft was closed without merge only because the connector's ready-for-review GraphQL mutation failed internally; no quality gate was bypassed.

## Active P2.2 scope

Implement the GitHub transport/gateway foundation only:

- [~] typed REST client wrapper.
- [ ] pagination helper with trusted GitHub API next-link validation.
- [ ] stable GitDock error translation.
- [ ] rate-limit capture/model.
- [ ] bounded retry policy for safe transient requests only.
- [ ] contract test doubles/fixtures.

### P2.2 boundaries

- No Telegram repository screens in this item; those belong to P2.3.
- No repository write/admin operations.
- No raw GitHub HTTP calls from Telegram handlers/services outside the gateway.
- GitHub API host is fixed/validated; pagination must not create an SSRF-capable arbitrary URL fetcher.
- Authentication/authorization bodies, tokens, and raw sensitive response content must not enter exception messages or logs.
- Retry GET/HEAD and explicitly safe operations only; do not create a generic blind write retry.

## Required P2.2 verification

Before P2.2 can be marked complete:

- Ruff format/lint green.
- mypy green.
- full pytest green on Python 3.12 and 3.13.
- gateway contract tests cover headers, pagination, error categories, rate limits, safe retries, no unsafe write retry, and hostile pagination URL rejection.
- compile check, `pip-audit`, `detect-secrets`, and PEP 751 lock drift green.
- PostgreSQL migration CI remains green even though P2.2 is not expected to change schema.
- project-control docs synchronized on the exact verified head.
- PR merged only from an unchanged green head, then `main` CI verified.

## Rules that remain in force

- GitHub App remains the primary credential model; broad long-lived PATs are not introduced.
- A setup/install `installation_id` remains untrusted until dual-context verification.
- GitHub remains source of truth for GitHub resources.
- Telegram handlers remain thin; transport details live in the gateway.
- Secrets/tokens/private keys/OAuth material are never committed, logged, or rendered to Telegram.
- No repository write/admin feature is pulled forward into P2.2.

## Handoff instruction

Read `AGENTS.md`, `docs/PROJECT_MEMORY.md`, this file, `docs/CONSTANTS.md`, `docs/ARCHITECTURE.md`, `docs/SECURITY_MODEL.md`, `docs/BUILD_PROTOCOL.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, and `docs/TEST_MATRIX.md`. Continue only P2.2 until its full CI and documentation closeout are green; then start P2.3 from verified `main`.