# GitDock — Architecture Specification

Status: baseline architecture + verified P2 foundations + P3.1 search + P3.2 authorization + P3.3 repository-administration implementation

## 1. Architectural goals

- Clear separation between Telegram UI, GitHub transport/auth, domain rules, persistence, and background processing.
- Restart-safe handling for important multi-step operations, confirmations, and GitHub webhooks.
- Testability without real Telegram/GitHub network calls in normal CI.
- Least-privilege authentication.
- Easy owner-only v1 deployment with clean multi-user-ready service/persistence boundaries.
- No hidden direct coupling between button callbacks and raw GitHub API calls.
- GitHub remains authoritative for GitHub resources; local caches exist only for navigation/preferences/operation/auth state where justified.

## 2. High-level topology

```text
Telegram Client
      |
      v
+------------------------+
| FastAPI HTTP Ingress   |
| - Telegram webhook     |
| - GitHub webhook       |
| - setup/OAuth callback |
| - health/readiness     |
+-----------+------------+
            |
     +------+------+
     |             |
     v             v
aiogram UI     Webhook verifier
     |             |
     v             v
Application      event_inbox DB
Services            |
     |               v
     |          Event Worker
     |               |
     +-------+-------+
             |
             v
       GitHub Gateway
     REST/Auth clients
             |
             v
           GitHub

Shared persistence:
PostgreSQL + Alembic
```

## 3. Runtime modes

### Development

- Telegram long polling is allowed for convenience.
- GitHub webhook testing may use a secure tunnel or local replay fixture.
- SQLite may be used for local unit/integration tests where portability is preserved.

### Production

- FastAPI serves Telegram webhook, GitHub webhook, setup/OAuth callbacks, health/readiness.
- PostgreSQL is required.
- Service is suitable for systemd.
- HTTPS terminates at a trusted reverse proxy or application deployment layer.
- Background event worker may run in the same deployment initially but remains a separate application component with DB-backed work state.

## 4. Source layout

```text
gitdock/
├── app.py
├── core/
│   ├── config.py
│   ├── logging.py
│   └── constants.py
├── http/
│   └── routes/
├── telegram/
│   ├── bot.py
│   ├── callbacks.py
│   ├── routers/
│   │   └── repository_admin.py
│   ├── keyboards/
│   │   └── repository_admin.py
│   ├── renderers/
│   │   └── repository_admin.py
│   ├── states/
│   │   └── repository_admin.py
│   └── middleware/
├── github/
│   ├── auth.py
│   ├── auth_state.py
│   ├── binding.py
│   ├── client.py
│   ├── connection.py
│   ├── credentials.py
│   ├── errors.py
│   ├── models.py
│   ├── pagination.py
│   ├── permissions.py
│   ├── repositories.py
│   ├── repository_admin.py
│   └── token_provider.py
├── domain/
├── services/
│   ├── confirmations.py
│   ├── identity.py
│   ├── repositories.py
│   ├── repository_admin.py
│   ├── repository_admin_confirmations.py
│   ├── repository_reconciliation.py
│   ├── runtime.py
│   └── user_authorization.py
├── db/
│   ├── migrations/versions/0005_audit_log.py
│   └── models/audit.py
├── workers/
└── security/

tests/
├── unit/
├── integration/
├── contract/
└── fixtures/
```

Exact filenames may evolve, but the boundaries are intentional.

## 5. Layer responsibilities

### Telegram layer

Responsible for receiving updates, rendering Arabic screens, building keyboards, collecting input, and mapping UI actions to application services.

Must not call GitHub HTTP endpoints directly, contain raw database queries, or embed durable business/risk/token rules.

P2.3/P3.1/P3.2/P3.3 follow this rule: Home, repository/search/account/admin screens, connect/authorize/refresh/disconnect callbacks, and repository create/settings flows call application services/renderers; they do not construct OAuth requests, refresh grants, SQL, installation tokens, or GitHub REST requests in handlers.

P3.3 Telegram administration is split into centralized callback helpers, keyboards, renderers, FSM states, and a thin router. Repository IDs and opaque confirmation tokens are transported compactly; server-side services own authority, validation, token context, precondition checks, reconciliation, persistence, and audit.

### Application services

Orchestrate use cases, domain rules, persistence, GitHub gateways/auth clients, audit, permission checks, and confirmation flows.

Verified services include:

- owner identity resolution;
- `RepositoryReadService` for installed repository navigation/cache synchronization;
- public search service;
- `GitHubUserAuthorizationService` for durable user authorization status, encrypted credential persistence, expiry-aware refresh, and local disconnect;
- `ConfirmationService` for restart-safe one-time sensitive confirmations;
- `RepositoryAdminService` for repository create/update/delete planning, confirmation consumption, credential-context selection, precondition refresh, reconciliation, cache synchronization, and audit;
- repository-admin confirmation cancellation service for operation-specific one-time create/update/delete cancellation;
- repository reconciliation helpers for uncertain write outcomes;
- runtime composition that wires auth, connection, user/install token providers, read/admin services, confirmation services, gateways, encryption, and DB factories once.

### Domain layer

Contains mostly pure rules such as risk classification, path validation, sync planning, state transitions, event normalization, and confirmation requirements.

### GitHub transport/auth boundaries

`GitHubRestClient` is the canonical normal REST transport boundary for ordinary API requests. Authentication-specific OAuth/App endpoints remain behind the GitHub auth client rather than Telegram handlers.

P2.2 verified REST behavior:

- outbound request construction owned centrally;
- typed parser boundaries;
- `GitHubResponse[T]` / `GitHubPage[T]` safe status/request/rate/pagination metadata;
- GitHub media type, API version `2026-03-10`, and `GitDock/0.1` User-Agent centralized;
- `SecretStr` bearer material only materialized at outbound request boundary;
- absolute REST targets restricted to HTTPS `api.github.com`;
- hostile pagination targets rejected;
- repeated-link/page-limit guards;
- redirects not followed automatically;
- stable error categories without raw body echo;
- typed rate-limit metadata;
- bounded GET/HEAD retry; write-like methods no retry by default unless a higher-level use case explicitly establishes safe replay semantics.

P2.3 and P3.1 add endpoint-specific repository/search parsing on top of the transport. P3.2 extends the existing authentication client for authenticated `/user` identity and OAuth refresh-token grants; this is not a parallel general-purpose GitHub HTTP stack.

P3.3 adds typed repository-administration gateway methods on top of the same transport:

- personal create;
- organization create;
- repository update;
- repository delete.

Write-like methods remain no-retry at the transport layer. When a higher-level write failure can represent an uncertain remote outcome, `RepositoryAdminService` reconciles current GitHub state before deciding whether the operation was applied, remains uncertain, or failed.

### Persistence

Stores GitDock identity/auth state, preferences, audit/inbox state, operation/confirmation state, and narrowly justified cache/context. GitHub remains source of truth for GitHub resources.

## 6. Authentication flows

### Telegram owner authentication — v1

- `GITDOCK_TELEGRAM_OWNER_ID` is the owner allowlist baseline.
- Middleware rejects/ignores unauthorized users before sensitive routing.
- Future multi-user support replaces this boundary policy without changing core services.

### GitHub App installation binding

1. Create short-lived setup state bound to GitDock user.
2. User installs/authorizes GitHub App.
3. Treat returned `installation_id` only as untrusted candidate data.
4. Perform authenticated GitHub user authorization with fresh one-time state + PKCE.
5. Resolve installation under App context and authenticated-user context.
6. Bind only after installation/account identities match and installation is not suspended.

P2.3 wires this P2.1 flow into Telegram/FastAPI. P3.2/P3.3 do not weaken or replace the dual-context binding rule.

### Durable GitHub user authorization — P3.2

P3.2 turns the previously available encrypted credential abstraction into a complete durable lifecycle for later features that genuinely require user context.

Flow:

1. Begin `USER_AUTHORIZATION` through the existing DB-backed state service.
2. Generate PKCE S256 challenge/verifier using the existing implementation.
3. User authorizes through GitHub.
4. OAuth callback atomically consumes the expected one-time state and decrypts its PKCE verifier.
5. Exchange code server-side.
6. Resolve authenticated identity through `GET /user` using the returned user access token.
7. Bind that GitHub user identity to the intended GitDock user, rejecting cross-user identity conflicts.
8. Persist access/refresh credentials only through the versioned encrypted credential store.
9. Store expiry metadata separately and increment `credential_generation`.

Standalone reauthorization uses this flow directly and does not reinstall or rebind the GitHub App installation unless the flow actually contains an installation-binding candidate.

### Expiry-aware refresh — P3.2

- Load one active durable user authorization for the GitDock user.
- Decrypt credentials only inside the credential service boundary.
- If access token remains valid beyond the refresh margin, reuse it.
- If refresh is required, snapshot account ID + `credential_generation` before network I/O.
- Exchange the refresh token using GitHub's refresh-token grant.
- Treat the returned refresh token as the rotated replacement.
- Re-open a transaction and persist the rotated pair only if account/user/generation/authorization state still match the snapshot.
- If reauthorization/disconnect changed generation while the network request was in flight, fail closed instead of overwriting newer state.

### Repository administration token context — P3.3

P3.3 deliberately uses different credential contexts for different GitHub operations rather than a broad permanent token:

- personal repository create: durable GitHub user OAuth token;
- organization repository create: durable GitHub user OAuth token for an explicitly requested organization, subject to GitHub authorization;
- repository update/delete: installation token scoped to the selected repository ID with centralized `administration: write` permission request.

Repository cache presence alone never grants write authority. Update/delete begin from a GitHub-backed repository selection, then sensitive execution refreshes current repository state and current token/permission context before the mutation.

## 7. GitHub permission/capability model

Permission strings remain centralized, not scattered in handlers. Capabilities map to required GitHub App permissions and token context.

P2.3/P3.1 are Tier 0 read-only. P3.2 adds durable **user context**, not broad administration. P3.3 deliberately enables repository administration only through the central capability model. Update/delete request repository-scoped `administration: write`; create uses durable user context because GitHub's user/organization creation endpoints are user-context operations.

## 8. Database model baseline

Core persisted concepts include:

- GitDock users/Telegram identities;
- GitHub accounts/installations;
- durable GitHub OAuth state;
- minimal repository cache/preferences;
- `pending_confirmations`;
- append-oriented `audit_log` records;
- future durable high-impact operation sessions;
- webhook delivery/event state.

GitHub resource state remains authoritative remotely.

### P2.3 `repositories_cache`

Migration `0003` adds minimal repository cache for compact Telegram navigation. It is user/installation-scoped, contains safe non-secret metadata only, is synchronized from GitHub, prunes removed repositories, and never grants authority by itself. Repository detail re-fetches GitHub before render.

### P3.2 authorization lifecycle persistence

Migration `0004_user_auth` adds the durable P3.2 state needed for concurrency-safe credentials and confirmations.

Architectural rules:

- GitHub account credential ciphertext remains in the dedicated credential fields/model, not in callback/cache tables;
- `credential_generation` versions the credential lifecycle and changes on persist/clear;
- `pending_confirmations` stores opaque token digest, user, operation, target fingerprint, safe payload metadata, risk tier, expiry, consumed state, and timestamps;
- confirmation payload/fingerprint may contain stable IDs and preconditions but no access/refresh tokens, OAuth code/state, PKCE verifier, private key, or client secret;
- sensitive execution reloads current DB state and compares preconditions before mutation.

The first attempted migration revision label was longer than Alembic's default 32-character version column. The stable revision ID is intentionally short: `0004_user_auth`.

### P3.3 administration audit persistence

Migration `0005_audit_log` adds append-oriented `audit_log` records for repository administration.

Audit entries may include safe operation/status/user/repository/request/reconciliation metadata, but never access tokens, refresh tokens, installation tokens, OAuth code/state, PKCE verifier, private key, client secret, or raw upstream auth/error bodies. Successful update refreshes cache state; successful/reconciled delete removes the target from local repository cache.

## 9. Confirmation architecture

A Telegram callback is transport, not durable authorization.

### P3.2 local disconnect

1. server loads current active user authorization and installation set;
2. creates a short-lived opaque confirmation and stores only its digest;
3. target fingerprint binds account ID/GitHub user ID/credential generation/current installation IDs;
4. Telegram receives only the opaque confirmation token in compact callback data;
5. confirm atomically consumes server-side confirmation state;
6. service reloads account + installation preconditions;
7. stale/reused/cancelled/invalid state exits without deletion;
8. only a matching confirmation clears local credential/binding/cache/pending state once.

Home explicitly consumes pending disconnect confirmations so abandoned old messages cannot retain active destructive authority.

### P3.3 repository administration

P3.3 reuses the same durable confirmation storage with operation-specific rules:

- create is Tier 1;
- repository update is Tier 2;
- repository delete is Tier 3;
- delete requires exact typed current `owner/name` before a delete confirmation is issued;
- target fingerprints bind the current operation/request/repository preconditions;
- confirmation consumption is single-use and user/operation-bound;
- stale, expired, reused, cancelled, wrong-target, or wrong-name paths fail closed;
- create/update/delete confirmation cancellation itself is persisted and one-time;
- edit/back/cancel consumes the pending confirmation before navigation, so an old Telegram message cannot retain write authority.

## 10. Exact P3.2 disconnect boundary

Local disconnect means **GitDock-local** cleanup:

- encrypted GitHub user credentials cleared;
- GitDock installation binding rows deleted;
- local repository navigation cache deleted;
- relevant unconsumed local OAuth/confirmation state invalidated.

It does not call GitHub to uninstall the App and does not represent itself as remote revocation. Installation state on GitHub remains GitHub's responsibility until a future explicitly designed remote-uninstall feature exists.

Legacy P2.3 installation-only state is valid input to local disconnect even when no durable UAT exists.

## 11. P3.3 repository write lifecycle

### Create

1. validate the create request and current durable user authorization;
2. persist Tier 1 confirmation with safe request fingerprint/payload;
3. confirmation atomically consumes once;
4. obtain current durable user token;
5. issue personal or organization create once;
6. on a potentially uncertain write error, reconcile current GitHub state instead of replaying the POST;
7. audit direct/reconciled/uncertain/failure outcome.

### Update

1. resolve selected repository inside current GitDock user/installation context;
2. fetch current repository snapshot and persist Tier 2 confirmation bound to the expected snapshot/request;
3. confirmation atomically consumes once;
4. refresh current repository state and reject stale preconditions;
5. obtain repository-scoped installation token with `administration: write`;
6. issue PATCH once;
7. on a potentially uncertain write error, re-fetch and compare remote state to requested mutation;
8. audit outcome and refresh local cache when applied.

### Delete

1. resolve/fetch current repository;
2. require exact typed current `owner/name`;
3. persist Tier 3 confirmation bound to the current repository snapshot;
4. confirmation atomically consumes once;
5. refresh current repository state and reject stale preconditions;
6. obtain repository-scoped installation token with `administration: write`;
7. issue DELETE once;
8. on a potentially uncertain write error, determine whether the repository still exists rather than replaying DELETE;
9. audit outcome and remove local cache entry when deletion is confirmed applied.

`RepositoryAdminState` distinguishes at least `APPLIED`, `STALE`, `INVALID`, and `UNCERTAIN`, preventing ambiguous remote outcomes from being falsely reported as ordinary success/failure.

## 12. Webhook ingestion pipeline

1. Read raw bytes.
2. Verify `X-Hub-Signature-256` with constant-time HMAC-SHA256 comparison.
3. Read event/delivery identifiers.
4. Validate supported envelope.
5. Insert delivery idempotently.
6. Persist required routing/work data.
7. Acknowledge HTTP quickly.
8. Worker normalizes/enriches/applies preferences.
9. Render Telegram notification.
10. Mark processed or retryable/terminal failure.

Duplicate delivery IDs must not create duplicate user-visible notifications.

## 13. Canonical notification event model

Renderers consume normalized delivery/event/action/repository/actor/target/title/summary/url/time/severity values rather than arbitrary raw webhook structures.

## 14. File operations

For a single-file update: fetch current SHA, collect replacement, show path/branch/diff summary, persist confirmation with expected SHA, and write only if precondition remains valid. Stale remote state stops the write and requires refresh/review.

## 15. ZIP/project synchronization architecture

Uploads use isolated temporary workspaces, member pre-scan, traversal/link/file-count/depth/uncompressed-size guards, and secret-like warnings before any repository write.

A persisted immutable `SyncPlan` records base commit, target strategy, added/modified/deleted/unchanged/binary/large/excluded files, warnings, and statistics. If base changes before apply, re-plan.

Apply prefers Git tree/commit primitives for one coherent change, normally on a review branch followed by optional PR. Direct default-branch application is a Tier 2 exception.

## 16. Clone/setup/run inference

Never execute repository instructions automatically. Detect project metadata, construct commands from trusted templates, quote values per OS, label confidence/source, and treat README/script content as untrusted text.

## 17. Search architecture

REST Search API is sufficient for core discovery; GraphQL is introduced only where it materially improves a use case. Public search results remain outside installed-repository authorization/cache context unless installation relationship is independently established.

## 18. Error model

Transport categories include authentication, missing permission, not found/inaccessible, conflict/precondition, validation, rate limited, transient, and unexpected GitHub/shape failure.

Higher layers may add domain context but must not replace safe categories with raw HTTP bodies or stack traces in Telegram. P3.2/P3.3 UI maps reauthorization, stale, invalid, expired/reused confirmation, and safe GitHub error states without echoing token/auth bodies.

P3.3 separates a genuinely uncertain write outcome from an ordinary terminal failure. Reconciliation may prove that the remote write applied; otherwise uncertainty remains explicit rather than being hidden by retry.

## 19. Rate limits and retries

- Parse GitHub rate-limit metadata and `Retry-After`.
- GET/HEAD use bounded exponential backoff + jitter for configured transient classes.
- Limits are centralized.
- Do not blindly retry writes/destructive operations.
- A non-read operation may opt into retry only after higher-level semantics establish safe replay.
- Rate-limit responses remain distinct from ordinary permission denial.

OAuth refresh itself is protected from stale persistence through credential-generation comparison; the service does not use blind application-level replay to hide uncertain credential rotation.

P3.3 repository writes are issued once. Errors classified as potentially uncertain trigger operation-specific remote reconciliation, not automatic replay.

## 20. Observability

Use safe correlation context such as Telegram update/user ID, GitHub delivery/request ID, operation ID, and repository identifier. Structured logging redacts authorization headers, tokens, secrets, OAuth codes/state, PKCE material, and private keys. Raw GitHub auth/error bodies are not normal log/error payloads.

P3.3 adds durable repository-administration audit records with safe outcome and reconciliation context. Audit is not a credential store.

## 21. Dependency direction rule

```text
telegram -> services -> domain
                    -> github gateway/auth
                    -> persistence
http setup/oauth -> connection/auth services -> github auth/binding
webhook ingress -> domain normalization -> services/notification
```

Domain must not import Telegram or concrete HTTP clients. Ordinary endpoint-specific GitHub services depend on canonical transport rather than bypass it.

## 22. Verified contract/integration progression

- P2.2: 49-test verified transport foundation.
- P2.3: 65-test verified repository-read implementation and PostgreSQL migration chain.
- P3.1: 83-test verified public-search implementation and full governance closeout.
- P3.2: 97-test verified durable user-authorization implementation, merged through PR #12 as `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`, followed by governance closeout PR #13.
- P3.3 complete implementation head before documentation synchronization: `4e71d7f1c962e61584d6532d03c913703dc5295a`; CI `33890407945` green with **117 tests** on Python 3.12/3.13, mypy clean on 72 source files, PostgreSQL 17 migration round trip including `0005_audit_log`, no known runtime vulnerabilities, no secret findings, and no PEP 751 lock drift.

P3.3 is implementation-verified but is not recorded as phase-complete until its documentation-head CI, non-draft PR, unchanged-head merge, post-merge `main` CI, and governance closeout complete.

## 23. Known non-blocking maintenance warnings

Green P3.3 implementation CI reports:

- Starlette/FastAPI `TestClient` deprecation warning for current `httpx` integration/future `httpx2` direction;
- Starlette test-client usage surfaces AnyIO's deprecated `anyio.abc.BlockingPortal` alias;
- Alembic deprecation warning because `alembic.ini` does not explicitly configure `path_separator` for `prepend_sys_path`.

These are tracked maintenance debt, not hidden test failures.

## 24. Source references for security/auth assumptions

- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- Installation authentication: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
- Webhook validation: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- Repository contents: https://docs.github.com/en/rest/repos/contents
- Actions workflows: https://docs.github.com/en/rest/actions/workflows
