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
- [x] Development and governance contracts established.
- [x] Architecture, security, UI/UX, test, changelog, memory, and handoff documents established.

## P1 — Project skeleton & quality gates ✅

- [x] Async Python package, FastAPI, aiogram, SQLAlchemy/Alembic, PostgreSQL production model.
- [x] Owner-only Telegram boundary.
- [x] Ruff, mypy, pytest, compile, audit, secret scan, Python 3.12/3.13 CI, PostgreSQL migration CI.
- [x] Exact runtime/dev pins and PEP 751 Linux locks.

## P2 — GitHub App connection & read-only core ✅

### P2.1 GitHub App auth foundation ✅
- [x] App JWT, installation tokens, OAuth + PKCE, encrypted credentials, permission mapping, identity verification.

### P2.2 GitHub gateway foundation ✅
- [x] Canonical typed REST transport, safe pagination/errors, bounded read retry, no blind write retry.

### P2.3 Home + repository read screens ✅
- [x] Connected/disconnected Home, installed repository navigation/detail, compact callbacks, non-authoritative cache.

## P3 — Search & repository administration ✅

### P3.1 GitHub search ✅
- [x] Public search, filters/sort/pagination, opaque active sessions, stale-session rejection, detail re-fetch.

### P3.2 User-context authorization ✅
- [x] Durable encrypted user OAuth context, rotating refresh, stale-concurrency guard, persisted confirmations, safe local disconnect.

### P3.3 Repository create/settings ✅
- [x] Personal/org create.
- [x] Rename/description/visibility/archive/default-branch settings.
- [x] Tier 2 settings confirmation and Tier 3 exact-name deletion.
- [x] Scoped permissions, audit, reconciliation, cancellation/stale safety.

---

## P4 — Repository contents, Git tools & run-command assistant ✅

### P4.1 File browser ✅
- [x] Directory navigation/pagination and branch/tag/SHA reads.
- [x] Text preview, binary/large fallback, bounded download.
- [x] Create/upload/edit/replace/delete with durable staging and preview.
- [x] Exact branch/file stale checks, scoped permissions, one-write reconciliation, audit, staged-content scrubbing.
- [x] **148 tests** on Python 3.12/3.13; mypy clean on **87 source files**.

### P4.2 Branch/commit tools ✅
- [x] Branch list/search and Tier 1 stale-safe branch creation.
- [x] Recent commits, commit detail, compare refs, bounded compare output.
- [x] Repository-scoped `contents: write`, one create-ref request, uncertain-result reconciliation, audit.
- [x] No normal v1 force-push/force-update/branch-delete UI.
- [x] **165 tests** on Python 3.12/3.13; mypy clean on **94 source files**.

### P4.3 Clone/setup/run assistant ✅

Final feature-delivery chain:

- implementation head `fba538e3c6071365361def7d5970ff7b19b5819c` — CI `34650497474` green;
- documentation-synchronized head `989e826f8e845934b9255a78c91bfeca48f10538` — CI `34650840434` green;
- non-draft PR #20 CI `34650940874` green on unchanged mergeable head;
- protected squash merge `0f0750388a1a919917ba81586fad42ae2ab11336`;
- post-feature `main` CI `34651051039` green.

Implementation/acceptance:

- [x] fresh clone commands.
- [x] update-existing-clone commands.
- [x] Windows PowerShell, Linux, and macOS targets.
- [x] bounded evidence detection for Python/Node/Docker/Gradle/Maven.
- [x] explicit confidence/source explanation.
- [x] safe path/ref quoting where applicable.
- [x] public unauthenticated evidence reads; installed/private reads through installation context.
- [x] repository/search UI entry points with compact callbacks.
- [x] stale public-search sessions fail closed.
- [x] README/script bodies are never copied/executed as arbitrary shell commands.
- [x] generated commands never contain GitHub credentials.
- [x] output warns about repository-controlled hooks/build logic/scripts.
- [x] command generation only; no automatic shell execution.
- [x] **182 tests** on Python 3.12/3.13; mypy clean on **100 source files**.
- [x] Ruff/compile/audit/secret/PEP 751/PostgreSQL gates green.
- [x] documentation-head CI, non-draft PR CI, protected squash merge, and post-feature `main` CI verified.

P4 acceptance:

- [x] owner can browse and safely update one file at a time without blind overwrite.
- [x] branch/commit operations preserve stale-safe/scoped-write invariants.
- [x] generated clone/update/setup/run commands are OS-aware, evidence-backed, credential-free, and non-executing.
- [x] repository-controlled README/script text is never silently executed.
- [x] P4 feature delivery and post-merge verification complete.

---

## P5 — Webhooks & notification engine

### P5.1 Secure ingestion — ACTIVE

- [~] Establish secure, durable webhook ingestion boundary.
- [ ] GitHub webhook endpoint in existing FastAPI ingress.
- [ ] Verify `X-Hub-Signature-256` against the exact raw request body using HMAC-SHA256.
- [ ] Reject missing/forged signatures before trusted processing.
- [ ] Validate/capture GitHub delivery ID and event name.
- [ ] Durable webhook/event inbox.
- [ ] Unique delivery-ID deduplication/idempotency.
- [ ] Fast HTTP acknowledgement after validation + durable acceptance.
- [ ] Retryable/restart-safe processing state.
- [ ] Bounded payload/logging/retention policy.
- [ ] Migration and unit/integration/contract coverage.

Acceptance: forged signatures rejected; duplicate delivery is idempotent; accepted work survives restart; acknowledgement is fast; raw secrets/auth material are not overlogged.

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

- [ ] Per-repository event toggles.
- [ ] Mute repository.
- [ ] Immediate notification renderer.
- [ ] Safe deep-action navigation.
- [ ] Duplicate delivery produces no duplicate Telegram message.

---

## P6 — Issues & Pull Requests

### P6.1 Issues
- [ ] List/search/filter/detail/comments.
- [ ] Create/comment/reply/close/reopen.
- [ ] Labels/assignees where supported.

### P6.2 Pull Requests
- [ ] List/filter/detail.
- [ ] Changed files/diffs/conversation/reviews.
- [ ] Comment/reply/review.
- [ ] Merge Tier 2 with current CI/check state and stale-head protection.

Acceptance: common issue/PR tasks work from Telegram; merge requires explicit target preview; pending/failing CI is visible; writes are audited.

---

## P7 — GitHub Actions & releases

### P7.1 Actions read
- [ ] Workflows/runs/jobs/steps.
- [ ] Logs with truncation/document fallback.
- [ ] Artifact metadata/download flow.

### P7.2 Actions write
- [ ] Workflow dispatch with declared inputs/ref confirmation.
- [ ] Rerun failed run/jobs.
- [ ] Cancel run if included.
- [ ] Audit all write actions.

### P7.3 Releases
- [ ] Release list/latest detail/assets.
- [ ] Release webhook notification.

Acceptance: dispatch never runs without workflow/ref/input review; failed run can navigate to logs/retry; Actions secrets are never exposed.

---

## P8 — Safe ZIP/project synchronization

### P8.1 Upload/security
- [ ] Isolated workspace and upload limits.
- [ ] Archive member pre-scan.
- [ ] Traversal/absolute/symlink/hardlink policy.
- [ ] File-count/depth/uncompressed-size limits.
- [ ] Duplicate normalized-path detection.
- [ ] Secret-like warnings.

### P8.2 Diff planning
- [ ] Base commit snapshot.
- [ ] Added/modified/deleted/unchanged plan.
- [ ] Binary/large classification and text diff preview.
- [ ] Exclusions/warnings.
- [ ] Immutable persisted sync plan.

### P8.3 Apply
- [ ] Stale base re-check.
- [ ] Review branch by default.
- [ ] Coherent tree/commit apply.
- [ ] Optional PR.
- [ ] Direct default branch only via explicit Tier 2 exception.
- [ ] Audit and workspace cleanup.

Acceptance: malicious archives rejected; coherent reviewable change; default branch not silently overwritten; changed base invalidates/replans; restart/reconciliation safe.

---

## P9 — Hardening & production readiness

- [ ] PostgreSQL deployment/backup/restore runbooks.
- [ ] systemd/reverse proxy/HTTPS.
- [ ] Log rotation/retention and DB cleanup.
- [ ] Credential key rotation procedure.
- [ ] GitHub App permission/operator docs.
- [ ] End-to-end live test checklist.
- [ ] Rate-limit/load/webhook replay/restart tests.
- [ ] Security review of ZIP/file/write flows.
- [ ] Full secret/dependency vulnerability review.
- [ ] Release checklist.

Acceptance: clean server deploys from docs; restart recovery; restore verified; no required operational knowledge exists only in chat history.

---

## P10 — Expansion (post-v1)

Candidates:

- [ ] Multi-user roles/accounts.
- [ ] Multiple GitHub accounts/installations per Telegram user.
- [ ] Organization/team management subset.
- [ ] Scheduled/digest notifications.
- [ ] Saved searches/watchlists.
- [ ] Release creation/management.
- [ ] Richer GraphQL aggregation.
- [ ] Optional AI summarization isolated from core correctness.
- [ ] GitHub Enterprise host support.
- [ ] Web admin console if Telegram becomes insufficient.

---

## Roadmap rule

When priorities change, do not erase old intent silently. Update this file and add a decision entry if the change materially affects architecture/product scope.
