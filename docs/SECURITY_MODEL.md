# GitDock — Security Model

Status: mandatory baseline through verified P5.1 secure webhook-ingestion implementation; delivery closeout pending.

## 1. Security goals

Protect GitHub repositories/write authority, Telegram owner identity/intent, GitHub App/client/webhook secrets and tokens, private repository content, staged write content/preconditions, durable webhook payloads/processing state, and audit/confirmation integrity.

GitDock must resist credential theft, accidental clicks, stale/replayed authority, forged webhooks, unsafe repository/archive input, overpowered credentials, blind overwrite, and blind write replay.

## 2. Trust boundaries

Untrusted inputs include Telegram messages/callbacks/uploads; GitHub webhook body and headers until signature verification succeeds; repository names/refs/paths/README/scripts/files/commit text; GitHub API responses until validated; OAuth/setup parameters; local cache; and opaque confirmation/staging tokens until durable state is loaded.

Trusted only after validation include configured deployment secrets, owner identity, consumed server-side confirmation authority, verified GitHub identities/permissions, current remote preconditions, and authenticated GitHub webhook bytes/metadata.

## 3. Telegram access control

v1 is owner-only. Telegram numeric user ID is checked before sensitive routing. Username/display name/callback possession is never authorization proof. Production Telegram webhook validates its configured secret-token header.

## 4. GitHub credential model

GitHub App remains primary. Do not use a broad permanent PAT as normal product credential model.

- user OAuth context is encrypted and refresh-aware;
- repository administration requests scoped administration authority only when required;
- one-file writes request repository-scoped `contents: write`; workflow files additionally require `workflows: write`;
- branch creation requests repository-scoped `contents: write` only after persisted confirmation and current precondition revalidation;
- installation tokens are short-lived and not persisted in operation state.

## 5. Credential handling prohibitions

Never commit/print/send tokens, keys, client/webhook secrets, OAuth state/code, PKCE verifier, auth headers, or raw auth response bodies. Never embed credentials in generated clone/run commands. Durable user credentials remain encrypted with the versioned Fernet abstraction and deployment key outside the repository/DB.

## 6. P5.1 GitHub webhook authentication

Mandatory order implemented in P5.1:

1. receive `POST /github/webhook` in existing FastAPI ingress;
2. require configured `GITDOCK_GITHUB_WEBHOOK_SECRET` or return unavailable;
3. read the **original raw body bytes** with a `25_000_000` byte ceiling;
4. require a syntactically valid `X-Hub-Signature-256` SHA-256 digest;
5. compute HMAC-SHA256 with the configured webhook secret over those exact raw bytes;
6. compare using constant-time `hmac.compare_digest`;
7. reject missing/malformed/forged signature with no durable acceptance;
8. only after authentication validate/trust `X-GitHub-Delivery` and `X-GitHub-Event`;
9. durably insert/deduplicate the delivery before HTTP 202 acknowledgement.

The webhook secret, supplied signature, raw auth material, and raw payload are never echoed in normal HTTP responses.

## 7. P5.1 metadata/body safety

- `X-GitHub-Delivery` is required, bounded to 128 characters, and restricted to a safe identifier character set.
- `X-GitHub-Event` is required, bounded to 128 characters, and restricted to a safe event-name character set.
- authenticated malformed metadata returns a client error without persistence.
- unauthenticated malformed metadata still fails at the signature boundary first.
- request body is bounded to exactly `25_000_000` bytes; over-limit bodies are rejected without durable persistence.
- P5.1 does not trust/parse event-specific JSON for business behavior; normalization is deferred to P5.2.

## 8. Durable idempotency/conflict safety

`github_webhook_deliveries.delivery_id` is unique and is the durable idempotency key.

- exact same delivery ID + event + body is duplicate/idempotent;
- duplicate acceptance does not create a second durable row/work item;
- same delivery ID with different event/body is an explicit conflict;
- deduplication is DB-backed, not process-memory-backed, so it survives restarts and multi-process deployment.

Payload SHA-256, byte length, and stored raw bytes are compared for exact duplicate semantics rather than assuming an ID collision/reuse is harmless.

## 9. Durable worker/retry safety

P5.1 states: `pending`, `processing`, `failed`, `processed`.

- claim increments `attempt_count` and records `processing_started_at`;
- PostgreSQL claim uses row locking/skip-locked semantics for normal concurrent workers;
- failed work records a bounded safe `last_error_code` and `next_attempt_at`, not arbitrary exception text;
- processing rows whose lease expires become claimable again after a crash/restart;
- processed rows can be pruned after retention expiry;
- downstream work must not create a second notification merely because a delivery is retried.

SQLite is a portable development/test target; production concurrency guarantees target PostgreSQL.

## 10. Raw webhook payload confidentiality/retention

Raw payloads are private durable work data, not audit/logging data.

- store only because restart-safe downstream processing needs authenticated original content;
- apply bounded size and retention;
- do not copy raw payloads into audit rows;
- do not include raw payloads in normal route responses;
- do not log unbounded raw payloads, signature values, or webhook secrets;
- production DB access/backups must treat raw webhook payloads as potentially private repository/account data.

## 11. OAuth / installation binding

OAuth state is high-entropy, one-time, short-lived, server-bound, persisted as digest only, with PKCE S256. Authenticated `/user` resolves durable user identity. App setup `installation_id` is candidate input until independently verified under App and authenticated-user contexts. Credential generation guards stale concurrent refresh/disconnect writes.

## 12. Confirmation/staging safety

Telegram buttons are transport, not durable authority. `pending_confirmations` binds user/operation/target/risk/expiry/consumption state. Repository admin, file writes, and branch create revalidate current remote preconditions after consumption before mutation.

File staging stores temporary private bytes only for the bounded review lifecycle; integrity digests are rechecked and bytes are scrubbed on consume/cancel/supersede/expiry/prune.

## 13. Repository/ref/path safety

Repository paths remain normalized repository-relative POSIX paths and reject traversal/control/absolute/drive-prefix patterns. Refs/branches are bounded/validated and URL path components are encoded. GitHub is final authority for existence/accessibility.

## 14. Write execution/reconciliation

Write-like GitHub methods are not blindly retried. Repository administration, Contents writes, and branch creation issue the intended write once and reconcile remote state if response loss makes outcome uncertain. No normal v1 force-push/force branch-update UI exists.

## 15. Repository callback/cache safety

Repository cache/callback presence is navigation context, never authorization. Current user/installation/repository state is resolved server-side and tokens come only from configured providers.

## 16. Network restrictions

Canonical outbound REST transport accepts repository-relative API paths or canonical HTTPS `api.github.com`, rejects external/credential-bearing/non-HTTPS/protocol-relative/fragment targets, and does not follow redirects automatically. P5.1 inbound webhook verification does not add an outbound fetch path.

## 17. Clone/setup/run safety

Command generation only. Never insert tokens or automatically execute README/script instructions. Repository text is untrusted. Use trusted templates, bounded evidence, shell-aware quoting, and confidence/source labels.

## 18. Archive/Actions future boundaries

Future Actions dispatch must preview workflow/ref/inputs and never expose secrets. Future archive/ZIP intake remains untrusted and must enforce traversal/link/device/count/depth/size/cleanup controls before use.

## 19. Database security / migration chain

- parameterized ORM/query use;
- transactions for consume/claim/apply transitions;
- migrations reviewed and tested on SQLite/PostgreSQL;
- repository cache/audit contain no credentials;
- temporary staged file bytes and raw webhook payloads are treated as private content with bounded lifecycle.

Migration chain now includes:

- `0003` repository cache;
- `0004_user_auth` credential/confirmation lifecycle;
- `0005_audit_log`;
- `0006_file_write_sessions`;
- `0007_github_webhook_deliveries.py` with revision `0007_webhook_inbox`.

PostgreSQL 17 upgrade → downgrade → upgrade through revision `0007_webhook_inbox` passed CI `34652564335`.

## 20. Security verification — P5.1 implementation head

Head `e55c6e99001bb657ed2064459e92caca1f2e3481`, CI `34652564335`:

- **213 tests** on Python 3.12/3.13;
- mypy clean on **104 source files**;
- Ruff format/lint green on **176 files**;
- compile green;
- `pip-audit`: no known runtime vulnerabilities;
- `detect-secrets`: no findings;
- PEP 751 locks reproduced byte-for-byte;
- PostgreSQL migration round-trip green.

Direct webhook security regressions cover forged/missing/malformed signatures, changed raw body, auth-before-metadata ordering, bounded body/headers, duplicate/conflict semantics, restart persistence, retry/lease recovery, route secrecy, and migration behavior.

## 21. Hard prohibitions

- No broad permanent PAT as normal product credential model.
- No credential/token/secret/signature material in Telegram callbacks/messages/audit rows.
- No arbitrary outbound URL fetcher hidden inside features.
- No blind replay of GitHub write-like operations.
- No silent overwrite on stale file or moved branch base.
- No normal v1 force-push/force branch-update UI.
- No automatic execution of repository instructions.
- No treating repository cache/callback possession as authority.
- No trusting/parsing webhook event business content before signature verification.
- No in-memory-only webhook deduplication when durable acceptance is claimed.
- No successful webhook acknowledgement before durable acceptance.
