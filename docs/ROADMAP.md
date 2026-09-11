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

- [x] P2.1 GitHub App auth foundation.
- [x] P2.2 canonical GitHub gateway foundation.
- [x] P2.3 Home + installed repository read screens.

## P3 — Search & repository administration ✅

- [x] P3.1 public repository search.
- [x] P3.2 durable GitHub user-context authorization/disconnect.
- [x] P3.3 repository create/settings/delete administration.

## P4 — Repository contents, Git tools & run-command assistant ✅

### P4.1 File browser ✅
- [x] Directory/ref browsing, preview/download, single-file create/update/delete.
- [x] Durable staging, stale checks, scoped permissions, one-write reconciliation, audit/scrubbing.
- [x] **148 tests**; mypy **87 source files**.

### P4.2 Branch/commit tools ✅
- [x] Branch reads/search/create, recent commits/detail, compare refs.
- [x] Persisted confirmation, base/target revalidation, one create-ref, reconciliation/audit.
- [x] **165 tests**; mypy **94 source files**.

### P4.3 Clone/setup/run assistant ✅
- [x] Fresh clone and update-existing-clone commands.
- [x] Windows PowerShell, Linux, macOS.
- [x] Python/Node/Docker/Gradle/Maven bounded evidence inference.
- [x] Confidence/source reporting and safe shell-aware quoting.
- [x] Credential-free command output; no automatic command execution.
- [x] README/script bodies remain untrusted and are never copied as arbitrary commands.
- [x] **182 tests**; mypy **100 source files**; all CI/security/migration gates green.
- [x] Protected feature merge + governance closeout + final `main` CI complete.

---

## P5 — Webhooks & notification engine

### P5.1 Secure ingestion — IMPLEMENTATION VERIFIED / DELIVERY CLOSEOUT ACTIVE

Implementation head `e55c6e99001bb657ed2064459e92caca1f2e3481`, push CI `34652564335` green.

- [x] GitHub webhook endpoint in the existing FastAPI ingress.
- [x] Exact raw-body `X-Hub-Signature-256` HMAC-SHA256 verification.
- [x] Missing/forged/malformed signatures rejected before trusted event processing.
- [x] Bounded validation/capture of GitHub delivery ID and event name.
- [x] Durable `github_webhook_deliveries` inbox.
- [x] Unique delivery-ID deduplication/idempotency.
- [x] Same delivery ID with different content fails as conflict.
- [x] Fast HTTP 202 acknowledgement after validation + durable acceptance.
- [x] Durable `pending/processing/failed/processed` state.
- [x] Processing lease supports crash/restart recovery.
- [x] Failure state supports bounded retry scheduling and safe error codes.
- [x] 25 MiB payload ceiling, bounded retention, and processed-payload pruning.
- [x] HTTP/logging boundary avoids echoing webhook secret/signature/raw payload.
- [x] Migration `0007_github_webhook_inbox` with SQLite/PostgreSQL round-trip coverage.
- [x] Unit/integration/contract coverage for signature, idempotency, restart safety, retry lifecycle, route behavior, and HTTP secrecy.
- [x] **213 tests** on Python 3.12/3.13; Ruff **176 files**; mypy **104 source files**; compile/audit/secrets/locks/PostgreSQL green.
- [~] Documentation-head CI → non-draft PR CI → protected squash merge → post-feature `main` CI → governance closeout.

Acceptance implementation is satisfied. P5.1 is not formally complete until the delivery chain above is finished.

### P5.2 Event normalization — NOT ACTIVE YET

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

---

## P7 — GitHub Actions & releases

- [ ] Actions workflows/runs/jobs/steps/logs/artifacts.
- [ ] Dispatch/rerun/cancel with explicit review/authorization.
- [ ] Release list/latest/assets and release notifications.

---

## P8 — Safe ZIP/project synchronization

- [ ] Secure bounded archive intake.
- [ ] Coherent added/modified/deleted/unchanged diff plan.
- [ ] Stale-base recheck and review-branch default.
- [ ] Coherent tree/commit apply + optional PR + cleanup/audit.

---

## P9 — Hardening & production readiness

- [ ] PostgreSQL backup/restore runbooks.
- [ ] systemd/reverse proxy/HTTPS.
- [ ] Log/data retention and cleanup.
- [ ] Credential key rotation.
- [ ] End-to-end/rate-limit/replay/restart/security review.
- [ ] Release checklist.

---

## P10 — Expansion (post-v1)

Candidates include multi-user roles, multiple GitHub accounts/installations, richer organization/team support, digests/watchlists, richer GraphQL aggregation, optional AI summaries, GitHub Enterprise host support, and a web admin console if Telegram becomes insufficient.

---

## Roadmap rule

When priorities change, do not erase old intent silently. Update this file and add a decision entry if the change materially affects architecture/product scope.
