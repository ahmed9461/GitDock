# GitDock — Architecture Specification

Status: baseline architecture + verified P2.2 transport implementation

## 1. Architectural goals

- Clear separation between Telegram UI, GitHub transport, domain rules, persistence, and background event processing.
- Restart-safe handling for important multi-step operations and GitHub webhooks.
- Testability without real Telegram/GitHub network calls.
- Least-privilege authentication.
- Easy owner-only v1 deployment with a clean path to multi-user support.
- No hidden direct coupling between button callbacks and raw GitHub API calls.

## 2. High-level topology

```text
Telegram Client
      |
      v
+------------------------+
| FastAPI HTTP Ingress   |
| - Telegram webhook     |
| - GitHub webhook       |
| - OAuth callback       |
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
      REST / GraphQL
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

- FastAPI serves Telegram webhook, GitHub webhook, OAuth callback, health/readiness.
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
├── telegram/
│   ├── bot.py
│   ├── routers/
│   ├── keyboards/
│   ├── renderers/
│   ├── states/
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
│   └── token_provider.py
├── domain/
├── services/
├── db/
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

Must not call GitHub HTTP endpoints directly, contain raw database queries, or embed durable business/risk rules.

### Application services

Orchestrate use cases, domain rules, persistence, GitHub gateway, audit, permission checks, and confirmation flows.

### Domain layer

Contains mostly pure rules such as risk classification, path validation, sync planning, state transitions, event normalization, and confirmation requirements.

### GitHub gateway

The **only normal application boundary that understands GitHub REST request details**.

P2.2 verified implementation:

- `GitHubRestClient` owns outbound REST request construction.
- Callers supply payload parsers; transport does not leak unvalidated dict shapes upward as the intended service contract.
- `GitHubResponse[T]` and `GitHubPage[T]` attach safe metadata: HTTP status, GitHub request ID, rate-limit state, and validated pagination links.
- Canonical request headers are centralized: GitHub media type, API version `2026-03-10`, and `GitDock/0.1` User-Agent.
- Authentication is accepted as `SecretStr` and materialized only into the outbound Authorization header at the transport boundary.
- Absolute targets are restricted to HTTPS `api.github.com`; relative `/...` API paths are allowed.
- Pagination refuses protocol-relative URLs, credentials in URLs, fragments, external hosts, non-HTTPS targets, and noncanonical ports.
- Pagination iteration detects repeated next links and enforces `GITHUB_MAX_PAGES`.
- Redirects are not automatically followed.
- Error translation produces stable GitDock categories and does not copy raw GitHub response bodies into exceptions.
- Rate-limit headers are parsed into a dedicated model.
- GET/HEAD retry bounded transient failures by default; non-read methods default to no retry.
- Explicit retry for a non-read operation requires a higher layer to opt into `RetryMode.SAFE` after establishing retry/idempotency safety.

Future endpoint-specific repository/issue/PR/Actions methods build on this transport rather than creating parallel HTTP clients.

### Persistence

Stores GitDock state/preferences/audit/inbox. GitHub remains source of truth for GitHub resources; do not build a shadow GitHub database unnecessarily.

## 6. Authentication flows

### Telegram owner authentication — v1

- `GITDOCK_TELEGRAM_OWNER_ID` is the owner allowlist baseline.
- Middleware rejects/ignores unauthorized users before sensitive routing.
- Future multi-user support replaces this boundary policy without changing core services.

### GitHub App installation

1. Create a short-lived setup session bound to Telegram user.
2. User installs/authorizes GitHub App.
3. Treat returned `installation_id` only as untrusted candidate data.
4. Perform authenticated user authorization with one-time state + PKCE.
5. Resolve installation under App context and authenticated-user context.
6. Bind only after account/installation identities match and installation is not suspended.

### GitHub user authorization

- cryptographically random short-lived state;
- server-side one-time validation;
- PKCE S256;
- server-side code exchange;
- encrypted persistence only when durable user context is genuinely required;
- token values never sent to Telegram.

## 7. GitHub permission/capability model

Permission strings are centralized, not scattered in handlers. Capabilities map to required GitHub App permissions and token context, allowing services to distinguish available, missing app permission, user/repository authority failure, installation exclusion, and invalid resource state.

## 8. Database model baseline

Core models include users/Telegram identities, GitHub accounts/installations, minimal repository cache/preferences, webhook delivery/event work state, pending confirmations, durable high-impact operation sessions, and append-oriented audit records.

GitHub resource state remains authoritative remotely.

## 9. Webhook ingestion pipeline

1. Read raw bytes.
2. Verify `X-Hub-Signature-256` using constant-time HMAC-SHA256 comparison.
3. Read event/delivery identifiers.
4. Validate supported envelope.
5. Insert delivery idempotently.
6. Persist required routing/work data.
7. Acknowledge HTTP quickly.
8. Worker normalizes/enriches/applies preferences.
9. Render Telegram notification.
10. Mark processed or retryable/terminal failure.

Duplicate delivery IDs must not create duplicate user-visible notifications.

## 10. Canonical notification event model

Renderers consume normalized event values such as delivery/event type/action/repository/actor/target/title/summary/url/time/severity rather than every raw GitHub webhook shape.

## 11. File operations

For a single-file update: fetch current SHA, collect replacement, show path/branch/diff summary, persist confirmation with expected SHA, and write only if precondition remains valid. Stale remote state stops the write and requires refresh/review.

## 12. ZIP/project synchronization architecture

Uploads use isolated temporary workspaces, member pre-scan, traversal/link/file-count/depth/uncompressed-size guards, and secret-like warnings before any repository write.

A persisted immutable `SyncPlan` records base commit, target strategy, added/modified/deleted/unchanged/binary/large/excluded files, warnings, and statistics. If the base changes before apply, re-plan.

Apply prefers Git tree/commit primitives for one coherent change, normally on a review branch followed by optional PR. Direct default-branch application is a Tier 2 exception.

## 13. Clone/setup/run inference

Never execute repository instructions automatically. Detect project metadata, construct commands from trusted templates, quote values per OS, label confidence/source, and treat README/script content as untrusted text.

## 14. Search architecture

REST Search API is sufficient for core discovery; GraphQL is introduced only where it materially improves a use case. Normalize results to GitDock models and avoid long-lived shadow search state.

## 15. Error model

P2.2 establishes transport categories:

- authentication required;
- missing permission;
- not found/inaccessible;
- conflict/precondition failure;
- validation rejection;
- rate limited;
- transient failure;
- unexpected GitHub/shape failure.

Higher layers may add domain-specific context, but must not replace these with raw HTTP bodies or stack traces in Telegram.

Transport errors may expose only safe metadata such as status code, GitHub request ID, and parsed rate-limit state.

## 16. Rate limits and retries

- Parse GitHub rate-limit resource/limit/remaining/used/reset and `Retry-After`.
- GET/HEAD use bounded exponential backoff + jitter for network/timeouts and HTTP 408/500/502/503/504.
- Maximum retry count/base/max delay are centralized constants.
- Do not blindly retry write-like or destructive operations.
- A non-read operation can opt into retry only after the endpoint/use case is explicitly classified safe/idempotent by its higher-level service.
- Rate-limit responses are translated distinctly from ordinary 403 permission failures.

## 17. Observability

Use correlation context such as Telegram update/user ID, GitHub delivery/request ID, operation ID, and repository identifier where safe. Structured logging redacts authorization headers, tokens, secrets, OAuth codes, PKCE material, and private keys. Raw GitHub error bodies are not normal log/error payloads.

## 18. Dependency direction rule

```text
telegram -> services -> domain
                    -> github gateway
                    -> persistence
webhook ingress -> domain normalization -> services/notification
```

Domain must not import Telegram or concrete HTTP clients. Endpoint-specific GitHub services/gateways depend on the P2.2 REST transport rather than bypass it.

## 19. P2.2 contract verification

CI run `33406986504` verified the transport on Python 3.12 and 3.13 with the complete 49-test suite. Twelve gateway contract tests cover canonical headers, fixture parsing, pagination, hostile-target rejection, error categories, rate limits, body/token non-leakage, transient safe retry, default no-write-retry, and explicit safe retry. PostgreSQL migration, audit, secret scan, compile, and PEP 751 lock checks remained green.

## 20. Source references for security/auth assumptions

- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- Installation authentication: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
- Webhook validation: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- Repository contents: https://docs.github.com/en/rest/repos/contents
- Actions workflows: https://docs.github.com/en/rest/actions/workflows
