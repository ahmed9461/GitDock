# GitDock — Architecture Specification

Status: baseline architecture for implementation

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

## 4. Recommended source layout

```text
gitdock/
├── app.py
├── core/
│   ├── config.py
│   ├── logging.py
│   ├── errors.py
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
│   ├── client.py
│   ├── rest.py
│   ├── graphql.py
│   ├── permissions.py
│   ├── webhooks.py
│   └── models.py
├── domain/
│   ├── repositories.py
│   ├── files.py
│   ├── sync.py
│   ├── notifications.py
│   ├── actions.py
│   └── risk.py
├── services/
│   ├── repo_service.py
│   ├── file_service.py
│   ├── sync_service.py
│   ├── issue_service.py
│   ├── pr_service.py
│   ├── action_service.py
│   ├── search_service.py
│   └── notification_service.py
├── db/
│   ├── base.py
│   ├── models/
│   ├── repositories/
│   └── migrations/
├── workers/
│   ├── event_worker.py
│   └── cleanup_worker.py
└── security/
    ├── crypto.py
    ├── redaction.py
    ├── confirmations.py
    └── archive_safety.py

tests/
├── unit/
├── integration/
├── contract/
└── fixtures/
```

Exact filenames may evolve, but the boundaries are intentional.

## 5. Layer responsibilities

### Telegram layer

Responsible for:

- receiving updates/callbacks/messages/files;
- rendering Arabic screens;
- building keyboards;
- collecting wizard input;
- mapping UI actions to application service calls.

Must not:

- call GitHub HTTP endpoints directly from handlers;
- contain durable business rules;
- contain raw database queries;
- construct dangerous operations without domain risk checks.

### Application services

Responsible for use cases such as:

- list repositories;
- create repository;
- prepare file update;
- confirm/apply sync;
- dispatch workflow;
- merge PR;
- manage notification preferences.

Services orchestrate domain rules, persistence, GitHub gateway, audit, and permission checks.

### Domain layer

Pure or mostly pure rules:

- risk classification;
- path validation;
- diff/sync plan representation;
- operation state transitions;
- notification event normalization;
- confirmation requirements.

Domain code should be easy to unit test without network/database.

### GitHub gateway

Only component that understands GitHub REST/GraphQL request details, token refresh, pagination, rate-limit headers, ETags where used, and GitHub-specific error translation.

Expose typed methods/capabilities to services.

### Persistence

Stores GitDock state/preferences/audit/inbox. GitHub remains source of truth for GitHub data.

Do not build a shadow GitHub database unnecessarily.

## 6. Authentication flows

### Telegram owner authentication — v1

- `GITDOCK_TELEGRAM_OWNER_ID` is the owner allowlist baseline.
- Middleware rejects/ignores unauthorized users before sensitive routing.
- Future multi-user support replaces this with persisted user/access policy without changing core services.

### GitHub App installation

1. GitDock creates a short-lived installation/setup session bound to Telegram user.
2. User follows GitHub App install/authorization URL.
3. GitHub redirects to GitDock callback/setup URL.
4. GitDock validates the session/state and binds GitHub account/installation to the Telegram user.
5. Repository operations use installation access tokens when suitable.

### GitHub user authorization

Some user-context operations require a GitHub App user access token.

1. Create cryptographically random short-lived authorization state bound to Telegram user.
2. Send authorization URL.
3. Validate callback state exactly once.
4. Exchange code server-side.
5. Encrypt stored token/refresh material at rest when persistence is required.
6. Never send token values to Telegram.

Personal repository creation for the authenticated user is treated as user-context functionality.

## 7. GitHub permission/capability model

Do not scatter permission strings in handlers.

Define capabilities, for example:

```text
CAP_REPO_READ
CAP_REPO_ADMIN
CAP_CONTENT_READ
CAP_CONTENT_WRITE
CAP_WORKFLOW_EDIT
CAP_ISSUE_WRITE
CAP_PR_WRITE
CAP_ACTIONS_WRITE
```

A central mapper describes which GitHub App permission(s) and token context each capability requires.

Before showing/enabling an action, the service can report:

- available;
- missing app permission;
- repository/user lacks authority;
- installation does not include repository;
- unsupported for current resource state.

## 8. Database model baseline

### `users`

- id
- created_at
- status

### `telegram_accounts`

- user_id
- telegram_user_id (unique)
- username/display metadata as non-authoritative convenience

### `github_accounts`

- user_id
- github_user_id
- login
- encrypted user-token material if needed
- token metadata/expiry

### `github_installations`

- user_id/account relation
- installation_id (unique)
- account type/login
- permissions snapshot/cache
- suspended status

### `repositories_cache`

Minimal cache/index fields only, e.g. GitHub repository id, full name, installation, default branch, visibility, timestamps.

### `repository_preferences`

- repository id
- notification mode
- selected event toggles
- mute flags
- preferred branch behavior

### `webhook_deliveries`

- GitHub delivery id (unique)
- event name/action
- installation/repository identifiers
- received timestamp
- signature-verified flag
- processing status
- attempt count
- last error category

Raw payload retention should be minimized and governed; store only what is required for retry/audit/debug policy.

### `event_inbox`

May be merged with `webhook_deliveries` if one table cleanly supports durable processing state. Do not duplicate concepts without need.

### `pending_confirmations`

- opaque confirmation id
- user id
- operation name
- canonical target snapshot
- expected preconditions/SHA where relevant
- risk tier
- expires_at
- consumed_at

### `operation_sessions`

Used for durable high-impact wizards, especially ZIP sync.

### `audit_log`

Append-oriented record of user-triggered GitHub write operations and outcomes.

## 9. Webhook ingestion pipeline

1. Read raw request bytes.
2. Validate GitHub `X-Hub-Signature-256` against configured secret using constant-time comparison.
3. Read event name + delivery id.
4. Validate supported event envelope.
5. Insert delivery id idempotently.
6. Persist normalized minimum routing metadata/payload required for worker.
7. Return successful HTTP response quickly.
8. Worker loads pending delivery.
9. Normalize GitHub-specific payload into GitDock event model.
10. Apply repository/user notification preferences.
11. Enrich with GitHub API only if needed.
12. Render/send Telegram notification.
13. Mark processed or retryable/terminal failure.

Duplicate delivery IDs must not create duplicate Telegram notifications.

## 10. Canonical notification event model

Example fields:

```text
event_id
source_delivery_id
event_type
action
repository_id
repository_full_name
actor_login
target_type
target_number_or_ref
title
summary
url
occurred_at
severity
```

Renderers operate on this canonical model instead of every raw GitHub webhook shape.

## 11. File operations

### Read

- resolve repository + ref + path;
- detect file/directory;
- validate returned encoding/size;
- render text preview or metadata/download flow.

### Single-file update

1. Fetch current content metadata/SHA.
2. User submits replacement/new content.
3. Show path, branch, change type, compact diff/summary.
4. Create confirmation containing expected SHA.
5. On confirm, update using the expected SHA/precondition.
6. If stale/conflicted, stop and require refresh/review.

Do not silently overwrite when repository state changed after review.

## 12. ZIP/project synchronization architecture

### Workspace

- create unique isolated temporary directory;
- stream/save upload with configured size guard;
- inspect archive members before extraction;
- reject traversal/absolute paths/suspicious links;
- enforce file count, depth, and total extracted size limits;
- optionally detect secret-like files before any upload.

### Plan

Build a `SyncPlan` domain object containing:

- base repository/ref/commit;
- target branch strategy;
- added files;
- modified files;
- deleted files;
- unchanged files;
- binary/large files;
- excluded files;
- warnings;
- statistics.

The plan is immutable after confirmation. If base commit changes before apply, require re-plan or explicit conflict handling.

### Apply

Prefer Git data primitives/tree+commit for a coherent multi-file commit. Create/update a review branch by default. Direct default-branch application is a Tier 2 exception requiring explicit confirmation and repository policy allowance.

## 13. Clone/setup/run inference

Never execute repository instructions automatically.

Inference pipeline:

1. inspect canonical project files;
2. score supported project types;
3. optionally inspect relevant README sections;
4. construct commands from trusted templates;
5. quote repository/path values;
6. label confidence/source;
7. present OS-specific commands.

Do not turn arbitrary README shell text into executable server commands.

## 14. Search architecture

- REST Search API is sufficient for core repository discovery.
- GraphQL may be introduced when it materially reduces round trips or improves a screen.
- Normalize results into GitDock repository summary model.
- Cache only short-lived search/result metadata when useful; avoid stale permanent search mirrors.

## 15. Error model

Translate infrastructure errors into stable application categories:

- authentication required
- missing GitHub permission
- repository not installed/accessible
- not found
- conflict/stale SHA
- validation error
- rate limited
- transient GitHub failure
- GitHub validation rejection
- Telegram delivery failure
- database unavailable
- internal unexpected failure

Telegram renderers should not display raw stack traces or tokens.

## 16. Rate limits and retries

- Observe GitHub rate-limit headers.
- Show the user a useful retry/reset message where appropriate.
- Retry bounded transient failures with jitter.
- Do not blindly retry non-idempotent/destructive operations.
- Use expected SHA/ref state and operation IDs to prevent duplicate writes.

## 17. Observability

Every request/operation should carry correlation context such as:

- Telegram update id/user id (non-secret)
- GitHub delivery id
- operation id
- repository id/full name where safe

Structured log events; redact authorization headers, tokens, secrets, OAuth codes, webhook secrets, and private key material.

## 18. Dependency direction rule

Allowed conceptual direction:

```text
telegram -> services -> domain
                    -> github gateway
                    -> persistence
webhook ingress -> domain normalization -> services/notification
```

Domain must not import Telegram or concrete HTTP client modules.

## 19. Source references for security/auth assumptions

- GitHub App permissions and least privilege: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- Installation authentication: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
- Webhook signature validation: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- Repository contents writes: https://docs.github.com/en/rest/repos/contents
- Actions workflows/dispatch: https://docs.github.com/en/rest/actions/workflows
