# GitDock — Test Matrix

Last updated: 2026-09-11

Purpose: acceptance and regression matrix for GitDock. A checked item means direct automated coverage or an explicitly verified CI gate exists. Unchecked items remain future roadmap work.

## Universal quality gates

Every implementation-bearing branch/PR must pass:

- [x] Python 3.12 CI.
- [x] Python 3.13 CI.
- [x] `ruff format --check .`.
- [x] `ruff check .`.
- [x] `mypy gitdock` strict configuration.
- [x] `pytest`.
- [x] `python -m compileall -q gitdock`.
- [x] `pip-audit -r requirements.txt`.
- [x] `detect-secrets` scan.
- [x] PEP 751 runtime-lock regeneration/diff for each supported Python version.
- [x] PostgreSQL 17 Alembic upgrade → downgrade → upgrade.

P4.2 implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518`, CI `34647181024`:

- **165 tests passed** on Python 3.12 and 3.13.
- mypy clean on **94 source files**.
- Ruff reported **157 files already formatted** and lint clean.
- `pip-audit`: no known runtime vulnerabilities.
- secret scan: no findings.
- PEP 751 locks reproduced byte-for-byte.
- PostgreSQL migration round-trip passed through `0006_file_write_sessions`.

Known warning-only debt:

- Starlette/FastAPI TestClient deprecation toward httpx2.
- AnyIO `BlockingPortal` alias deprecation through Starlette.
- Alembic `prepend_sys_path` warning because `path_separator` is not explicit.

## P1 — foundation

- [x] settings validation/fail-closed startup behavior.
- [x] health/readiness routes.
- [x] Telegram owner middleware.
- [x] polling/webhook bootstrap.
- [x] fresh Router per Dispatcher regression.
- [x] async DB foundation and migration smoke coverage.
- [x] redaction tests.

## P2.1 — GitHub App auth

- [x] App JWT creation/claims.
- [x] installation-token lifecycle/cache.
- [x] OAuth state entropy/digest/expiry/one-time consumption.
- [x] PKCE S256.
- [x] encrypted durable credential abstraction.
- [x] setup/install identity validation under App and authenticated-user contexts.
- [x] suspended/conflicting installation rejection.
- [x] capability → permission mapping.

## P2.2 — GitHub gateway

- [x] canonical GitHub API headers/version/User-Agent.
- [x] typed response/page/rate metadata.
- [x] safe status/error mapping without raw-body echo.
- [x] canonical-host pagination.
- [x] external/credential-bearing/non-HTTPS/protocol-relative/fragment target rejection.
- [x] pagination loop/page-limit guards.
- [x] GET/HEAD bounded transient retry.
- [x] write-like methods no retry by default.
- [x] redirects are not automatically followed.
- [x] P4.1 Contents endpoint contracts.
- [x] P4.2 branch/commit/compare/create-ref endpoint contracts.
- [x] P4.2 create-ref transient failure produces one POST only.
- [x] compare refs containing slash are percent-encoded on the raw HTTP path.

## P2.3 — installed repository read

- [x] connected/disconnected Home.
- [x] installed repository list/filter/page.
- [x] compact stable repository callbacks.
- [x] invalid/stale callback fails closed.
- [x] cache scoped to user/installation.
- [x] repository detail re-fetch from GitHub.
- [x] repository cache never acts as authorization proof.

## P3.1 — public repository search

- [x] public search without installation.
- [x] query validation.
- [x] sorting/filtering/pagination.
- [x] opaque active search-session callbacks.
- [x] stale search session rejection.
- [x] public results isolated from installed repository authorization/cache state.
- [x] detail re-fetch.
- [x] Home/start clears transient search FSM state.

## P3.2 — durable GitHub user authorization

- [x] authenticated `/user` identity resolution.
- [x] standalone OAuth authorization without reinstalling App.
- [x] encrypted access/refresh persistence.
- [x] expiry-aware refresh/rotation.
- [x] `credential_generation` stale-concurrency protection.
- [x] restart-safe pending confirmation storage.
- [x] local disconnect preview/confirm.
- [x] stale/expired/reused/cancelled confirmation does nothing.
- [x] local disconnect removes local state only and never claims remote App uninstall.

## P3.3 — repository administration

- [x] personal create.
- [x] organization-create gateway/service path.
- [x] rename/description/visibility/archive/default-branch update.
- [x] Tier 2 settings confirmation.
- [x] Tier 3 exact-name delete confirmation.
- [x] update/delete repository-scoped `administration: write`.
- [x] edit/back/cancel consumes authority.
- [x] stale/reused/expired/wrong-target confirmation rejection.
- [x] uncertain create/update/delete reconciliation.
- [x] no blind replay of repository-admin writes.
- [x] safe audit rows without credentials/raw auth bodies.

## P4.1 — file browser and stale-safe one-file writes

Read path:

- [x] directory listing/pagination.
- [x] parent navigation.
- [x] branch/tag/SHA selection for reads.
- [x] UTF-8 preview pagination.
- [x] binary/large/missing-inline-content fallback.
- [x] bounded download.
- [x] long paths remain server-side; callbacks stay compact.

Write path:

- [x] create text file.
- [x] upload/create-or-replace document.
- [x] edit/replace existing file.
- [x] delete file.
- [x] preview/diff before execution.
- [x] durable staged write survives process restart long enough for review.
- [x] staged content digest/Git blob integrity validation.
- [x] stage TTL and content scrubbing.
- [x] same-target staging supersedes older authority.
- [x] create requires target absence.
- [x] update/delete require exact file SHA.
- [x] exact branch-head SHA precondition.
- [x] archived repository write rejection.
- [x] normal writes use repository-scoped `contents: write`.
- [x] workflow paths additionally require `workflows: write`.
- [x] write request issued once.
- [x] uncertain outcome reconciles remote file state instead of replay.
- [x] audit excludes body bytes/credentials.

## P4.2 — branch/commit tools — verified implementation

### Branch reads/search

- [x] list branches from GitHub.
- [x] branch parser validates required shape/SHA.
- [x] search/filter branches case-insensitively.
- [x] compact branch/commit callback context round-trips under Telegram callback limit.

### Branch create

- [x] create branch from explicit known base ref/SHA.
- [x] base ref resolves to concrete commit SHA before preview.
- [x] no external write occurs during preview/planning.
- [x] persisted one-time confirmation binds repository + target branch + base ref + base SHA.
- [x] branch create is Tier 1.
- [x] duplicate target branch rejected before write.
- [x] missing base ref rejected before write.
- [x] moved base SHA after preview returns stale without write.
- [x] target absence rechecked at confirm time.
- [x] repository-scoped `contents: write` requested only at execution.
- [x] create-ref request body uses exact `refs/heads/<branch>` + expected SHA.
- [x] create-ref write is issued once; transport does not retry POST.
- [x] uncertain create reconciles by reading target branch rather than replaying POST.
- [x] exact target SHA after uncertain response proves applied.
- [x] unresolved target state remains `UNCERTAIN`.
- [x] cancel consumes confirmation and reuse does nothing.
- [x] audit records safe branch/base/SHA/result/request metadata only.
- [x] no force-push/force-update/branch-delete action exists in normal v1 UI.

### Commits/compare

- [x] recent commits from default ref.
- [x] recent commits from explicit branch/tag/SHA ref.
- [x] commit detail for requested SHA/ref.
- [x] commit summary/detail response parsing.
- [x] compare refs through canonical gateway.
- [x] compare refs with slash are raw-path encoded.
- [x] large comparison summary is bounded to 10 file rows while returned total file count remains visible.
- [x] canonical GitHub commit link rendering.

### P4.2 regression notes

- [x] Arabic/emoji UI retains strict linting globally; only the three intended P4.2 Telegram UI files ignore Ruff `RUF001` ambiguous-Unicode warnings.
- [x] contract test uses `httpx.URL.raw_path` for encoded path assertion because `.path` is decoded by httpx; production behavior remains percent-encoded.

## P4.3 — clone/setup/run assistant — future

- [ ] fresh clone commands.
- [ ] update-existing-clone commands.
- [ ] project stack inference from repository evidence.
- [ ] Windows PowerShell commands.
- [ ] Linux commands.
- [ ] macOS commands.
- [ ] quote paths safely per OS.
- [ ] label confidence/source of inference.
- [ ] never insert credentials/tokens.
- [ ] never execute repository/README/script instructions automatically.

## P5 — webhook/notification engine — future

- [ ] raw-body HMAC-SHA256 verification.
- [ ] delivery ID uniqueness/idempotency.
- [ ] forged signature rejection.
- [ ] durable event inbox/retry state.
- [ ] event normalization.
- [ ] repository/event notification preferences.
- [ ] duplicate delivery produces no duplicate Telegram message.

## P6 — Issues/PRs — future

- [ ] issue list/search/detail/comments.
- [ ] issue create/comment/close/reopen.
- [ ] PR list/detail/files/diff/reviews.
- [ ] PR comment/review.
- [ ] merge preview with current head/check state.
- [ ] stale-head protection for merge.
- [ ] audited PR writes.

## P7 — Actions/releases — future

- [ ] workflows/runs/jobs/steps.
- [ ] log truncation/document fallback.
- [ ] artifact metadata/download.
- [ ] dispatch with workflow/ref/inputs review.
- [ ] rerun/cancel where authorized.
- [ ] release list/latest/assets.
- [ ] never expose Actions secrets.

## P8 — ZIP/project synchronization — future

- [ ] archive traversal/absolute/link/device rejection.
- [ ] file-count/depth/uncompressed-size limits.
- [ ] duplicate normalized-path detection.
- [ ] secret-like warnings.
- [ ] base commit snapshot.
- [ ] added/modified/deleted/unchanged plan.
- [ ] stale base rejection/replan.
- [ ] review branch by default.
- [ ] coherent tree/commit apply.
- [ ] optional PR.
- [ ] workspace cleanup.
- [ ] no silent default-branch mass overwrite.

## P9 — production hardening — future

- [ ] backup/restore drill.
- [ ] systemd/reverse proxy/HTTPS runbook.
- [ ] log/data retention.
- [ ] credential-key rotation runbook.
- [ ] end-to-end live checklist.
- [ ] rate-limit/replay/restart tests.
- [ ] full security/dependency review.

## Matrix rule

Do not check a row because a nearby behavior “probably covers it.” Add direct regression coverage where the row is material to acceptance or safety. Do not weaken CI gates to obtain green status.
