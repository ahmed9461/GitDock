# GitDock — Canonical Constants

Status: authoritative constants through P4.1 implementation verification. Change intentionally and record meaningful architecture/security changes in `docs/DECISIONS.md`.

## Product identity

| Key | Value |
|---|---|
| `APP_NAME` | `GitDock` |
| `APP_SLUG` | `gitdock` |
| `TELEGRAM_CALLBACK_PREFIX` | `gd` |
| `PRIMARY_UI_LANGUAGE` | `ar` |
| `GITHUB_REST_API_VERSION` | `2026-03-10` |
| `GITHUB_API_BASE_URL` | `https://api.github.com` |
| `GITHUB_WEB_BASE_URL` | `https://github.com` |
| `GITHUB_ACCEPT_HEADER` | `application/vnd.github+json` |
| `GITHUB_USER_AGENT` | `GitDock/0.1` |

Do not duplicate these literals throughout handlers/services.

## HTTP/callback paths

| Constant | Value |
|---|---|
| `HEALTH_PATH` | `/health` |
| `READINESS_PATH` | `/ready` |
| `TELEGRAM_WEBHOOK_PATH` | `/telegram/webhook` |
| `GITHUB_SETUP_CALLBACK_PATH` | `/github/setup/callback` |
| `GITHUB_OAUTH_CALLBACK_PATH` | `/github/oauth/callback` |

## GitHub authentication timing/security constants

| Constant | Value | Purpose |
|---|---:|---|
| `GITHUB_APP_JWT_IAT_SKEW_SECONDS` | 60 | tolerate clock skew when issuing App JWT |
| `GITHUB_APP_JWT_LIFETIME_SECONDS` | 540 | bounded App JWT lifetime |
| `INSTALLATION_TOKEN_REFRESH_MARGIN_SECONDS` | 300 | refresh installation token before near expiry |
| `USER_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS` | 300 | P3.2 durable user-token refresh margin |
| `GITHUB_AUTH_STATE_TTL_SECONDS` | 600 | restart-safe OAuth/setup state expiry |
| `CONFIRMATION_TTL_SECONDS` | 300 | DB-backed sensitive confirmation expiry |
| `CONFIRMATION_TOKEN_BYTES` | 12 | random opaque confirmation-token entropy source bytes |
| `FILE_WRITE_SESSION_TTL_SECONDS` | 900 | P4.1 durable staged one-file write lifetime |

Do not reuse a UI timeout as a credential/security lifetime unless it is the canonical constant for that lifecycle.

## Telegram UI constants

| Constant | Current value | Purpose |
|---|---:|---|
| `DEFAULT_PAGE_SIZE` | 8 | installed repository list pagination |
| `SEARCH_PAGE_SIZE` | 6 | P3.1 richer public search rows |
| `CALLBACK_SCHEMA_VERSION` | `v1` | callback compatibility/versioning |
| `FILE_BROWSE_SESSION_ID_BYTES` | 6 | short opaque P4.1 browse-session context |

Policy/spec values still planned for later milestones include maximum two primary actions per row, archive limits, and higher-risk mass-update confirmation patterns. Where a value becomes executable code, `gitdock/core/constants.py` is the source that must match this document.

### Canonical navigation labels

- `🏠 الرئيسية`
- `❌ إلغاء`
- `⬅️ رجوع`
- `🔄 تحديث`

### Common state icons

- success: `✅`
- failed: `❌`
- warning: `⚠️`
- running/loading: `⏳`
- public repository: `🌐`
- private repository: `🔒`
- archived repository: `📦`
- branch: `🌿`
- commit: `📝`
- issue: `❗`
- pull request: `🔀`
- workflow/action: `⚙️`
- release: `🏷️`
- notification: `🔔`
- search: `🔎`
- file: `📄`
- folder: `📁`
- account/user context: `👤`

## Callback namespace

Canonical form:

`gd:v1:<area>:<action>:<compact-context>`

Verified shapes include:

### Home / connection

- `gd:v1:home:open`
- `gd:v1:home:refresh`
- `gd:v1:connect:begin`
- `gd:v1:connect:info`

### Installed repositories

- `gd:v1:repos:list:<filter>:<page>`
- `gd:v1:repos:filters:<filter>:<page>`
- `gd:v1:repos:filter:<filter>`
- `gd:v1:repo:open:<filter>:<page>:<repo-id-base36>`

### P3.1 search

Search uses compact opaque active-session/result context rather than embedding arbitrary repository names. Exact parser helpers remain centralized in `gitdock/telegram/callbacks.py`.

### P3.2 GitHub account

- `gd:v1:account:open`
- `gd:v1:account:authorize`
- `gd:v1:account:refresh`
- `gd:v1:account:disconnect:begin`
- `gd:v1:account:disconnect:yes:<opaque-token>`
- `gd:v1:account:disconnect:no:<opaque-token>`

### P4.1 file browser

P4.1 file callbacks are centralized in `gitdock/telegram/file_callbacks.py`. They carry only compact repository/browse navigation context, short browse session IDs, entry indexes/actions, or opaque write-confirmation tokens. **Repository file paths are not embedded in callback data.**

Rules:

- Never use arbitrary raw repository/path/login values when a compact stable ID/session is available.
- Repository callbacks use stable GitHub numeric repository ID plus navigation context.
- Search callbacks use active session/result context and fail closed when session is stale.
- P3.2 confirmation callbacks may carry only the opaque confirmation token; the DB stores a digest plus target preconditions.
- P4.1 file callbacks carry short browse/session/index/token context; path/ref/write authority resolves server-side.
- Callback possession is never authorization proof.
- Reject unknown/malformed callback schema versions safely.
- Keep callback data within Telegram's 64-byte limit; tests enforce current repository/search/account/file shapes.
- Never place GitHub credentials, OAuth code/state, PKCE verifier, private keys, client secret, raw auth bodies, or staged file bodies into callbacks.

## P2.3 repository filter values

Machine identifiers:

- `all`
- `private`
- `public`
- `active`
- `archived`
- `source`
- `fork`

Do not invent handler-local aliases without deliberate callback compatibility/versioning change.

## P3.1 search limits

| Constant | Value |
|---|---:|
| `SEARCH_QUERY_MAX_CHARS` | 180 |
| `SEARCH_COMPILED_QUERY_MAX_CHARS` | 240 |
| `SEARCH_SESSION_ID_BYTES` | 6 |
| `SEARCH_OWNER_LOGIN_MAX_CHARS` | 39 |
| `SEARCH_TOPIC_MAX_CHARS` | 50 |
| `SEARCH_MIN_STARS_MAX` | 1,000,000,000 |

## Repository/file operation policy limits

P4.1 file-browser values below are executable and centralized in `gitdock/core/constants.py`. ZIP/project-sync limits remain later policy targets.

| Policy / constant | Value | Status / notes |
|---|---:|---|
| `FILE_TEXT_PREVIEW_MAX_BYTES` | 256 KiB | executable P4.1 text-preview ceiling |
| `FILE_SINGLE_UPLOAD_MAX_BYTES` | 20 MiB | executable P4.1 single Telegram file boundary |
| `FILE_PREVIEW_PAGE_CHARS` | 2800 | executable P4.1 preview-page target |
| `FILE_PATH_MAX_CHARS` | 1024 | executable P4.1 normalized repo-path ceiling |
| `FILE_REF_MAX_CHARS` | 255 | executable P4.1 branch/tag/SHA input ceiling |
| `FILE_COMMIT_MESSAGE_MAX_CHARS` | 500 | executable P4.1 commit-message ceiling |
| `FILE_BROWSE_SESSION_ID_BYTES` | 6 bytes | executable short browse-session entropy source |
| `FILE_WRITE_SESSION_TTL_SECONDS` | 900 sec | executable staged write lifetime |
| ZIP max files | 5000 | later zip-bomb guard target |
| ZIP max extracted bytes | 250 MiB | later extracted-size guard target |
| ZIP max path depth | 25 | later path-abuse guard target |
| diff preview max files | 200 | later batch-review target |
| diff text max/file | 512 KiB | later batch-diff target |
| temp workspace TTL | 60 minutes | later sync-workspace cleanup target |

These are GitDock application policy values, not claims about GitHub/Telegram platform hard limits.

## GitHub HTTP/retry/pagination defaults

| Constant | Value | Meaning |
|---|---:|---|
| `HTTP_CONNECT_TIMEOUT_SECONDS` | 10.0 | outbound connect timeout |
| `HTTP_READ_TIMEOUT_SECONDS` | 30.0 | outbound read/write timeout baseline |
| `GITHUB_MAX_RETRIES` | 3 | transient retries after initial attempt |
| `RETRY_BASE_DELAY_SECONDS` | 0.5 | exponential-backoff base |
| `RETRY_MAX_DELAY_SECONDS` | 8.0 | backoff ceiling |
| `GITHUB_MAX_PAGES` | 100 | pagination iterator safety ceiling |
| `GITHUB_REPOSITORY_FETCH_PAGE_SIZE` | 100 | GitHub repository fetch page size |

Rules:

- GET/HEAD safe retry by default for configured transient classes.
- Write-like methods default to no retry.
- Non-read method may opt into safe retry only after higher layer establishes idempotency/replay safety.
- Redirects are not followed automatically.
- Absolute API/pagination targets accepted only for canonical HTTPS `api.github.com`.

## GitHub event names planned for initial subscriptions

- `installation`
- `installation_repositories`
- `push`
- `issues`
- `issue_comment`
- `pull_request`
- `pull_request_review`
- `pull_request_review_comment`
- `workflow_run`
- `release`
- `star`
- `fork`
- `create`
- `delete`

## GitHub permission groups

Do not map permissions ad hoc in handlers. Centralize capability -> permission/token-context mapping.

### Baseline/read capability

- Metadata: read — repository list/detail baseline
- Contents: read — verified P4.1 file browsing
- Issues: read when issue browsing enabled
- Pull requests: read when PR browsing enabled
- Actions: read when workflow/run inspection enabled

### Write capability milestones

- Contents: write — verified P4.1 one-file create/update/delete using repository-scoped installation token
- Issues: write — issue/comment/labels/assignees
- Pull requests: write — PR interactions/reviews/merges
- Actions: write — dispatch/retry/cancel where needed
- Workflows: write — verified P4.1 special capability required only when editing `.github/workflows/`
- Administration: write — verified P3.3 repository settings/rename/delete scope

P3.2 durable user authorization does not by itself enable any of these write permissions.

## Risk tiers

| Tier | Name | Examples | Confirmation |
|---|---|---|---|
| 0 | Read | browse/search/view | none |
| 1 | Reversible/sensitive local or write | comment, branch, workflow dispatch, local account disconnect | context/persisted confirmation where appropriate |
| 2 | High impact | merge, direct default-branch update, ZIP sync, rename/archive/visibility | dedicated persisted confirmation |
| 3 | Destructive | delete repo, transfer, destructive mass delete | exact target verification + final persisted confirm |

P3.2 local disconnect is local-state destructive enough to require persisted confirmation even though it does not delete a GitHub resource. P4.1 one-file writes use persisted staged intent/confirmation even when their operation-specific tier is below repository deletion because stale/replay safety requires durable server-side authority.

## Audit operation names

Stable examples:

- `repo.create`
- `repo.update_settings`
- `repo.rename`
- `repo.archive`
- `repo.visibility_change`
- `repo.delete`
- `file.create`
- `file.update`
- `file.delete`
- `sync.apply`
- `branch.create`
- `issue.create`
- `issue.comment`
- `issue.close`
- `pr.comment`
- `pr.review`
- `pr.merge`
- `workflow.dispatch`
- `workflow.rerun`
- `workflow.cancel`

Read-only cache refresh/navigation is not a GitHub write audit operation.

## Environment variable naming convention

Secrets/deployment settings use uppercase `GITDOCK_*` keys where practical, including:

- `GITDOCK_ENV`
- `GITDOCK_LOG_LEVEL`
- `GITDOCK_DATABASE_URL`
- `GITDOCK_TELEGRAM_BOT_TOKEN`
- `GITDOCK_TELEGRAM_OWNER_ID`
- `GITDOCK_PUBLIC_BASE_URL`
- `GITDOCK_TELEGRAM_WEBHOOK_SECRET`
- `GITDOCK_GITHUB_APP_ID`
- `GITDOCK_GITHUB_APP_SLUG`
- `GITDOCK_GITHUB_CLIENT_ID`
- `GITDOCK_GITHUB_CLIENT_SECRET`
- `GITDOCK_GITHUB_PRIVATE_KEY_PATH`
- `GITDOCK_GITHUB_WEBHOOK_SECRET`
- credential-encryption key/version settings for protected stored material.

Real values must never be committed.
