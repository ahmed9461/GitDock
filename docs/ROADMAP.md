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

## P1 — Project skeleton & quality gates ✅

Verified by GitHub Actions run `33344826152` after committed PEP 751 lock verification was enabled.

### P1.1 Application skeleton

- [x] Python package layout created according to architecture boundaries.
- [x] Python version policy selected and documented; CI verifies 3.12 and 3.13.
- [x] Dependency manager/lock strategy selected: exact direct pins + PEP 751 per-Python Linux runtime locks.
- [x] typed settings/config module.
- [x] `.env.example` with placeholders only.
- [x] `.gitignore` covers venv/cache/log/db/temp/secret artifacts.
- [x] structured logging baseline with redaction hooks.

### P1.2 HTTP/bot bootstrap

- [x] FastAPI application boots under integration tests.
- [x] `/health` endpoint.
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
- [x] migration test from empty DB and upgrade/downgrade/re-upgrade on PostgreSQL 17.

### P1.4 Quality gates

- [x] formatter configured and green.
- [x] linter configured and green.
- [x] type checker configured and green.
- [x] unit test harness.
- [x] async/integration test harness.
- [x] secret scan configured and green.
- [x] dependency/security check selected and green.
- [x] CI workflow configured with Python 3.12/3.13 + PostgreSQL migration job.
- [x] exact check commands written into `docs/BUILD_PROTOCOL.md`.
- [x] PEP 751 runtime lock regeneration/drift checks green for Python 3.12 and 3.13 Linux.

Acceptance:

- [x] fresh clone can be configured without real secrets committed;
- [x] app starts under the full pinned dependency set used by CI;
- [x] health endpoint passes under the full suite;
- [x] unauthorized Telegram user is blocked/ignored under the full suite;
- [x] DB migration/bootstrap works on PostgreSQL CI;
- [x] all configured quality gates green.

---

## P2 — GitHub App connection & read-only core

### P2.1 GitHub App auth foundation ✅

Squash-merged through PR #5 as `81dfaf406d046205b39980d6a64c681ea3ab18c6`; post-merge `main` CI run `33348851085` passed.

- [x] GitHub App configuration model.
- [x] JWT generation for app authentication.
- [x] installation discovery/binding.
- [x] installation access-token provider with expiry-aware refresh.
- [x] user authorization state model/callback scaffold.
- [x] encrypted token persistence abstraction.
- [x] central capability/permission mapper.

P2.1 additionally verifies restart-safe hashed one-time state, PKCE S256 with encrypted verifier storage, and dual app/user-context installation identity verification before binding.

### P2.2 GitHub gateway foundation ✅

Squash-merged through PR #7 into `main` as `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`; post-merge `main` CI run `33409825480` passed.

- [x] typed REST client wrapper.
- [x] pagination helper with canonical GitHub API URL validation, loop guard, and page limit.
- [x] standard safe error translation without raw response-body leakage.
- [x] rate-limit capture/model.
- [x] bounded retry policy for safe transient requests; write-like methods do not retry by default.
- [x] HTTPX MockTransport contract test doubles/fixtures.

P2.2 contract coverage includes canonical headers, parser boundaries, list/keyed pagination, malicious pagination target rejection, authentication/permission/not-found/conflict/validation/rate-limit categories, request/rate metadata, safe GET retry, and default no-write-retry behavior.

### P2.3 Home + repository read screens ✅

Squash-merged through non-draft PR #8 into `main` as `939d218d76fd87f3ba6cf0a80a89b4a816aac557`; post-merge `main` CI run `33424799759` passed.

- [x] GitHub connection screen and runtime setup/OAuth callback wiring.
- [x] Home status screen.
- [x] installed repository list.
- [x] stable application pagination.
- [x] repository filters: all/private/public/active/archived/source/fork.
- [x] repository dashboard metadata.
- [x] refresh, empty, stale-selection, and mapped GitHub error states.
- [x] compact versioned repository callbacks resolved server-side.
- [x] minimal non-authoritative `repositories_cache` + Alembic migration `0003`.
- [x] repository details revalidated from GitHub before render.
- [x] read-only Telegram renderers/keyboards/handlers with thin handler boundary.
- [x] contract/integration/unit coverage expanding the suite from 49 to 65 tests.
- [x] documentation-head CI + non-draft PR + squash merge + post-merge `main` verification.

Acceptance:

- [x] owner can start the safe GitHub App installation/user-authorization flow from Telegram;
- [x] setup `installation_id` still passes through P2.1 dual-context verification before binding;
- [x] GitDock lists repositories returned for the bound installation(s);
- [x] compact repository callbacks are scoped to the GitDock user and active installation context;
- [x] repository detail is refreshed from GitHub before display rather than trusting cache as authority;
- [x] tokens/OAuth/PKCE/private keys/raw GitHub error bodies are not exposed through Telegram repository screens/cache;
- [x] rate/auth/permission/not-found/transient classes have safe renderer paths;
- [x] no repository write/admin permission is required for the read-only flow;
- [x] merge/post-merge governance closeout completed and verified.

---

## P3 — Search & repository administration

### P3.1 GitHub search ✅

Verified delivery chain:

- implementation head `4a4f00d50e886ab494e2a83f2c649cd64b7398b2` — CI `33453960817` green;
- documentation-synchronized feature head `14e149ea307871abd8406ffc6212fe062ead9098` — branch CI `33454438202` green;
- non-draft PR #10 — PR CI `33454524953` green and mergeable on unchanged head;
- squash merge `d822338fcc1546418ed2100cc9534cdc71a6bcbe`;
- post-merge `main` CI `33454619065` green.

- [x] repository search query flow.
- [x] stars/forks/language/license/updated metadata.
- [x] sort by stars/update.
- [x] language/min-stars/owner/topic/archive filters.
- [x] result pagination.
- [x] repository detail from active search result context with GitHub re-fetch.
- [x] compact session-scoped callbacks and stale-session rejection.
- [x] public/anonymous search works without a bound installation.
- [x] public search state remains separate from installed `repositories_cache`.
- [x] `/start` and Home clear transient search FSM state.
- [x] 83-test branch/PR/main verification across Python 3.12/3.13 plus PostgreSQL and all configured quality/security gates.
- [x] download-command entry point is present as a safe placeholder only; actual clone/setup/run command generation is intentionally deferred to P4.3.

P3.1 remains Tier 0 read-only and introduces no repository write/admin permission.

### P3.2 User-context authorization

- [ ] GitHub App user authorization completed for durable user-context features that genuinely require it.
- [ ] one-time state validation reused through the established auth foundation.
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

- [x] P3.1 search is useful without GitDock owning/installing the repository and preserves installed-vs-public provenance;
- [ ] repository creation uses correct user context/permission;
- [ ] dangerous settings never execute from one tap;
- [ ] deletion tests cover expired/reused/wrong-name/permission-failure cases.

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
