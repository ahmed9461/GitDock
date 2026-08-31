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

**Current implementation item:** **P3.1 — GitHub repository search — Active** on `feat/p3-1-github-search`.

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

Final verified gate set:

- Python 3.12: Ruff format ✅, Ruff lint ✅, mypy ✅, **65 pytest tests ✅**, compile ✅, `pip-audit` ✅, `detect-secrets` ✅, PEP 751 lock regeneration/diff ✅;
- Python 3.13: same configured complete gate set ✅;
- PostgreSQL 17: Alembic upgrade -> downgrade -> re-upgrade including migration `0003` ✅;
- `pip-audit`: no known runtime vulnerabilities reported ✅.

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

## P3.1 active scope

Build **GitHub repository search** without adding repository writes:

- search query flow using GitHub repository search;
- typed public-search result model over the canonical P2.2 REST transport;
- stars/forks/language/license/archived/updated metadata;
- sort by stars/update;
- filters for language/min-stars/owner/topic/archive as planned;
- result pagination using `SEARCH_PAGE_SIZE`;
- result detail screen;
- safe search session/context for compact callbacks without polluting installed `repositories_cache`;
- clone-command entry point may be shown but command-generation implementation remains P4.3 unless explicitly scoped;
- safe no-results/rate/validation/transient/error states;
- search remains usable for public discovery even when no GitHub installation is bound;
- Telegram callbacks remain compact/versioned;
- public search results must not be inserted into installed `repositories_cache` as if they belonged to a GitHub App installation.

### P3.1 boundaries

- Tier 0 read-only only.
- Do not implement repository creation/settings/deletion yet; that is P3.3.
- Do not introduce write/admin GitHub permission for search.
- Do not bypass `GitHubRestClient` with raw HTTP in handlers/services.
- Do not treat search results as installed-repository authorization context.
- Do not start P4 file browsing or clone-command inference from the search milestone.
- Search-session state may be ephemeral because it authorizes no write; stale/restarted sessions must fail closed and ask for a new search.

## P3.1 verification required before completion

- typed GitHub search payload parsing and metadata coverage;
- safe query/filter construction with validation;
- public/anonymous search behavior and rate-limit mapping;
- stars/update sorting and planned filter qualifiers;
- stable result pagination and no-results behavior;
- search detail resolution only inside the active search session/context;
- compact callbacks remain within Telegram's 64-byte limit;
- search result state remains separate from installed `repositories_cache`;
- owner middleware still blocks unauthorized message/callback paths;
- Ruff, mypy, full pytest, compile, `pip-audit`, `detect-secrets`, PEP 751 locks, and PostgreSQL migration CI remain green;
- project-control documentation is synchronized on the final green head;
- non-draft PR is merged from an unchanged green head and post-merge `main` CI is verified.

## Handoff instruction

Continue only P3.1 on `feat/p3-1-github-search` until its implementation, tests, documentation, PR, and post-merge verification are complete. Preserve D-013, D-016, and D-017. The next roadmap item after verified P3.1 is P3.2 user-context authorization/disconnect support.
