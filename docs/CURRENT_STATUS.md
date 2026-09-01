# GitDock — Current Status / Handoff

Last updated: 2026-09-01

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅
- P2.3 — Home + repository read screens ✅

**Current phase:** P3 — Search & repository administration

**Current implementation item:** **P3.1 — GitHub repository search — implementation verified on branch; closure pending PR + post-merge `main` verification** on `feat/p3-1-github-search`.

## P2.3 final closeout

P2.3 was squash-merged through non-draft PR #8 into `main` as commit:

`939d218d76fd87f3ba6cf0a80a89b4a816aac557`

Final governance closeout was squash-merged through PR #9 as:

`ac8230eb1f8b7099979c55e767d9f6d14e0118a7`

Verification evidence:

- implementation-head CI `33423169021` — green;
- documentation-synchronized branch-head CI `33424505117` — green;
- PR #8 CI `33424652835` — green;
- post-P2.3 merge `main` CI `33424799759` — green;
- closeout PR #9 CI `33444114152` — green;
- post-closeout `main` CI `33444410513` — green.

## P3.1 implementation verified

Implementation head:

`4a4f00d50e886ab494e2a83f2c649cd64b7398b2`

GitHub Actions run `33453960817` is green across the complete configured gate set:

- Python 3.12: Ruff format ✅, Ruff lint ✅, mypy ✅, **83 pytest tests ✅**, compile ✅, `pip-audit` ✅, `detect-secrets` ✅, PEP 751 lock regeneration/diff ✅;
- Python 3.13: same configured complete gate set ✅;
- PostgreSQL 17: Alembic upgrade -> downgrade -> re-upgrade ✅;
- `pip-audit`: no known runtime vulnerabilities reported ✅.

P3.1 currently implements:

- public GitHub repository search without requiring a bound GitHub App installation;
- typed repository-search payload/result models over the canonical `GitHubRestClient`;
- query validation and normalized GitHub qualifiers;
- stars/forks/language/license/default-branch/topics/archive/update metadata;
- sorting by stars or last update;
- filters for language, minimum stars, `user:`/`org:` owner scope, topic, and archive visibility;
- stable application pagination using `SEARCH_PAGE_SIZE`;
- Arabic result/detail/filter UI and `/search` entry point;
- compact versioned callbacks with opaque search-session IDs;
- active-session validation so callbacks from an older search fail closed;
- detail resolution only through the active result context followed by a fresh GitHub detail request;
- Home navigation clears transient search FSM state;
- public search state remains separate from installed `repositories_cache` and grants no repository authorization;
- search remains Tier 0 read-only and introduces no repository write/admin permission.

The search detail screen exposes a **📥 أوامر التنزيل** entry point only as a safe placeholder. Actual clone/setup/run command generation is intentionally deferred to P4.3 and must not be reported as implemented in P3.1.

## P3.1 closure still required

P3.1 is not yet marked final/merged complete until all of the following occur:

1. synchronize project-control documentation on the verified feature branch;
2. run CI on that final documentation-synchronized head;
3. open a non-draft PR from the unchanged green head;
4. verify PR CI and mergeability;
5. squash-merge without changing the verified head;
6. verify post-merge `main` CI;
7. record exact PR/merge/main-CI facts in the governance closeout before moving P3.1 to final ✅ state.

## P3.1 durable invariants

- GitHub remains source of truth.
- Public search is discovery context, not installed-repository authorization context.
- Public search results must never be inserted into `repositories_cache` as though they belonged to a GitHub App installation.
- Search callbacks carry compact session/result identifiers instead of arbitrary repository names.
- A stale/restarted/older search session fails closed and asks for a new search.
- Search detail is re-fetched from GitHub before display.
- Search may use ephemeral FSM state because it is Tier 0 and authorizes no write; Home explicitly clears that state.
- Telegram handlers remain thin; search service owns query/filter behavior and the GitHub gateway owns normal HTTP details.
- P3.1 does not request repository write/admin permissions.
- Clone/setup/run command generation remains P4.3.

## Known non-blocking maintenance warnings

The verified suite still reports the two recorded deprecation warnings:

- Starlette/FastAPI `TestClient` warning about the current `httpx` integration/future `httpx2` direction;
- Alembic warning because `alembic.ini` does not yet set explicit `path_separator` for `prepend_sys_path`.

They are maintenance debt, not hidden test failures.

## Handoff instruction

Continue only P3.1 closure on `feat/p3-1-github-search` until documentation-head CI, non-draft PR, squash merge, post-merge `main` CI, and final governance closeout are verified. Preserve D-013, D-016, and D-017. Do not start P3.2 before P3.1 is fully closed. The next roadmap item after verified P3.1 is P3.2 user-context authorization/disconnect support.
