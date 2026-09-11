# GitDock — Current Status / Handoff

Last updated: 2026-09-11

## Project state

**Verified complete before this feature branch:**

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

P4.2 implementation and acceptance coverage are complete on the feature branch. The remaining work for this item is governance only: documentation-head CI, non-draft PR CI, protected merge, post-merge `main` CI, then final handoff. Do not start P4.3 until that chain is complete.

## P4.2 implementation verification

Implementation head: `5a4f7aa4eb557e69665a7311f32c8060e38b1518`.

GitHub Actions run `34647181024` is fully green:

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
- Branch-create preview binds repository ID, target branch, base ref, and resolved base commit SHA.
- Confirm-time base SHA revalidation rejects a moved base as `STALE` before any write.
- Target branch is checked for absence before preview and checked again immediately before write; duplicate target produces no replacement/update.
- Missing base ref fails before write.
- Branch creation is Tier 1 and uses a repository-scoped installation token requesting `contents: write` + metadata read only for the selected repository.
- Create-ref POST is never blindly retried. If the response is uncertain, GitDock re-reads the target branch: exact expected SHA can prove applied; otherwise the result remains explicit `UNCERTAIN`.
- Audit records contain safe branch/base/SHA/result/request metadata only; no credentials.
- Telegram callbacks remain compact; repository/ref/confirmation authority is resolved server-side/FSM-side rather than inferred from callback possession.
- No normal v1 force-push, branch force-update, or branch-delete UI was introduced.

## P4.2 direct acceptance coverage

The current suite directly covers:

- list/search branches;
- create branch from a known base;
- duplicate branch rejection without write;
- missing base rejection without write;
- stale base rejection without write;
- recent commits;
- commit detail;
- compare refs;
- bounded large-diff summary;
- compact callback round trips;
- scoped write authority;
- cancel/reuse rejection;
- uncertain-create reconciliation without replay;
- REST method/path/body/token contracts, including encoded compare refs.

## P4.1 final feature-delivery reference

P4.1 remains complete and must not be reopened unless a real regression is found:

- implementation `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010`;
- documentation head `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457`;
- PR #16 CI `34641248664`;
- squash merge `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6`;
- post-feature `main` CI `34641411838`.

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
- Branch creation follows preview → persisted confirmation → base/target revalidation → scoped token → single create-ref → reconcile → audit.
- No normal v1 force-push/force-update UI.

## Exact next work after P4.2 governance completes

**P4.3 — Clone/setup/run assistant.**

Scope:

- fresh-clone commands;
- update-existing-clone commands;
- detect Python/Node/Docker/Gradle/Maven baseline from repository evidence;
- Windows PowerShell, Linux, and macOS command variants;
- label confidence/source of inference;
- never insert GitHub tokens into commands;
- never automatically execute repository/README/script instructions.
