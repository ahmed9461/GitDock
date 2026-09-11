# GitDock — Security Model

Status: mandatory baseline + verified P2 foundations + P2.3 repository-read controls + P3.1 search isolation + P3.2 authorization lifecycle + P3.3 repository-administration controls + P4.1 file-browser/write implementation verification

## 1. Security goals

Protect:

- GitHub repositories and write authority;
- Telegram owner identity and operation intent;
- GitHub App private key, client secret, webhook secret, installation/user tokens;
- repository contents, especially private repositories;
- staged file-write content and preconditions;
- uploaded ZIP/project data;
- audit integrity and durable operation/confirmation state.

The main risk is not only credential theft. A Telegram control bot can also cause serious damage through accidental clicks, stale state, replayed callbacks, forged webhooks, unsafe archive extraction, overpowered permissions, blind overwrite, or replaying a write whose remote outcome is uncertain. GitDock must defend against malicious and accidental failure modes.

## 2. Trust boundaries

Untrusted inputs include:

- Telegram messages/callbacks/uploads;
- GitHub webhook bodies until signature validation succeeds;
- repository names, refs, paths, README text, file contents, and commit messages;
- archive paths/metadata;
- GitHub API responses until structurally validated;
- OAuth/setup callback parameters until server-side state and identity checks succeed;
- setup/install `installation_id` until independently verified through App and authenticated-user contexts;
- repository IDs carried in Telegram callbacks until user/installation/cache validation succeeds;
- local repository cache as potentially stale navigation state, never authorization proof;
- opaque confirmation/staging tokens carried by Telegram until DB state/preconditions are loaded and validated;
- repository-admin form values and exact delete names until operation-specific server-side validation succeeds.

Trusted only after validation:

- configured owner Telegram ID;
- App private key/webhook secrets loaded from secure deployment storage;
- validated/persisted one-time OAuth/confirmation state;
- installation binding whose identity matched across App and authenticated-user contexts;
- durable GitHub user account identity resolved through authenticated `/user`;
- repository read state revalidated against the active installation and GitHub itself where required;
- P3.3 administration execution only after server-side confirmation consumption, refreshed preconditions, and correct credential context;
- P4.1 file execution only after staged-write confirmation consumption, repository/ref/path validation, branch-head/file-SHA precondition checks, and a repository-scoped write token with the required capabilities.

## 3. Telegram access control

v1 is owner-only.

- Check Telegram user ID in middleware before command/callback/file processing.
- Do not trust username/display name for authorization.
- Unauthorized users receive no sensitive information.
- Callback queries re-check authorization; callback payload is not identity proof.
- Production Telegram webhook validates Telegram secret-token header when configured.

Repository/account/file callbacks are transport identifiers only. Server-side user, installation/account, operation, expiry, consumed state, target, and relevant preconditions must still be checked.

## 4. GitHub App over broad PAT

Do not use a broad permanent PAT as the product's primary credential model.

Use GitHub App permissions and operation-specific token contexts with least privilege. High-power permissions are enabled only when the corresponding feature is intentionally implemented.

Verified contexts:

- P2.3/P3.1: read-only repository/search paths;
- P3.2: durable user context, not blanket repository administration;
- P3.3 personal/organization repository creation: durable user OAuth context;
- P3.3 repository update/delete: installation token scoped to the selected repository with `administration: write`;
- P4.1 repository file reads: repository-scoped installation context with contents read;
- P4.1 create/update/delete: repository-scoped installation token with `contents: write`;
- P4.1 `.github/workflows/*` writes additionally require `workflows: write`.

## 5. Credential handling

### Never

- commit real `.env` files;
- print tokens/private keys/client/webhook secrets;
- send tokens to Telegram;
- include tokens in exception/audit rows;
- embed tokens in clone commands;
- store plaintext durable user access/refresh tokens;
- assume token validity/type from legacy prefix/length alone;
- store credentials/OAuth/private keys in `repositories_cache`, `pending_confirmations`, `file_write_sessions`, or `audit_log`;
- render OAuth code/state, PKCE verifier, tokens, installation tokens, or raw upstream auth bodies in HTML/Telegram errors.

### At rest

Durable GitHub user credentials use authenticated encryption from the maintained `cryptography` library through GitDock's versioned Fernet abstraction.

Rules:

- master key outside DB/repository;
- ciphertext separate from expiry metadata;
- key version persisted;
- old-key decrypt/new-key encrypt supported during rotation windows;
- no custom cryptography.

P4.1 does not add another durable credential store. Installation tokens remain short-lived provider output and are not persisted in cache, confirmation, staging, or audit state.

### Credential generation — P3.2

`GitHubAccount.credential_generation` is a durable concurrency/version precondition.

- Persisting a new credential set advances generation.
- Clearing credential state advances generation.
- Long-running refresh/disconnect logic compares the expected generation before applying results.
- A stale generation fails closed rather than overwriting/deleting newer authorization.

## 6. GitHub webhook validation

Mandatory order:

1. read original raw bytes;
2. require expected signature header;
3. compute HMAC-SHA256 with webhook secret;
4. constant-time compare;
5. reject mismatch before JSON/business processing;
6. then parse/route.

Use `X-Hub-Signature-256`. Deduplicate GitHub delivery ID. A valid duplicate must not produce duplicate user-visible effects.

## 7. OAuth/user authorization security

- cryptographically random high-entropy `state`;
- bind state to one GitDock user and intended flow;
- DB-backed short expiry;
- one-time consumption;
- reject missing/mismatch/expired/wrong-flow/already-consumed state;
- exchange code only server-side;
- PKCE S256;
- redact code/token/state/verifier from logs;
- validate resulting GitHub identity and bind to intended GitDock user.

Implemented state rules:

- raw state is never persisted; only `SHA-256(state)`;
- PKCE verifier is encrypted with key version;
- consumption is atomic and constrained by digest, flow, consumed state, and expiry;
- state is restart-safe because it is DB-backed.

### Installation-binding rule

The setup/install `installation_id` is an untrusted candidate. Binding persists only after the same installation/account identity is independently resolved under App context and authenticated-user context, identities match, suspension checks pass, and cross-user ownership conflicts are rejected.

### Durable P3.2 user authorization

Standalone user authorization reuses the same one-time state/PKCE system and does not require reinstalling the App. After OAuth code exchange, GitDock resolves authenticated identity through `GET /user` and persists access/refresh credentials only through encrypted credential storage.

### Refresh-token rotation

Treat refresh tokens as rotating credentials. Snapshot account ID + `credential_generation` before network refresh and persist the rotated pair only if current durable account/user/generation/authorization state still matches. Concurrent reauthorization/disconnect makes the old refresh fail closed.

## 8. Permission model

Capabilities map centrally to GitHub App permissions/token context. High-power permissions such as Administration write and Workflows write are not baseline convenience permissions.

Services still respect actual user/repository authority and GitHub branch protection/rules.

P4.1 rules:

- normal file create/update/delete requests `contents: write`;
- a workflow path detected under `.github/workflows/` also requests `workflows: write`;
- the installation token request is scoped to exactly the selected GitHub repository ID;
- archived repositories are rejected before staging a write;
- Telegram handlers never build permission dictionaries directly.

## 9. Confirmation security

A Telegram button is not durable authorization for a sensitive/destructive operation.

`pending_confirmations` is the restart-safe one-time confirmation primitive. It stores a digest of the opaque token plus user, operation, target fingerprint, safe payload/preconditions, risk tier, expiry, consumed state, and timestamps.

On confirm: re-check Telegram access, load server-side confirmation, require intended operation/user, require unexpired/unconsumed state, atomically consume, reload current target/preconditions, then apply at most once.

### P3.2 local disconnect

Confirmation fingerprints current account identity, credential generation, and installation set. Reauthorization/install-set change makes an older confirmation stale. Home/Cancel invalidates outstanding authority. Local disconnect never claims to uninstall/revoke the GitHub App remotely.

### P3.3 repository administration

Create is Tier 1, update is Tier 2, and repository deletion is Tier 3 plus exact typed current `owner/name`. Edit/back/cancel consumes pending confirmation so an old Telegram button cannot remain executable.

### P4.1 file writes

P4.1 uses a dedicated restart-safe staging record plus the same confirmation primitive:

- migration `0006_file_write_sessions` stores one-file staged intent;
- staging stores user, operation, repository/installation IDs, current repository full name/default branch, branch, path, branch-head SHA, expected file SHA, desired blob SHA, content digest, temporary content bytes, commit message, risk tier, expiry, and consumed state;
- confirmation payload contains safe identifiers/preconditions only and is fingerprinted server-side;
- the raw confirmation token is not stored; only its digest is persisted by the confirmation service;
- staged create/update content is temporary and has a 15-minute TTL;
- `content_bytes` is cleared on consume, cancel, expiry cleanup, and same-target supersession;
- before external GitHub write, staging is consumed once and the DB copy of file content is cleared; the already-validated content exists only in the in-process staged object needed for that one execution;
- a newer staging for the same user + repository + branch + path consumes/supersedes the older staged session and clears its content bytes;
- cancelled/reused/expired/superseded/invalid confirmation cannot execute later.

Risk rules:

- create/update on a non-default branch: Tier 1;
- create/update on the current default branch: Tier 2;
- delete: Tier 2 on any branch.

## 10. File staging confidentiality/integrity

P4.1 temporarily persists staged create/update bytes because the write must survive Telegram navigation/process restart long enough for explicit review/confirmation. This is not an audit store or long-term repository mirror.

Integrity controls:

- store SHA-256 content digest and Git blob SHA alongside temporary bytes;
- on consume, recompute and require both digests to match;
- corrupt/tampered staging is consumed, content cleared, and no write executes;
- staged bytes are absent from confirmation payload/fingerprint and audit details;
- audit records use safe metadata such as branch, path, expected SHA, desired blob SHA, risk tier, workflow-path flag, request ID, commit SHA, and reconciliation state;
- audit never stores full file contents.

Operational requirement: production DB backups/access controls must treat temporary staged content as private repository data while it exists.

## 11. Repository path/ref/content safety — P4.1

Paths:

- repository-relative POSIX form only;
- reject NUL, backslash, leading slash, drive prefixes, empty/dot/dot-dot segments, and overlong paths;
- nested callbacks use server-side compact context rather than treating arbitrary callback text as a trusted path.

Refs:

- must be non-empty trimmed text within configured length;
- reject control characters and Git-invalid patterns such as `..`, `@{`, repeated slash, invalid suffixes/segments, and forbidden ref characters.

Content/commit limits:

- text preview classification limit: 256 KiB;
- single staged upload limit: 20 MiB;
- text preview page target: 2800 characters;
- path max: 1024 characters;
- ref max: 255 characters;
- commit message max: 500 characters;
- content over the single-file limit is rejected before staging.

Binary/non-UTF-8/NUL-containing or oversized files use metadata/fallback behavior rather than pretending to be safe text preview.

## 12. P4.1 stale-state/conflict protection

GitHub remains source of truth. A staged file write binds to remote preconditions captured during review.

Before execution GitDock requires:

- current selected repository still belongs to the same installation/context;
- current repository full name and default branch still match staged context;
- target branch still exists;
- current branch HEAD SHA exactly matches staged `branch_head_sha`;
- create: target file is still absent;
- update/delete: current file exists and SHA equals staged `expected_file_sha`.

Any mismatch yields `STALE` and no GitHub write.

This intentionally blocks unrelated commits that move the branch HEAD after staging; the user must refresh/review against current GitHub state rather than allowing a confirmation to silently apply to a changed base.

## 13. Same-target write serialization

P4.1 prevents multiple live staged authorities for the same user/repository/branch/path.

Creating a newer staging consumes the older unresolved `file_write_sessions` row for that target and clears its temporary content. The older confirmation may remain visible in Telegram but cannot produce a valid staged write when consumed.

This is application-level stale/replay protection; it does not replace GitHub SHA/branch preconditions.

## 14. File write execution and uncertain-result reconciliation

Write-like GitHub methods remain no-retry by default.

Execution:

- create/update use Contents API PUT with branch/message/content and expected SHA for update;
- delete uses Contents API DELETE with exact expected file SHA;
- non-delete success additionally checks GitHub's returned content SHA against the desired Git blob SHA;
- a response SHA mismatch is classified `UNCERTAIN`, not success.

Potentially uncertain gateway failures are reconciled rather than blindly replayed:

- create/update: re-fetch target and compare current file SHA to desired Git blob SHA;
- delete: not-found after uncertain delete is evidence that deletion applied;
- if reconciliation proves requested state, record reconciled applied outcome;
- if the result cannot be proven, retain `UNCERTAIN`;
- never turn ambiguity into a second automatic PUT/DELETE.

## 15. P3.3 repository-administration reconciliation

Repository create/update/delete retain their established operation-specific reconciliation rules. P4.1 follows the same safety precedent without coupling file writes to repository-administration permissions.

## 16. Repository callback/cache safety

`repositories_cache` is navigation state, not authorization.

Mandatory rules:

- safe non-secret metadata only;
- scope to GitDock user + installation;
- stable GitHub repository ID for compact callback resolution;
- validate parser/version/positive IDs;
- require current user ownership and active installation context;
- obtain tokens through normal providers;
- re-fetch authoritative GitHub state where required;
- never infer file/admin write authority from cache existence;
- never store credentials/OAuth/PKCE/private-key/raw-error/file-content material in repository cache.

## 17. GitHub API/network restrictions

Core GitHub clients target approved GitHub endpoints. No generic fetch-URL-from-Telegram capability.

Canonical REST transport accepts repository-relative API paths or canonical HTTPS `api.github.com`; rejects scheme-relative, credential-bearing, external-host, non-HTTPS, fragment-bearing, and noncanonical targets before network I/O. Redirects are not followed automatically by the generic transport.

GET/HEAD bounded retry remains separate from write safety.

## 18. GitHub Actions/workflow safety

- Actions read is separate from Actions write;
- dispatch shows workflow/ref/inputs and requires confirmation;
- re-run/cancel targets explicit run/job IDs;
- never display Actions secrets;
- P4.1 workflow YAML/content edits under `.github/workflows/*` require `workflows: write` in addition to normal file-write safeguards and `contents: write`;
- workflow-path detection does not weaken stale SHA/branch-head confirmation rules.

## 19. Archive/ZIP security

Uploaded archives remain untrusted. Before extraction enforce upload size, member inspection, traversal/absolute/device/special/link policy, depth/count/uncompressed-size limits, duplicate normalized paths, isolated workspace, and cleanup.

Never execute uploaded code or automatically source `.env`/shell files. ZIP/project sync remains P8 work and is not implied by P4.1 single-file support.

## 20. Command-generation safety

Clone/setup/run generates commands only.

- never insert tokens;
- correct quoting per OS;
- never automatically execute README commands;
- repository scripts/README are untrusted text;
- trusted templates + detected metadata;
- uncertainty labelled.

## 21. Database security

- parameterized ORM/query use only;
- transactions for consume/apply transitions;
- migrations reviewed/tested;
- backups/access control documented before production launch;
- repository cache contains no credentials;
- audit rows contain safe identifiers/metadata only and are not a credential sink;
- temporary `file_write_sessions.content_bytes` must be treated as private repository content and cleared through the lifecycle described above.

Migration chain includes:

- `0003` repository cache;
- `0004_user_auth` credential-generation/confirmation lifecycle;
- `0005_audit_log` durable GitHub-write audit rows;
- `0006_file_write_sessions` restart-safe one-file staging.

PostgreSQL 17 upgrade -> downgrade -> upgrade including `0006_file_write_sessions` passed in CI `34639736010`.

## 22. Logging/redaction

Redact authorization, access/refresh token, installation token, client/webhook secret, private key, OAuth code/state, PKCE verifier, credential key, Telegram bot token, and similarly named sensitive fields.

Authentication/gateway errors must not echo raw GitHub response bodies. Do not log full private webhook bodies by default.

Repository/file audit must never serialize credential objects, raw upstream auth/error bodies, or staged file contents.

## 23. Audit log

Audit user-triggered GitHub writes with operation ID, Telegram/GitDock user identity, safe installation/repository context, repository/resource/path, branch, timestamp, result/status, GitHub request ID when safe, commit SHA where available, and reconciliation outcome where relevant.

P4.1 stable operations are:

- `file.create`;
- `file.update`;
- `file.delete`.

P4.1 audit details intentionally exclude file content and staged `content_bytes`.

## 24. Error handling

Telegram receives stable local errors, not raw tracebacks or auth bodies.

Gateway categories remain authentication, permission, not-found, conflict, validation, rate-limit, transient, unexpected.

Higher layers distinguish safe states such as reauthorization-required, stale/invalid confirmation, `APPLIED`, `STALE`, `INVALID`, and `UNCERTAIN`.

For P4.1:

- stale branch/file/repository preconditions claim no write occurred;
- expired/reused/cancelled/superseded staging claims no write occurred;
- uncertain remote outcome explicitly says GitDock did not automatically replay the write.

## 25. Dependency/supply-chain baseline

- exact direct runtime pins in `requirements.txt`;
- exact dev/test pins in `requirements-dev.txt`;
- Python/platform PEP 751 runtime locks committed for 3.12/3.13 Linux;
- CI regenerates/compares locks byte-for-byte;
- maintained libraries only;
- `pip-audit` and secret scan in CI;
- no dynamic package install from Telegram input.

During P4.1 verification, disabling Actions dependency caches exposed normal transitive resolver drift to `anyio 4.15.1` and `multidict 6.8.0`. The two runtime lock files were refreshed to exactly the resolver output. Direct runtime pins were unchanged. CI `34639736010` subsequently verified both locks byte-for-byte.

## 26. Known non-blocking maintenance warnings

Green P4.1 implementation CI still reports:

- Starlette/FastAPI `TestClient` deprecation warning around current `httpx` integration/future `httpx2` direction;
- Starlette test-client usage surfaces AnyIO's deprecated `anyio.abc.BlockingPortal` alias;
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

Tracked maintenance debt; not hidden test failures.

## 27. P4.1 implementation verification facts

Verified implementation head before documentation synchronization: `614f013b35644fcdd05e880c9a37ff30fd503fdf`.

CI `34639736010` verified:

- Ruff format/lint green on Python 3.12 and 3.13;
- mypy clean on **87 source files**;
- **148 tests passed** on both supported Python versions;
- compile green;
- `pip-audit` reported no known runtime vulnerabilities;
- `detect-secrets` reported no findings;
- Python 3.12 and 3.13 PEP 751 locks reproduced byte-for-byte;
- PostgreSQL 17 migration upgrade -> downgrade -> upgrade including `0006_file_write_sessions`.

The 148-test suite includes direct regression coverage that a newer staged write for the same user/repository/branch/path invalidates the old staging, clears its temporary content, and leaves only the newest staging consumable.

P4.1 remains merge/governance pending until the documentation-head CI, non-draft PR, unchanged-head merge, post-merge `main` CI, and governance closeout complete.

## 28. Deployment baseline

Before public production use:

- HTTPS for webhook/setup/OAuth;
- restricted service filesystem permissions;
- private key readable only by service account;
- environment/secrets not world-readable;
- non-root service where practical;
- reverse-proxy limits aligned with upload policy;
- least-privileged PostgreSQL credentials;
- DB access/backups treated as sensitive because short-lived staged private file bytes may exist in `file_write_sessions`;
- backup/restore tested;
- health/readiness reveal no secrets.
