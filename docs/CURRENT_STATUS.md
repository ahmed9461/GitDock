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

**Current implementation item:** **P4.3 — Clone/setup/run assistant (implementation verified; delivery closeout pending).**

P4.3 code and direct acceptance coverage are implemented on `feat/p4-3-run-assistant`. Push CI is green. The remaining delivery steps are documentation-head CI, non-draft PR CI/mergeability, protected squash merge, post-merge `main` CI, and final governance closeout. Do not start P5 implementation until those steps are complete.

## P4.3 implementation verification

- verified implementation head `fba538e3c6071365361def7d5970ff7b19b5819c` — CI `34650497474` green;
- Python 3.12 and 3.13 quality jobs green;
- Ruff format/lint green on **167 files**;
- mypy clean on **100 source files**;
- **182 tests passed** on both Python versions;
- compileall green;
- `pip-audit` reported no known runtime vulnerabilities;
- `detect-secrets` reported no findings;
- PEP 751 runtime locks reproduce byte-for-byte;
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade remains green through `0006_file_write_sessions`.

Known maintenance warnings remain unchanged: Starlette/FastAPI TestClient deprecation toward httpx2, AnyIO `BlockingPortal` alias deprecation through Starlette, and Alembic `prepend_sys_path`/`path_separator` warning. They are not test failures.

## P4.3 delivered behavior

- Repository dashboard and public-search detail expose a real `📥 تشغيل/تنزيل` / download-command assistant entry point.
- User chooses Windows PowerShell, Linux, or macOS before command generation.
- Fresh clone and update-existing-clone commands are generated separately.
- Stack inference supports Python, Node.js, Docker, Gradle, and Maven from bounded repository evidence.
- Setup/run suggestions show inference confidence and evidence sources.
- Public repositories can be inspected without an Authorization header; installed/private repositories continue through the existing installation read context.
- P4.3 reuses the canonical `GitHubRestClient`/Contents gateway instead of introducing a parallel HTTP stack.
- Generated commands never contain GitHub tokens or credentials.
- GitDock never executes generated commands automatically.
- README text is treated as untrusted evidence and is never copied/executed as shell instructions.
- Node package script bodies are never copied into generated shell text; GitDock emits only the bounded script invocation form such as `npm run <safe-name>`.
- Python entry-point/script names used for generated commands are constrained to safe identifiers.
- Branch/ref/path shell arguments use target-OS-aware quoting where applicable.
- Evidence collection is bounded by known root files and file-size/read limits rather than arbitrary repository crawling.
- Stale public-search callbacks remain fail-closed through the existing active search-session contract.
- The rendered result explicitly warns that setup/run commands can execute hooks, build logic, or scripts contained in the repository when the user runs them locally.

## P4.2 final delivery chain

- implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518` — CI `34647181024` green;
- documentation-synchronized feature head `73e48dfced65d72d0d27e9defc4c3e107527107f` — push CI `34647866083` green;
- non-draft PR #18 on the unchanged head — PR CI `34648080794` green and mergeable;
- protected squash merge `b4e7dcd9de5db1e958e831508443d3fa1445213d`;
- post-feature `main` CI `34648224733` green.

The verified P4.2 contract remains **165 tests** on Python 3.12/3.13 with mypy clean on **94 source files** and all quality/security/migration gates green.

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
- Clone/setup/run is command generation only; GitDock does not provide arbitrary shell execution.

## Active closeout — P4.3 Clone/setup/run assistant

Implementation and push verification are complete. Finish only these delivery steps next:

1. synchronize `ROADMAP.md`, `PROJECT_MEMORY.md`, and `CHANGELOG.md` with the verified P4.3 contract;
2. verify the documentation-synchronized feature head in CI;
3. open a non-draft PR to `main` and require green PR CI + mergeability;
4. squash merge without bypassing protections;
5. verify post-merge `main` CI;
6. perform governance closeout and only then mark P4 complete / P5.1 active.
