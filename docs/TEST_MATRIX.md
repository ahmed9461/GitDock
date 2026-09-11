# GitDock — Test Matrix

Status: authoritative quality expectations, updated through P4.1 implementation verification.

P4.1 implementation reference: final implementation head before documentation synchronization `614f013b35644fcdd05e880c9a37ff30fd503fdf`, GitHub Actions run `34639736010` fully green on Python 3.12, Python 3.13, and PostgreSQL 17. The suite contains **148 tests** and mypy verifies **87 source files**. Checkmarks indicate direct current coverage, not merely intended behavior.

## 1. Test layers

### Unit

Fast tests for domain rules, risk/confirmation rules, callback encoding/decoding, renderers/keyboards, input/path/ref validation, permission mapping, safe error translation, credential encryption helpers, repository/file administration UI helpers, and later command-generation templates.

### Integration

Controlled boundary tests for SQLAlchemy + test DB, Alembic, FastAPI routes, aiogram service wiring, DB-backed OAuth/confirmation lifecycle, repository read/admin/file services/cache/audit, durable staged file-write state, uncertain-write reconciliation, and later webhook/workspace persistence.

### GitHub contract/mock integration

Use constructed responses/MockTransport rather than a live mutable account for normal CI. Verify method/path/headers/body, parsing, pagination, token context, permissions, rate limits, validation failures, retry policy, write no-retry behavior, and safe error handling.

### Live smoke

Manual/controlled tests against dedicated GitHub test resources before production use of high-risk behaviors. Never use an important production repository as the first destructive target.

## 2. Universal feature checklist

Every feature considers, where applicable:

- [x] authorized success for implemented P0-P4.1 paths
- [x] unauthorized Telegram user baseline
- [x] invalid user input on implemented forms
- [x] empty/disconnected state on implemented read/account paths
- [x] missing installation/repository access on implemented repository paths
- [x] missing GitHub permission on implemented repository-admin/file paths
- [x] not found/inaccessible on implemented gateway paths
- [x] GitHub validation failure on implemented gateway/admin/file paths
- [x] rate-limit/transient translation in gateway foundation
- [x] stale callback/session/precondition on implemented search/auth/admin/file paths
- [ ] Telegram edit/send failure injection for every newer UI path
- [x] audit behavior for P3.3/P4.1 GitHub writes
- [x] secret redaction/security gates

Not every box applies to every read-only helper; exclusions must remain explicit rather than faked green.

## 3. Configuration/startup

- [x] missing Telegram token fails closed.
- [x] missing owner ID fails closed in owner-only mode.
- [x] malformed DB URL handled.
- [x] GitHub App configuration validation.
- [ ] private-key load failure does not dump key content through all live startup paths.
- [x] production webhook secret requirements validated where configured.
- [x] `/health` contains no secret data.
- [x] readiness reflects DB/config dependencies.

## 4. Telegram authorization/navigation

- [x] owner command accepted.
- [x] non-owner command ignored/rejected by policy.
- [x] non-owner callback blocked.
- [x] compact repository callback parser rejects malformed context and service scopes repository to current GitDock user/installation.
- [x] cross-user repository callback rejected.
- [x] repository detail callback remains within Telegram 64-byte limit including large repository ID context.
- [x] long repository name is not embedded in callback payload.
- [x] P3.1 search callbacks are active-session scoped and stale session fails closed.
- [x] `/start` and Home clear transient search FSM state.
- [x] P3.2 account/local-disconnect callbacks remain compact and one-time.
- [x] P3.2 Cancel/Home invalidates outstanding disconnect authority.
- [x] P3.3 create/update/delete confirmation callbacks round-trip within Telegram callback-data limits.
- [x] P3.3 repository settings callbacks use compact repository IDs + navigation context rather than full repository names.
- [x] P3.3 create edit/cancel and update/delete back/cancel consume the persisted write confirmation.
- [x] repeated P3.3 cancellation is one-time and cannot leave the confirmation executable.
- [x] P4.1 file callbacks remain within Telegram callback-data limits while long repository paths stay server/FSM-side.
- [x] P4.1 stale browse-session context fails closed rather than resolving arbitrary path data from callback input.
- [ ] generic stale callback-version rejection beyond currently implemented parser namespaces.

## 5. GitHub authentication

### Installation token

- [x] App JWT generated with configured identity/RS256.
- [x] installation token request success.
- [x] GitHub REST API version header sent by auth client.
- [x] token parsing does not assume legacy fixed length.
- [x] cache scoped by requested permissions/repository IDs.
- [x] cached token reused only while safely valid.
- [x] near-expiry token refreshed.
- [x] repository detail requests repository-scoped installation token.
- [x] P3.3 update/delete request repository-scoped installation token with `administration: write`.
- [x] P4.1 browse requests repository-scoped `contents: read` authority.
- [x] P4.1 ordinary one-file writes request repository-scoped `contents: write` authority.
- [x] P4.1 `.github/workflows/*` writes require `workflows: write` in addition to the contents-write path.
- [x] spoofed setup/install candidate identity rejected before DB binding.
- [x] installation binding persists only after App-context/authenticated-user-context identity match.
- [x] FastAPI setup/OAuth callback routes have safe success/error paths.
- [ ] deleted/suspended installation end-to-end behavior against real GitHub response.

### OAuth state / PKCE foundation

- [x] state opaque/high entropy and raw state not persisted.
- [x] state bound to GitDock user/flow.
- [x] state expires and is one-time use.
- [x] wrong-flow/state context rejected safely.
- [x] state consumption remains restart-safe/DB-backed.
- [x] OAuth code/auth response secrets are not echoed by local auth exceptions.
- [x] PKCE S256 lifecycle verified.
- [x] PKCE verifier encrypted before persistence.
- [x] credential encryption supports versioned key rotation.

### P3.2 durable user authorization / refresh

- [x] authenticated `/user` request uses user bearer context and resolves typed GitHub identity.
- [x] standalone authorization reuses state + PKCE without reinstalling App.
- [x] access/refresh tokens encrypted before DB persistence; expiry preserved.
- [x] credential generation increments on persist/clear.
- [x] durable account status separates authorization from installation count.
- [x] still-valid access token returns without refresh.
- [x] near-expiry token uses refresh grant and persists rotated pair.
- [x] stale concurrent generation prevents refresh result from overwriting newer state.
- [x] missing/expired durable credentials produce reauthorization-required path.
- [x] raw refresh/token-like values absent from user-facing errors.

### P3.3 create user context

- [x] personal repository creation obtains durable GitHub user authorization.
- [x] organization repository creation uses durable user context and canonical organization endpoint.
- [x] missing durable user authorization fails before a repository create write.
- [x] create flow does not substitute a broad PAT or repository installation token for user-context creation.

## 6. Durable confirmation/storage

### P3.2 local disconnect

- [x] confirmation DB-backed rather than FSM-only.
- [x] opaque token stored only as digest.
- [x] confirmation bound to user + operation, expiry enforced, single-use.
- [x] target fingerprint includes account/generation/current installation IDs.
- [x] reauthorization/install-set change makes old confirmation stale.
- [x] Home/Cancel consumes pending local-disconnect confirmation.
- [x] successful local disconnect clears only GitDock-local credential/binding/cache/pending state.
- [x] legacy installation-only state can disconnect safely.
- [x] UI says local disconnect does not uninstall GitHub App remotely.

### P3.3 repository administration

- [x] create confirmation is Tier 1 and persisted.
- [x] update confirmation is Tier 2 and persisted.
- [x] delete confirmation is Tier 3 and persisted.
- [x] create/update/delete confirmations are user/operation-bound, expiring, single-use, and target-fingerprinted.
- [x] create/update/delete confirmation cancellation is server-side and one-time.
- [x] cancelled confirmation cannot execute later from an old Telegram button.
- [x] reused confirmation rejected.
- [x] malformed/stale payload fails closed.

### P4.1 staged one-file writes

- [x] `file_write_sessions` state is DB-backed and migration `0006_file_write_sessions` is verified.
- [x] staged intent binds user, repository/installation, branch/path, branch-head SHA, expected file SHA where applicable, desired/content digests, operation, risk tier, nonce/version, expiry, and commit message.
- [x] staged create/update content survives restart long enough for reviewed confirmation.
- [x] staged file bytes are cleared when consumed.
- [x] staged file bytes are cleared when cancelled.
- [x] expired/pruned staged sessions clear file bytes.
- [x] a newer same user/repository/branch/path staging consumes the older authority and clears its bytes.
- [x] the old same-path confirmation token becomes unusable; the newest staging remains consumable.

## 7. GitHub gateway foundation and typed feature gateways

- [x] canonical `Accept`, API version, `User-Agent` headers.
- [x] optional bearer injection without token leak through result representation.
- [x] typed response parsing and unexpected-shape errors.
- [x] safe canonical pagination and hostile target rejection.
- [x] rate-limit metadata and error categories.
- [x] raw token-like body absent from translated error.
- [x] bounded transient GET retry.
- [x] writes no retry by default.
- [x] explicitly safe operation can opt into retry.
- [x] P3.3 personal create endpoint contract.
- [x] P3.3 organization create endpoint contract.
- [x] P3.3 repository PATCH contract.
- [x] P3.3 repository DELETE contract including expected empty response.
- [x] repository-admin contract verifies write methods are not automatically replayed.
- [x] P4.1 Contents gateway directory/file/ref/write endpoint contracts.
- [x] P4.1 write contracts preserve no-blind-retry semantics.

Deferred: live mutable GitHub smoke, ETag behavior if introduced, artifact/release redirect policy.

## 8. Repository list/dashboard/search

### P2.3 installed repository read

- [x] typed installed-repository payload parsing.
- [x] stable pagination and private/public/archive/source/fork filters.
- [x] detail resolves only in same GitDock user context.
- [x] repository-scoped token + GitHub re-fetch before detail render.
- [x] removed repos pruned from callback cache.
- [x] cache contains no credential fields and is non-authoritative.
- [x] rate-limit/stale-selection user-facing states.

### P3.1 public search

- [x] validation, parsing, stars/update sort, language/min-star/user/org/topic/archive filters.
- [x] no-results, pagination, public path without installation.
- [x] current active search context + GitHub detail re-fetch.
- [x] older search session fails closed.
- [x] callbacks compact/versioned; public result context separate from installed cache.
- [x] Tier 0 read-only; download-command button remains P4.3 placeholder.

## 9. Repository administration — P3.3 verified

### Create

- [x] private/public request models and Telegram selection paths.
- [x] personal creation uses durable user context.
- [x] organization creation gateway/service path verified.
- [x] invalid name/input rejected before write.
- [x] missing durable user authorization handled.
- [x] preview does not create before persisted confirmation.
- [x] repeated confirm cannot duplicate creation.
- [x] success/failure/reconciliation audit uses safe metadata without credentials.

### Rename/settings/visibility/archive/default branch

- [x] exact target/current/request values retained in server-side plan.
- [x] Tier 2 persisted confirmation.
- [x] stale repository snapshot rejected before write.
- [x] scoped `administration: write` installation token used.
- [x] GitHub failure translated through safe gateway error path.
- [x] local repository cache refreshed after applied update.
- [x] Telegram name/description/default-branch input validation.
- [x] visibility and archive/unarchive are not one-tap writes; they pass through preview/confirmation.

### Delete

- [x] wrong typed full repo name rejected.
- [x] exact current `owner/name` reaches persisted final stage.
- [x] final Tier 3 persisted confirmation required.
- [x] confirmation expiry tested.
- [x] confirmation reuse rejected.
- [x] repository changed/unavailable before delete fails closed.
- [x] missing admin permission tested.
- [x] audit contains no credentials.
- [x] confirmed deletion removes repository cache row.

### Uncertain-write reconciliation

- [x] uncertain create error triggers remote reconciliation, not blind POST replay.
- [x] create matching remote state can be classified applied.
- [x] uncertain update error re-fetches and compares requested fields.
- [x] uncertain delete error checks whether target still exists.
- [x] unresolved uncertainty remains explicit rather than being mislabeled success/failure.
- [x] reconciliation outcomes are audited safely.

### Telegram administration UI

- [x] repository creation callbacks/keyboards/renderers.
- [x] repository settings callbacks/keyboards/renderers.
- [x] compact callback size/parse behavior.
- [x] Tier 2/Tier 3 preview keyboards.
- [x] delete isolated from harmless navigation.
- [x] stale/invalid confirmation copy does not claim a write happened.
- [x] cancellation callbacks encode operation/destination/token and consume authority server-side.

## 10. File browser/read — P4.1 verified implementation

- [x] directory listing/nested navigation.
- [x] directory pagination and parent navigation.
- [x] branch/ref switch.
- [x] UTF-8 preview.
- [x] text preview pagination.
- [x] binary fallback.
- [x] large/missing-content fallback.
- [x] bounded file download flow.
- [x] not-found handling.
- [x] traversal/invalid path rejected pre-network.
- [x] unsafe/invalid ref rejected.
- [x] long path uses short callback context rather than raw path callback data.

## 11. Single-file writes — P4.1 verified implementation

- [x] create text file.
- [x] upload/create document.
- [x] text update/edit.
- [x] document replace.
- [x] delete.
- [x] preview/diff before write.
- [x] branch-head/current file SHA preconditions.
- [x] stale SHA/head blocks overwrite/delete.
- [x] wrong/unsafe ref/path blocked.
- [x] workflow path requires Workflows capability.
- [x] same-path pending authority serialized by superseding the older staging.
- [x] same-path supersession regression test verifies old token invalid + staged bytes scrubbed.
- [x] write-like GitHub call is not blindly replayed.
- [x] uncertain create/update/delete outcome reconciled against current GitHub state.
- [x] audit write contains safe metadata only.
- [x] file body absent from audit/log metadata.
- [x] credentials/secrets absent from callbacks/audit/logs.

## 12. Branch/commit tools — P4.2 target

- [ ] list/search branches.
- [ ] create branch from known base.
- [ ] duplicate branch handling.
- [ ] missing base ref.
- [ ] recent commits.
- [ ] commit detail.
- [ ] compare refs.
- [ ] large diff summary.

No normal v1 force-update test because normal UI must not expose it.

## 13. Clone/setup/run generation — P4.3 target

- [ ] Python requirements/pyproject.
- [ ] Node/npm/pnpm/yarn.
- [ ] Docker.
- [ ] Gradle/Maven.
- [ ] ambiguous multi-stack.
- [ ] unknown metadata honest fallback.
- [ ] Windows/Linux/macOS quoting.
- [ ] no access token embedded.
- [ ] malicious README command not promoted to trusted automatic command.

## 14. Webhook security/ingestion — P5 target

- [ ] valid `X-Hub-Signature-256` accepted.
- [ ] missing/invalid signature rejected.
- [ ] body modification invalidates signature.
- [ ] duplicate delivery idempotent.
- [ ] unsupported event safe behavior.
- [ ] accepted event persisted before processing.
- [ ] restart resumes durable pending work.
- [ ] retry/terminal state transitions.
- [ ] malformed payload does not loop forever.
- [ ] private raw payload absent from normal logs.

## 15. Event normalization/notifications — P5 target

Fixture coverage required for push, issues, issue_comment, pull_request, pull_request_review, pull_request_review_comment, workflow_run, release, star, fork, installation, installation_repositories.

For relevant events verify normalized values, repository/event mute, correct navigation, and no duplicate resend.

## 16. Issues — P6 target

- [ ] list/filter/pagination.
- [ ] detail/comments.
- [ ] create/comment/close/reopen.
- [ ] labels/assignees.
- [ ] permission denial.
- [ ] stale state between view/action.
- [ ] audit writes.

## 17. Pull requests — P6 target

- [ ] list/detail/changed files/diffs.
- [ ] comments/review threads.
- [ ] comment/reply/approve/request changes.
- [ ] merge confirmation.
- [ ] failing/pending checks surfaced.
- [ ] head SHA change revalidation.
- [ ] branch protection/rule denial.
- [ ] repeated merge callback safe.
- [ ] audit writes.

## 18. GitHub Actions/releases — P7 target

- [ ] workflow/run/job/step reads.
- [ ] log truncation/document fallback.
- [ ] artifact metadata.
- [ ] dispatch capability + workflow/ref/inputs confirmation.
- [ ] invalid required inputs.
- [ ] retry/cancel state handling where supported.
- [ ] notification -> logs/retry navigation.
- [ ] no GitHub secret output added by GitDock.
- [ ] audit write operations.
- [ ] release list/detail/assets.

## 19. ZIP/project sync archive safety — P8 target

Malicious fixtures include traversal, absolute/Windows paths, excessive depth/count/uncompressed size, duplicate normalized path, symlink/hardlink/special entries where format permits, invalid path edge, nested secret-like file. All unsafe cases fail before repository writes.

## 20. ZIP/project sync planning/apply — P8 target

Planning:

- [ ] unchanged/additions/modifications/deletions/mixed.
- [ ] rename-like Git tree outcome.
- [ ] binary/large text/exclusions.
- [ ] base commit recorded.
- [ ] totals match details.
- [ ] displayed plan matches immutable persisted plan.

Apply:

- [ ] review branch default.
- [ ] coherent single batch commit.
- [ ] optional PR.
- [ ] stale base stops/replans.
- [ ] direct default branch requires separate Tier 2 path.
- [ ] cleanup on success/cancel/error/expiry.

## 21. CI / migration regression contract

For code changes, required CI gates remain:

- Ruff format;
- Ruff lint;
- mypy;
- pytest;
- compileall;
- `pip-audit`;
- `detect-secrets`;
- PEP 751 lock regeneration/diff for Python 3.12 Linux;
- PEP 751 lock regeneration/diff for Python 3.13 Linux;
- PostgreSQL 17 Alembic upgrade -> downgrade -> upgrade when schema/migrations exist.

P4.1 implementation result `34639736010` on `614f013b35644fcdd05e880c9a37ff30fd503fdf`:

- **148 passed** on Python 3.12;
- **148 passed** on Python 3.13;
- Ruff format/lint green on both supported Python versions;
- mypy clean on **87 source files**;
- compile green;
- `pip-audit`: no known runtime vulnerabilities;
- `detect-secrets`: no findings;
- PEP 751 locks match fresh current resolver byte-for-byte on both Python targets;
- PostgreSQL 17 round trip passed including migration `0006_file_write_sessions`;
- direct runtime pins unchanged; transitive lock refresh records current `anyio==4.15.1` and `multidict==6.8.0` after cache-disabled CI exposed drift;
- known non-blocking warnings: Starlette/FastAPI TestClient -> httpx2 direction, AnyIO `BlockingPortal` alias, Alembic `path_separator`.

The documentation-synchronized head must run this same CI contract again before PR creation/merge. P4.1 remains implementation-verified, not phase-complete, until the feature PR/main and governance-closeout chain are also green.

## 22. Test honesty rule

Do not weaken assertions, skip security checks, broaden secret-scan exclusions, disable migration round trips, or mark planned behavior implemented merely to obtain green CI. A failing gate must be fixed at its cause or recorded as a real blocker.
