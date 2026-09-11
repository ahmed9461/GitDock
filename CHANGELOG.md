# Changelog

All notable project changes are recorded here. This repository is pre-v1; entries are organized under `Unreleased` until a release policy is introduced.

## Unreleased

### Added

#### P4.2 — branch/commit tools

- Added typed `GitHubGitToolsGateway` on the canonical REST transport for:
  - branch listing and branch detail lookup;
  - recent commits and commit detail;
  - compare refs;
  - create Git ref/branch.
- Added `GitToolsService` for GitHub-backed branch/commit reads plus branch-create confirmation, stale checks, scoped credential selection, uncertain-result reconciliation, and audit.
- Made repository dashboard `🌿 الفروع` and `📝 Commits` actions real.
- Added Arabic branch listing/search flow with explicit create/compare/refresh/navigation actions.
- Added recent-commits flow with default or explicit branch/tag/SHA ref selection.
- Added commit detail UI with SHA, author/time, message, changed-file/addition/deletion/parent summary, and canonical GitHub link.
- Added compare-refs flow with ahead/behind/commit/file summary and bounded first-10-file rendering.
- Added Tier 1 branch creation from explicit target + base ref/SHA with preview showing repository, target, base ref, and resolved base commit SHA.
- Reused restart-safe `pending_confirmations` for branch create; P4.2 introduces no new DB migration.
- Added branch-create audit entries using existing `audit_log`.
- Added direct unit/integration/contract coverage for branch search, known-base create, duplicate target, missing base, stale base, recent commits, commit detail, compare refs, large compare summary, callback compactness, encoded refs, scoped write authority, cancellation/reuse, no-retry create-ref, and uncertain-result reconciliation.

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

#### P4.2 safety and UX

- Branch create now follows preview → persisted one-time confirmation → confirm-time repository/base/target revalidation → repository-scoped `contents: write` → one create-ref request → reconciliation → audit.
- Persisted branch-create fingerprint binds repository ID, target branch, base ref, and exact resolved base SHA.
- A moved base after preview now returns stale and performs no write.
- Existing target branch now returns exists and is never replaced/force-updated by the create flow.
- Missing base ref performs no write.
- Create-ref POST remains no-retry; uncertain response is reconciled by re-reading target branch and only exact expected SHA proves applied.
- No normal v1 force-push, branch force-update, or branch-delete UI was introduced.
- P4.2 callbacks use compact repository/page/index/token context rather than long GitHub data.
- Ruff `RUF001` is ignored only for the three intended P4.2 Telegram UI files so Arabic/emoji copy remains readable while the rule stays active elsewhere.
- P4.2 governance is complete and P4.3 is now the active roadmap item.

#### P4.1/P3 safety

- File writes use durable staged intent, exact remote preconditions, scoped permissions, one write, reconciliation, and content scrubbing.
- Repository administration uses operation-specific credential context, persisted confirmation, refreshed preconditions, one write, reconciliation, and audit.
- Repository cache remains navigation state, never authorization.

### Fixed

#### P4.2 verification

- Formatted the initial P4.2 implementation after CI correctly identified nine Ruff-format mismatches.
- Resolved intentional Arabic/emoji `RUF001` lint findings with narrow per-file ignores instead of disabling the rule project-wide or altering Arabic UI copy.
- Corrected the compare-ref contract assertion to inspect `httpx.URL.raw_path`; `URL.path` is decoded by httpx and therefore cannot prove `%2F` raw encoding. Production compare URL construction did not require a behavior change.
- Added direct acceptance tests for branch search, commit detail, duplicate branch rejection, missing base rejection, and bounded large-compare rendering rather than checking the test matrix by implication.

### Security

#### P4.2

- Branch creation is Tier 1 and requires persisted one-time confirmation.
- Confirmation payload/fingerprint contains safe target/base preconditions only and no credentials.
- Confirm-time exact base-SHA check blocks stale branch creation.
- Target branch absence is checked both before review and before write.
- Write token is requested only after confirmation/revalidation and scoped to exactly the selected repository with `contents: write` + metadata read.
- Create-ref is issued once; uncertain state reconciles rather than blindly replaying POST.
- Audit stores safe branch/base/SHA/risk/request/result metadata only.
- Normal v1 UI exposes no force-push/force branch update.

#### Existing security baseline

- Durable user credentials remain encrypted.
- GitHub App installation binding requires App/user-context identity agreement.
- Generic REST transport enforces canonical GitHub targets and no automatic redirect following.
- GET/HEAD bounded retry is separated from write safety.
- File bodies never enter audit logs; temporary P4.1 staged bytes are scrubbed by lifecycle.
- Workflow-file writes additionally require `workflows: write`.

### Verification

#### P4.2 final feature-delivery chain

- implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518` — CI `34647181024` green;
- documentation-synchronized feature head `73e48dfced65d72d0d27e9defc4c3e107527107f` — push CI `34647866083` green;
- non-draft PR #18 CI `34648080794` green on the unchanged mergeable head;
- protected squash merge `b4e7dcd9de5db1e958e831508443d3fa1445213d`;
- post-feature `main` CI `34648224733` green.

Verified contract:

- Python 3.12 and 3.13 quality jobs green.
- **165 tests passed** on both versions.
- mypy: **94 source files**, no issues.
- Ruff: **157 files already formatted**, lint clean.
- compileall green.
- `pip-audit`: no known runtime vulnerabilities.
- `detect-secrets`: no findings.
- PEP 751 runtime locks reproduce byte-for-byte.
- PostgreSQL 17 Alembic upgrade → downgrade → upgrade green through `0006_file_write_sessions`.

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
