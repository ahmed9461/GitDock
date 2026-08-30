# GitDock — Test Matrix

Status: authoritative quality expectations. Concrete tool commands are finalized in P1.

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

- [ ] missing Telegram token fails closed with clear configuration error.
- [ ] missing owner ID fails closed in owner-only mode.
- [ ] malformed database URL handled.
- [ ] GitHub App configuration validation.
- [ ] private key load failure does not dump key content.
- [ ] production mode refuses obviously unsafe/missing webhook secrets where required.
- [ ] `/health` returns no secret data.
- [ ] readiness reflects DB/config dependency status.

## 4. Telegram authorization/navigation

- [ ] owner command accepted.
- [ ] non-owner command ignored/rejected per policy.
- [ ] non-owner callback blocked.
- [ ] stale callback version rejected safely.
- [ ] callback short ID resolves only inside intended user/session context.
- [ ] callback cannot cross users in future multi-user tests.
- [ ] Back returns to correct parent state.
- [ ] Cancel invalidates active operation/confirmation.
- [ ] Home resets navigation safely without applying pending writes.
- [ ] repeated callback does not duplicate completed write.

## 5. GitHub authentication

### Installation token

- [ ] JWT generation with configured app identity.
- [ ] installation token request success.
- [ ] cached token reused only while valid.
- [ ] near-expiry token refreshed.
- [ ] expired token path refreshes/retries appropriately.
- [ ] suspended/deleted installation handled.
- [ ] repo outside installation rejected cleanly.

### User authorization

- [ ] state is high entropy/opaque.
- [ ] state bound to Telegram user.
- [ ] state expires.
- [ ] state one-time use.
- [ ] wrong state rejected.
- [ ] callback code not logged.
- [ ] token encrypted before persistence.
- [ ] disconnect removes/invalidates local credential state safely.

## 6. Repository list/dashboard/search

- [ ] pagination stable.
- [ ] public/private/archive/fork metadata rendered correctly.
- [ ] very long repository names do not break callback limits.
- [ ] empty repository list.
- [ ] inaccessible repository disappears/errors correctly after installation change.
- [ ] search query validation.
- [ ] sort by stars.
- [ ] sort by update.
- [ ] language/min-star/owner/topic filters.
- [ ] archived filter.
- [ ] no-results state.
- [ ] rate-limit state.

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

- [ ] Telegram bot token.
- [ ] Authorization Bearer header.
- [ ] GitHub user token.
- [ ] installation token.
- [ ] client secret.
- [ ] webhook secret.
- [ ] OAuth code.
- [ ] private key marker/body.

## 21. Migrations

For every schema migration:

- [ ] clean upgrade from base.
- [ ] upgrade from previous released schema.
- [ ] expected indexes/unique constraints.
- [ ] no accidental data loss.
- [ ] downgrade tested when migration policy supports it.
- [ ] PostgreSQL behavior validated before production release.

## 22. Live smoke checklist — dedicated test resources

Before production-grade release:

- [ ] connect GitHub App.
- [ ] list private test repository.
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

## 23. Release gate

A release cannot be called production-ready while known applicable mandatory tests in this matrix are absent or failing. `docs/CURRENT_STATUS.md` must state any intentionally deferred test category.