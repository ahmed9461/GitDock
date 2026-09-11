# GitDock — Security Model

Status: mandatory baseline + verified P2 foundations + P2.3 repository-read controls + P3.1 search isolation + P3.2 authorization lifecycle + P3.3 repository-administration controls + P4.1 file-write controls + P4.2 branch/commit controls.

## 1. Security goals

Protect:

- GitHub repositories and write authority;
- Telegram owner identity and operation intent;
- GitHub App private key, client secret, webhook secret, installation/user tokens;
- private repository metadata/content;
- staged file-write content and preconditions;
- branch-create target/base/preconditions;
- future uploaded ZIP/project data;
- audit integrity and durable confirmation/operation state.

The main risk is not only credential theft. GitDock must also resist accidental clicks, stale state, callback replay, forged webhooks, unsafe archives, overpowered credentials, blind overwrite, and replay of a write whose remote outcome is uncertain.

## 2. Trust boundaries

Untrusted inputs include:

- Telegram messages/callbacks/uploads;
- GitHub webhook bodies before signature validation;
- repository names, refs, paths, branch names, README text, file contents, commit messages;
- archive paths/metadata;
- GitHub API responses until structurally validated;
- OAuth/setup callback parameters until server-side state/identity checks succeed;
- setup/install `installation_id` until independently verified;
- repository IDs in Telegram callbacks until scoped server-side resolution succeeds;
- local repository cache as potentially stale navigation state, never authorization proof;
- opaque confirmation/staging tokens until DB state/preconditions are loaded and validated.

Trusted only after validation:

- configured Telegram owner ID;
- deployment secrets loaded from secure storage;
- validated one-time OAuth/confirmation state;
- installation binding whose App/user identities match and are active;
- durable user account identity from authenticated `/user`;
- repository state refreshed from GitHub when authority/preconditions require it;
- P3.3 administration execution after confirmation + current preconditions + correct credential context;
- P4.1 file execution after staged confirmation + branch/file preconditions + scoped write token;
- P4.2 branch creation after persisted confirmation + exact base-SHA revalidation + target-absence recheck + scoped write token.

## 3. Telegram access control

v1 is owner-only.

- Check Telegram numeric user ID in middleware before command/callback/file processing.
- Username/display name is not authorization.
- Unauthorized users receive no sensitive information.
- Callback queries re-check authorization; callback payload is not identity proof.
- Production Telegram webhook validates configured secret-token header.

Repository/account/file/git-tool callbacks are transport identifiers only. User, repository/installation, operation, expiry, consumed state, target, and relevant preconditions are validated server-side.

## 4. GitHub App over broad PAT

Do not use a broad permanent PAT as the product's primary credential model.

Use GitHub App permissions and operation-specific token contexts with least privilege.

Verified contexts:

- P2.3/P3.1: read-only repository/search paths;
- P3.2: durable user context, not blanket repository administration;
- P3.3 personal/organization repository creation: durable user OAuth context;
- P3.3 repository update/delete: installation token scoped to selected repository with `administration: write`;
- P4.1 file reads: repository-scoped installation context with contents read;
- P4.1 file create/update/delete: repository-scoped installation token with `contents: write`;
- P4.1 `.github/workflows/*` writes additionally require `workflows: write`;
- P4.2 branch/commit reads: current installed-repository read context through canonical resolver/gateway;
- P4.2 branch create: repository-scoped installation token with `contents: write` only after confirmation and precondition revalidation.

## 5. Credential handling

Never:

- commit real `.env` files;
- print/send tokens, private keys, client/webhook secrets;
- embed tokens in clone commands;
- store plaintext durable user access/refresh tokens;
- store credentials/OAuth/private keys in repository cache, pending confirmations, file-write staging, or audit rows;
- render OAuth code/state, PKCE verifier, token material, or raw upstream auth body in Telegram/HTTP errors.

Durable user credentials use authenticated encryption through the maintained `cryptography` library and GitDock's versioned Fernet abstraction. Master key stays outside DB/repository; key version is persisted; rotation supports old-key decrypt/new-key encrypt.

Installation tokens remain short-lived provider output and are not persisted in P4.1/P4.2 operation state.

## 6. GitHub webhook validation

Mandatory order for future P5 ingestion:

1. read original raw bytes;
2. require `X-Hub-Signature-256`;
3. HMAC-SHA256 with webhook secret;
4. constant-time compare;
5. reject mismatch before JSON/business processing;
6. parse/route only after validation;
7. deduplicate delivery ID.

## 7. OAuth/user authorization security

- high-entropy one-time state;
- bind state to GitDock user and intended flow;
- short DB-backed expiry;
- raw state never persisted, only SHA-256 digest;
- PKCE S256;
- encrypted PKCE verifier;
- server-side code exchange;
- authenticated `/user` identity validation;
- credential/token/state/verifier redaction.

### Installation binding

Setup/install `installation_id` is untrusted. Persist binding only after same installation/account identity is resolved under App and authenticated-user context, identities match, suspension checks pass, and cross-user conflicts are rejected.

### Credential generation

`GitHubAccount.credential_generation` is a durable concurrency/version precondition. New credentials or clearing credentials advances generation. Long-running refresh/disconnect results persist only if current generation/account/authorization state still matches.

## 8. Permission model

Capabilities map centrally to GitHub App permissions/token context. High-power permissions such as Administration write and Workflows write are not convenience defaults.

Handlers never build permission dictionaries directly.

P4.1:

- ordinary file writes request `contents: write`;
- workflow path additionally requests `workflows: write`;
- token request is scoped to selected repository ID;
- archived repository write rejected before staging.

P4.2:

- branch/commit reads do not request branch-write authority;
- branch create is the only P4.2 write;
- write authority is requested only after confirmation consumption and base/target revalidation;
- token is scoped to the selected repository ID;
- required capability is `contents: write` plus metadata read as resolved centrally;
- no branch force-update, force-push, or deletion capability is exposed in normal v1 UI.

GitHub branch protection/rules remain authoritative. Creating a new ref does not grant authority to bypass repository rules.

## 9. Confirmation security

A Telegram button is not durable authorization.

`pending_confirmations` stores a digest of the opaque token plus user, operation, target fingerprint, safe payload/preconditions, risk tier, expiry, consumed state, and timestamps.

On confirm: re-check user, load intended operation, require unexpired/unconsumed state, atomically consume, reload current target/preconditions, then apply at most once.

### P3.2 local disconnect

Fingerprint current account identity, credential generation, and installation set. Reauthorization/install-set change makes older confirmation stale. Local disconnect never claims remote App uninstall.

### P3.3 repository administration

Create Tier 1, update Tier 2, delete Tier 3 + exact current `owner/name`. Edit/back/cancel consumes pending authority.

### P4.1 file writes

Dedicated restart-safe `file_write_sessions` staging + confirmation binds repository/installation/user, branch/path, branch-head SHA, expected file SHA, desired blob/content digest, operation/risk/expiry. Temporary create/update bytes have 15-minute TTL and are scrubbed on consume/cancel/supersede/expiry/prune.

### P4.2 branch create

P4.2 reuses `pending_confirmations` and `audit_log`; no new migration is required.

Confirmation properties:

- operation type: branch create;
- risk tier: **Tier 1**;
- target fingerprint binds selected GitHub repository ID + target branch + base ref + resolved base commit SHA;
- safe payload contains only those stable identifiers/preconditions;
- no credential/token is stored;
- raw confirmation token is not persisted by the confirmation service;
- cancel/reuse/invalid/expired state cannot execute later.

Execution after consumption must re-resolve repository context, re-resolve base ref, require exact staged base SHA, and re-check target branch absence before requesting write authority.

## 10. P4.1 staging confidentiality/integrity

Temporary staged file bytes are restart-safety data, not audit data.

- store SHA-256 content digest and Git blob SHA;
- recompute digests on consume;
- tampered staging is consumed/scrubbed and does not write;
- bytes stay out of confirmation payload/fingerprint and audit details;
- production DB backups/access controls must treat temporary staged bytes as private repository content.

## 11. Repository path/ref/branch safety

Repository paths:

- repository-relative POSIX form;
- reject NUL/backslash/leading slash/drive prefixes/dot-dot and overlong paths;
- long paths remain server-side rather than trusted callback text.

Refs:

- non-empty trimmed text within configured limit;
- reject control characters and dangerous Git-invalid patterns handled by existing validators;
- endpoint path components are percent-encoded before REST requests;
- GitHub remains final authority for whether a ref exists/is accessible.

P4.2 target branch names receive dedicated local branch-name validation before create-ref. No create-ref happens for missing/invalid base, and GitHub validation errors are surfaced safely without raw upstream body echo.

## 12. P4.1 stale-state/conflict protection

Before a staged file write, GitDock requires current repository context, exact branch-head SHA, and target absence/file SHA as appropriate. Any mismatch yields stale with no write. This deliberately rejects even unrelated branch movement after review.

## 13. P4.2 stale-state/conflict protection

GitHub remains source of truth for branches and commits.

Before preview:

- base ref must resolve to a concrete commit SHA;
- target branch must not exist.

Before execution after confirmation:

- current repository context is resolved again;
- base ref is resolved again and must equal staged `base_sha` exactly;
- target branch is queried again and must still be absent;
- only then is the repository-scoped write token requested.

Outcomes:

- changed base → `STALE`, no create-ref;
- existing target → `EXISTS`, no replacement/force update;
- missing/invalid confirmation → `INVALID`, no write;
- successful exact create → `APPLIED`;
- ambiguous remote state after write error → reconciliation, otherwise `UNCERTAIN`.

## 14. Write execution and uncertain-result reconciliation

Write-like GitHub methods remain no-retry by default.

### P3.3 repository administration

Operation-specific reconciliation remains authoritative.

### P4.1 files

Potentially uncertain PUT/DELETE outcomes re-fetch target state and compare desired SHA/deletion state; never blindly replay.

### P4.2 branch create

- create uses one POST to `/git/refs` with `refs/heads/<target>` and staged base SHA;
- transport does not retry POST;
- if gateway reports an error that may have occurred after remote application, service queries target branch;
- target exists at exact staged SHA → reconciled `APPLIED`;
- target missing/unreadable/unexpected SHA without proof → explicit `UNCERTAIN`;
- no second automatic create-ref request is issued.

This is important because replaying a write merely because the response was lost can misreport or conflict with current GitHub state.

## 15. Audit/logging

Audit is not a credential or content store.

Safe metadata may include:

- GitDock user ID;
- operation name;
- repository ID/full name;
- target branch/ref/path;
- expected/base/head SHA;
- risk tier;
- GitHub request ID;
- final/reconciled state.

P4.2 branch-create audit records branch, base ref, base SHA, risk tier, request ID where available, and outcome. It does not store access/installation tokens or raw GitHub bodies.

Structured logging redacts authorization headers/tokens/secrets/OAuth/PKCE/private keys and avoids raw private webhook/auth bodies by default.

## 16. Repository callback/cache safety

`repositories_cache` is navigation state, not authorization.

- safe non-secret metadata only;
- scoped to GitDock user + installation;
- stable numeric GitHub repository ID for compact callback resolution;
- current user/installation context required;
- tokens obtained only through providers;
- authoritative GitHub state re-fetched where required;
- never infer P3.3/P4.1/P4.2 write authority from cache existence.

## 17. GitHub API/network restrictions

Canonical REST transport accepts repository-relative API paths or canonical HTTPS `api.github.com`. It rejects scheme-relative, credential-bearing, external-host, non-HTTPS, fragment-bearing, and noncanonical targets before network I/O. Generic transport does not follow redirects automatically.

GET/HEAD bounded retry remains separate from write safety.

P4.2 branch/commit refs are encoded as URL path components; tests assert encoded raw path for slash-containing compare refs.

## 18. GitHub Actions/workflow safety

Actions read/write remains future P7. Workflow dispatch must show workflow/ref/inputs and require confirmation; secrets are never displayed. P4.1 edits under `.github/workflows/*` already require `workflows: write` in addition to file-write safeguards.

## 19. Archive/ZIP security

Future P8 uploads remain untrusted. Enforce upload/member/depth/count/uncompressed-size limits, traversal/absolute/device/symlink/hardlink policy, duplicate normalized paths, isolated workspace, and cleanup. Never execute uploaded code or auto-source environment/shell files.

## 20. Clone/setup/run safety — P4.3

Clone/setup/run generates commands only.

- never insert tokens;
- quote per OS;
- never auto-execute README/script commands;
- repository instructions are untrusted text;
- use trusted templates plus detected metadata;
- label uncertainty/confidence/source.

## 21. Database security

- parameterized ORM/query use;
- transactions for consume/apply transitions;
- migrations reviewed/tested;
- repository cache contains no credentials;
- audit rows contain safe metadata only;
- temporary P4.1 staged bytes are treated as private repository content and scrubbed through lifecycle.

Migration chain through P4.2 remains:

- `0003` repository cache;
- `0004_user_auth` credential-generation/confirmation lifecycle;
- `0005_audit_log` GitHub-write audit rows;
- `0006_file_write_sessions` restart-safe one-file staging.

P4.2 requires no schema migration. PostgreSQL 17 upgrade → downgrade → upgrade through `0006_file_write_sessions` passed in CI `34647181024`.

## 22. Security verification through P4.2

Implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518`, CI `34647181024`:

- 165 tests on Python 3.12/3.13;
- mypy clean on 94 source files;
- Ruff format/lint green;
- compile green;
- `pip-audit`: no known runtime vulnerabilities;
- `detect-secrets`: no findings;
- PEP 751 locks reproduced byte-for-byte;
- PostgreSQL migration round-trip green.

Direct P4.2 security regressions include duplicate target, missing base, stale base, cancellation/reuse, scoped write token, one POST on transient failure, and uncertain-create reconciliation.

## 23. Hard prohibitions

- No broad permanent PAT as normal product credential model.
- No credential/token material in Telegram callbacks/messages/audit rows.
- No arbitrary outbound URL fetcher hidden inside repository/browser features.
- No blind retry of write-like GitHub operations.
- No silent overwrite on stale file or moved branch base.
- No normal v1 force-push/force branch update UI.
- No automatic execution of repository instructions.
- No treating repository cache/callback possession as authority.
