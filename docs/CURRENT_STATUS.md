# GitDock — Current Status / Handoff

Last updated: 2026-09-01

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅
- P2.3 — Home + repository read screens ✅
- P3.1 — GitHub repository search ✅

**Current phase:** P3 — Search & repository administration

**Next implementation item:** **P3.2 — user-context authorization/disconnect support**. Do not start it from this closeout branch; begin from a fresh feature branch after this governance closeout is merged and its `main` CI is green.

## P2.3 final closeout

P2.3 was squash-merged through non-draft PR #8 into `main` as `939d218d76fd87f3ba6cf0a80a89b4a816aac557`. Governance closeout PR #9 merged as `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`; post-closeout `main` CI `33444410513` is green.

## P3.1 — verified complete

P3.1 public GitHub repository search is implementation-, PR-, merge-, and post-merge-verified.

Verification chain:

- implementation head `4a4f00d50e886ab494e2a83f2c649cd64b7398b2` — CI `33453960817` green;
- final documentation-synchronized feature head `14e149ea307871abd8406ffc6212fe062ead9098` — branch CI `33454438202` green;
- non-draft PR #10 — PR CI `33454524953` green and `mergeable=true` on the unchanged head;
- PR #10 squash merge commit `d822338fcc1546418ed2100cc9534cdc71a6bcbe`;
- post-merge `main` CI `33454619065` — green on Python 3.12, Python 3.13, and PostgreSQL 17.

Verified gate set:

- Ruff format ✅;
- Ruff lint ✅;
- mypy ✅;
- **83 pytest tests ✅**;
- compile ✅;
- `pip-audit` ✅ with no known runtime vulnerabilities reported;
- `detect-secrets` ✅;
- PEP 751 lock regeneration/diff ✅;
- PostgreSQL 17 Alembic upgrade -> downgrade -> re-upgrade ✅.

P3.1 implements:

- public GitHub repository search without requiring a bound GitHub App installation;
- typed repository-search payload/result models over the canonical `GitHubRestClient`;
- query validation and normalized GitHub qualifiers;
- stars/forks/language/license/default-branch/topics/archive/update metadata;
- sorting by stars or last update;
- filters for language, minimum stars, `user:`/`org:` owner scope, topic, and archive visibility;
- stable application pagination using `SEARCH_PAGE_SIZE`;
- Arabic result/detail/filter UI and `/search` entry point;
- compact versioned callbacks with opaque search-session IDs;
- active-session validation so callbacks from older searches fail closed;
- detail resolution only through the active result context followed by a fresh GitHub detail request;
- `/start` and Home clearing transient search FSM state;
- public search state kept separate from installed `repositories_cache`;
- Tier 0 read-only behavior with no repository write/admin permission.

The search detail screen exposes **📥 أوامر التنزيل** only as a safe placeholder. Actual clone/update/setup/run command generation remains P4.3 and is not part of P3.1 completion.

## P3.1 durable invariants

- GitHub remains source of truth.
- Public search is discovery context, never installed-repository authorization context.
- Public search results must never be inserted into `repositories_cache` as though they belonged to a GitHub App installation.
- Search callbacks carry compact session/result identifiers rather than arbitrary repository names.
- A stale/restarted/older search session fails closed.
- Search detail is re-fetched from GitHub before display.
- Search may use ephemeral FSM state because it is Tier 0 and authorizes no write; Home/start explicitly clear that state.
- Telegram handlers remain thin; the search service owns query/filter behavior and the GitHub gateway owns normal HTTP details.
- P3.1 adds no repository write/admin permission.
- Clone/setup/run command generation remains P4.3.

## Known non-blocking maintenance warnings

The verified suite still reports the two recorded deprecation warnings:

- Starlette/FastAPI `TestClient` warning about the current `httpx` integration/future `httpx2` direction;
- Alembic warning because `alembic.ini` does not yet set explicit `path_separator` for `prepend_sys_path`.

They are maintenance debt, not hidden test failures.

## Handoff instruction

Finish only the `docs/p3-1-closeout` governance PR and verify its post-merge `main` CI. Then open a fresh branch for P3.2 from that final green `main` commit and mark P3.2 Active before implementation. Preserve D-013, D-016, D-017, the P2.1 secure OAuth/PKCE/encryption invariants, and all P3.1 public-search provenance/session boundaries.
