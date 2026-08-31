# GitDock — Build & Development Protocol

Status: mandatory process for implementation work

This protocol exists to prevent GitDock from becoming a collection of half-finished features, stale notes, and undocumented patches.

## 1. Meaning of “build” in this project

A successful build/change is not merely “the code ran once.” A successful implementation cycle means:

1. requested scope is implemented;
2. acceptance criteria pass;
3. automated checks relevant to the change pass;
4. failure/empty/permission states are handled;
5. project state/control docs are updated;
6. repository is left with an explicit next handoff point.

## 2. Session start protocol

Every coding session must:

1. Read root `AGENTS.md`.
2. Read `docs/CURRENT_STATUS.md`.
3. Read the relevant master/spec files for the active feature.
4. Check `docs/ROADMAP.md` acceptance criteria.
5. Inspect existing code/tests before changing architecture.
6. Confirm the worktree/branch state before edits.
7. Select one coherent implementation target.

Do not start by generating files from memory without inspecting the repository.

## 3. Planning the change

Before coding, state internally/in the task record:

- target milestone/item;
- files/modules expected to change;
- data/schema changes;
- GitHub permissions/capabilities affected;
- Telegram screens affected;
- risk tier;
- tests required;
- control docs likely needing updates.

If a task grows beyond a coherent reviewable unit, split it rather than hiding multiple subsystems in one commit.

## 4. Branch policy

### P0 planning foundation

Direct documentation initialization on `main` is acceptable.

### Once implementation starts

Default workflow:

```text
main
  └── feat/<short-purpose>
        └── PR -> checks -> review -> merge
```

Suggested prefixes:

- `feat/`
- `fix/`
- `refactor/`
- `docs/`
- `test/`
- `security/`
- `chore/`

Do not use force-push to `main` as normal workflow.

## 5. Commit convention

Use focused conventional prefixes:

```text
feat: add repository list service
fix: prevent duplicate webhook notifications
refactor: isolate GitHub token provider
test: cover stale file SHA conflict
docs: update Actions milestone status
security: reject archive path traversal
chore: update development tooling
```

A commit message should describe the meaningful outcome, not “updates” or “changes.”

## 6. Implementation order for a feature

Recommended sequence:

1. Domain model/rules.
2. Persistence model/migration if required.
3. GitHub gateway interface + implementation/mocks.
4. Application service/use case.
5. Telegram renderer/keyboard.
6. Telegram handler/state flow.
7. Tests across affected layers.
8. Documentation/state update.

Small read-only features may combine steps, but the layer boundaries remain.

## 7. Database change protocol

For schema changes:

1. update SQLAlchemy models;
2. create Alembic migration;
3. inspect migration manually;
4. test upgrade from previous schema;
5. test clean database bootstrap;
6. test downgrade when safe/required by migration policy;
7. update architecture/data documentation if truth changed.

Do not edit production schema manually as the normal path.

## 8. GitHub API change protocol

For any new GitHub API operation:

1. identify token context: IAT, UAT, or public/anonymous;
2. identify exact required GitHub App permission/capability;
3. add it to centralized permission mapping;
4. implement typed gateway method;
5. translate GitHub errors into GitDock error categories;
6. test success + permission denied + not found + rate/transient paths as relevant;
7. decide idempotency/retry behavior;
8. add audit behavior if it writes;
9. update security/architecture docs if privilege surface changed.

Never make a raw `httpx` GitHub API call directly from a Telegram handler.

## 9. Telegram screen change protocol

For a new/changed screen:

- follow `docs/UI_UX_SPEC.md`;
- use centralized renderer/text helpers;
- use centralized keyboard builders;
- callback payloads follow the versioned namespace;
- handle stale/expired callbacks;
- Back/Cancel/Home behavior is explicit;
- test authorization middleware behavior;
- test empty/error/loading state where meaningful.

## 10. Risky operation protocol

Tier 2/3 operations must have:

- server-side pending confirmation;
- expiry;
- user binding;
- exact target snapshot;
- precondition refresh where relevant;
- single-use consumption;
- audit record;
- clear cancellation path;
- tests for stale/reused/expired confirmation.

Tier 3 repository deletion also requires exact repository-name entry.

## 11. ZIP/project sync protocol

Implementation cannot be called complete until it handles:

- upload limits;
- safe archive inspection/extraction;
- path traversal rejection;
- link handling;
- file count/size/depth limits;
- secret-like file warnings;
- repository/base commit snapshot;
- added/modified/deleted/unchanged classification;
- text diff preview;
- binary/large-file treatment;
- stale base detection before apply;
- review branch creation by default;
- coherent batch commit;
- optional PR creation;
- cleanup after success/cancel/expiry/failure;
- audit trail.

## 12. Check suite — concrete P1 commands

### Bootstrap a fresh development environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

### Required quality checks

Run from repository root:

```bash
ruff format --check .
ruff check .
mypy gitdock
pytest
python -m compileall -q gitdock
pip-audit -r requirements.txt
```

Secret scan equivalent to CI:

```bash
detect-secrets scan --all-files \
  --exclude-files '(^|/)(tests|docs)/|(^|/)\.env\.example$' \
  > /tmp/gitdock-secrets.json
python - <<'PY'
import json
from pathlib import Path

results = json.loads(Path('/tmp/gitdock-secrets.json').read_text()).get('results', {})
if results:
    raise SystemExit(f"Potential secrets detected: {sorted(results)}")
PY
```

### Migration validation

Development/SQLite smoke:

```bash
export GITDOCK_DATABASE_URL='sqlite+aiosqlite:///./migration-test.db'
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

Production-relevant migration validation must also run against PostgreSQL. CI provides a PostgreSQL service and executes:

```bash
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

### CI contract

`.github/workflows/ci.yml` must execute:

- Ruff format check;
- Ruff lint;
- mypy strict type check;
- full pytest suite;
- Python compile check;
- pip-audit against runtime dependencies;
- detect-secrets repository scan;
- PostgreSQL migration upgrade/downgrade/re-upgrade.

A workflow run that fails before any step starts is an infrastructure/pre-run failure and is **not** a green build or an application-test result. Record it in `docs/CURRENT_STATUS.md`; do not weaken checks to hide it.

### Current dependency caveat

`requirements.txt` and `requirements-dev.txt` exactly pin direct dependencies/tooling. They are not yet a full transitive hash lock. The final lock strategy must be settled before P1 is declared fully complete.

## 13. Test selection rule

Run the smallest relevant tests during iteration, then the required broader suite before declaring success.

Examples:

- copy-only Telegram change -> renderer/keyboard/handler tests + broader unit suite;
- GitHub gateway change -> contract mocks + service tests;
- DB model change -> migration + repository/integration tests;
- security-sensitive change -> targeted negative tests + full relevant suite;
- pre-release -> full suite.

## 14. No test-cheating rule

Forbidden as a way to “finish” a task:

- deleting a failing test without a valid behavior change;
- weakening an assertion just to pass;
- skipping a failing test without documenting a real external blocker;
- catching and ignoring exceptions so tests turn green;
- disabling lint/type/security checks to merge;
- mocking the unit under test so the test proves nothing.

## 15. Successful-build documentation transaction

After all required checks pass, update documentation before final commit/merge.

### Always update

`docs/CURRENT_STATUS.md`

Include:

- completed item;
- checks executed + result;
- exact next task;
- blockers/known limitations.

`docs/ROADMAP.md`

- mark only acceptance criteria that really passed.

`CHANGELOG.md`

- add meaningful change under `Unreleased`.

### Update when truth changed

- `docs/PROJECT_MEMORY.md`
- `docs/CONSTANTS.md`
- `docs/ARCHITECTURE.md`
- `docs/UI_UX_SPEC.md`
- `docs/SECURITY_MODEL.md`
- `docs/DECISIONS.md`
- `docs/TEST_MATRIX.md`

Code and documentation describing code must not knowingly disagree at merge time.

## 16. Failed/partial build protocol

When work is partial or checks fail:

1. do not mark roadmap items complete;
2. keep or restore a coherent runnable state;
3. write the blocker in `docs/CURRENT_STATUS.md` if handing off;
4. record durable discoveries in `docs/PROJECT_MEMORY.md`;
5. preserve a failing regression test if it accurately captures a real unresolved bug;
6. distinguish “implemented but unverified” from “verified working.”

## 17. Release protocol

Before a tagged release:

- full required test/check suite green;
- migrations validated;
- `.env.example` accurate;
- no secrets in repository/history introduced by release work;
- version updated consistently;
- `CHANGELOG.md` moves release items from `Unreleased` to version/date;
- `docs/CURRENT_STATUS.md` records release and next milestone;
- deployment notes/migrations known;
- rollback/recovery notes for risky changes;
- GitHub App permission changes documented to operator/user.

## 18. Definition of a clean handoff

A session is safe to hand off when another developer/agent can answer from repository files alone:

- What phase are we in?
- What is verified working?
- What is incomplete?
- What tests were last run?
- What is the next exact task?
- What decisions/constraints must not change accidentally?

If not, update the control files before stopping.
