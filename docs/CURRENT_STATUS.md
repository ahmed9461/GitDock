# GitDock — Current Status / Handoff

Last updated: 2026-09-12

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
- P4.2 — branch/commit tools ✅

**Current phase:** P4 — Repository contents, Git tools & run-command assistant.

**Current implementation item:** **P4.3 — Clone/setup/run assistant.**

P4.2 is fully delivered and governance-verified. Do not reopen it unless a real regression is found. New implementation work should now target P4.3 only.

## P4.2 final delivery chain

- implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518` — CI `34647181024` green;
- documentation-synchronized feature head `73e48dfced65d72d0d27e9defc4c3e107527107f` — push CI `34647866083` green;
- non-draft PR #18 on the unchanged head — PR CI `34648080794` green and mergeable;
- protected squash merge `b4e7dcd9de5db1e958e831508443d3fa1445213d`;
- post-feature `main` CI `34648224733` green.

The verified P4.2 contract remains:

- Python 3.12 and 3.13;
- Ruff format/lint;
- mypy clean on **94 source files**;
- **165 tests passed** on both Python versions;
- compileall;
- `pip-audit` with no known runtime vulnerabilities;
- `detect-secrets` with no findings;
- PEP 751 lock regeneration/diff byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade through `0006_file_write_sessions`.

Known maintenance warnings remain unchanged: Starlette/FastAPI TestClient deprecation toward httpx2, AnyIO `BlockingPortal` alias deprecation through Starlette, and Alembic `prepend_sys_path`/`path_separator` warning. They are not test failures.

## P4.2 delivered behavior

- Real repository-dashboard `🌿 الفروع` and `📝 Commits` actions in Telegram.
- Branch listing from current GitHub state with case-insensitive local filtering/search over the fetched branch set.
- Recent commits from the default branch or an explicitly entered branch/tag/SHA ref.
- Commit detail with SHA, author, authored time, first-line message, parent count, changed-file count, additions/deletions, and canonical GitHub link.
- Ref comparison through GitHub Compare API with ahead/behind/commit/file summary and a bounded first-10-files Telegram rendering for large comparisons.
- Branch creation from an explicit current base ref/SHA using preview → persisted one-time confirmation → revalidation → scoped write token → single create-ref request → reconciliation/audit.
- Confirm-time base SHA revalidation rejects a moved base as `STALE` before any write.
- Target branch absence is checked before preview and again before write; duplicate targets are never replaced/force-updated.
- Missing base ref fails before write.
- Branch creation is Tier 1 and uses a repository-scoped installation token requesting `contents: write` + metadata read only for the selected repository.
- Create-ref POST is never blindly retried. Uncertain outcomes are reconciled by re-reading the target branch; only exact expected SHA proves applied.
- Audit records safe branch/base/SHA/result/request metadata only; no credentials.
- Telegram callbacks remain compact and transport-only.
- No normal v1 force-push, branch force-update, or branch-delete UI exists.

## Durable invariants carried forward

- GitHub remains source of truth.
- GitHub App remains the primary credential model.
- Repository cache is navigation/context state, never authorization proof.
- Telegram callbacks are transport only; sensitive authority is server-side.
- Current remote state and scoped permissions are revalidated before sensitive execution.
- GET/HEAD may use bounded safe retry; write-like GitHub calls are not blindly replayed.
- Uncertain write outcomes remain uncertain unless reconciliation proves final state.
- Repository deletion remains Tier 3 exact-name gated.
- Single-file writes remain stage → preview → confirm → revalidate → scoped token → single write → reconcile → audit.
- Branch creation remains preview → persisted confirmation → base/target revalidation → scoped token → single create-ref → reconcile → audit.
- No normal v1 force-push/force-update UI.
- Repository/README/script text is untrusted input and is never automatically executed.

## Active task — P4.3 Clone/setup/run assistant

Implement command **generation only**, not arbitrary execution.

Required scope:

- fresh clone commands;
- update-existing-clone commands;
- detect Python/Node/Docker/Gradle/Maven baseline from repository evidence;
- Windows PowerShell commands;
- Linux commands;
- macOS commands;
- explicit confidence/source explanation for inferred setup/run commands;
- safe quoting for paths/refs where applicable;
- never insert GitHub tokens or credentials into generated commands;
- never automatically execute repository/README/script instructions.

Before coding P4.3, inspect existing repository/search/detail UI and tests, then update this file if implementation is split into a narrower active subtask.
