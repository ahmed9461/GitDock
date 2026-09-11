# GitDock — Roadmap

Status legend:

- [ ] not started
- [~] in progress
- [x] verified implementation/acceptance item
- `[BLOCKED]` blocked with reason in `docs/CURRENT_STATUS.md`

A phase is complete only after implementation, required CI, merge, post-merge verification, and governance/documentation truth are complete.

---

## P0 — Planning & governance foundation ✅

- [x] Product identity/scope established.
- [x] `AGENTS.md` development contract.
- [x] Master plan, memory, current status, constants, architecture, UI/UX, security, build protocol, test matrix, decisions, changelog, PR checklist.
- [x] A fresh session can reconstruct project direction without chat history.

---

## P1 — Project skeleton & quality gates ✅

- [x] Python async package foundation and typed settings.
- [x] FastAPI health/readiness + Telegram polling/webhook bootstrap.
- [x] owner-only Telegram boundary.
- [x] async SQLAlchemy + Alembic + PostgreSQL production model.
- [x] Ruff, mypy, pytest, compile, audit, secret scan, Python 3.12/3.13 CI, PostgreSQL migration CI.
- [x] exact direct runtime/dev pins and PEP 751 per-Python Linux locks.

---

## P2 — GitHub App connection & read-only core ✅

### P2.1 GitHub App auth foundation ✅

Squash merge `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge CI `33348851085` green.

- [x] App JWT / installation tokens.
- [x] OAuth + PKCE S256.
- [x] restart-safe one-time state.
- [x] encrypted credential abstraction.
- [x] dual App/user-context installation identity verification.
- [x] centralized capability/permission mapping.

### P2.2 GitHub gateway foundation ✅

Squash merge `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge CI `33409825480` green.

- [x] canonical typed REST transport.
- [x] safe canonical-host pagination.
- [x] stable safe error/rate-limit modeling.
- [x] bounded safe read retries; write-like methods no retry by default.
- [x] contract/mock test foundation.

### P2.3 Home + repository read screens ✅

Feature merge `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; governance closeout `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`.

- [x] connected/disconnected Home.
- [x] installed repository list/filter/pagination/detail.
- [x] compact repository callbacks.
- [x] minimal non-authoritative `repositories_cache` migration `0003`.
- [x] detail revalidation against GitHub.
- [x] 65-test verified suite.

---

## P3 — Search & repository administration ✅

### P3.1 GitHub search ✅

Feature merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`; closeout `ef2c5f618102063df8166f84b4828243f5efb5c6`.

- [x] public search without installation.
- [x] sort/filter/pagination.
- [x] active opaque search sessions and stale-session rejection.
- [x] detail re-fetch.
- [x] public discovery isolated from installed authorization/cache state.
- [x] 83-test verified suite.

### P3.2 User-context authorization ✅

Implementation CI `33515291600`; docs CI `33517270731`; PR #12 CI `33527318485`; feature merge `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`; closeout `aeb003cec79d1952dc80a520c03a4eee819872bc`.

- [x] authenticated `/user` identity.
- [x] durable encrypted user access/refresh credentials.
- [x] expiry-aware rotating refresh lifecycle.
- [x] `credential_generation` stale-concurrency guard.
- [x] durable `pending_confirmations` migration `0004_user_auth`.
- [x] stale-safe local disconnect that does not claim remote App uninstall.
- [x] Arabic account UI.
- [x] 97-test verified suite.

### P3.3 Repository create/settings ✅

Verification chain:

- implementation `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945`;
- docs head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482`;
- PR #14 CI `33891899602`;
- feature merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature main CI `33892100584`.

- [x] personal create using durable GitHub user context.
- [x] authorized organization create gateway/service path.
- [x] rename/description/visibility/archive/default-branch updates.
- [x] Tier 2 repository settings confirmation.
- [x] Tier 3 exact-name repository deletion.
- [x] repository-scoped `administration: write` for update/delete.
- [x] durable audit migration `0005_audit_log`.
- [x] cancellation consumes pending write authority.
- [x] uncertain write reconciliation instead of blind replay.
- [x] 117-test verified suite.

---

## P4 — Repository contents, Git tools & run-command assistant

### P4.1 File browser ✅

Final feature-delivery verification chain:

- implementation head `614f013b35644fcdd05e880c9a37ff30fd503fdf` — CI `34639736010` green;
- documentation-synchronized head `185d99d33e863e0909e7e0459d9fcf7fe5df1244` — CI `34641130457` green;
- non-draft PR #16 CI `34641248664` green;
- squash merge `32ef6ec55772f01fcce4ba8c6db1d836aadb45c6`;
- post-feature `main` CI `34641411838` green;
- governance closeout `d113872e703b005f4c3c8e2b1da8fc2597e8ecd7`.

Implementation/acceptance:

- [x] directory navigation and pagination.
- [x] text preview/pagination.
- [x] binary/large-file metadata fallback.
- [x] branch/tag/SHA selection for reads.
- [x] create text file and upload document.
- [x] update/edit and replace file.
- [x] bounded file download.
- [x] delete file.
- [x] diff/preview before write execution.
- [x] durable `file_write_sessions` staging + persisted confirmation.
- [x] migration `0006_file_write_sessions`.
- [x] stale branch-head/current-file-SHA protection.
- [x] same user/repository/branch/path staging supersedes older pending authority and scrubs old staged content.
- [x] repository-scoped `contents: write` for ordinary writes.
- [x] `.github/workflows/*` additionally requires `workflows: write`.
- [x] uncertain writes reconcile GitHub state; no blind replay.
- [x] audit excludes file bodies and credentials.
- [x] short callback sessions/indexes/tokens keep long paths out of callback data.
- [x] temporary staged content scrubbed on consume/cancel/supersede/expiry/prune.
- [x] **148 tests** on Python 3.12 and 3.13; mypy clean on **87 source files**.
- [x] PostgreSQL 17 migration round-trip through `0006_file_write_sessions`.
- [x] documentation-head CI, non-draft PR CI, protected squash merge, post-feature main CI, and governance handoff verified.

### P4.2 Branch/commit tools ✅

Final feature-delivery verification chain:

- implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518` — CI `34647181024` green;
- documentation-synchronized feature head `73e48dfced65d72d0d27e9defc4c3e107527107f` — push CI `34647866083` green;
- non-draft PR #18 CI `34648080794` green on unchanged mergeable head;
- protected squash merge `b4e7dcd9de5db1e958e831508443d3fa1445213d`;
- post-feature `main` CI `34648224733` green.

Implementation/acceptance:

- [x] list branches from authoritative GitHub state.
- [x] case-insensitive search/filter over fetched branch list.
- [x] create branch from explicit known base ref/SHA with resolved base commit SHA.
- [x] persisted Tier 1 branch-create preview/confirmation.
- [x] revalidate base SHA at confirm time; moved base returns stale without write.
- [x] check target absence before preview and again before write.
- [x] duplicate branch handling without replacement/update.
- [x] missing base handling without write.
- [x] repository-scoped `contents: write` for create-ref.
- [x] single create-ref request; uncertain outcome reconciles remote target rather than replaying POST.
- [x] safe branch-create audit metadata.
- [x] recent commits from default or explicit ref.
- [x] commit detail.
- [x] compare refs.
- [x] bounded large-compare summary.
- [x] compact callback/navigation context.
- [x] no normal v1 force-push/force-update/branch-delete UI.
- [x] **165 tests** on Python 3.12 and 3.13; mypy clean on **94 source files**.
- [x] Ruff/compile/audit/secret/PEP 751/PostgreSQL gates green.
- [x] documentation-head CI, non-draft PR CI, protected squash merge, post-feature `main` CI, and final governance handoff verified.

### P4.3 Clone/setup/run assistant — active

- [ ] fresh clone commands.
- [ ] update-existing-clone commands.
- [ ] detect Python/Node/Docker/Gradle/Maven baseline from repository evidence.
- [ ] Windows PowerShell commands.
- [ ] Linux commands.
- [ ] macOS commands.
- [ ] confidence/source explanation.
- [ ] safe path/ref quoting where applicable.
- [ ] no token insertion/no arbitrary command execution.

P4 acceptance:

- [x] owner can browse and safely update one file at a time without blind overwrite;
- [x] repository-controlled file/README text is displayed only and never automatically executed by P4.1;
- [x] P4.2 branch/commit implementation, acceptance tests, merge, post-merge CI, and governance are complete;
- [ ] P4.3 generated commands clearly separate clone/update/setup/run.

---

## P5 — Webhooks & notification engine

### P5.1 Secure ingestion

- [ ] GitHub webhook endpoint.
- [ ] raw-body HMAC-SHA256 validation.
- [ ] delivery ID uniqueness/deduplication.
- [ ] durable webhook/event inbox.
- [ ] fast HTTP acknowledgement.
- [ ] retryable worker state.

### P5.2 Event normalization

- [ ] push.
- [ ] issues.
- [ ] issue_comment.
- [ ] pull_request.
- [ ] pull_request_review.
- [ ] pull_request_review_comment.
- [ ] workflow_run.
- [ ] release.
- [ ] star.
- [ ] fork.
- [ ] installation/install-repository changes.

### P5.3 Notification UX/preferences

- [ ] per-repository event toggles.
- [ ] mute repository.
- [ ] immediate notification renderer.
- [ ] safe deep-action navigation.
- [ ] duplicate delivery produces no duplicate Telegram message.

Acceptance: forged signatures rejected; duplicate delivery idempotent; restart-safe durable work; preferences honored; private raw payload not overlogged.

---

## P6 — Issues & Pull Requests

### P6.1 Issues

- [ ] list/search/filter/detail/comments.
- [ ] create/comment/reply/close/reopen.
- [ ] labels/assignees where supported.

### P6.2 Pull Requests

- [ ] list/filter/detail.
- [ ] changed files/diffs/conversation/reviews.
- [ ] comment/reply/review.
- [ ] merge Tier 2 with current CI/check state and stale-head protection.

Acceptance: common issue/PR tasks from Telegram; merge requires explicit target preview; failing/pending CI shown; writes audited.

---

## P7 — GitHub Actions & releases

### P7.1 Actions read

- [ ] workflows/runs/jobs/steps.
- [ ] logs with truncation/document fallback.
- [ ] artifacts metadata/download flow.

### P7.2 Actions write

- [ ] workflow dispatch with declared inputs/ref confirmation.
- [ ] rerun failed run/jobs.
- [ ] cancel run if included.
- [ ] audit all write actions.

### P7.3 Releases

- [ ] release list/latest detail/assets.
- [ ] release webhook notification.

Acceptance: dispatch never runs without workflow/ref/inputs review; failed run can navigate to logs/retry; Actions secrets never exposed.

---

## P8 — Safe ZIP/project synchronization

### P8.1 Upload/security

- [ ] isolated workspace and upload limits.
- [ ] archive member pre-scan.
- [ ] traversal/absolute/symlink/hardlink policy.
- [ ] file-count/depth/uncompressed-size limits.
- [ ] duplicate normalized-path detection.
- [ ] secret-like warnings.

### P8.2 Diff planning

- [ ] base commit snapshot.
- [ ] added/modified/deleted/unchanged plan.
- [ ] binary/large classification and text diff preview.
- [ ] exclusions/warnings.
- [ ] immutable persisted sync plan.

### P8.3 Apply

- [ ] stale base re-check.
- [ ] review branch by default.
- [ ] coherent tree/commit apply.
- [ ] optional PR.
- [ ] direct default branch only via explicit Tier 2 exception.
- [ ] audit and workspace cleanup.

Acceptance: malicious archives rejected; coherent reviewable change; default branch not silently overwritten; changed base invalidates/replans; restart/reconciliation safe.

---

## P9 — Hardening & production readiness

- [ ] PostgreSQL deployment/backup/restore runbooks.
- [ ] systemd/reverse proxy/HTTPS.
- [ ] log rotation/retention and DB cleanup.
- [ ] credential key rotation procedure.
- [ ] GitHub App permission/operator docs.
- [ ] end-to-end live test checklist.
- [ ] rate-limit/load/webhook replay/restart tests.
- [ ] security review of ZIP/file/write flows.
- [ ] full secret/dependency vulnerability review.
- [ ] release checklist.

Acceptance: clean server deploys from docs; restart recovery; restore verified; no required operational knowledge exists only in chat history.

---

## P10 — Expansion (post-v1)

Candidates:

- [ ] multi-user roles/accounts.
- [ ] multiple GitHub accounts/installations per Telegram user.
- [ ] organization/team management subset.
- [ ] scheduled/digest notifications.
- [ ] saved searches/watchlists.
- [ ] release creation/management.
- [ ] richer GraphQL aggregation.
- [ ] optional AI summarization isolated from core correctness.
- [ ] GitHub Enterprise host support.
- [ ] web admin console if Telegram becomes insufficient.

---

## Roadmap rule

When priorities change, do not erase old intent silently. Update this file and add a decision entry if the change materially affects architecture/product scope.
