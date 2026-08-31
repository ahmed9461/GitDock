# GitDock — Security Model

Status: mandatory baseline + verified P2.1/P2.2 foundations + P2.3 repository-read controls

## 1. Security goals

Protect:

- GitHub repositories and write authority;
- Telegram owner identity and operation intent;
- GitHub App private key, client secret, webhook secret, installation/user tokens;
- repository contents, especially private repositories;
- uploaded ZIP/project data;
- audit integrity and operation state.

The main risk is not only credential theft. A Telegram control bot can also cause serious damage through accidental clicks, stale state, replayed callbacks, forged webhooks, unsafe archive extraction, or overpowered permissions. GitDock must defend against both malicious and accidental failure modes.

## 2. Trust boundaries

Untrusted inputs include:

- Telegram messages/callbacks/uploads;
- GitHub webhook bodies until signature verification succeeds;
- repository names/paths/README text/file contents;
- archive member paths and metadata;
- GitHub API responses as external data that still require structural validation;
- OAuth/setup callback parameters until server-side state and GitHub identity validation succeeds;
- `installation_id` returned through GitHub's setup/install redirect until independently verified through GitHub App and authenticated-user contexts;
- repository IDs carried in Telegram callback data until server-side user/installation/cache validation succeeds;
- local repository cache contents as potentially stale navigation state, never authorization proof.

Trusted only after validation:

- configured owner Telegram ID;
- GitHub App private key loaded from secure deployment storage;
- webhook secret from secure deployment configuration;
- validated/persisted confirmation state;
- a GitHub installation binding whose installation/account identity matched in both App-authenticated and authenticated-user contexts;
- repository read state revalidated against the current user's active bound installation and, for detail display, refreshed from GitHub.

## 3. Telegram access control

v1 is owner-only.

- Check Telegram user ID in middleware before command/callback/file processing.
- Do not trust username/display name for authorization.
- Unauthorized users should not receive sensitive information.
- Callback queries must also re-check authorization; a callback payload is not proof of identity.
- Production Telegram webhook should use Telegram's webhook secret-token mechanism when configured and validate the expected header.

### P2.3 repository callback rule

Repository callbacks are compact/versioned transport data only. The repository ID in a callback must be resolved server-side inside the current GitDock user context and a currently bound, unsuspended GitHub installation. A callback or cache row alone never grants access.

The current integration suite verifies that a repository callback cached for one GitDock user is rejected for a different user.

## 4. GitHub App over broad PAT

Default rule: do not use a broad permanent PAT as the product's primary credential model.

Use GitHub App permissions and token contexts with least privilege. GitHub App permissions start with no privileges and should be enabled by capability/milestone. Installation access tokens are short-lived and are generated as needed.

P2.3 repository list/detail remains Tier 0 read-only and uses repository metadata/read capability. It does not introduce repository write/admin permission.

## 5. Credential handling

### Never

- commit real `.env` files;
- print tokens/private keys/client secrets/webhook secrets;
- send tokens to Telegram;
- include tokens in exception messages or audit rows;
- embed a token in a clone command shown to the user;
- store plaintext user access tokens in the database;
- assume a GitHub token's type or validity from a fixed legacy prefix/length alone;
- store credentials, OAuth material, or private keys in `repositories_cache`;
- render OAuth codes, PKCE verifier/state, tokens, or raw upstream auth errors in setup/OAuth HTML pages.

### At rest

If GitHub user access/refresh material must be persisted:

- encrypt using an authenticated encryption scheme from a maintained crypto library;
- keep the encryption master key outside the database and repository;
- store token metadata separately from ciphertext;
- design for key rotation/versioning.

P2.1 implements this baseline with version-aware Fernet encryption. Access/refresh ciphertext, access expiry, refresh expiry, and key version are stored separately. Old-key decryption/new-key encryption is supported during rotation windows.

A user access token used only to prove that an authenticated GitHub user can access an installation is not persisted merely because the proof flow used it. Durable user-token storage is reserved for features that actually require durable user context.

Do not invent custom cryptography.

## 6. GitHub webhook validation

Mandatory order:

1. read original raw bytes;
2. require the expected signature header;
3. compute HMAC-SHA256 using the webhook secret;
4. compare with constant-time comparison;
5. reject on mismatch before JSON processing/business logic;
6. only then parse/route payload.

Use `X-Hub-Signature-256`; do not rely on the legacy SHA-1 header.

Also require/deduplicate the GitHub delivery ID. A valid duplicate delivery should not produce duplicate user-visible effects.

Reference: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

## 7. OAuth/user authorization security

- Use cryptographically random, high-entropy `state` values.
- Bind authorization state to one GitDock user and one intended flow.
- Store state server-side with short expiry.
- State is one-time use.
- Reject missing, mismatched, expired, wrong-flow, or already-consumed state.
- Exchange authorization code only server-side.
- Use PKCE S256 for the GitHub user-authorization flow.
- Redact codes/tokens/state/PKCE verifier from logs.
- Validate the resulting GitHub identity and bind it explicitly to the intended GitDock user.

### Implemented state-storage rules

- The raw state value is never persisted. GitDock stores only `SHA-256(state)` for lookup/comparison.
- The PKCE code verifier is encrypted before persistence and includes the credential-encryption key version.
- State consumption is an atomic database update constrained by digest, intended flow, unconsumed status, and expiry.
- State survives process restart because it is database-backed rather than volatile FSM-only data.

### Implemented installation-binding rule

GitHub's setup/install redirect may contain an `installation_id`. GitDock treats that value only as an **untrusted candidate identifier**.

Before persisting a user-to-installation binding GitDock must:

1. consume the intended installation-flow state;
2. start a fresh authenticated GitHub user-authorization step using one-time state + PKCE;
3. fetch the candidate installation using GitHub App JWT context;
4. fetch the same installation using the authenticated user access token;
5. require installation ID, account ID, account login, and account type to match across both contexts;
6. reject a suspended installation;
7. reject an installation already bound to another GitDock user;
8. persist only after all checks pass.

P2.3 wires this flow to actual FastAPI setup/OAuth routes. UI wiring does not change the trust rule. Setup and OAuth callback error pages use stable local copy and do not echo raw GitHub bodies, OAuth codes, or tokens.

Do not simplify this to trusting the query-string `installation_id` or matching account login alone.

## 8. Permission model

GitDock must have a central capability-to-permission map.

High-power permissions such as repository `Administration: write` and `Workflows: write` are not treated as baseline convenience permissions. They are enabled only when corresponding features are intentionally supported.

Repository operations must still respect the actual user's/repository's authority and GitHub branch protection/rules.

P2.3 list/detail uses metadata/read only. Repository detail may request an installation token narrowed to the selected repository ID.

Reference: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app

## 9. Confirmation security

A Telegram button is not itself durable authorization for a destructive operation.

Pending confirmations include opaque random ID, Telegram user id, operation type, target repository/resource, branch/ref/path and expected SHA when relevant, risk tier, intended payload summary/hash where practical, expiration, and consumed state.

On confirm: re-check Telegram authorization, load server-side state, verify unexpired/unconsumed target/preconditions, atomically consume/mark executing, then apply once.

Tier 3 deletion additionally requires exact repository name entry before final button confirmation.

P2.3 is read-only and does not use write confirmations; later repository administration must not infer write authority from the P2.3 repository cache.

## 10. Stale-state/conflict protection

For file updates and batch operations:

- capture source blob SHA/base commit during review;
- verify it remains valid before write;
- if source moved, stop and ask user to refresh/review;
- do not silently overwrite newer remote work.

For merges/actions, refresh critical state immediately before the final write where practical.

For P2.3 repository reads, stale callback/cache state is refreshed against GitHub before detail render. A not-found/inaccessible repository removes or rejects stale cache context rather than continuing from local metadata.

## 11. Archive/ZIP security

Uploaded archives are untrusted.

Before extraction enforce upload size limits, inspect members, reject absolute/traversal/device/special/link entries per policy, enforce depth/count/uncompressed-size limits, detect duplicate normalized paths, and prevent writes outside isolated workspace.

After extraction never execute uploaded code, never automatically source `.env` or shell files, scan/flag secret-like content where feasible, and clean temporary workspace after completion/expiry.

## 12. Secret-like file safeguards for project sync

Default warnings/blocklist candidates include `.env` except reviewed safe examples, private keys, credential/token files, unexpected local databases, and auth/session cache directories.

The scanner is a safety layer, not a guarantee. It must avoid claiming that an upload is secret-free.

## 13. Repository path safety

- Canonicalize paths as repository-relative POSIX-style paths.
- Reject leading slash, drive-letter paths, NUL, and path traversal.
- Do not allow UI short IDs to be interpreted directly as paths without server-side resolution.
- Treat `.github/workflows/*` as a special protected area requiring Workflows capability.

## 14. Repository callback/cache safety — P2.3

`repositories_cache` exists because Telegram callback payloads are small; it is not a shadow authorization database.

Mandatory rules:

- cache only safe non-secret repository metadata/context;
- scope rows to a GitDock user and bound GitHub installation;
- use stable GitHub repository ID for compact callback resolution;
- do not embed arbitrary long repository `owner/name` in callbacks;
- validate callback parser/version/positive IDs before use;
- require the cached row to belong to the current GitDock user;
- require the related installation to belong to that user and be unsuspended;
- obtain the repository read token through the normal installation-token provider;
- re-fetch GitHub repository detail before rendering;
- if GitHub reports not found/inaccessible, delete/reject stale callback cache state;
- never use cache existence as evidence of write/admin permission;
- never place access tokens, refresh tokens, OAuth code/state, PKCE verifier, private key, or raw upstream bodies in cache rows.

Current P2.3 tests verify callback size/round-trip, long-name non-embedding, cross-user rejection, repository-scoped detail token request, stale cache pruning, and disconnected state.

## 15. Command-generation safety

Clone/setup/run feature generates commands only.

- Never insert access tokens into user-visible commands.
- Quote shell arguments correctly per OS.
- Do not automatically execute README commands.
- Treat repository-controlled scripts and README content as untrusted instructions.
- Inferred run/setup commands come from trusted templates plus detected project metadata, with uncertainty labeled.

## 16. SSRF/network restrictions

Core GitHub clients should target configured official GitHub API/GraphQL endpoints and approved GitHub hosts. Do not implement a generic “fetch URL from Telegram” capability as part of the GitHub gateway.

Redirects/downloads for artifacts/releases need host and size validation according to that feature's design.

### Implemented REST gateway rules

- The canonical REST transport accepts repository-relative API paths or HTTPS URLs whose host is exactly `api.github.com`.
- Scheme-relative URLs, credential-bearing URLs, non-HTTPS absolute URLs, and external hosts are rejected before network I/O.
- Pagination `Link` targets use the same canonical host policy.
- The REST client does not follow HTTP redirects automatically.
- Repeated pagination next-link is an unexpected gateway failure and page traversal is capped.

These rules make pagination incapable of becoming an arbitrary URL fetcher merely because external input supplied a `Link` value.

## 17. GitHub API writes

- Use preconditions/current SHA where endpoints support them.
- Serialize conflicting Contents API operations for the same path.
- Batch multi-file changes coherently instead of racing independent writes.
- Do not blindly retry destructive/non-idempotent writes after uncertain network result; first reconcile state.

### Retry boundary

- `GET` and `HEAD` use bounded retry behavior for transient network failures and selected transient HTTP statuses.
- Writes are `RetryMode.NEVER` by default. A higher layer must explicitly opt an operation into safe retry only when its semantics/preconditions make replay safe.
- Backoff is bounded exponential delay with jitter and the global configured retry ceiling.
- Rate-limit responses are surfaced distinctly with parsed metadata instead of being blindly retried.

Reference: https://docs.github.com/en/rest/repos/contents

## 18. GitHub Actions safety

- Actions read is separate from Actions write.
- Manual dispatch requires showing workflow, ref, and input values before confirmation.
- Re-run/cancel operations target explicit run/job IDs.
- Never display Actions secrets.
- Editing workflow YAML requires explicit Workflows write permission and normal file-review safeguards.

Reference: https://docs.github.com/en/rest/actions/workflows

## 19. Database security

- Parameterized ORM/query use only; no string-concatenated SQL from user input.
- Unique constraints for delivery IDs and identity bindings.
- Transactions for consume-and-execute confirmation transitions where applicable.
- Migration scripts reviewed/tested.
- Database backups/access controls are deployment concerns to document before production launch.
- P2.3 migration `0003` is included in PostgreSQL 17 upgrade -> downgrade -> upgrade CI.
- Repository cache is safe metadata/context only; credentials live only in their dedicated encrypted credential model where required.

## 20. Logging/redaction

Structured logger must redact keys/patterns including authorization, token/access/refresh token, client/webhook secret, private key material, OAuth codes/state, PKCE verifier, credential key, and Telegram bot token.

Authentication/gateway HTTP errors must not echo raw GitHub response bodies that may contain credential material.

P2.3 setup/OAuth HTML errors and Telegram repository error renderers consume stable local categories/messages rather than raw upstream bodies.

Do not log full webhook bodies by default for private repositories. Prefer event IDs and selected safe metadata.

## 21. Audit log

Audit user-triggered writes with operation id, Telegram user id, GitHub account/installation identity, repository, operation/resource, timestamp, result/status, and safe GitHub result identifiers.

Do not place secret content or full sensitive file contents in audit rows.

P2.3 introduces no GitHub write and therefore does not treat read-cache synchronization as a write-audit substitute.

## 22. Error handling

User-facing errors must reveal enough to resolve the issue but not infrastructure secrets.

Raw traceback stays in protected logs with redaction. Telegram receives stable local errors/correlation where appropriate.

Gateway categories remain authentication, permission, not-found, conflict, validation, rate-limit, transient, and unexpected. P2.3 maps these to Arabic repository UI messages plus a distinct stale-selection message.

## 23. Dependency/supply-chain baseline

- exact direct runtime pins are maintained in `requirements.txt`;
- Python/platform-specific runtime selections/hashes are committed as PEP 751 locks generated by `pip lock`;
- CI regenerates and byte-compares locks for Python 3.12 and 3.13 Linux;
- use maintained libraries;
- run `pip-audit` in CI;
- do not install packages dynamically from Telegram input;
- CI includes repository secret scanning.

P2.3 introduces no runtime dependency drift. Implementation CI `33423169021` reports no known runtime vulnerabilities, no secret-scan findings, and no PEP 751 lock drift.

## 24. Known non-blocking maintenance warnings

Green P2.3 CI currently reports:

- Starlette/FastAPI `TestClient` deprecation warning for the current `httpx` integration/future `httpx2` direction;
- Alembic deprecation warning because `alembic.ini` does not explicitly set `path_separator` for `prepend_sys_path`.

These warnings are tracked maintenance debt; they are not test failures and must not be silently forgotten.

## 25. Deployment baseline

Before public production use:

- HTTPS required for webhook/setup/OAuth endpoints;
- restrict service filesystem permissions;
- private key readable only by service account;
- environment/secrets not world-readable;
- run service as non-root where practical;
- reverse proxy request-size/time limits aligned with upload policy;
- PostgreSQL credentials least-privileged;
- backups configured and restore tested;
- health endpoint must not leak secrets/config values.
