# GitDock — Current Status / Handoff

Last updated: 2026-09-04

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

**Current phase:** P4 — Repository contents, Git tools & run-command assistant

**Current implementation item:** **P4.1 — File browser**.

## P3.3 final verification chain

- implementation head `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945` green;
- documentation-synchronized head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482` green;
- non-draft PR #14 — PR CI `33891899602` green and mergeable on unchanged head;
- squash merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature `main` CI `33892100584` green.

Verified suite: **117 tests** on Python 3.12 and 3.13, plus Ruff format/lint, mypy, compile, dependency audit, secret scan, PEP 751 lock verification, and PostgreSQL 17 Alembic upgrade/downgrade/re-upgrade including `0005_audit_log`.

## P3.3 delivered behavior

- Personal and authorized organization repository creation.
- Repository name, description, visibility, archive/unarchive, and default-branch updates.
- Tier 1 create, Tier 2 update, and Tier 3 delete confirmation flows.
- Exact current `owner/name` required before repository deletion.
- Repository-scoped administration authority for update/delete.
- Server-side one-time cancellation of pending create/update/delete confirmations.
- Stale/expired/reused/cancelled confirmation paths fail closed.
- Uncertain create/update/delete outcomes reconcile current GitHub state instead of blindly replaying writes.
- Durable repository-administration audit records through migration `0005_audit_log`.
- Arabic Telegram repository creation wizard and repository settings UI with thin handlers and centralized callbacks/keyboards/renderers/FSM.

## Durable invariants carried into P4

- GitHub remains source of truth.
- GitHub App remains the primary credential model.
- Repository cache is navigation/context state, never authorization proof.
- Sensitive execution depends on current server-side preconditions and persisted confirmation state.
- Telegram callbacks are transport only.
- Do not blindly retry uncertain/destructive GitHub writes; reconcile remote state first.
- Repository deletion remains Tier 3 and exact-name gated.

## Known non-blocking maintenance warnings

- Starlette/FastAPI TestClient deprecation toward httpx2.
- AnyIO BlockingPortal alias deprecation surfaced through Starlette tests.
- Alembic prepend_sys_path warning because path_separator is not yet explicit.

These remain maintenance debt, not hidden test failures.

## Exact next task — P4.1 File browser

Implement on a new feature branch from the post-closeout `main` head:

1. directory navigation;
2. text preview/pagination;
3. binary/large-file metadata fallback;
4. branch/ref selection;
5. create file;
6. update/replace file;
7. delete file;
8. current-SHA stale-write protection;
9. special workflow-file permission handling;
10. persisted write confirmation/preconditions and audit behavior;
11. thin Telegram handlers over the canonical GitHub gateway.

P4.1 follows the same completion discipline: synchronized docs, green final-head CI, non-draft PR, unchanged-head merge, post-merge `main` CI, and governance closeout.
