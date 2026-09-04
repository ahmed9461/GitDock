# GitDock — Security Model

Status: mandatory baseline + verified P2 foundations + P2.3 repository-read controls + P3.1 search isolation + P3.2 authorization lifecycle + P3.3 repository-administration controls

## 1. Security goals

Protect:

- GitHub repositories and write authority;
- Telegram owner identity and operation intent;
- GitHub App private key, client secret, webhook secret, installation/user tokens;
- repository contents, especially private repositories;
- uploaded ZIP/project data;
- audit integrity and durable operation/confirmation state.

The main risk is not only credential theft. A Telegram control bot can also cause serious damage through accidental clicks, stale state, replayed callbacks, forged webhooks, unsafe archive extraction, or overpowered permissions. GitDock must defend against both malicious and accidental failure modes.

## 2. Trust boundaries

Untrusted inputs include:

- Telegram messages/callbacks/uploads;
- GitHub webhook bodies until signature validation succeeds;
- repository names/paths/README text/file contents;
- archive paths/metadata;
- GitHub API responses until structurally validated;
- OAuth/setup callback parameters until server-side state and identity checks succeed;
- setup/install `installation_id` until independently verified through App and authenticated-user contexts;
- repository IDs carried in Telegram callbacks until user/installation/cache validation succeeds;
- local repository cache as potentially stale navigation state, never authorization proof;
- opaque local confirmation tokens carried by Telegram until DB state/preconditions are loaded and validated;
- repository-admin form values and exact delete names until operation-specific server-side validation succeeds.

Trusted only after validation:

- configured owner Telegram ID;
- App private key/webhook secrets loaded from secure deployment storage;
- validated/persisted one-time OAuth/confirmation state;
- installation binding whose identity matched across App and authenticated-user contexts;
- durable GitHub user account identity resolved through authenticated `/user`;
- repository read state revalidated against the active installation and, for detail, GitHub itself;
- P3.3 write execution only after server-side confirmation consumption, refreshed preconditions, and correct credential context are established.

## 3. Telegram access control

v1 is owner-only.

- Check Telegram user ID in middleware before command/callback/file processing.
- Do not trust username/display name for authorization.
- Unauthorized users receive no sensitive information.
- Callback queries re-check authorization; callback payload is not identity proof.
- Production Telegram webhook validates Telegram secret-token header when configured.

Repository and account callbacks are transport identifiers only. Server-side user, installation/account, operation, expiry, consumed state, and relevant preconditions must still be checked.

## 4. GitHub App over broad PAT

Do not use a broad permanent PAT as the product's primary credential model.

Use GitHub App permissions and token contexts with least privilege. High-power permissions are enabled only when the corresponding feature is intentionally implemented.

P2.3/P3.1 are read-only. P3.2 adds durable user context but does not itself grant broad repository administration. P3.3 deliberately introduces only the write contexts it needs:

- personal/organization repository creation through durable user OAuth context;
- repository update/delete through an installation token scoped to the selected repository and requesting centralized `administration: write`.

## 5. Credential handling

### Never

- commit real `.env` files;
- print tokens/private keys/client/webhook secrets;
- send tokens to Telegram;
- include tokens in exception/audit rows;
- embed tokens in clone commands;
- store plaintext user access/refresh tokens;
- assume token validity/type from legacy prefix/length alone;
- store credentials/OAuth/private keys in `repositories_cache`, `pending_confirmations`, or `audit_log`;
- render OAuth code/state, PKCE verifier, tokens, installation tokens, or raw upstream auth bodies in HTML/Telegram errors.

### At rest

Durable GitHub user credentials use authenticated encryption from the maintained `cryptography` library through GitDock's existing versioned Fernet abstraction.

Rules:

- master key outside DB/repository;
- ciphertext separate from expiry metadata;
- key version persisted;
- old-key decrypt/new-key encrypt supported during rotation windows;
- no custom cryptography.

P3.2 uses this existing store for explicit durable user-context authorization. P3.3 reuses those credentials for create operations and does not introduce another durable credential store. Installation tokens for update/delete remain short-lived provider output and are not persisted in audit/cache/confirmation state.

### Credential generation — P3.2

`GitHubAccount.credential_generation` is a durable concurrency/version precondition.

- Persisting a new credential set advances generation.
- Clearing credential state advances generation.
- Long-running refresh/disconnect logic must compare the expected generation before applying results.
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

The setup/install `installation_id` is an untrusted candidate. Before binding:

1. consume installation-flow state;
2. start fresh user authorization with one-time state + PKCE;
3. fetch candidate installation under App JWT context;
4. fetch same installation under authenticated-user token;
5. require installation ID/account ID/login/type match;
6. reject suspended installation;
7. reject binding owned by another GitDock user;
8. persist only after all checks pass.

Do not simplify this to trusting query-string installation ID or login alone.

### Durable P3.2 user authorization

Standalone user authorization reuses the same one-time state/PKCE system and does not require reinstalling the App.

After OAuth code exchange:

- call authenticated `GET /user`;
- require a valid positive GitHub user ID/login shape;
- reject a GitHub identity already bound to a different GitDock user;
- persist access/refresh credentials only through encrypted credential storage.

### Refresh-token rotation — P3.2

Treat refresh tokens as rotating credentials.

- Do not log or expose refresh grant bodies.
- Before network refresh, snapshot account ID + credential generation.
- Reject refresh if no usable refresh token exists or refresh expiry has passed.
- After GitHub returns the rotated pair, re-open durable state and require same user/account/generation and still-active authorization.
- Persist rotated access + refresh credentials atomically only after preconditions match.
- If reauthorization/disconnect occurred concurrently, raise a safe changed-authorization condition and do not overwrite current credentials.

## 8. Permission model

Capabilities map centrally to GitHub App permissions/token context. High-power permissions such as Administration write and Workflows write are not baseline convenience permissions.

Services still respect actual user/repository authority and GitHub branch protection/rules.

P3.2 durable user context is not itself repository write authority. P3.3 selects credential context per operation:

- create uses the explicit durable user authorization required for GitHub user/organization create endpoints;
- update/delete request `administration: write` through the installation token provider and scope the token request to exactly the selected GitHub repository ID.

Permission strings remain in the centralized capability mapping, never Telegram handlers.

## 9. Confirmation security

A Telegram button is not durable authorization for a sensitive/destructive operation.

`pending_confirmations` introduced in P3.2 is the general restart-safe storage boundary for one-time confirmation state. It stores:

- GitDock user ID;
- operation type;
- opaque random token digest;
- target fingerprint;
- safe payload/preconditions;
- risk tier;
- expiry;
- consumed timestamp;
- creation timestamp.

Raw confirmation token may travel in compact Telegram callback data, but only its digest is persisted.

On confirm: re-check Telegram access, load server-side confirmation, require intended operation/user, require unexpired/unconsumed state, atomically consume, reload current target/preconditions, then apply at most once.

### P3.2 local-disconnect confirmation

The fingerprint binds:

- active GitHub account DB ID when present;
- GitHub user ID when present;
- `credential_generation` when present;
- ordered current installation IDs.

Consequences:

- reauthorization makes an old confirmation stale;
- credential clear/reconnect makes it stale;
- installation set changes make it stale;
- cancelled/reused/invalid tokens cannot execute;
- stale/invalid states return copy that says nothing was deleted.

Home consumes outstanding GitHub disconnect confirmations to invalidate old message buttons.

### P3.3 repository-administration confirmations

Operation-specific rules reuse the same persisted confirmation primitive:

- create is Tier 1;
- update/visibility/archive/default-branch changes are Tier 2;
- repository deletion is Tier 3;
- delete requires the exact current `owner/name` to be typed before the pending delete confirmation is issued;
- target fingerprint/payload binds the intended request and current repository snapshot/preconditions;
- confirm is user/operation-bound, expiring, atomic, and single-use;
- stale, expired, reused, cancelled, wrong-operation, wrong-target, and wrong-name paths fail closed;
- edit/back/cancel is not cosmetic: the operation-specific cancellation service consumes the pending confirmation before navigation;
- a previously rendered Telegram confirm button therefore loses authority immediately after a successful cancellation.

Tests verify one-time cancellation for create/update/delete and negative delete cases including expired, reused, wrong-name, and permission failure.

## 10. P3.2 exact disconnect scope

`🔌 قطع الربط المحلي` is intentionally local-only.

On a valid confirmation GitDock may:

- clear encrypted local GitHub user credentials;
- delete GitDock installation bindings for the user;
- delete local repository navigation cache;
- invalidate unconsumed local OAuth state/confirmations.

It does **not** uninstall/revoke the GitHub App on GitHub and must never tell the user that it did.

A legacy P2.3 installation-only local state with no durable user token can still be disconnected safely.

## 11. Stale-state/conflict protection

For file updates/batch operations, capture expected SHA/base commit and revalidate before write. If source moved, stop and require refresh/review.

For merges/actions, refresh critical state before final write where practical.

For repository reads, stale cache is revalidated against GitHub.

For P3.2 credentials/confirmations, credential generation and target fingerprints are the relevant durable stale-state preconditions.

For P3.3 update/delete:

- cache selection is resolved inside the current user/installation context;
- current GitHub repository state is refreshed before sensitive execution;
- confirmation fingerprint/request preconditions are compared against current state;
- stale repository state stops the write rather than silently targeting a renamed/reconfigured resource.

## 12. Uncertain-write reconciliation — P3.3

Write-like GitHub methods remain no-retry by default. A timeout/transient response can occur after GitHub applied a mutation, so automatically replaying create/update/delete can duplicate or misreport side effects.

P3.3 therefore uses operation-specific reconciliation:

- create: inspect current remote repository state for a repository matching the intended creation before deciding outcome;
- update: re-fetch and compare requested fields against remote state;
- delete: re-fetch to determine whether the target still exists;
- if reconciliation proves the requested state, record a reconciled applied outcome;
- if reconciliation disproves it safely, record failure where justified;
- if the remote outcome cannot be established, retain an explicit `UNCERTAIN` result instead of claiming success/failure.

Reconciliation is not permission bypass and must use the correct current credential context. It never justifies blind replay.

## 13. Archive/ZIP security

Uploaded archives are untrusted. Before extraction enforce upload size, member inspection, traversal/absolute/device/special/link policy, depth/count/uncompressed-size limits, duplicate normalized paths, isolated workspace, and cleanup.

Never execute uploaded code or automatically source `.env`/shell files. Scan/flag secret-like content where feasible without claiming certainty.

## 14. Secret-like file safeguards

Warn/block candidates include `.env` except reviewed safe examples, private keys, credential/token files, unexpected local DBs, and auth/session caches. Scanner is a safety layer, not proof that an upload is secret-free.

## 15. Repository path safety

- repository-relative POSIX paths;
- reject leading slash, drive paths, NUL, traversal;
- short UI IDs resolve server-side rather than becoming paths directly;
- `.github/workflows/*` requires explicit Workflows capability.

## 16. Repository callback/cache safety

`repositories_cache` is navigation state, not authorization.

Mandatory rules:

- safe non-secret metadata only;
- scope to GitDock user + installation;
- stable GitHub repository ID for compact callback resolution;
- no arbitrary long names in callback payloads;
- validate parser/version/positive IDs;
- require current user ownership and unsuspended installation;
- obtain token through normal provider;
- re-fetch GitHub detail before render;
- delete/reject stale inaccessible cache rows;
- never infer write/admin authority from cache;
- never store credentials/OAuth/PKCE/private-key/raw-error material.

P3.3 uses repository cache only to resolve navigation context. Update/delete authority is rebuilt from current user/install binding, fresh GitHub repository state, persisted confirmation, and current scoped token capability.

## 17. Command-generation safety

Clone/setup/run generates commands only.

- never insert tokens;
- correct quoting per OS;
- never automatically execute README commands;
- repository scripts/README are untrusted text;
- trusted templates + detected metadata;
- uncertainty labelled.

## 18. SSRF/network restrictions

Core GitHub clients target approved GitHub endpoints. No generic fetch-URL-from-Telegram capability.

Canonical REST transport allows repository-relative API paths or HTTPS `api.github.com`; rejects scheme-relative, credential-bearing, external-host, non-HTTPS, fragment-bearing, and noncanonical targets before network I/O. Redirects are not automatically followed.

## 19. GitHub API writes

- use preconditions/current SHA where supported;
- serialize conflicting same-path operations;
- batch coherent multi-file changes;
- never blindly retry destructive/non-idempotent writes after uncertain result; reconcile first;
- distinguish a reconciled applied write from an ordinary direct response in application result/audit state;
- if uncertainty remains after reconciliation, expose safe uncertainty instead of lying about success/failure.

GET/HEAD bounded retry remains separate from write safety.

## 20. GitHub Actions safety

- Actions read separate from Actions write;
- dispatch shows workflow/ref/inputs and requires confirmation;
- re-run/cancel targets explicit run/job IDs;
- never display Actions secrets;
- workflow YAML edits require Workflows write plus normal file-review safeguards.

## 21. Database security

- parameterized ORM/query use only;
- unique constraints for identity/delivery bindings where needed;
- transactions for consume/apply transitions;
- migrations reviewed/tested;
- backups/access control documented before production launch;
- repository cache contains no credentials;
- audit rows contain safe identifiers/metadata only and are not a credential sink.

Migration verification:

- `0003` repository cache remains in PostgreSQL round trip;
- `0004_user_auth` adds credential-generation/confirmation lifecycle;
- P3.3 `0005_audit_log` adds durable administration audit rows;
- PostgreSQL 17 upgrade -> downgrade -> upgrade including `0005_audit_log` passed in implementation CI `33890407945`.

## 22. Logging/redaction

Redact authorization, access/refresh token, installation token, client/webhook secret, private key, OAuth code/state, PKCE verifier, credential key, Telegram bot token, and similarly named sensitive fields.

Authentication/gateway errors must not echo raw GitHub response bodies. Do not log full private webhook bodies by default.

Repository-administration audit details must never serialize credential objects or raw upstream auth/error bodies.

## 23. Audit log

Audit user-triggered GitHub writes with operation ID, Telegram/GitDock user identity, GitHub account/installation context where safe, repository/resource, timestamp, result/status, GitHub request ID when safe, and reconciliation outcome where relevant.

Do not place secrets or full sensitive file contents in audit rows.

P3.3 `AuditLog` records repository create/update/delete success/failure/reconciled/uncertain context while keeping credential material out of `details`.

Successful update refreshes repository cache metadata. Confirmed successful/reconciled delete removes the deleted repository from local cache so navigation state does not imply the resource still exists.

## 24. Error handling

Telegram receives stable local errors, not raw tracebacks or auth bodies.

Gateway categories remain authentication, permission, not-found, conflict, validation, rate-limit, transient, unexpected.

P3.2 additionally distinguishes safe reauthorization-required, changed/stale authorization, stale confirmation, and invalid/consumed confirmation states. Copy must never claim deletion when preconditions fail.

P3.3 adds explicit safe repository-admin outcome states including applied/stale/invalid/uncertain. An uncertain write is never rendered as definite failure if reconciliation cannot prove that assertion.

## 25. Dependency/supply-chain baseline

- exact direct runtime pins in `requirements.txt`;
- exact dev/test pins in `requirements-dev.txt`;
- Python/platform PEP 751 runtime locks committed for 3.12/3.13 Linux;
- CI regenerates/compares locks;
- maintained libraries only;
- `pip-audit` and secret scan in CI;
- no dynamic package install from Telegram input.

P3.3 adds no runtime dependency drift. Implementation CI `33890407945` reports no known runtime vulnerabilities, no secret findings, and no PEP 751 lock drift on Python 3.12/3.13.

## 26. Known non-blocking maintenance warnings

Green P3.3 implementation CI still reports:

- Starlette/FastAPI `TestClient` deprecation warning around current `httpx` integration/future `httpx2` direction;
- Starlette test-client usage surfaces AnyIO's deprecated `anyio.abc.BlockingPortal` alias;
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

Tracked maintenance debt; not hidden test failures.

## 27. P3.3 verification facts

Implementation head before documentation synchronization: `4e71d7f1c962e61584d6532d03c913703dc5295a`.

CI `33890407945` verified:

- Ruff format/lint green on Python 3.12 and 3.13;
- mypy clean on 72 source files;
- **117 tests passed** on both supported Python versions;
- compile green;
- `pip-audit` no known runtime vulnerabilities;
- `detect-secrets` no findings;
- PEP 751 locks reproduce byte-for-byte;
- PostgreSQL 17 migration upgrade -> downgrade -> upgrade including `0005_audit_log`.

P3.3 remains merge/governance pending until the documentation-head CI, non-draft PR, unchanged-head merge, post-merge `main` CI, and governance closeout finish.

## 28. Deployment baseline

Before public production use:

- HTTPS for webhook/setup/OAuth;
- restricted service filesystem permissions;
- private key readable only by service account;
- environment/secrets not world-readable;
- non-root service where practical;
- reverse-proxy limits aligned with upload policy;
- least-privileged PostgreSQL credentials;
- backup/restore tested;
- health/readiness reveal no secrets.
