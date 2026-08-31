# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅
- P2.3 — Home + repository read screens ✅

**Current phase:** P3 — Search & repository administration

**Next implementation item:** **P3.1 — GitHub repository search**.

## P2.3 final closeout

P2.3 was squash-merged through non-draft PR #8 into `main` as commit:

`939d218d76fd87f3ba6cf0a80a89b4a816aac557`

Verification evidence:

- implementation-head CI `33423169021` — green;
- documentation-synchronized branch-head CI `33424505117` — green;
- PR #8 CI `33424652835` — green;
- post-merge `main` CI `33424799759` — green.

Final verified gate set:

- Python 3.12: Ruff format ✅, Ruff lint ✅, mypy ✅, **65 pytest tests ✅**, compile ✅, `pip-audit` ✅, `detect-secrets` ✅, PEP 751 lock regeneration/diff ✅;
- Python 3.13: same configured complete gate set ✅;
- PostgreSQL 17: Alembic upgrade -> downgrade -> re-upgrade including migration `0003` ✅;
- `pip-audit`: no known runtime vulnerabilities reported ✅.

## What P2.3 delivered

- working Arabic Telegram home/connection state;
- working GitHub App installation/setup + OAuth callback wiring through the existing secure P2.1 state/PKCE/dual-context binding flow;
- installed repository list sourced through the P2.2 gateway;
- stable pagination and filters: all/private/public/active/archived/source/fork;
- repository dashboard metadata: visibility, archive/fork state, default branch, language, stars/forks, description, update time;
- refresh, disconnected/empty, stale-selection, authentication, permission, not-found, rate-limit, transient/error states;
- compact versioned repository callbacks that remain under Telegram callback limits;
- minimal `repositories_cache` + Alembic migration `0003` for server-side callback/navigation context;
- repository callback resolution scoped to GitDock user + active unsuspended installation;
- repository detail re-fetch from GitHub before render;
- stale cache pruning when repositories leave an installation;
- owner identity and runtime composition services;
- expanded test suite from 49 to **65 tests**.

## P2.3 durable invariants

- GitHub remains source of truth.
- `repositories_cache` is navigation/callback context only; it is not authorization proof and not a shadow GitHub database.
- Cache rows contain no access/refresh tokens, OAuth code/state, PKCE material, private keys, or raw GitHub error bodies.
- Repository callbacks use compact stable repository IDs + navigation context instead of arbitrary long `owner/name` strings.
- Repository selection is resolved server-side against the current GitDock user and bound unsuspended installation.
- Repository detail is revalidated from GitHub before display.
- P2.3 remains Tier 0 read-only and introduced no repository write/admin permission.
- Setup `installation_id` is still untrusted until P2.1 dual-context verification completes.
- Telegram handlers remain thin; application services own use cases and the GitHub gateway owns normal HTTP details.

## Known non-blocking maintenance warnings

The verified P2.3 suite still reports two recorded deprecation warnings:

- Starlette/FastAPI `TestClient` warning about the current `httpx` integration/future `httpx2` direction;
- Alembic warning because `alembic.ini` does not yet set explicit `path_separator` for `prepend_sys_path`.

They are maintenance debt, not hidden test failures.

## P3.1 scope — next

Build **GitHub repository search** without adding repository writes:

- search query flow using GitHub repository search;
- typed search-result model over the canonical P2.2 REST transport;
- stars/forks/language/license/archived/updated metadata;
- sort by stars/update;
- filters for language/min-stars/owner/topic/archive as planned;
- result pagination;
- result detail screen;
- clone-command entry point may be shown but command-generation implementation remains P4.3 unless explicitly scoped;
- safe no-results/rate/auth/error states;
- Telegram callbacks remain compact/versioned;
- public search results must not be inserted into installed `repositories_cache` as if they belonged to a GitHub App installation.

### P3.1 boundaries

- Do not implement repository creation/settings/deletion yet; that is P3.3.
- Do not introduce write/admin GitHub permission for search.
- Do not bypass `GitHubRestClient` with raw HTTP in handlers/services.
- Do not treat search results as installed-repository authorization context.
- Do not start P4 file browsing from the search milestone.

## Handoff instruction

Read `AGENTS.md` and mandatory pre-flight docs, branch from verified `main`, mark **P3.1 Active**, then build the repository-search use case through the existing gateway/service/Telegram boundaries. Preserve D-013, D-016, and D-017.
