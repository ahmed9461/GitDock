# GitDock — Roadmap

Status legend:

- [ ] not started
- [~] in progress / delivery closeout pending
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
- [x] Fresh clone commands.
- [x] Update-existing-clone commands.
- [x] Windows PowerShell, Linux, and macOS targets.
- [x] Bounded evidence detection for Python/Node/Docker/Gradle/Maven.
- [x] Explicit confidence/source explanation.
- [x] Safe path/ref quoting where applicable.
- [x] Public unauthenticated evidence reads; installed/private reads through installation context.
- [x] Repository/search UI entry points with compact callbacks.
- [x] Stale public-search sessions fail closed.
- [x] README/script bodies are never copied/executed as arbitrary shell commands.
- [x] Generated commands never contain GitHub credentials.
- [x] Output warns about repository-controlled hooks/build logic/scripts.
- [x] Command generation only; no automatic shell execution.
- [x] **182 tests** on Python 3.12/3.13; mypy clean on **100 source files**.
- [x] Documentation-head CI, non-draft PR CI, protected squash merge, post-feature `main` CI, and governance closeout verified.

---

## P5 — Webhooks & notification engine

### P5.1 Secure ingestion ✅

- [x] GitHub webhook endpoint in existing FastAPI ingress.
- [x] Verify `X-Hub-Signature-256` against exact raw request body using HMAC-SHA256.
- [x] Reject missing/forged/malformed signatures before trusted processing.
- [x] Validate/capture GitHub delivery ID and event name.
- [x] Durable `github_webhook_deliveries` inbox.
- [x] Unique delivery-ID deduplication/idempotency.
- [x] Same delivery ID with different event/content is explicit conflict.
- [x] Fast HTTP 202 acknowledgement after validation + durable acceptance.
- [x] Retryable/restart-safe `pending/processing/failed/processed` state.
- [x] Processing lease recovers abandoned work after crash/restart.
- [x] Bounded payload/logging/retention policy; `GITHUB_WEBHOOK_MAX_BODY_BYTES=25_000_000`.
- [x] Processed payload pruning after retention expiry.
- [x] Migration `0007_github_webhook_deliveries.py` / revision `0007_webhook_inbox`.
- [x] Unit/integration/contract coverage for signature, duplicate/conflict, route security, persistence/restart, retry/lease, retention, migration.
- [x] **213 tests** on Python 3.12/3.13; mypy **104 source files**; Ruff **176 files**; compile/audit/secrets/locks/PostgreSQL green.
- [x] Documentation-head CI `34654662909` green.
- [x] Non-draft PR #22 CI `34654757724` green on unchanged mergeable head.
- [x] Protected squash merge `c13c16cf9d2354079294ebf01afbe098635b6247`.
- [x] Post-feature `main` CI `34654852954` green.

### P5.2 Event normalization — ACTIVE

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

P5.2 consumes only authenticated durable P5.1 deliveries, preserves source delivery identity/idempotency, and produces normalized event data. Telegram notification preferences/rendering/delivery remain P5.3.

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
