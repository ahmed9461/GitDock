# Changelog

All notable project changes are recorded here. This repository is pre-v1; entries are organized under `Unreleased` until a release policy is introduced.

## Unreleased

### Added

#### P4.3 — clone/setup/run assistant

- Added pure `gitdock.domain.run_assistant` inference and command-generation logic.
- Added `RunAssistantService` to collect bounded repository evidence and generate a command plan without executing repository instructions.
- Added target OS selection for Windows PowerShell, Linux, and macOS.
- Added separate fresh-clone and update-existing-clone command groups.
- Added baseline evidence-driven setup/run inference for Python, Node.js, Docker, Gradle, and Maven.
- Added explicit confidence and source information for inferred setup/run suggestions.
- Added repository-dashboard and public-search entry points for `📥 تشغيل/تنزيل` command generation.
- Added compact P4.3 callback encoding/decoding and OS-selection keyboards.
- Added bounded public repository evidence reads through the existing Contents gateway without Authorization while installed/private repositories continue through the existing installation read context.
- Added direct unit/integration/contract coverage for stack inference, OS variants, quoting, service evidence collection, public unauthenticated reads, callback compactness, renderer behavior, and malicious repository-script bodies.

#### P4.2 — branch/commit tools

- Added typed `GitHubGitToolsGateway` on the canonical REST transport for branch listing/detail, recent commits/detail, compare refs, and create-ref.
- Added `GitToolsService` for GitHub-backed branch/commit reads plus branch-create confirmation, stale checks, scoped credential selection, uncertain-result reconciliation, and audit.
- Made repository dashboard `🌿 الفروع` and `📝 Commits` actions real.
- Added Arabic branch listing/search, recent commits, commit detail, compare refs, and Tier 1 branch creation flows.

#### P4.1 — repository files

- Added GitHub Contents gateway, Arabic file browser, directory pagination, parent/ref navigation, UTF-8 preview, binary/large fallback, bounded download, create/upload/edit/replace/delete flows, diff/review UI, restart-safe one-file staging, and migration `0006_file_write_sessions`.
- Added repository-scoped content/workflow permission paths and one-write reconciliation semantics.
- Added same-target staging supersession and staged-content scrubbing lifecycle.

#### P3.3 — repository administration

- Added personal/organization create service paths; repository rename/description/visibility/archive/default-branch updates; Tier 2 settings confirmation; Tier 3 exact-name delete; repository-scoped `administration: write`; durable audit migration `0005_audit_log`; uncertain-write reconciliation.

#### P3.2 — durable user authorization

- Added authenticated `/user` identity binding, encrypted durable user access/refresh credentials, expiry-aware rotation, `credential_generation`, DB-backed `pending_confirmations`, and safe local disconnect that does not claim remote App uninstall.

#### Earlier foundation

- Added GitHub App auth, OAuth + PKCE, encrypted credential abstraction, canonical REST transport, installed-repository Home/read flows, public search, PostgreSQL/Alembic persistence, Telegram owner boundary, CI/security gates, and PEP 751 runtime locks.

### Changed

#### P4.3 inference, safety, and UX

- `GitHubRestClient`/Contents remains the canonical read path; P4.3 introduces no parallel raw HTTP stack.
- Read-only `list_directory`/`get_file` paths can operate without a token for public repository evidence, while write operations retain their existing token/permission requirements.
- Public-search command generation remains tied to an active opaque search session and stale sessions fail closed.
- Generated commands use target-OS-aware quoting for repository path/ref material where applicable.
- README is treated as untrusted evidence and its shell snippets are never copied or automatically executed.
- Node package script bodies are not copied into output; only safe script names can produce an invocation such as `npm run <name>`.
- Python entry-point/script names used for generated commands are constrained to safe identifiers.
- Generated output never includes GitHub tokens or credentials.
- Rendered results explicitly warn that setup/run commands may invoke repository-controlled hooks, build logic, or scripts when the user executes them locally.
- Evidence collection is bounded to known root candidates and bounded file reads rather than arbitrary repository crawling.

#### P4.2 safety and UX

- Branch create follows preview → persisted one-time confirmation → confirm-time repository/base/target revalidation → repository-scoped `contents: write` → one create-ref request → reconciliation → audit.
- A moved base after preview returns stale and performs no write.
- Existing target branch is never replaced/force-updated by the create flow.
- Create-ref POST remains no-retry; uncertain response is reconciled by re-reading target branch.
- No normal v1 force-push, branch force-update, or branch-delete UI was introduced.

#### P4.1/P3 safety

- File writes use durable staged intent, exact remote preconditions, scoped permissions, one write, reconciliation, and content scrubbing.
- Repository administration uses operation-specific credential context, persisted confirmation, refreshed preconditions, one write, reconciliation, and audit.
- Repository cache remains navigation state, never authorization.

### Fixed

#### P4.3 verification

- Corrected PowerShell generated path/entry-point rendering so commands are valid shell syntax rather than over-escaped or rendered as inert text.
- Added explicit typing for OS keyboard construction before mypy verification.
- Added direct public-read gateway coverage to prove no Authorization header is sent for unauthenticated public evidence reads.
- Kept intentional Arabic/emoji renderer copy under a narrow P4.3 `RUF001` per-file ignore rather than weakening lint globally.
- Formatted P4.3 UI tests after Ruff identified one assertion layout mismatch.
- Wrapped the repository-code execution warning after lint correctly flagged an overlong line.

#### P4.2 verification

- Resolved initial Ruff-format mismatches and intentional Arabic/emoji `RUF001` findings with narrow per-file ignores.
- Corrected compare-ref contract assertion to inspect `httpx.URL.raw_path` for encoded refs.
- Added direct acceptance tests for branch search, commit detail, duplicate/missing-base rejection, and bounded large-compare rendering.

### Security

#### P4.3

- GitDock generates commands only; it never provides arbitrary automatic shell execution through this feature.
- README/script contents are untrusted repository-controlled input and are never copied into arbitrary generated shell commands.
- Package-script bodies are intentionally ignored even when malicious; only validated script names can be referenced.
- Generated commands never embed installation tokens, OAuth credentials, PATs, or other GitHub secrets.
- Public evidence reads intentionally omit Authorization rather than leaking installation context into unrelated public repository requests.
- Installed/private reads reuse the existing installation authorization boundary.
- Evidence collection is bounded by candidate names and read-size limits.
- The UI warns that dependency/build/run tools may execute repository-controlled code when the user chooses to run generated commands.

#### P4.2

- Branch creation is Tier 1 and requires persisted one-time confirmation.
- Confirm-time exact base-SHA check blocks stale branch creation.
- Target branch absence is checked before review and before write.
- Write token is repository-scoped with `contents: write` + metadata read.
- Create-ref is issued once; uncertain state reconciles rather than blindly replaying POST.
- Normal v1 UI exposes no force-push/force branch update.

#### Existing security baseline

- Durable user credentials remain encrypted.
- GitHub App installation binding requires App/user-context identity agreement.
- Generic REST transport enforces canonical GitHub targets and no automatic redirect following.
- GET/HEAD bounded retry is separated from write safety.
- File bodies never enter audit logs; temporary P4.1 staged bytes are scrubbed by lifecycle.
- Workflow-file writes additionally require `workflows: write`.

### Verification

#### P4.3 implementation verification

- implementation head `fba538e3c6071365361def7d5970ff7b19b5819c` — CI `34650497474` green.

Verified implementation contract:

- Python 3.12 and 3.13 quality jobs green.
- **182 tests passed** on both versions.
- mypy: **100 source files**, no issues.
- Ruff: **167 files already formatted**, lint clean.
- compileall green.
- `pip-audit`: no known runtime vulnerabilities.
- `detect-secrets`: no findings.
- PEP 751 runtime locks reproduce byte-for-byte.
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade green through `0006_file_write_sessions`.

Delivery closeout remains pending until the documentation-synchronized head CI, non-draft PR CI/mergeability, protected squash merge, post-feature `main` CI, and governance closeout all succeed.

#### P4.2 final feature-delivery chain

- implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518` — CI `34647181024` green;
- documentation-synchronized feature head `73e48dfced65d72d0d27e9defc4c3e107527107f` — push CI `34647866083` green;
- non-draft PR #18 CI `34648080794` green on the unchanged mergeable head;
- protected squash merge `b4e7dcd9de5db1e958e831508443d3fa1445213d`;
- post-feature `main` CI `34648224733` green.

Verified contract: **165 tests** on Python 3.12/3.13, mypy clean on **94 source files**, Ruff/compile/audit/secret/PEP 751/PostgreSQL gates green.

#### P4.1 final reference

- implementation head `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010`;
- docs head `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457`;
- PR #16 CI `34641248664`;
- squash merge `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6`;
- post-feature main CI `34641411838`;
- governance closeout `d113872e703b005f4c3c8e2b1da8fc2597e8ecd7`.

#### P3.3 final reference

- implementation `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945`;
- docs head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482`;
- PR #14 CI `33891899602`;
- feature merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature main CI `33892100584`.

### Maintenance warnings

The following warnings are tracked and non-blocking:

- FastAPI/Starlette `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias surfaced through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.
