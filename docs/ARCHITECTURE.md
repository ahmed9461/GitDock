# GitDock — Architecture Specification

Status: verified architecture through P4.1 file-browser implementation; P4.1 merge/governance pending

## 1. Architectural goals

- Clear separation between Telegram UI, GitHub transport/auth, domain rules, persistence, and background processing.
- Restart-safe handling for important multi-step operations, confirmations, staged file writes, and GitHub webhooks.
- Testability without real Telegram/GitHub network calls in normal CI.
- Least-privilege authentication.
- Owner-only v1 deployment with multi-user-ready service/persistence boundaries.
- No hidden coupling between button callbacks and raw GitHub API calls.
- GitHub remains authoritative for GitHub resources; local state exists only for identity/auth, navigation/cache, preferences, audit, confirmation/operation staging, and durable work where justified.

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

- Telegram long polling allowed.
- GitHub webhook testing may use a secure tunnel/replay fixture.
- SQLite may be used for portable tests/development.

### Production

- FastAPI serves Telegram webhook, GitHub webhook, setup/OAuth callbacks, health/readiness.
- PostgreSQL required.
- Deployment remains suitable for systemd.
- HTTPS terminates at a trusted reverse proxy/application deployment layer.
- Background event worker may initially share deployment but remains a distinct DB-backed component.

## 4. Source layout through P4.1

```text
gitdock/
├── app.py
├── core/
│   ├── config.py
│   ├── logging.py
│   └── constants.py
├── http/routes/
├── telegram/
│   ├── bot.py
│   ├── callbacks.py
│   ├── file_callbacks.py
│   ├── routers/
│   │   ├── repository_admin.py
│   │   └── files.py
│   ├── keyboards/
│   │   ├── repository_admin.py
│   │   └── files.py
│   ├── renderers/
│   │   ├── repository_admin.py
│   │   └── files.py
│   ├── states/
│   │   ├── repository_admin.py
│   │   └── files.py
│   └── middleware/
├── github/
│   ├── auth.py
│   ├── auth_state.py
│   ├── binding.py
│   ├── client.py
│   ├── connection.py
│   ├── contents.py
│   ├── credentials.py
│   ├── errors.py
│   ├── models.py
│   ├── pagination.py
│   ├── permissions.py
│   ├── repositories.py
│   ├── repository_admin.py
│   └── token_provider.py
├── domain/
│   └── files.py
├── services/
│   ├── confirmations.py
│   ├── identity.py
│   ├── repositories.py
│   ├── repository_admin.py
│   ├── repository_admin_confirmations.py
│   ├── repository_reconciliation.py
│   ├── file_browser.py
│   ├── file_context.py
│   ├── file_reads.py
│   ├── file_types.py
│   ├── file_write_store.py
│   ├── file_writes.py
│   ├── file_audit.py
│   ├── runtime.py
│   └── user_authorization.py
├── db/
│   ├── migrations/versions/
│   │   ├── 0005_audit_log.py
│   │   └── 0006_file_write_sessions.py
│   └── models/
│       ├── audit.py
│       └── file_write.py
├── workers/
└── security/

tests/
├── unit/
├── integration/
├── contract/
└── fixtures/
```

Exact filenames may evolve; the layer boundaries are intentional.

## 5. Layer responsibilities

### Telegram layer

Receives updates, renders Arabic screens, builds keyboards, collects input, and maps user actions to application services.

It must not:

- issue raw GitHub HTTP;
- contain raw DB queries;
- construct OAuth/token flows;
- infer write authority from callback possession;
- own durable confirmation/staging/risk rules.

P3.3 repository administration and P4.1 files follow the same pattern: centralized callback helpers, keyboards, renderers, FSM states, and thin routers. P4.1 specifically keeps long file paths out of callback data; callbacks transport short browse-session IDs, indexes/actions, or opaque confirmation tokens while services own path/ref validation, authorization, staging, preconditions, writes, reconciliation, and audit.

### Application services

Verified service boundaries include:

- owner identity resolution;
- `RepositoryReadService` for installed repository navigation/cache sync;
- public search service;
- `GitHubUserAuthorizationService` for durable user auth/refresh/local disconnect;
- `ConfirmationService` for restart-safe one-time confirmations;
- `RepositoryAdminService` plus confirmation/reconciliation helpers;
- `FileBrowserService` plus `file_context`, `file_reads`, `file_writes`, `file_write_store`, and `file_audit` helpers;
- runtime composition that wires clients/providers/services/gateways/DB factories once.

`FileBrowserService` deliberately decomposes P4.1 rather than placing GitHub/DB/security behavior inside one aiogram router.

### Domain layer

Contains pure rules such as risk classification, path/ref validation, text/binary detection helpers, diff/hash planning, sync planning, state transitions, event normalization, and confirmation requirements.

### GitHub transport/auth boundaries

`GitHubRestClient` remains canonical ordinary REST transport. Authentication-specific OAuth/App endpoints remain behind auth clients.

Verified transport invariants:

- centralized GitHub headers/API version/User-Agent;
- `SecretStr` material only materialized at outbound boundary;
- canonical HTTPS `api.github.com` absolute targets only;
- hostile pagination target rejection and loop/page guards;
- redirects not automatically followed;
- stable safe error categories without raw-body echo;
- typed rate-limit metadata;
- bounded GET/HEAD retry;
- write-like methods no retry by default.

Feature gateways layer typed endpoint contracts on this transport:

- repository read/search;
- P3.3 repository administration;
- P4.1 repository Contents (`GitHubContentsGateway`).

No feature creates a parallel raw HTTP stack.

## 6. Authentication and capability contexts

### Telegram owner authentication

`GITDOCK_TELEGRAM_OWNER_ID` is v1 ingress allowlist. Middleware rejects/ignores unauthorized users before sensitive routing.

### GitHub App installation binding

Setup `installation_id` is untrusted candidate data. Binding occurs only after App-context and authenticated-user-context identity match and suspension/conflict checks pass.

### Durable GitHub user authorization — P3.2

P3.2 reuses one-time OAuth state + PKCE S256, authenticated `GET /user`, encrypted versioned credential storage, expiry metadata, and `credential_generation`. Refresh persists rotated credentials only if generation/account/preconditions remain current.

### Repository administration — P3.3

- personal/org create: durable GitHub user OAuth context;
- repository update/delete: repository-scoped installation token with `administration: write`.

### File browser/write — P4.1

- repository browsing/file reads: repository-scoped installation token with `contents: read`;
- ordinary one-file create/update/delete: repository-scoped installation token with `contents: write`;
- `.github/workflows/*` writes: explicit workflow-write capability (`workflows: write`) in addition to the content-write path.

Repository cache/callback presence never grants any capability.

## 7. Persistence model

Core persisted concepts:

- GitDock users/Telegram identities;
- GitHub accounts/installations and encrypted durable user credentials;
- durable OAuth state;
- minimal `repositories_cache`;
- `pending_confirmations`;
- append-oriented `audit_log`;
- P4.1 `file_write_sessions`;
- future webhook/event and batch-operation state.

GitHub remains source of truth for repository resources.

### `repositories_cache` — migration 0003

Minimal safe navigation context only; user/installation scoped; no credentials; revalidated against GitHub for detail/authority.

### Durable auth/confirmation — migration `0004_user_auth`

Adds `credential_generation` and DB-backed `pending_confirmations`. Confirmation payload/fingerprint may contain stable IDs/preconditions but no credentials/OAuth/PKCE/private-key/client-secret material.

### Audit — migration `0005_audit_log`

Append-oriented safe operation/outcome/reconciliation metadata. Audit is never a credential store.

### P4.1 staged file writes — migration `0006_file_write_sessions`

`file_write_sessions` persists reviewed one-file write intent across restart. Staging includes user, installation/repository, operation, branch/path, branch-head SHA, expected file SHA where applicable, desired blob/content digest, commit message, risk tier, confirmation nonce/version, expiry/consumed timestamps, and temporary content bytes for create/update.

Important data-lifetime rule:

- temporary file body bytes may exist in PostgreSQL for at most the staged-write lifetime (15 minutes);
- bytes are cleared on consume, cancellation, same-target supersession, expiry/prune, and equivalent invalidation;
- file body bytes are never copied into `audit_log`;
- DB/backup access remains security-sensitive because staged content may briefly exist there.

## 8. Confirmation/staging architecture

A Telegram callback is transport, not durable authorization.

### P3.2 local disconnect

Persist one-time confirmation bound to current account/generation/installation set. Home/Cancel/Confirm consumes authority. Stale state removes nothing.

### P3.3 repository administration

Create/update/delete confirmations are persisted, user/operation-bound, expiring, single-use, and target-fingerprinted. Update/delete refresh current GitHub state before mutation. Delete additionally requires exact current `owner/name`.

### P4.1 one-file writes

1. validate selected installed repository context and normalized branch/path;
2. fetch current branch head and current file state where applicable;
3. build create/update/delete plan and diff/metadata preview;
4. persist `file_write_sessions` staged intent plus general persisted confirmation;
5. if a same user/repository/branch/path staging already exists, consume it and scrub its body bytes before creating the newer staging;
6. Telegram receives only compact confirmation/session context;
7. confirm atomically consumes server-side authority;
8. re-resolve installation/repository context and refresh branch/file preconditions;
9. obtain repository-scoped content/workflow permission token;
10. issue the GitHub write once;
11. if outcome may be uncertain, reconcile remote branch/file state rather than replaying the write;
12. audit safe outcome metadata and scrub staged content.

Invalid/expired/reused/cancelled/stale confirmation performs no new GitHub write.

## 9. P4.1 read lifecycle

Directory/file reads:

1. resolve current GitDock user + installed repository context;
2. validate normalized path/ref before network I/O;
3. obtain repository-scoped `contents: read` installation token;
4. call typed Contents gateway;
5. classify file content as text/binary/large/missing-inline-content;
6. paginate text server-side for Telegram rendering;
7. keep path/ref in server/FSM context; callback carries only compact session/index/action.

Text preview ceiling is 256 KiB, preview pages target 2800 chars, and P4.1 single Telegram file transfer is bounded at 20 MiB.

## 10. P3.3 repository write lifecycle

Create/update/delete follow the established pattern: validate → persisted confirmation → refresh current authority/preconditions → scoped credential → issue once → reconcile uncertainty → audit/cache update. `RepositoryAdminState` distinguishes `APPLIED`, `STALE`, `INVALID`, and `UNCERTAIN`.

## 11. GitHub write strategy

- P4.1 simple single-file writes use Contents API with current branch-head/file-SHA protection and durable staging.
- P8 multi-file/ZIP synchronization remains a coherent reviewable tree/commit operation, normally on a review branch + optional PR.
- Direct default-branch mass replacement is not the default.
- No blind replay of uncertain writes.

## 12. Webhook ingestion pipeline

Future P5 pipeline remains: raw bytes → HMAC verification → delivery/event validation → idempotent durable insert → quick ACK → worker normalization/enrichment/preferences → Telegram render → processed/retry state. Duplicate delivery IDs never create duplicate notifications.

## 13. Clone/setup/run inference

Never execute repository instructions automatically. Detect project metadata, construct commands from trusted templates, quote per OS, label confidence/source, and treat README/script content as untrusted text.

## 14. Error model / retry semantics

Transport categories include authentication, missing permission, not found/inaccessible, conflict/precondition, validation, rate limited, transient, and unexpected shape/GitHub failure.

Higher layers add domain context but never expose raw response/auth material. P4.1 adds explicit stale/invalid/uncertain file-write outcomes; uncertainty remains explicit unless remote reconciliation proves final state.

GET/HEAD may bounded-retry transient failures. Write-like calls are issued once unless higher-level semantics have proven replay safety; P3.3/P4.1 uncertain writes reconcile instead of blindly retrying.

## 15. Observability/audit

Safe correlation may include Telegram update/user ID, GitHub request/delivery ID, operation ID, repository ID/full name, branch/path, commit SHA, and status. Structured logging redacts auth headers/tokens/secrets/OAuth/PKCE/private keys and avoids raw upstream auth/error bodies.

P4.1 audit may include operation, risk tier, repository, branch/path, expected/head SHA, commit/reconciliation/status/reason. It never includes staged file body or credentials.

## 16. Dependency direction

```text
telegram -> services -> domain
                    -> github gateway/auth
                    -> persistence
http setup/oauth -> connection/auth services -> github auth/binding
webhook ingress -> domain normalization -> services/notification
```

Domain must not import Telegram or concrete HTTP clients. Endpoint-specific feature gateways use canonical transport rather than bypass it.

## 17. Verified progression

- P2.2: 49-test transport foundation.
- P2.3: 65-test repository-read implementation.
- P3.1: 83-test public-search implementation.
- P3.2: 97-test durable user-authorization implementation.
- P3.3: 117-test repository-administration implementation, fully merged/governance verified.
- P4.1 implementation head `614f013b35644fcdd05e880c9a37ff30fd503fdf`: CI `34639736010` green with **148 tests** on Python 3.12/3.13, mypy clean on **87 source files**, compile/audit/secrets/PEP 751 locks green, and PostgreSQL 17 migration roundtrip through `0006_file_write_sessions` green.

P4.1 remains implementation-verified, not phase-complete, until documentation-head CI, non-draft PR CI, unchanged-head merge, post-feature `main` CI, and governance closeout complete.

## 18. Known non-blocking maintenance warnings

- Starlette/FastAPI `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias surfaced through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

These are tracked debt, not hidden test failures.

## 19. Source references for security/auth assumptions

- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- Installation authentication: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
- Webhook validation: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- Repository contents: https://docs.github.com/en/rest/repos/contents
- Actions workflows: https://docs.github.com/en/rest/actions/workflows
