# GitDock — Roadmap

Status legend:

- [ ] not started
- [~] in progress
- [x] verified complete
- `[BLOCKED]` blocked with reason in `docs/CURRENT_STATUS.md`

Do not mark a phase complete merely because code exists. Its acceptance criteria must be verified.

---

## P0 — Planning & governance foundation ✅

Goal: make the project self-describing before feature code starts.

- [x] Repository identity and product direction established.
- [x] `AGENTS.md` mandatory development contract.
- [x] Master product plan.
- [x] Durable project memory.
- [x] Current status/handoff file.
- [x] Canonical constants.
- [x] Architecture specification.
- [x] Telegram UI/UX specification.
- [x] Security model.
- [x] Build protocol.
- [x] Test matrix.
- [x] Decision log.
- [x] Changelog.
- [x] Pull request completion checklist.
- [x] Final consistency pass + mark P0 complete.

Acceptance:

- [x] a new session can understand scope, architecture, UX, security, current state, and next task without chat history;
- [x] post-build documentation rules are explicit;
- [x] no production feature is falsely marked implemented.

---

## P1 — Project skeleton & quality gates `[BLOCKED]`

Implementation exists on `feat/p1-foundation` / draft PR #1. Verification is blocked because GitHub Actions jobs are failing before any runner step begins. See `docs/CURRENT_STATUS.md`.

### P1.1 Application skeleton

- [~] Python package layout created according to architecture boundaries.
- [~] Python version policy selected and documented.
- [~] Dependency manager/lock strategy selected. Direct pins exist; complete transitive/hash lock still must be finalized.
- [~] typed settings/config module.
- [~] `.env.example` with placeholders only.
- [~] `.gitignore` covers venv/cache/log/db/temp/secret artifacts.
- [~] structured logging baseline with redaction hooks.

### P1.2 HTTP/bot bootstrap

- [~] FastAPI application boots.
- [~] `/health` endpoint.
- [~] readiness endpoint/check structure.
- [~] aiogram bot/router bootstrap.
- [~] development polling mode.
- [~] production Telegram webhook-ready path.
- [~] owner authorization middleware.

### P1.3 Persistence

- [~] async SQLAlchemy setup.
- [~] PostgreSQL production configuration.
- [~] Alembic initialized.
- [~] initial identity/account tables.
- [~] migration test from empty DB.

### P1.4 Quality gates

- [~] formatter configured.
- [~] linter configured.
- [~] type checker configured.
- [~] unit test harness.
- [~] async/integration test harness.
- [~] secret scan configured.
- [~] dependency/security check selected.
- [~] CI workflow configured.
- [x] exact check commands written into `docs/BUILD_PROTOCOL.md`.

Acceptance:

- [ ] fresh clone can be configured without real secrets committed;
- [ ] app starts locally with the pinned full dependency set;
- [ ] health endpoint passes under the full suite;
- [ ] unauthorized Telegram user is blocked/ignored under the full suite;
- [ ] DB migration/bootstrap works on PostgreSQL CI;
- [ ] all configured quality gates green.

---

## P2 — GitHub App connection & read-only core

### P2.1 GitHub App auth foundation

- [ ] GitHub App configuration model.
- [ ] JWT generation for app authentication.
- [ ] installation discovery/binding.
- [ ] installation access-token provider with expiry-aware refresh.
- [ ] user authorization state model/callback scaffold.
- [ ] encrypted token persistence abstraction.
- [ ] central capability/permission mapper.

### P2.2 GitHub gateway foundation

- [ ] typed REST client wrapper.
- [ ] pagination helper.
- [ ] standard error translation.
- [ ] rate-limit capture/model.
- [ ] retry policy for safe transient requests.
- [ ] test doubles/fixtures.

### P2.3 Home + repository read screens

- [ ] GitHub connection screen.
- [ ] Home status screen.
- [ ] repository list/pagination/filter basics.
- [ ] repository dashboard metadata.
- [ ] refresh and empty/error states.

Acceptance:

- owner can connect/bind GitHub App installation safely;
- GitDock lists only accessible installed repositories;
- tokens are not exposed in logs/Telegram;
- rate/auth/permission failures render correctly;
- no write permission is required for the read-only flow.

---

## P3 — Search & repository administration

### P3.1 GitHub search

- [ ] repository search query flow.
- [ ] stars/forks/language/license/updated metadata.
- [ ] sort by stars/update.
- [ ] language/min-stars/owner/topic/archive filters.
- [ ] result pagination.
- [ ] repository detail from search result.
- [ ] clone-command entry from search result.

### P3.2 User-context authorization

- [ ] GitHub App user authorization completed.
- [ ] one-time state validation.
- [ ] encrypted token storage/refresh behavior as applicable.
- [ ] disconnect/revoke local binding flow.

### P3.3 Repository create/settings

- [ ] create personal repository.
- [ ] optional organization repository creation when authorized.
- [ ] edit name/description/settings supported by scope.
- [ ] archive/unarchive.
- [ ] visibility-change Tier 2 flow.
- [ ] delete Tier 3 exact-name confirmation.
- [ ] audit writes.

Acceptance:

- search is useful without GitDock owning a repo;
- repository creation uses correct user context/permission;
- dangerous settings never execute from one tap;
- deletion tests cover expired/reused/wrong-name/permission-failure cases.

---

## P4 — Repository contents, Git tools & run-command assistant

### P4.1 File browser

- [ ] directory navigation.
- [ ] text preview/pagination.
- [ ] binary/large-file metadata flow.
- [ ] branch/ref selection.
- [ ] create file.
- [ ] update/replace file.
- [ ] delete file.
- [ ] stale SHA protection.
- [ ] workflow-file special permission handling.

### P4.2 Branch/commit tools

- [ ] list/search branches.
- [ ] create branch.
- [ ] recent commits.
- [ ] commit detail/diff summary.
- [ ] compare refs.

### P4.3 Clone/setup/run assistant

- [ ] fresh clone commands.
- [ ] update-existing-clone commands.
- [ ] project detector for Python/Node/Docker/Gradle/Maven baseline.
- [ ] Windows PowerShell commands.
- [ ] Linux commands.
- [ ] macOS commands.
- [ ] confidence/source explanation.
- [ ] no token insertion/no arbitrary command execution.

Acceptance:

- owner can browse and safely update files without blind overwrite;
- repository-controlled README text is never automatically executed;
- generated commands are clearly separated into clone/update/setup/run.

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
- [ ] deep-action buttons to issue/PR/action where safe.
- [ ] duplicate delivery produces no duplicate Telegram message.

Acceptance:

- forged signature rejected;
- duplicate delivery idempotent;
- restart after durable ingest does not lose pending event;
- event-type preferences honored;
- private repo payload content is not overlogged.

---

## P6 — Issues & Pull Requests

### P6.1 Issues

- [ ] list/search/filter.
- [ ] issue detail.
- [ ] comments.
- [ ] create issue.
- [ ] comment/reply.
- [ ] close/reopen.
- [ ] labels/assignees where supported.

### P6.2 Pull Requests

- [ ] list/filter.
- [ ] detail.
- [ ] changed files/diffs.
- [ ] conversation/review threads.
- [ ] comment/reply.
- [ ] submit review.
- [ ] approve/request changes where authorized.
- [ ] merge Tier 2 flow.
- [ ] display current checks/CI before merge.
- [ ] stale PR/head precondition handling.

Acceptance:

- common issue/PR tasks are possible from Telegram;
- merge cannot happen without explicit target preview/confirmation;
- failing/pending CI state is shown, not hidden;
- all writes audited.

---

## P7 — GitHub Actions & releases

### P7.1 Actions read

- [ ] workflows list.
- [ ] runs list/detail.
- [ ] jobs/steps.
- [ ] logs with truncation/document fallback.
- [ ] artifacts list/download metadata/flow.

### P7.2 Actions write

- [ ] workflow dispatch.
- [ ] collect declared inputs.
- [ ] ref selection.
- [ ] dispatch confirmation.
- [ ] re-run failed run/jobs.
- [ ] cancel run if included in implementation scope.
- [ ] audit all write actions.

### P7.3 Releases

- [ ] release list.
- [ ] latest release detail.
- [ ] assets metadata/access flow.
- [ ] release webhook notification.

Acceptance:

- workflow dispatch never runs without showing workflow/ref/inputs;
- failed workflow notification can navigate to logs/retry;
- Actions secrets are never exposed.

---

## P8 — Safe ZIP/project synchronization

### P8.1 Upload/security

- [ ] isolated workspace.
- [ ] upload size guard.
- [ ] archive member pre-scan.
- [ ] traversal/absolute path rejection.
- [ ] symlink/hardlink policy enforced.
- [ ] count/depth/uncompressed-size limits.
- [ ] duplicate normalized-path detection.
- [ ] secret-like file warnings.

### P8.2 Diff planning

- [ ] base commit snapshot.
- [ ] added/modified/deleted/unchanged plan.
- [ ] binary/large file classification.
- [ ] text diff preview.
- [ ] exclusions/warnings screen.
- [ ] immutable persisted sync plan.

### P8.3 Apply

- [ ] stale base re-check.
- [ ] review branch by default.
- [ ] coherent tree/commit apply.
- [ ] optional PR creation.
- [ ] direct default branch only through explicit Tier 2 exception flow.
- [ ] audit result.
- [ ] workspace cleanup success/cancel/error/expiry.

Acceptance:

- malicious ZIP fixtures rejected;
- mass update produces a reviewable coherent change;
- default branch is not silently overwritten;
- changed base invalidates/replans safely;
- operation survives/reconciles process restart where needed.

---

## P9 — Hardening & production readiness

- [ ] complete PostgreSQL deployment runbook.
- [ ] systemd unit/runbook.
- [ ] reverse proxy/HTTPS configuration notes.
- [ ] backup/restore procedure tested.
- [ ] log rotation/retention.
- [ ] database cleanup/retention jobs.
- [ ] token encryption key rotation procedure.
- [ ] GitHub App permission/operator documentation.
- [ ] end-to-end live test checklist.
- [ ] rate-limit/load behavior tests.
- [ ] webhook replay/restart tests.
- [ ] security review of ZIP/file/write flows.
- [ ] full secret scan.
- [ ] dependency vulnerability review.
- [ ] release checklist green.

Acceptance:

- clean server can deploy from documented steps;
- service recovers from restart;
- DB restore verified;
- no required operational knowledge exists only in chat history.

---

## P10 — Expansion (post-v1)

Not part of initial Done criteria unless reprioritized.

Candidates:

- [ ] multi-user accounts/roles.
- [ ] multiple GitHub accounts/installations per Telegram user.
- [ ] organization/team management subset.
- [ ] scheduled/digest notifications.
- [ ] saved searches/watchlists.
- [ ] release creation/management.
- [ ] richer GraphQL aggregation.
- [ ] optional AI summarization of diffs/issues/PRs, isolated from core correctness.
- [ ] GitHub Enterprise host support.
- [ ] web admin console if Telegram becomes insufficient for selected workflows.

---

## Roadmap rule

When priorities change, do not erase old intent silently. Update this file and add a decision entry explaining the change if it materially affects architecture/product scope.
