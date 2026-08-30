# AGENTS.md — GitDock mandatory development contract

This file is authoritative for every coding session, agent, contributor, or automation that changes GitDock.

## 1. Mandatory pre-flight

Before writing or changing code, read these files in order:

1. `docs/PROJECT_MASTER_PLAN.md`
2. `docs/PROJECT_MEMORY.md`
3. `docs/CURRENT_STATUS.md`
4. `docs/CONSTANTS.md`
5. `docs/ARCHITECTURE.md`
6. `docs/UI_UX_SPEC.md`
7. `docs/SECURITY_MODEL.md`
8. `docs/BUILD_PROTOCOL.md`
9. `docs/ROADMAP.md`
10. `docs/DECISIONS.md`
11. `docs/TEST_MATRIX.md`

Do not rely on chat history when repository documentation can answer the question.

## 2. Scope discipline

- Work only on the active milestone/task recorded in `docs/CURRENT_STATUS.md`, unless the requested change explicitly changes priority.
- Never silently skip a planned requirement. Mark it as completed, blocked, deferred, or superseded with a reason.
- Do not introduce architecture, dependency, naming, UX, security, or persistence changes that contradict the control documents without recording a decision in `docs/DECISIONS.md`.
- Prefer coherent implementation over patches. Fix root causes and keep boundaries clean.
- Preserve backward compatibility unless a deliberate breaking change is recorded.

## 3. Product invariants

These rules must not be violated without an explicit recorded decision:

- Telegram is the primary UI.
- Arabic is the primary user-facing language in v1; technical identifiers remain English.
- Prefer editing an existing bot message over flooding the chat when navigating screens.
- Inline keyboards are the primary navigation surface.
- Navigation row is consistently: `🏠 الرئيسية` / `❌ إلغاء` / `⬅️ رجوع` as context allows.
- Default layout is at most two primary action buttons per row; destructive actions are isolated.
- Every destructive or high-impact GitHub action requires explicit confirmation.
- Repository deletion, transfer, visibility changes, force operations, and mass replacement are never one-tap actions.
- GitHub webhook signatures must be verified before payload processing.
- GitHub delivery IDs must be deduplicated.
- Secrets/tokens must never be committed, logged, or shown in full to Telegram.
- Prefer GitHub App installation/user tokens with minimum permissions over broad long-lived PATs.
- Multi-file project updates must be reviewed as a batch and committed atomically where practical.
- Do not mark a feature complete unless tests and its Definition of Done pass.

## 4. Required workflow for every implementation task

### Before coding

1. Identify the roadmap item and acceptance criteria.
2. Update `docs/CURRENT_STATUS.md` with the active task if needed.
3. Inspect existing tests and related code first.
4. Determine whether the change affects constants, architecture, UX, permissions, database schema, or security.

### During coding

1. Keep domain logic separate from Telegram handlers and GitHub transport code.
2. Add/adjust tests with the implementation, not after it.
3. Never hardcode UI copy, callback namespaces, pagination limits, timeout values, permission names, or risky-operation rules when they belong in centralized constants/configuration.
4. Keep GitHub API calls behind service/client interfaces so they can be mocked.
5. Keep Telegram handlers thin.
6. Database schema changes require Alembic migrations.
7. Validate all external payloads and user inputs.

### Before declaring success

Run the appropriate checks described in `docs/BUILD_PROTOCOL.md` and `docs/TEST_MATRIX.md`. At minimum for code changes:

- format/lint
- type checks where configured
- unit tests
- integration tests relevant to the feature
- migration validation for schema changes
- secret scan or equivalent repository check

A failed check means the build is not successful.

## 5. Mandatory post-success documentation update

After every successful implementation/build, update all relevant control files **in the same change set**:

1. `docs/CURRENT_STATUS.md`
   - what was completed
   - exact next task
   - tests/checks run and their result
   - known blockers or risks
2. `docs/PROJECT_MEMORY.md`
   - durable facts learned or decisions that future sessions must remember
3. `docs/ROADMAP.md`
   - mark completed acceptance criteria; do not mark incomplete items done
4. `CHANGELOG.md`
   - user-visible or meaningful engineering change under `Unreleased`
5. `docs/DECISIONS.md`
   - only when a technical/product/security decision changed or was introduced
6. `docs/CONSTANTS.md`
   - when canonical names/limits/callbacks/permissions/config keys change
7. `docs/ARCHITECTURE.md`, `docs/UI_UX_SPEC.md`, `docs/SECURITY_MODEL.md`, or `docs/TEST_MATRIX.md`
   - whenever implementation changes their truth

If code passes but these records are stale, the task is **not done**.

## 6. Failed or partial work

If work cannot be completed:

- do not mark roadmap items complete;
- record the blocker and current safe state in `docs/CURRENT_STATUS.md`;
- record any durable discovery in `docs/PROJECT_MEMORY.md`;
- leave the repository in a runnable/testable state when possible;
- do not hide failing tests or disable checks merely to get green status.

## 7. Git discipline

- Use focused commits with conventional prefixes: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `security:`.
- Prefer feature branches + PR review once implementation starts.
- Never force-push the protected/default branch as normal workflow.
- Do not commit generated secrets, local databases, virtual environments, logs, caches, or downloaded artifacts.
- Large project/ZIP sync operations should create a reviewable branch/commit rather than mutating many files invisibly.

## 8. Definition of Done

A task is Done only when all are true:

- acceptance criteria implemented;
- relevant tests pass;
- no known regression introduced;
- error/empty/loading/permission-denied states handled;
- security rules satisfied;
- user-facing copy/buttons match the UX spec;
- docs and state files updated;
- next handoff point is explicit.

## 9. Handoff rule

At the end of every successful session, a new developer/agent must be able to open the repository, read the control files, and know exactly:

- what GitDock currently does;
- what is verified working;
- what is not implemented;
- what changed last;
- what task comes next;
- what constraints must not be broken.

If that is not true, improve the documentation before ending the session.