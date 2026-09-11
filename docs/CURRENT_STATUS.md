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

**Current phase:** P4 — Repository contents, Git tools & run-command assistant.

**Current implementation item:** **P4.1 — File browser — implementation verified; merge/governance pending.**

Do not mark P4.1 phase-complete yet. The implementation head is green, but documentation-head CI, non-draft PR CI, unchanged-head merge, post-merge `main` CI, and governance closeout still remain.

## P4.1 implementation verification

- Final implementation head: `614f013b35644fcdd05e880c9a37ff30fd503fdf`.
- Feature CI: `34639736010` — fully green.
- Python 3.12 and 3.13: Ruff format/lint, mypy, pytest, compile, dependency audit, secret scan, and PEP 751 runtime-lock verification all green.
- `mypy`: **87 source files**.
- `pytest`: **148 passed** on both Python versions.
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade is green through migration `0006_file_write_sessions`.
- Runtime locks were refreshed after the cache-disabled CI environment exposed current transitive resolution for `anyio==4.15.1` and `multidict==6.8.0`; direct dependency pins are unchanged.

## P4.1 delivered behavior

- Real `📁 الملفات` repository action in Telegram.
- Directory browsing with pagination and parent navigation.
- Branch/Tag/SHA ref selection for reads.
- UTF-8 text preview with pagination; binary/large/missing-content fallback.
- File download when GitHub returns bounded content.
- Text-file create/edit, document create/replace, and file delete flows.
- Diff/preview before writes.
- Durable staged create/update/delete intent through `file_write_sessions` and persisted confirmations.
- Current branch-head/file-SHA preconditions reject stale overwrites/deletes.
- A newer staged write for the same user/repository/branch/path invalidates the older staged authority; regression coverage is explicit.
- Normal writes use repository-scoped `contents: write`; `.github/workflows/*` writes additionally require `workflows: write`.
- Write-like requests are issued once; uncertain outcomes reconcile GitHub state instead of blind replay.
- File-write audit records contain safe metadata, not file bodies or credentials.
- Long repository paths are never placed in Telegram callback data; callbacks carry short session IDs/indexes/tokens and resolve server-side context.

## P4.1 staging/data-lifetime facts

- File body bytes may be persisted temporarily in `file_write_sessions` so a reviewed write survives process restart.
- Staged write TTL is **15 minutes**.
- Staged content is cleared on consume, cancel, same-target supersession, expiry/prune, or invalidation paths that consume the staged session.
- This staged file content is **not** audit-log data.
- Audit metadata excludes access/refresh/installation tokens and file bodies.

## Executable P4.1 limits

- text preview ceiling: 256 KiB;
- single Telegram upload/download boundary used by P4.1: 20 MiB;
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

## Known non-blocking maintenance warnings

- Starlette/FastAPI TestClient deprecation toward httpx2.
- AnyIO `BlockingPortal` alias deprecation surfaced through Starlette tests.
- Alembic `prepend_sys_path` warning because `path_separator` is not yet explicit.

These are maintenance debt, not hidden test failures.

## Exact next work

Finish the P4.1 governance chain on the unchanged verified feature head:

1. synchronize control docs and run documentation-head CI;
2. open a non-draft P4.1 PR to `main`;
3. require green PR CI and mergeable unchanged head;
4. squash-merge with expected-head protection;
5. require post-feature `main` CI green;
6. perform the docs-only P4.1 governance closeout and verify it through PR + post-closeout `main` CI.

Only after that closeout does **P4.2 — Branch/commit tools** become the exact implementation task.
