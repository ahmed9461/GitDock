# Changelog

All notable project changes are recorded here. This repository is pre-v1; entries are organized under `Unreleased` until a release policy is introduced.

## Unreleased

### Added

#### P4.3 — clone/setup/run assistant

- Added pure `gitdock.domain.run_assistant` inference and OS-aware command generation.
- Added `RunAssistantService` for bounded repository-evidence collection and command-plan construction.
- Added Windows PowerShell, Linux, and macOS targets.
- Added separate fresh-clone, update-existing-clone, setup, and run guidance.
- Added baseline evidence-driven Python, Node.js, Docker, Gradle, and Maven detection.
- Added explicit confidence/source information for inferred setup/run suggestions.
- Added repository-dashboard and public-search entry points with compact callbacks.
- Added public repository evidence reads without Authorization while installed/private repositories continue through existing installation context.
- Added unit/integration/contract coverage for inference, OS variants, quoting, malicious repository script bodies, public unauthenticated reads, service evidence collection, UI callbacks, and renderer safety.

#### P4.2 — branch/commit tools

- Added typed branch/commit/compare/create-ref gateway and service orchestration.
- Added Arabic branch list/search, recent commits, commit detail, compare refs, and Tier 1 stale-safe branch creation.
- Added repository-scoped branch-create permission/reconciliation/audit flow.

#### P4.1 — repository files

- Added GitHub Contents browser, ref navigation, text preview, binary/large fallback, bounded download, create/upload/edit/replace/delete, review/diff, restart-safe staging, stale protection, scoped permissions, reconciliation, audit, and staged-content scrubbing.

#### P3 and earlier

- Added public search, durable GitHub user-context authorization, repository create/settings/delete administration, GitHub App auth, canonical REST gateway, installed repository Home/read flows, PostgreSQL/Alembic persistence, owner-only Telegram boundary, CI/security gates, and PEP 751 runtime locks.

### Changed

#### P4.3 inference, safety, and UX

- P4.3 uses the canonical `GitHubRestClient`/Contents gateway instead of a parallel HTTP stack.
- Read-only Contents access can omit Authorization for public repository evidence; write operations keep existing token/permission requirements.
- Public-search command generation remains tied to active opaque search sessions and stale sessions fail closed.
- Generated clone/update commands use target-shell-aware quoting where applicable.
- README and repository scripts are treated as untrusted input and are not copied into arbitrary shell output.
- Node package script bodies are ignored; only validated script names may produce `npm run <name>`.
- Python entry-point/script names are constrained to safe identifiers.
- Generated output never embeds GitHub credentials.
- Output explicitly warns that setup/run commands may invoke repository-controlled hooks, build logic, or scripts when run locally.
- Evidence collection is bounded to known root candidates and read limits rather than arbitrary repository crawling.

#### P4/P3 write safety baseline

- File writes use durable staged intent, exact remote preconditions, scoped permissions, one write, reconciliation, audit, and temporary-content scrubbing.
- Branch creation uses persisted preview/confirmation, exact base/target revalidation, repository-scoped permission, one create-ref request, reconciliation, and audit.
- Repository administration uses operation-specific credential context, persisted confirmation, refreshed preconditions, one write, reconciliation, and audit.
- Repository cache remains navigation state, never authorization.

### Fixed

#### P4.3 verification

- Corrected PowerShell path/entry-point rendering to valid command syntax.
- Added explicit typing for OS keyboard construction before mypy verification.
- Added direct public-read gateway coverage proving no Authorization header is sent for public evidence reads.
- Kept intentional Arabic/emoji renderer copy under a narrow P4.3 `RUF001` per-file ignore rather than weakening lint globally.
- Corrected Ruff formatting for the P4.3 UI assertion and wrapped the final repository-code warning to satisfy line-length policy.

### Security

#### P4.3

- GitDock generates commands only; it does not automatically execute shell commands.
- README/script content is repository-controlled untrusted input and is never copied as arbitrary generated shell instructions.
- Package script bodies are ignored even when malicious; only validated script names can be referenced.
- Generated commands never embed installation tokens, OAuth credentials, PATs, or other GitHub secrets.
- Public evidence reads intentionally omit Authorization; installed/private reads reuse existing installation authorization boundaries.
- Evidence collection is bounded by known candidate names and read-size limits.
- UI warns that dependency/build/run tools may execute repository-controlled code when the user chooses to run generated commands.

#### Existing baseline

- Durable user credentials remain encrypted.
- GitHub App installation binding requires App/user-context identity agreement.
- Generic REST transport restricts canonical GitHub targets and does not blindly follow/replay unsafe requests.
- File bodies never enter audit logs.
- Workflow-file writes additionally require `workflows: write`.
- Normal v1 UI exposes no force-push/force branch-update capability.

### Verification

#### P4.3 final feature-delivery chain

- implementation head `fba538e3c6071365361def7d5970ff7b19b5819c` — CI `34650497474` green;
- documentation-synchronized head `989e826f8e845934b9255a78c91bfeca48f10538` — push CI `34650840434` green;
- non-draft PR #20 — PR CI `34650940874` green and mergeable;
- protected squash merge `0f0750388a1a919917ba81586fad42ae2ab11336`;
- post-feature `main` CI `34651051039` green.

Verified P4.3 contract:

- Python 3.12 and 3.13 quality jobs green.
- **182 tests passed** on both versions.
- mypy clean on **100 source files**.
- Ruff format/lint green on **167 files**.
- compileall green.
- `pip-audit`: no known runtime vulnerabilities.
- `detect-secrets`: no findings.
- PEP 751 runtime locks reproduce byte-for-byte.
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade green through `0006_file_write_sessions`.

P4.3 feature delivery is complete; this governance closeout marks the overall P4 phase complete and activates **P5.1 Secure webhook ingestion**.

#### Earlier P4 verification baselines

- P4.2: **165 tests** on Python 3.12/3.13; mypy clean on **94 source files**; all quality/security/migration gates green.
- P4.1: **148 tests** on Python 3.12/3.13; mypy clean on **87 source files**; all quality/security/migration gates green.

### Maintenance warnings

The following warnings are tracked and non-blocking:

- FastAPI/Starlette `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias surfaced through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.
