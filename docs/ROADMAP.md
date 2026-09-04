# GitDock — Roadmap

Status legend:

- [ ] not started
- [~] in progress
- [x] verified implementation/acceptance item
- `[BLOCKED]` blocked with reason in `docs/CURRENT_STATUS.md`

Do not mark a phase complete merely because code exists. Its acceptance criteria and required merge/governance verification must pass.

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

## P1 — Project skeleton & quality gates ✅

Verified by the P1 PR/main CI chain and committed PEP 751 lock verification.

### P1.1 Application skeleton

- [x] Python package layout according to architecture boundaries.
- [x] Python version policy; CI verifies 3.12 and 3.13.
- [x] exact direct pins + PEP 751 per-Python Linux runtime locks.
- [x] typed settings/config module.
- [x] `.env.example` placeholders only.
- [x] `.gitignore` for venv/cache/log/db/temp/secret artifacts.
- [x] structured logging baseline with redaction hooks.

### P1.2 HTTP/bot bootstrap

- [x] FastAPI application boots under integration tests.
- [x] `/health`.
- [x] readiness endpoint/check structure.
- [x] aiogram bot/router bootstrap.
- [x] development polling mode.
- [x] production Telegram webhook-ready path.
- [x] owner authorization middleware.

### P1.3 Persistence

- [x] async SQLAlchemy setup.
- [x] PostgreSQL production configuration.
- [x] Alembic initialized.
- [x] initial identity/account tables.
- [x] migration bootstrap and PostgreSQL upgrade/downgrade/re-upgrade verification.

### P1.4 Quality gates

- [x] formatter.
- [x] linter.
- [x] type checker.
- [x] unit/async/integration harnesses.
- [x] secret scan.
- [x] dependency/security audit.
- [x] Python 3.12/3.13 CI + PostgreSQL migration job.
- [x] exact check commands documented.
- [x] PEP 751 lock regeneration/drift checks.

Acceptance:

- [x] fresh clone configurable without committed real secrets;
- [x] app starts under pinned dependencies;
- [x] health passes;
- [x] unauthorized Telegram user blocked/ignored;
- [x] DB migration/bootstrap works on PostgreSQL CI;
- [x] configured quality gates green.

---

## P2 — GitHub App connection & read-only core

### P2.1 GitHub App auth foundation ✅

Squash-merged through PR #5 as `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge `main` CI `33348851085` passed.

- [x] GitHub App configuration model.
- [x] JWT generation for App authentication.
- [x] installation discovery/binding.
- [x] installation access-token provider with expiry-aware refresh.
- [x] user authorization state model/callback scaffold.
- [x] encrypted token persistence abstraction.
- [x] central capability/permission mapper.
- [x] restart-safe hashed one-time OAuth state.
- [x] PKCE S256 with encrypted verifier storage.
- [x] dual App/user-context installation identity verification before binding.

### P2.2 GitHub gateway foundation ✅

Squash-merged through PR #7 as `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge `main` CI `33409825480` passed.

- [x] typed REST client wrapper.
- [x] canonical-host pagination helper with loop/page limits.
- [x] stable safe error translation without raw response-body leakage.
- [x] rate-limit capture/model.
- [x] bounded retry for safe transient reads; write-like methods no retry by default.
- [x] HTTPX MockTransport contract doubles/fixtures.

### P2.3 Home + repository read screens ✅

Squash-merged through PR #8 as `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; post-merge `main` CI `33424799759` passed. Governance closeout PR #9 merged as `ac8230eb1f8b7099979c55e767d9f6d14e0118a7`; post-closeout `main` CI `33444410513` passed.

- [x] GitHub connection screen and runtime setup/OAuth callback wiring.
- [x] Home status screen.
- [x] installed repository list.
- [x] stable application pagination.
- [x] filters: all/private/public/active/archived/source/fork.
- [x] repository dashboard metadata.
- [x] refresh, empty, stale-selection, and mapped GitHub error states.
- [x] compact versioned repository callbacks resolved server-side.
- [x] minimal non-authoritative `repositories_cache` + migration `0003`.
- [x] repository details revalidated from GitHub before render.
- [x] thin read-only Telegram handlers/renderers/keyboards.
- [x] 65-test verified suite at P2.3.
- [x] documentation/PR/merge/main/governance closeout verification.

Acceptance:

- [x] owner can start safe GitHub App installation/user-authorization flow from Telegram;
- [x] setup `installation_id` still passes dual-context verification;
- [x] GitDock lists repositories returned for bound installation(s);
- [x] callbacks are scoped to GitDock user/current installation context;
- [x] repository detail refreshes from GitHub rather than trusting cache;
- [x] token/OAuth/PKCE/private-key/raw-error material is absent from Telegram repository screens/cache;
- [x] stable auth/permission/not-found/rate/transient/stale renderer paths;
- [x] no repository write/admin permission required;
- [x] governance closeout completed.

---

## P3 — Search & repository administration

### P3.1 GitHub search ✅

Verification chain:

- implementation CI `33453960817` green;
- documentation-head CI `33454438202` green;
- PR #10 CI `33454524953` green;
- squash merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`;
- post-feature `main` CI `33454619065` green;
- governance closeout PR #11 merge `ef2c5f618102063df8166f84b4828243f5efb5c6`;
- post-closeout `main` CI `33454972020` green.

- [x] repository search query flow.
- [x] stars/forks/language/license/updated metadata.
- [x] sort by stars/update.
- [x] language/min-stars/owner/topic/archive filters.
- [x] result pagination.
- [x] detail from active search context followed by GitHub re-fetch.
- [x] compact session-scoped callbacks and stale-session rejection.
- [x] public/anonymous search without bound installation.
- [x] public search state separated from installed `repositories_cache`.
- [x] `/start` and Home clear transient search FSM state.
- [x] 83-test verified suite at P3.1.
- [x] download-command entry point remains placeholder; actual generation deferred to P4.3.

P3.1 is Tier 0 read-only and introduces no repository write/admin permission.

### P3.2 User-context authorization ✅

Verification chain:

- implementation head `5068b58ec41fb5ac417408d3a535bbb5d66207fc` — CI `33515291600` green with **97 tests**;
- documentation-synchronized head `492183bfba311827a965153eff61747bfabf76ed` — CI `33517270731` green;
- PR #12 CI `33527318485` green on unchanged head;
- squash merge `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`;
- post-feature `main` CI `33527484948` green;
- governance closeout PR #13 merge `aeb003cec79d1952dc80a520c03a4eee819872bc`.

- [x] authenticated GitHub `/user` identity resolution for durable user context.
- [x] standalone GitHub App user authorization for durable user-context features that genuinely require it.
- [x] established P2.1 one-time OAuth state validation reused; no second state system.
- [x] existing PKCE S256 lifecycle reused.
- [x] existing versioned encrypted credential store reused.
- [x] access/refresh expiry metadata preserved.
- [x] expiry-aware refresh implemented.
- [x] rotating refresh token replacement implemented.
- [x] `credential_generation` prevents stale refresh from overwriting reconnect/disconnect state.
- [x] durable DB-backed `pending_confirmations` introduced for one-time sensitive confirmations.
- [x] local-disconnect target fingerprint binds account identity, credential generation, and current installation IDs.
- [x] expired/invalid/reused/cancelled disconnect confirmation fails closed.
- [x] stale confirmation after reauthorization fails closed.
- [x] stale confirmation after installation-set change fails closed.
- [x] Home invalidates outstanding disconnect confirmations.
- [x] local disconnect clears encrypted GitDock credentials, local installation bindings, local repository cache, and relevant pending local state.
- [x] local disconnect explicitly does **not** claim or perform remote GitHub App uninstall/revocation.
- [x] legacy P2.3 installation-only state can be disconnected safely.
- [x] connected Home exposes `👤 حساب GitHub`.
- [x] Arabic account UI exposes authorization state, activate/re-authorize, refresh, and isolated local-disconnect confirmation.
- [x] callbacks stay compact and within Telegram callback-data limits.
- [x] Telegram handlers remain thin; auth/token/encryption/confirmation rules stay in services.
- [x] migration `0004_user_auth` passes PostgreSQL upgrade/downgrade/re-upgrade.
- [x] no runtime dependency or PEP 751 lock drift.
- [x] no new repository write/admin feature or broad permission introduced by P3.2.
- [x] documentation/PR/merge/main/governance closeout completed.

### P3.3 Repository create/settings ✅

Verification chain:

- implementation head `4e71d7f1c962e61584d6532d03c913703dc5295a` — CI `33890407945` green with **117 tests**;
- documentation-synchronized head `0cabc820751482c1c6f3dc13dcef5861aa2901d1` — CI `33891756482` green;
- non-draft PR #14 CI `33891899602` green and mergeable on unchanged head;
- squash merge `c0ed95a0360d49cdd67cb6c5f702d6beb78e0368`;
- post-feature `main` CI `33892100584` green.

- [x] create personal repository using durable GitHub user context.
- [x] optional organization repository creation when authorized.
- [x] edit supported repository name/description/default branch settings.
- [x] archive/unarchive.
- [x] visibility-change Tier 2 flow.
- [x] delete Tier 3 exact-name confirmation.
- [x] audit repository administration writes through migration `0005_audit_log`.
- [x] update/delete use repository-scoped installation tokens with `administration: write`.
- [x] create/update/delete confirmations are persisted, expiring, user-bound, single-use, and stale-safe.
- [x] cancel/back/edit consumes pending confirmation so old Telegram buttons cannot retain write authority.
- [x] uncertain create/update/delete outcomes reconcile remote state before GitDock claims success/failure.
- [x] Arabic Telegram creation wizard and repository-settings UX are wired through centralized callbacks/keyboards/renderers/FSM/router layers.
- [x] no blind retry for write-like GitHub operations.
- [x] no runtime dependency or PEP 751 lock drift.
- [x] documentation-synchronized final-head CI, non-draft PR, squash merge, post-merge `main` CI, and governance closeout verified.

Acceptance:

- [x] P3.1 search remains useful without GitDock owning/installing the repository and preserves installed-vs-public provenance;
- [x] P3.2 provides verified durable user context and stale-safe local disconnect semantics before repository-administration work begins;
- [x] repository creation uses correct durable user context/permission;
- [x] organization creation has a verified gateway/service path rather than an untested stub;
- [x] dangerous settings never execute from one tap;
- [x] deletion tests cover expired/reused/wrong-name/permission-failure cases;
- [x] stale repository preconditions fail closed;
- [x] uncertain write outcomes are reconciled before final outcome reporting;
- [x] cancellation invalidates persisted authority rather than merely navigating away;
- [x] implementation, documentation-head, PR, and post-merge `main` CI are green on Python 3.12, Python 3.13, PostgreSQL 17, audit, secrets, and lock checks;
- [x] governance closeout moves the exact next task to P4.1.

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
- [ ] detector for Python/Node/Docker/Gradle/Maven baseline.
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

- common issue/PR tasks possible from Telegram;
- merge cannot happen without explicit target preview/confirmation;
- failing/pending CI state shown, not hidden;
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

When priorities change, do not erase old intent silently. Update this file and add a decision entry if the change materially affects architecture/product scope.
