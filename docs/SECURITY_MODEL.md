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
- OAuth callback parameters until state validation succeeds.

Trusted only after validation:

- configured owner Telegram ID;
- GitHub App private key loaded from secure deployment storage;
- webhook secret from secure deployment configuration;
- validated/persisted confirmation state.

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
- store plaintext user access tokens in the database.

### At rest

If GitHub user access/refresh material must be persisted:

- encrypt using an authenticated encryption scheme from a maintained crypto library;
- keep the encryption master key outside the database and repository;
- store token metadata separately from ciphertext;
- design for key rotation/versioning.

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
- Bind authorization state to one Telegram user and one intended flow.
- Store state server-side with short expiry.
- State is one-time use.
- Reject missing, mismatched, expired, or already-consumed state.
- Exchange authorization code only server-side.
- Redact codes/tokens from logs.
- Validate the resulting GitHub identity and bind it explicitly to the intended GitDock user.

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

## 16. GitHub API writes

- Use preconditions/current SHA where endpoints support them.
- Serialize conflicting Contents API create/update/delete operations for the same path; GitHub documents conflicts when create/update and delete operations are run concurrently.
- Batch multi-file changes coherently instead of racing many independent writes.
- Do not blindly retry destructive/non-idempotent writes after an uncertain network result; first reconcile state.

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
- Telegram bot token

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

## 22. Dependency/supply-chain baseline

During P1:

- pin/lock dependencies using the chosen Python dependency workflow;
- use maintained libraries;
- add dependency vulnerability review/update process;
- do not install packages dynamically based on Telegram input;
- CI should include a secret scan and dependency/security checks when tooling is selected.

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

## 24. Security Definition of Done for risky features

A Tier 2/3 feature is not complete until tests cover:

- authorized success;
- unauthorized Telegram user;
- missing GitHub permission;
- expired confirmation;
- reused confirmation;
- target changed/stale state;
- GitHub rejection;
- network timeout/uncertain outcome reconciliation where relevant;
- audit record behavior;
- secret redaction.

Archive sync additionally requires traversal/link/size/count/secret-warning tests.