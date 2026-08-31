# GitDock — Security Model

Status: mandatory baseline

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
- `installation_id` returned through GitHub's setup/install redirect until independently verified through GitHub App and authenticated-user contexts.

Trusted only after validation:

- configured owner Telegram ID;
- GitHub App private key loaded from secure deployment storage;
- webhook secret from secure deployment configuration;
- validated/persisted confirmation state;
- a GitHub installation binding whose installation/account identity matched in both the App-authenticated and authenticated-user contexts.

## 3. Telegram access control

v1 is owner-only.

- Check Telegram user ID in middleware before command/callback/file processing.
- Do not trust username/display name for authorization.
- Unauthorized users should not receive sensitive information.
- Callback queries must also re-check authorization; a callback payload is not proof of identity.
- Production Telegram webhook should use Telegram's webhook secret-token mechanism when configured and validate the expected header.

## 4. GitHub App over broad PAT

Default rule: do not use a broad permanent PAT as the product's primary credential model.

Use GitHub App permissions and token contexts with least privilege.

GitHub App permissions start with no privileges and should be enabled by capability/milestone. Installation access tokens are short-lived and are generated as needed.

## 5. Credential handling

### Never

- commit real `.env` files;
- print tokens/private keys/client secrets/webhook secrets;
- send tokens to Telegram;
- include tokens in exception messages or audit rows;
- embed a token in a clone command shown to the user;
- store plaintext user access tokens in the database;
- assume a GitHub token's type or validity from a fixed legacy prefix/length alone.

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

### Implemented P2.1 state-storage rules

- The raw state value is never persisted. GitDock stores only `SHA-256(state)` for lookup/comparison.
- The PKCE code verifier is encrypted before persistence and includes the credential-encryption key version.
- State consumption is an atomic database update constrained by digest, intended flow, unconsumed status, and expiry. The successful update returns the minimum data needed to complete the flow.
- State survives process restart because it is database-backed rather than volatile FSM-only data.

### Implemented P2.1 installation-binding rule

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

Do not simplify this to trusting the query-string `installation_id` or matching account login alone.

## 8. Permission model

GitDock must have a central capability-to-permission map.

High-power permissions such as repository `Administration: write` and `Workflows: write` are not treated as baseline convenience permissions. They are enabled only when corresponding features are intentionally supported.

Repository operations must still respect the actual user's/repository's authority and GitHub branch protection/rules.

Reference: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app

## 9. Confirmation security

A Telegram button is not itself durable authorization for a destructive operation.

Pending confirmations include:

- opaque random ID;
- Telegram user id;
- operation type;
- target repository/resource;
- branch/ref/path and expected SHA when relevant;
- risk tier;
- exact intended payload summary/hash where practical;
- expiration;
- consumed state.

On confirm:

- re-check Telegram authorization;
- load pending confirmation server-side;
- ensure unexpired/unconsumed;
- ensure target still matches;
- re-check relevant preconditions;
- atomically consume or mark executing;
- apply once.

Tier 3 deletion additionally requires exact repository name entry before final button confirmation.

## 10. Stale-state/conflict protection

For file updates and batch operations:

- capture source blob SHA/base commit during review;
- verify it remains valid before write;
- if source moved, stop and ask user to refresh/review;
- do not silently overwrite newer remote work.

For merges/actions, refresh critical state immediately before the final write where practical.

## 11. Archive/ZIP security

Uploaded archives are untrusted.

Before extraction:

- enforce uploaded size limits;
- inspect member list;
- reject absolute paths;
- normalize paths and reject `..` traversal escaping workspace;
- reject device/special file types;
- reject or safely handle symlinks/hardlinks; v1 default is reject archive links;
- enforce max path depth;
- enforce file count;
- enforce total uncompressed size;
- detect duplicate/conflicting normalized paths;
- prevent overwrite outside the isolated workspace.

After extraction:

- never execute uploaded code;
- never automatically source `.env` or shell files;
- scan/flag secret-like filenames/content before GitHub upload where feasible;
- clean temporary workspace after completion/expiry.

## 12. Secret-like file safeguards for project sync

Default warnings/blocklist candidates include:

- `.env` (except explicitly safe examples such as `.env.example` after review)
- private keys (`*.pem`, `id_rsa`, etc.)
- credential/token files
- local database files when unexpected
- auth/session cache directories

The scanner is a safety layer, not a guarantee. It must avoid claiming that an upload is secret-free.

## 13. Repository path safety

- Canonicalize paths as repository-relative POSIX-style paths.
- Reject leading slash, drive-letter paths, NUL, and path traversal.
- Do not allow UI short IDs to be interpreted directly as paths without server-side resolution.
- Treat `.github/workflows/*` as a special protected area requiring Workflows capability.

## 14. Command-generation safety

Clone/setup/run feature generates commands only.

- Never insert access tokens into user-visible commands.
- Quote shell arguments correctly per OS.
- Do not automatically execute README commands.
- Treat repository-controlled scripts and README content as untrusted instructions.
- Inferred run/setup commands come from trusted templates plus detected project metadata, with uncertainty labeled.

## 15. SSRF/network restrictions

Core GitHub clients should target configured official GitHub API/GraphQL endpoints and approved GitHub hosts. Do not implement a generic “fetch URL from Telegram” capability as part of the GitHub gateway.

Redirects/downloads (for artifacts/releases) need host and size validation according to the feature's design.

### Implemented P2.2 REST gateway rules

- The canonical REST transport accepts repository-relative API paths or HTTPS URLs whose host is exactly `api.github.com`.
- Scheme-relative URLs, credential-bearing URLs, non-HTTPS absolute URLs, and external hosts are rejected before network I/O.
- Pagination `Link` targets are validated through the same canonical host policy before they can be followed.
- The REST client does not follow HTTP redirects automatically; later artifact/release download flows must introduce a separate reviewed redirect policy rather than weakening the core API client.
- A repeated pagination next-link is treated as an unexpected gateway failure, and page traversal is capped by the configured safety limit.

These rules make pagination incapable of becoming an arbitrary URL fetcher merely because GitHub/external input supplied a `Link` value.

## 16. GitHub API writes

- Use preconditions/current SHA where endpoints support them.
- Serialize conflicting Contents API create/update/delete operations for the same path; GitHub documents conflicts when create/update and delete operations are run concurrently.
- Batch multi-file changes coherently instead of racing many independent writes.
- Do not blindly retry destructive/non-idempotent writes after an uncertain network result; first reconcile state.

### Implemented P2.2 retry boundary

- `GET` and `HEAD` use bounded retry behavior for transient network failures and selected transient HTTP statuses.
- Writes are `RetryMode.NEVER` by default. A higher layer must explicitly opt an operation into safe retry only when its semantics/preconditions make replay safe.
- Backoff is bounded exponential delay with jitter and the global configured retry ceiling.
- Rate-limit responses are translated and surfaced with parsed rate-limit metadata instead of being blindly retried as generic transient failures.

Reference: https://docs.github.com/en/rest/repos/contents

## 17. GitHub Actions safety

- Actions read is separate from Actions write.
- Manual dispatch requires showing workflow, ref, and input values before confirmation.
- Re-run/cancel operations target explicit run/job IDs.
- Never display Actions secrets.
- Editing workflow YAML requires explicit Workflows write permission and normal file-review safeguards.

Reference: https://docs.github.com/en/rest/actions/workflows

## 18. Database security

- Parameterized ORM/query use only; no string-concatenated SQL from user input.
- Unique constraints for delivery IDs and identity bindings.
- Transactions for consume-and-execute confirmation transitions where applicable.
- Migration scripts reviewed/tested.
- Database backups and access controls are deployment concerns to document before production launch.

## 19. Logging/redaction

Structured logger must redact keys/patterns including:

- `authorization`
- `token`
- `access_token`
- `refresh_token`
- `client_secret`
- `webhook_secret`
- private key material
- OAuth codes
- OAuth state
- PKCE verifier
- Telegram bot token

Authentication HTTP errors must not echo raw GitHub response bodies that may contain credential material.

P2.2 extends the same rule to the general GitHub REST gateway: translated exceptions expose stable categories, status/request identifiers and safe rate-limit metadata, but do not embed the raw GitHub response body. Parser/shape failures likewise use a stable generic message rather than dumping returned payloads.

Do not log full webhook bodies by default for private repositories. Prefer event IDs and selected safe metadata.

## 20. Audit log

Audit user-triggered writes with:

- operation id;
- Telegram user id;
- GitHub account/installation identity;
- repository;
- operation name;
- resource target;
- timestamp;
- result/status;
- GitHub response identifiers such as commit/issue/PR/run IDs.

Do not place secret content or full sensitive file contents in audit rows.

## 21. Error handling

User-facing errors must reveal enough to resolve the issue but not infrastructure secrets.

Raw traceback stays in protected logs with redaction. Telegram receives a stable operation/correlation ID.

P2.2 defines stable gateway categories for authentication, permission, not-found, conflict, validation, rate-limit, transient, and unexpected response failures. Application services/renderers must consume these categories rather than branch on arbitrary GitHub body text.

## 22. Dependency/supply-chain baseline

During P1/P2.1/P2.2:

- exact direct runtime pins are maintained in `requirements.txt`;
- Python/platform-specific runtime selections/hashes are committed as PEP 751 locks generated by `pip lock`;
- CI regenerates and byte-compares locks for Python 3.12 and 3.13 Linux;
- use maintained libraries;
- run dependency vulnerability review (`pip-audit`) in CI;
- do not install packages dynamically based on Telegram input;
- CI includes repository secret scanning.

P2.1 crypto/JWT runtime dependencies are exactly pinned to `PyJWT==2.13.0` and `cryptography==50.0.1` and are included in both supported runtime locks.

P2.2 introduces no new runtime dependency or database schema change; it builds on the already pinned `httpx` transport and standard-library parsing primitives. The implementation-head CI run `33406986504` reported no known runtime vulnerabilities, no secret-scan findings, and no PEP 751 lock drift.

## 23. Deployment baseline

Before public production use:

- HTTPS required for webhook endpoints;
- restrict service filesystem permissions;
- private key file readable only by service account;
- environment/secrets not world-readable;
- run service as non-root where practical;
- reverse proxy request-size/time limits aligned with upload policy;
- PostgreSQL credentials least-privileged;
- backups configured and restore tested;
- health endpoint must not leak secrets/config values.
