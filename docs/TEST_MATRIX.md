# GitDock — Test Matrix

Status: authoritative quality expectations. Concrete tool commands are finalized in P1.

P3.1 implementation verification reference: GitHub Actions run `33453960817` passed the current suite on Python 3.12, Python 3.13, and the PostgreSQL 17 migration job. The suite now contains **83 tests**. P3.1 adds public repository-search REST contracts, query/filter/service validation, search UI/callback coverage, active-session context isolation, and transient-navigation-state coverage on top of the P2.3 suite. Checkmarks below remain conservative: a box is marked only where the current suite directly exercises that requirement.

## 1. Test layers

### Unit

Fast, no real network, normally no real database unless the unit is persistence-specific.

Targets:

- domain rules;
- risk classification;
- callback encoding/decoding;
- renderers;
- keyboard builders;
- input/path validation;
- archive safety primitives;
- sync plan calculation;
- permission/capability mapping;
- error translation;
- command generation templates.

### Integration

Exercise boundaries together using controlled infrastructure/fixtures:

- SQLAlchemy repositories + test DB;
- Alembic migrations;
- FastAPI routes;
- aiogram handler/service wiring;
- DB-backed confirmation lifecycle;
- DB-backed webhook inbox/worker;
- filesystem temporary workspace behavior.

### GitHub contract/mock integration

No dependence on a live mutable GitHub account for the normal suite.

Use recorded/constructed GitHub API fixtures or mock HTTP transport to verify:

- request method/path/body/headers;
- pagination;
- token-context selection;
- permission failures;
- rate-limit responses;
- validation errors;
- stale SHA/conflict responses;
- retry-safe transient errors;
- uncertain write outcomes where relevant.

### Live smoke

Manual/controlled tests against a dedicated GitHub test repository and test bot/account. Required before production release for high-risk API behavior, but not on every unit CI run.

Never use an important production repository as the first destructive test target.

## 2. Universal feature checklist

Every feature should consider:

- [ ] authorized success
- [ ] unauthorized Telegram user
- [ ] invalid user input
- [ ] empty state
- [ ] GitHub not connected
- [ ] installation does not include repo
- [ ] missing GitHub permission
- [ ] GitHub not found
- [ ] GitHub validation error
- [ ] rate limit
- [ ] transient network/API error
- [ ] stale callback/session
- [ ] Telegram edit/send failure where relevant
- [ ] audit behavior for writes
- [ ] secret redaction in errors/logs

Not every box applies to every read-only helper; document exclusions sensibly.

## 3. Configuration/startup

- [x] missing Telegram token fails closed with clear configuration error.
- [x] missing owner ID fails closed in owner-only mode.
- [x] malformed database URL handled.
- [x] GitHub App configuration validation.
- [ ] private key load failure does not dump key content.
- [x] production mode refuses obviously unsafe/missing webhook secrets where required.
- [x] `/health` returns no secret data.
- [x] readiness reflects DB/config dependency status.

## 4. Telegram authorization/navigation

- [x] owner command accepted.
- [x] non-owner command ignored/rejected per policy.
- [x] non-owner callback blocked.
- [ ] stale callback version rejected safely beyond current parser rejection coverage.
- [x] repository callback short ID resolves only inside intended GitDock user/installation context.
- [x] repository callback cannot cross GitDock users in the current service integration test.
- [x] repository detail callback carries back page/filter context and generated callback stays within Telegram's 64-byte limit.
- [ ] Cancel invalidates active operation/confirmation.
- [x] Home/read-only navigation does not apply repository writes.
- [x] `/start` and Home clear transient FSM search state so later messages cannot be interpreted as abandoned search input.
- [ ] repeated callback does not duplicate completed write; not applicable to P2.3/P3.1 because they are read-only.

P2.3 UI unit coverage additionally verifies that a 200-character repository name is not embedded in callback payloads and that repository callbacks round-trip with a maximum signed 64-bit repository ID while remaining within Telegram's callback size limit.

P3.1 UI/context coverage verifies compact search callbacks, active-session isolation, result-context lookup, and Home/start cancellation of transient search state.

## 5. GitHub authentication

### Installation token

- [x] JWT generation with configured app identity.
- [x] installation token request success.
- [x] cached token reused only while valid.
- [x] near-expiry token refreshed.
- [ ] expired token path refreshes/retries appropriately.
- [ ] suspended/deleted installation handled end-to-end through a live GitHub response.
- [x] repository callback outside the current GitDock user's cached/installation context is rejected cleanly.

Additional P2.1/P2.3 contract coverage:

- [x] GitHub REST API version header is sent by the auth client.
- [x] installation token parsing does not assume legacy token length/format.
- [x] installation token cache is scoped by requested permissions/repository IDs.
- [x] repository detail requests a token narrowed to the selected repository ID.
- [x] spoofed setup/install candidate identity is rejected before database binding.
- [x] installation binding persists only after app-context and authenticated-user-context identity match.
- [x] actual FastAPI setup/OAuth callback routes are registered and exercise safe success/error paths.

### User authorization

- [x] state is high entropy/opaque and raw state is not persisted.
- [x] state bound to GitDock user/flow context.
- [x] state expires.
- [x] state one-time use.
- [x] wrong flow/state context rejected without consuming a valid state.
- [x] callback/OAuth code and authentication error bodies are not echoed into application errors/logs.
- [x] PKCE S256 challenge/verifier lifecycle verified.
- [x] PKCE verifier encrypted before persistence.
- [x] token encrypted before persistence.
- [x] access and refresh token expiry metadata preserved by the credential store.
- [x] credential encryption supports old-key decryption/new-key encryption for rotation.
- [ ] disconnect removes/invalidates local credential state safely through an end-user flow.

## 5.1 GitHub gateway foundation — P2.2

Implemented contract/mock coverage:

- [x] canonical `Accept`, GitHub API version, and `User-Agent` headers are sent.
- [x] optional bearer authorization header is injected without exposing the token through result representations.
- [x] typed response parsing succeeds for expected JSON shapes.
- [x] invalid/unexpected JSON response shape is converted to a stable unexpected-gateway error rather than leaking payload content.
- [x] keyed and plain-list pagination payloads are supported by the gateway page parser.
- [x] `Link` pagination follows a validated `api.github.com` next URL and does not reuse first-page query parameters on later pages.
- [x] hostile external-host pagination URLs are rejected before network I/O.
- [x] credential-bearing and scheme-relative pagination targets are rejected.
- [x] rate-limit headers are captured into typed metadata.
- [x] `403` rate-limit exhaustion is distinguished from an ordinary permission denial.
- [x] common GitHub HTTP failures map to stable authentication/permission/not-found/conflict/validation categories.
- [x] translated GitHub errors do not echo raw response-body token-like values.
- [x] transient safe `GET` requests retry with bounded exponential backoff.
- [x] write requests are not retried by default.
- [x] explicitly declared safe operations can opt into retry behavior.
- [x] P2.2/P2.3/P3.1 keep `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff green.

Deferred intentionally to later feature milestones:

- live mutable GitHub API smoke tests;
- ETag/conditional request behavior if introduced;
- artifact/release redirect/download host policy;
- operation-specific reconciliation for uncertain write outcomes.

## 6. Repository list/dashboard/search

### P2.3 repository list/dashboard — verified implementation coverage

- [x] installed-repository payload parsed into typed repository snapshots.
- [x] pagination stable at the application service boundary.
- [x] private/public metadata rendered correctly.
- [x] archived/source/fork metadata and filters implemented.
- [x] default branch/language/stars/forks/update metadata rendered where available.
- [x] very long repository names do not break callback limits and are not embedded in callback payloads.
- [x] empty/disconnected home/repository state has a safe renderer/service path.
- [x] repository detail resolves compact ID only inside the same GitDock user context.
- [x] repository detail requests a repository-scoped installation token and re-fetches GitHub before render.
- [x] repositories removed from the installation are pruned from local callback cache on refresh.
- [x] repository cache is non-authoritative and contains no credential fields.
- [x] filter coverage includes private and the filter implementation covers public/active/archived/source/fork branches.
- [x] GitHub gateway rate-limit category has a safe user-facing repository renderer mapping.
- [x] stale repository selection has a safe user-facing state.

### P3.1 search — verified implementation coverage

- [x] search query validation and normalization.
- [x] typed search payload parsing covers repository metadata used by UI/service.
- [x] sort by stars.
- [x] sort by update.
- [x] language/min-star/`user:`/`org:` owner/topic filters.
- [x] archived search visibility filter.
- [x] search no-results state.
- [x] public search pagination.
- [x] public/anonymous search path does not require a bound installation token.
- [x] search detail resolves only through the current active search result context, then re-fetches GitHub detail.
- [x] older search-session callbacks fail closed when a newer session is active.
- [x] search callbacks remain compact/versioned and within Telegram's callback size limit in UI coverage.
- [x] search session/result context is kept separate from installed `repositories_cache` by design/service boundary.
- [x] P3.1 remains Tier 0 read-only and adds no repository write path.
- [x] download-command button is intentionally only a placeholder; clone/setup/run generation remains tested/implemented under P4.3, not P3.1.

## 7. Repository administration

### Create

- [ ] valid private repository creation.
- [ ] valid public repository creation.
- [ ] duplicate/invalid name rejection.
- [ ] missing user authorization.
- [ ] missing Administration permission.
- [ ] preview does not create before confirm.
- [ ] repeated confirm does not create duplicates.
- [ ] audit result records repository id/name.

### Rename/settings/visibility/archive

- [ ] exact target shown.
- [ ] Tier 2 confirmation required where applicable.
- [ ] expired/reused confirmation rejected.
- [ ] GitHub-side conflict/validation handled.
- [ ] local cache refreshed after success.

### Delete

- [ ] wrong typed repo name rejected.
- [ ] normalized exact correct name accepted to final stage.
- [ ] final confirmation required.
- [ ] confirmation expires.
- [ ] reused confirmation rejected.
- [ ] repo changed/unavailable before delete handled.
- [ ] missing admin permission handled.
- [ ] uncertain network result reconciled before claiming failure/success where possible.
- [ ] audit record contains no credentials.

## 8. File browser/read

- [ ] directory listing.
- [ ] nested navigation.
- [ ] branch/ref switch.
- [ ] UTF-8 preview.
- [ ] large text pagination/truncation.
- [ ] binary detection/fallback.
- [ ] not found.
- [ ] invalid/traversal path rejected before API call.
- [ ] long path uses short callback context.

## 9. Single-file writes

- [ ] create text file.
- [ ] update text file using expected SHA.
- [ ] replace file upload.
- [ ] delete file.
- [ ] preview/diff before write.
- [ ] stale source SHA blocks overwrite.
- [ ] wrong branch/ref blocked.
- [ ] workflow path requires Workflows capability.
- [ ] same-path conflicting operations serialized/rejected.
- [ ] write audit record.
- [ ] secret/token content not leaked into logs.

## 10. Branch/commit tools

- [ ] list/search branches.
- [ ] create branch from known base.
- [ ] duplicate branch handling.
- [ ] base ref not found.
- [ ] recent commit list.
- [ ] commit detail.
- [ ] compare refs.
- [ ] large diff summary behavior.

No normal v1 test exists for force-update because the normal UI must not expose it.

## 11. Clone/setup/run command generation

- [ ] Python requirements project.
- [ ] Python pyproject project.
- [ ] Node/npm.
- [ ] pnpm.
- [ ] yarn.
- [ ] Docker.
- [ ] Gradle.
- [ ] Maven.
- [ ] ambiguous multi-stack repository.
- [ ] no recognized project metadata -> honest fallback.
- [ ] Windows PowerShell quoting.
- [ ] Linux shell quoting.
- [ ] macOS shell quoting.
- [ ] no access token embedded.
- [ ] malicious README command is not promoted to automatic trusted command.

## 12. Webhook security/ingestion

- [ ] valid `X-Hub-Signature-256` accepted.
- [ ] missing signature rejected.
- [ ] invalid signature rejected.
- [ ] body modification invalidates signature.
- [ ] duplicate delivery ID accepted idempotently/no duplicate notification.
- [ ] unsupported event safely ignored/recorded according to policy.
- [ ] valid delivery persisted before worker processing.
- [ ] simulated restart after persist resumes processing.
- [ ] retry counter/state transitions.
- [ ] terminal malformed payload does not loop forever.
- [ ] raw private payload not dumped into normal logs.

## 13. Event normalization/notifications

Each enabled event family needs fixture coverage:

- [ ] push
- [ ] issues
- [ ] issue_comment
- [ ] pull_request
- [ ] pull_request_review
- [ ] pull_request_review_comment
- [ ] workflow_run
- [ ] release
- [ ] star
- [ ] fork
- [ ] installation
- [ ] installation_repositories

For each relevant event:

- [ ] canonical model values correct;
- [ ] muted event not sent;
- [ ] muted repository not sent;
- [ ] notification button points to correct GitDock resource flow;
- [ ] duplicate delivery not resent.

## 14. Issues

- [ ] list/filter/pagination.
- [ ] detail + comments.
- [ ] create issue.
- [ ] comment.
- [ ] close/reopen.
- [ ] labels/assignees.
- [ ] permission denial.
- [ ] stale/closed state changes between view and action.
- [ ] audit writes.

## 15. Pull requests

- [ ] list/detail.
- [ ] changed files.
- [ ] diff pagination/large diff.
- [ ] comments/review threads.
- [ ] comment/reply.
- [ ] approve.
- [ ] request changes.
- [ ] merge confirmation.
- [ ] merge with failing/pending checks is surfaced.
- [ ] head SHA changes before merge -> revalidation.
- [ ] merge denied by branch protection/rules handled.
- [ ] repeated merge callback idempotent/clear.
- [ ] audit writes.

## 16. GitHub Actions

- [ ] workflow list.
- [ ] run list/detail.
- [ ] jobs/steps.
- [ ] log truncation/document fallback.
- [ ] artifacts metadata.
- [ ] dispatch requires Actions write permission.
- [ ] dispatch shows workflow/ref/inputs.
- [ ] invalid required input handling.
- [ ] retry failed jobs/run.
- [ ] already-running/completed state changes handled.
- [ ] notification -> logs/retry navigation.
- [ ] no secret output added by GitDock itself.
- [ ] audit write operations.

## 17. ZIP/project sync archive safety

Malicious fixtures must include:

- [ ] `../` traversal.
- [ ] absolute path.
- [ ] Windows drive path.
- [ ] excessive depth.
- [ ] excessive file count.
- [ ] excessive uncompressed size.
- [ ] duplicate normalized path.
- [ ] symlink.
- [ ] hardlink/special file where archive format permits.
- [ ] NUL/invalid path edge where library exposes it.
- [ ] nested secret-like file.

All unsafe cases must fail before repository writes.

## 18. ZIP/project sync planning

- [ ] all unchanged.
- [ ] only additions.
- [ ] only modifications.
- [ ] deletions.
- [ ] rename-like change represented correctly as Git tree outcome.
- [ ] mixed change set.
- [ ] binary file.
- [ ] large text file.
- [ ] ignored/excluded files.
- [ ] base commit recorded.
- [ ] totals match detailed lists.
- [ ] displayed plan matches immutable persisted plan.

## 19. ZIP/project sync apply

- [ ] review branch created by default.
- [ ] coherent single commit for batch.
- [ ] optional PR created.
- [ ] stale base commit blocks/replans.
- [ ] existing target review branch collision handled safely.
- [ ] partial GitHub API failure reconciled.
- [ ] cancellation before apply writes nothing.
- [ ] expired session writes nothing.
- [ ] workspace removed after success.
- [ ] workspace removed after cancel.
- [ ] workspace cleanup after failure/TTL.
- [ ] Tier 2 direct-main exception requires dedicated confirmation.
- [ ] audit captures resulting commit/PR.

## 20. Logging/redaction

Inject fake secrets and verify they do not appear in captured logs:

- [x] Telegram bot token/redaction baseline.
- [x] Authorization Bearer header.
- [x] GitHub token-shaped values/credential-key fields.
- [x] client-secret keyed values.
- [x] OAuth code.
- [x] PKCE verifier/state keyed values.
- [x] general GitHub gateway error translation does not echo token-like response-body text.
- [x] P2.3 setup/OAuth error pages avoid rendering OAuth code/token/raw upstream error material.
- [ ] private key marker/body fixture.

## 21. Migrations

For every schema migration:

- [x] clean upgrade from base in automated test/CI coverage.
- [x] upgrade from previous schema through the current Alembic chain including P2.3 `0003`.
- [ ] explicit schema-assertion coverage for every expected index/unique constraint.
- [ ] explicit non-destructive data-preservation fixture for upgrade/downgrade.
- [x] downgrade tested for the current migration chain.
- [x] PostgreSQL behavior validated in PostgreSQL 17 CI.

## 22. Live smoke checklist — dedicated test resources

Before production-grade release:

- [ ] connect GitHub App against the dedicated live test account/repository.
- [ ] list private test repository.
- [ ] verify P2.3 Telegram pagination/filter/detail against live GitHub test data.
- [ ] verify P3.1 public search/query/filter/detail against live public GitHub data.
- [ ] create test repository.
- [ ] rename/description update.
- [ ] create branch.
- [ ] create/update/delete test file.
- [ ] issue create/comment/close.
- [ ] PR read/comment/review on dedicated test PR.
- [ ] workflow dispatch on harmless test workflow.
- [ ] receive push/comment/workflow webhook notifications.
- [ ] upload safe sample ZIP and create review PR.
- [ ] verify delete flow only on disposable test repository.
- [ ] restart service with a queued webhook and confirm recovery.

## 23. Known non-blocking test-tool warnings

CI run `33453960817` is green but reports:

- Starlette/FastAPI `TestClient` deprecation warning for the current `httpx` integration/future `httpx2` direction.
- Alembic deprecation warning because `alembic.ini` does not yet set explicit `path_separator` for `prepend_sys_path`.

These warnings are recorded maintenance debt. They are not test failures and must not be silently forgotten.

## 24. Release gate

A release cannot be called production-ready while known applicable mandatory tests in this matrix are absent or failing. `docs/CURRENT_STATUS.md` must state any intentionally deferred test category.
