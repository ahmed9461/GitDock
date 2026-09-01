# GitDock — Test Matrix

Status: authoritative quality expectations, updated through P3.2 pre-merge verification.

P3.2 implementation reference: branch head before documentation synchronization `5068b58ec41fb5ac417408d3a535bbb5d66207fc`, GitHub Actions run `33515291600` fully green on Python 3.12, Python 3.13, and PostgreSQL 17. The suite contains **97 tests**. Checkmarks remain conservative: they indicate direct current coverage, not merely intended behavior.

## 1. Test layers

### Unit

Fast tests for domain rules, risk/confirmation rules, callback encoding/decoding, renderers/keyboards, input/path validation, permission mapping, safe error translation, credential encryption helpers, and command-generation templates.

### Integration

Controlled boundary tests for SQLAlchemy + test DB, Alembic, FastAPI routes, aiogram service wiring, DB-backed OAuth/confirmation lifecycle, repository services/cache, and later webhook/workspace persistence.

### GitHub contract/mock integration

Use constructed responses/MockTransport rather than a live mutable account for normal CI. Verify method/path/headers/body, parsing, pagination, token context, permissions, rate limits, validation failures, retry policy, and safe error handling.

### Live smoke

Manual/controlled tests against dedicated GitHub test resources before production use of high-risk behaviors. Never use an important production repository as the first destructive target.

## 2. Universal feature checklist

Every feature considers, where applicable:

- [ ] authorized success
- [ ] unauthorized Telegram user
- [ ] invalid user input
- [ ] empty/disconnected state
- [ ] missing installation/repository access
- [ ] missing GitHub permission
- [ ] not found/inaccessible
- [ ] GitHub validation failure
- [ ] rate limit
- [ ] transient network/API failure
- [ ] stale callback/session/precondition
- [ ] Telegram edit/send failure where relevant
- [ ] audit behavior for writes
- [ ] secret redaction in errors/logs

Not every box applies to every read-only helper; exclusions should be explicit rather than faked green.

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
- [x] repository detail callback remains within Telegram 64-byte limit including large signed repository ID context.
- [x] long repository name is not embedded in callback payload.
- [x] P3.1 search callbacks are active-session scoped and stale session fails closed.
- [x] `/start` and Home clear transient search FSM state.
- [x] P3.2 account callbacks are compact and local-disconnect confirmation callback round-trips under Telegram's limit.
- [x] P3.2 Cancel consumes a pending local-disconnect confirmation.
- [x] P3.2 Home invalidates outstanding local-disconnect confirmations.
- [x] repeated/reused P3.2 disconnect confirmation does not repeat deletion.
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
- [x] spoofed setup/install candidate identity rejected before DB binding.
- [x] installation binding persists only after App-context/authenticated-user-context identity match.
- [x] FastAPI setup/OAuth callback routes have safe success/error paths.
- [ ] deleted/suspended installation end-to-end behavior against real GitHub response.

### OAuth state / PKCE foundation

- [x] state opaque/high entropy and raw state not persisted.
- [x] state bound to GitDock user/flow.
- [x] state expires.
- [x] state one-time use.
- [x] wrong-flow/state context rejected safely.
- [x] state consumption remains restart-safe/DB-backed.
- [x] OAuth code/auth response secrets are not echoed by local auth exceptions.
- [x] PKCE S256 lifecycle verified.
- [x] PKCE verifier encrypted before persistence.
- [x] credential encryption supports versioned key rotation.

### P3.2 durable user authorization

- [x] authenticated `/user` request uses user bearer context.
- [x] `/user` payload resolves typed positive GitHub user ID/login.
- [x] standalone user authorization reuses existing state + PKCE.
- [x] standalone authorization does not bind/reinstall an installation when no installation candidate exists.
- [x] OAuth completion persists GitHub account identity.
- [x] access token encrypted before DB persistence.
- [x] refresh token encrypted before DB persistence.
- [x] plaintext token values absent from ciphertext assertions.
- [x] access expiry preserved.
- [x] refresh expiry preserved.
- [x] credential generation increments on persist.
- [x] durable account status separates authorization from installation count.

### P3.2 refresh rotation/concurrency

- [x] still-valid access token is returned without refresh.
- [x] near-expiry access token triggers refresh grant.
- [x] refresh grant uses `grant_type=refresh_token`.
- [x] rotated access token persisted.
- [x] rotated refresh token replaces old refresh token.
- [x] generation increments after rotated persistence.
- [x] stale concurrent credential generation prevents rotated result from overwriting newer state.
- [x] missing durable authorization produces reauthorization-required path.
- [x] expired/missing refresh credential produces reauthorization-required path.
- [x] raw refresh response/token-like values are absent from user-facing auth errors.

## 6. P3.2 durable local-disconnect confirmation

### Confirmation storage

- [x] confirmation stored DB-backed rather than FSM-only.
- [x] opaque token is not stored raw; digest used for lookup.
- [x] confirmation bound to GitDock user + operation.
- [x] expiry represented and enforced by confirmation service.
- [x] consumed/cancelled confirmation cannot execute later.
- [x] reused confirmation rejected.

### Target/precondition safety

- [x] fingerprint includes GitHub account identity when durable account exists.
- [x] fingerprint includes credential generation.
- [x] fingerprint includes ordered current installation IDs.
- [x] old confirmation after reauthorization is stale and removes nothing.
- [x] confirmation after installation-set change is stale and removes nothing.
- [x] malformed stored disconnect payload fails stale/closed.
- [x] Home consumes outstanding local-disconnect confirmation.

### Cleanup scope

- [x] successful local disconnect clears encrypted user credential state.
- [x] credential clear advances generation.
- [x] successful local disconnect deletes local installation bindings.
- [x] successful local disconnect deletes `repositories_cache` rows.
- [x] relevant unconsumed local OAuth/confirmation state is invalidated.
- [x] second confirm does not repeat cleanup.
- [x] legacy installation-only state can disconnect without durable UAT.
- [x] UI explicitly says local disconnect does not uninstall GitHub App remotely.
- [x] stale/invalid renderer never claims deletion occurred.
- [ ] remote GitHub App uninstall/revoke is intentionally **not implemented** in P3.2 and therefore has no success test.

## 7. GitHub gateway foundation — P2.2

- [x] canonical `Accept`, API version, `User-Agent` headers.
- [x] optional bearer injection without token leak through result representation.
- [x] typed response parsing.
- [x] unexpected JSON shape -> stable unexpected error.
- [x] keyed/plain-list pagination.
- [x] validated `api.github.com` pagination.
- [x] external/credential-bearing/scheme-relative pagination rejected.
- [x] rate-limit metadata parsing.
- [x] rate-limit exhaustion distinguished from ordinary permission denial.
- [x] common HTTP failures map to stable categories.
- [x] raw token-like response body absent from translated error.
- [x] bounded transient GET retry.
- [x] writes no retry by default.
- [x] explicitly safe operation can opt into retry.
- [x] P2.2/P2.3/P3.1/P3.2 keep audit/secret/lock gates green.

Deferred: live mutable GitHub smoke, ETag behavior if introduced, artifact/release redirect policy, operation-specific uncertain-write reconciliation.

## 8. Repository list/dashboard/search

### P2.3 installed repository read

- [x] typed installed-repository payload parsing.
- [x] stable application pagination.
- [x] private/public metadata render.
- [x] archived/source/fork filters.
- [x] default branch/language/stars/forks/update metadata.
- [x] long names do not break callback limits.
- [x] empty/disconnected state.
- [x] detail resolves only in same GitDock user context.
- [x] repository-scoped token + GitHub re-fetch before detail render.
- [x] removed repos pruned from callback cache.
- [x] cache contains no credential fields and is non-authoritative.
- [x] rate-limit/stale-selection user-facing states.

### P3.1 public search

- [x] search validation/normalization.
- [x] typed result parsing.
- [x] stars/update sort.
- [x] language/min-star/user/org/topic filters.
- [x] archive visibility.
- [x] no-results state.
- [x] pagination.
- [x] public path without bound installation.
- [x] detail only from current active result context then GitHub re-fetch.
- [x] older search session fails closed.
- [x] callbacks compact/versioned.
- [x] session/result context separate from installed cache.
- [x] Tier 0 read-only; no write path.
- [x] download-command button remains placeholder for P4.3.

## 9. Repository administration — P3.3 target

### Create

- [ ] valid private creation.
- [ ] valid public creation.
- [ ] optional organization creation when authorized.
- [ ] duplicate/invalid name rejection.
- [ ] missing durable user authorization.
- [ ] missing required GitHub capability/permission.
- [ ] preview does not create before confirm.
- [ ] repeated confirm does not duplicate creation.
- [ ] audit result records safe repository ID/name.

### Rename/settings/visibility/archive

- [ ] exact target/current/desired values shown.
- [ ] Tier 2 confirmation where applicable.
- [ ] expired/reused/stale confirmation rejected.
- [ ] GitHub conflict/validation handled.
- [ ] local cache refreshed after success.

### Delete

- [ ] wrong typed full repo name rejected.
- [ ] normalized exact name reaches final stage.
- [ ] final persisted confirmation required.
- [ ] confirmation expiry.
- [ ] reuse rejected.
- [ ] repo changed/unavailable before delete handled.
- [ ] missing admin permission handled.
- [ ] uncertain network result reconciled before claiming outcome where possible.
- [ ] audit contains no credentials.

## 10. File browser/read — P4.1 target

- [ ] directory listing/nested navigation.
- [ ] branch/ref switch.
- [ ] UTF-8 preview.
- [ ] large text pagination/truncation.
- [ ] binary fallback.
- [ ] not-found handling.
- [ ] traversal/invalid path rejected pre-network.
- [ ] long path uses short callback context.

## 11. Single-file writes — P4.1 target

- [ ] create/update/replace/delete.
- [ ] preview/diff before write.
- [ ] expected SHA precondition.
- [ ] stale SHA blocks overwrite.
- [ ] wrong branch/ref blocked.
- [ ] workflow path requires Workflows capability.
- [ ] same-path conflicts serialized/rejected.
- [ ] audit write.
- [ ] secrets absent from logs.

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

P3.2 verified result `33515291600`:

- **97 passed** on Python 3.12;
- equivalent full quality/security gates passed on Python 3.13;
- PostgreSQL round trip passed including migration `0004_user_auth`;
- no known runtime vulnerabilities;
- no secret findings;
- no PEP 751 lock drift;
- only the already-recorded Starlette/TestClient and Alembic `path_separator` maintenance warnings remain.

## 22. Test honesty rule

Do not weaken assertions, skip security checks, broaden secret-scan exclusions, disable migration round trips, or mark planned behavior implemented merely to obtain green CI. A failing gate must be fixed at its cause or recorded as a real blocker.
