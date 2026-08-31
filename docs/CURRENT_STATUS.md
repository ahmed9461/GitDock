# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Current item:** P2.3 — Home + repository read screens — implementation verified on `feat/p2-repository-read`; merge closeout pending.

## P2.2 final verification

P2.2 was squash-merged through non-draft PR #7 into `main` as commit `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`.

Verification evidence:

- implementation-head CI `33406986504` — green;
- synchronized Draft PR #6 CI `33409265057` — green;
- replacement PR #7 CI `33409418512` — green;
- final PR #7 head `153e30cc86499918f300a74e074213affd92f319` CI `33409670775` — green;
- post-merge `main` CI `33409825480` — green.

Python 3.12 and 3.13 each passed Ruff format/lint, mypy, **49 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff. PostgreSQL 17 migration upgrade -> downgrade -> upgrade also passed.

P2.2 durable invariants remain mandatory:

- `GitHubRestClient` is the canonical REST transport boundary;
- normal Telegram/application code does not issue raw GitHub HTTP;
- pagination targets are restricted to canonical HTTPS `api.github.com`;
- raw GitHub bodies/tokens are not exposed through gateway errors;
- GET/HEAD may retry bounded transient failures; writes do not retry by default;
- GitHub remains source of truth.

## P2.3 verified implementation

Implementation head `a6d57d5a99b58004fab4dbf84b9b6742a9475523` passed CI run `33423169021`.

Verified on the implementation head:

- Python 3.12: Ruff format ✅, Ruff lint ✅, mypy ✅, **65 pytest tests ✅**, compile ✅, `pip-audit` ✅, `detect-secrets` ✅, PEP 751 lock regeneration/diff ✅;
- Python 3.13: the same complete quality/security/lock gate set ✅;
- PostgreSQL 17 migration chain including `0003` upgrade -> downgrade -> upgrade ✅;
- `pip-audit` reported no known runtime vulnerabilities.

Implemented read-only user experience:

- [x] GitHub connection/home state and Arabic Telegram home screen.
- [x] working GitHub App setup + OAuth callback wiring using the existing P2.1 state/PKCE/binding services.
- [x] installed-repository list sourced from GitHub installation context.
- [x] stable pagination and repository filters: all/private/public/active/archived/source/fork.
- [x] repository dashboard metadata: visibility, archive/fork state, default branch, language, stars/forks, description, updated time.
- [x] refresh, empty, stale-selection, auth/permission/not-found/rate/transient user-facing states.
- [x] compact versioned Telegram callbacks with repository ID resolved server-side.
- [x] minimal `repositories_cache` and Alembic migration `0003` for callback/context resolution.
- [x] repository detail is re-fetched from GitHub before rendering; stale/not-found cache entries are removed.
- [x] thin Telegram handlers wired through application services and the P2.2 gateway.
- [x] contract/integration/unit UI coverage expanding the suite from 49 to **65 tests**.

### P2.3 security/architecture invariants

- Tier 0 read-only only; P2.3 introduces no repository write/admin feature.
- No new GitHub write permission is required.
- `repositories_cache` is **not** authoritative GitHub state. It stores only safe non-secret metadata/context needed for compact callbacks and navigation.
- Repository callbacks do not embed arbitrary long `owner/name`; they carry a compact versioned repository identifier plus navigation context.
- Callback repository resolution is scoped to the GitDock user and a currently bound, unsuspended installation.
- Repository detail is revalidated from GitHub before display.
- Tokens, OAuth codes, PKCE material, private keys, and raw upstream error bodies are never rendered to Telegram or stored in the repository cache.
- Setup `installation_id` remains untrusted until the P2.1 dual-context verification flow succeeds.
- GitHub remains source of truth.

## Known non-blocking maintenance warnings

The green CI currently reports deprecation warnings that do not fail the build:

- Starlette/FastAPI `TestClient` warns that its current `httpx` integration is deprecated in favor of the future `httpx2` path.
- Alembic warns that `alembic.ini` has no explicit `path_separator`; it falls back to legacy `prepend_sys_path` splitting.

These are maintenance follow-ups, not hidden test failures. Do not claim a zero-warning suite until they are resolved.

## P2.3 closeout still required

P2.3 is **not yet marked verified complete** until all of the following happen on an unchanged final head:

1. project-control documentation is synchronized;
2. full CI is green again on that documentation-synchronized head;
3. a non-draft PR is opened from the exact green head;
4. PR CI is green and the PR is mergeable;
5. merge uses the verified expected head SHA;
6. post-merge `main` CI is green;
7. final handoff documents record the merge commit and `main` CI result.

Do not begin P3.1 before this closeout is finished.

## Rules that remain in force

- GitHub App remains the primary credential model.
- A setup/install `installation_id` is untrusted until dual-context verification.
- GitHub remains source of truth.
- Telegram handlers stay thin; services own use cases; gateway owns GitHub HTTP.
- No secrets/tokens/private keys/OAuth material are committed, logged, cached as repository metadata, or rendered to Telegram.
- P2.3 introduces no write/admin feature.

## Handoff instruction

Read `AGENTS.md` and the mandatory pre-flight documents. Continue only P2.3 closeout on `feat/p2-repository-read`. After final documentation-head CI, PR merge, and post-merge `main` verification, mark P2.3 complete and move to **P3.1 — GitHub repository search**.
