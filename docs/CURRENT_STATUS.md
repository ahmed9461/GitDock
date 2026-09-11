# GitDock — Current Status / Handoff

Last updated: 2026-09-11

## Project state

**Verified complete:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅
- P2.3 — Home + repository read screens ✅
- P3.1 — GitHub repository search ✅
- P3.2 — durable GitHub user-context authorization/disconnect ✅
- P3.3 — repository create/settings administration ✅
- P4.1 — repository file browser + stale-safe single-file writes ✅

**Current phase:** P4 — Repository contents, Git tools & run-command assistant.

**Current implementation item:** **P4.2 — Branch/commit tools.**

P4.1 feature delivery is merged and post-feature `main` verified. This closeout records the completed governance state and hands implementation to P4.2. Do not reopen P4.1 unless a real regression is found.

## P4.1 final feature-delivery verification chain

- Implementation head: `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010` green.
- Documentation-synchronized feature head: `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457` green.
- Non-draft PR #16: unchanged head `185d99d33e863e0909e7e0459d9fcf7fe5df1244`, `mergeable=true`.
- PR #16 CI: `34641248664` — green.
- Protected squash merge using expected head: `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6`.
- Post-feature `main` CI: `34641411838` — green.

Verification contract remained green throughout:

- Python 3.12 and 3.13;
- Ruff format/lint;
- mypy clean on **87 source files**;
- **148 tests passed** on both Python versions;
- compileall;
- `pip-audit` with no known runtime vulnerabilities;
- `detect-secrets` with no findings;
- PEP 751 lock regeneration/diff byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade through `0006_file_write_sessions`.

## P4.1 delivered behavior

- Real `📁 الملفات` repository action in Telegram.
- Directory browsing with pagination and parent navigation.
- Branch/Tag/SHA ref selection for reads.
- UTF-8 text preview with pagination; binary/large/missing-content fallback.
- Bounded file download.
- Text-file create/edit, document create/replace, and file delete flows.
- Diff/preview before writes.
- Durable staged create/update/delete intent through `file_write_sessions` and persisted confirmations.
- Current branch-head/file-SHA preconditions reject stale overwrites/deletes.
- A newer staged write for the same user/repository/branch/path invalidates the older staged authority.
- Normal writes use repository-scoped `contents: write`; `.github/workflows/*` additionally requires `workflows: write`.
- Write-like requests are issued once; uncertain outcomes reconcile GitHub state instead of blind replay.
- File-write audit records contain safe metadata, not file bodies or credentials.
- Long repository paths are never placed in Telegram callback data; callbacks use short session IDs/indexes/tokens and resolve server-side context.

## P4.1 staging/data-lifetime facts

- File body bytes may be persisted temporarily in `file_write_sessions` so a reviewed write survives process restart.
- Staged write TTL is **15 minutes**.
- Staged content is cleared on consume, cancel, same-target supersession, expiry/prune, or invalidation paths that consume the staged session.
- Staged file content is **not** audit-log data.
- Audit metadata excludes access/refresh/installation tokens and file bodies.

## Executable P4.1 limits

- text preview ceiling: 256 KiB;
- single upload boundary: 20 MiB;
- preview page: 2800 characters;
- repository path: 1024 characters;
- ref: 255 characters;
- commit message: 500 characters;
- browse session entropy: 6 bytes;
- durable file-write staging TTL: 900 seconds.

## Durable invariants carried forward

- GitHub remains source of truth.
- GitHub App remains the primary credential model.
- Repository cache is navigation/context state, never authorization proof.
- Telegram callbacks are transport only; sensitive authority is server-side.
- Current remote state and scoped permissions are revalidated before sensitive execution.
- No blind retry of uncertain/destructive GitHub writes; reconcile remote state first.
- Repository deletion remains Tier 3 exact-name gated.
- Single-file writes follow stage → preview → confirm → revalidate → scoped token → single write → reconcile → audit.

## Known non-blocking maintenance warnings

- Starlette/FastAPI TestClient deprecation toward httpx2.
- AnyIO `BlockingPortal` alias deprecation surfaced through Starlette tests.
- Alembic `prepend_sys_path` warning because `path_separator` is not yet explicit.

These are maintenance debt, not hidden test failures.

## Exact next work — P4.2 Branch/commit tools

Start from the final closeout `main` head after this governance PR lands and its post-merge CI is green.

P4.2 scope:

- list branches;
- search/filter branches where useful;
- create branch from a known current base ref/SHA;
- recent commits;
- commit detail and safe diff summary;
- compare refs;
- preserve no-force-push v1 policy;
- keep callbacks compact and GitHub-backed state authoritative;
- branch creation must use explicit target/base preview and stale-safe preconditions where applicable.
