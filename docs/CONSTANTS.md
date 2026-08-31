# GitDock — Canonical Constants

Status: authoritative constants. Change intentionally and record meaningful architecture/security changes in `docs/DECISIONS.md`.

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

## Telegram UI constants

| Constant | Initial value | Purpose |
|---|---:|---|
| `DEFAULT_PAGE_SIZE` | 8 | General Telegram list pagination; used by P2.3 repository list |
| `SEARCH_PAGE_SIZE` | 6 | Richer repository search cards/rows for P3.1 |
| `MAX_PRIMARY_BUTTONS_PER_ROW` | 2 | Default keyboard density |
| `TEXT_PAGE_TARGET_CHARS` | 3500 | Safe target for paginated long text/log rendering |
| `CONFIRMATION_TTL_SECONDS` | 300 | General confirmation expiry |
| `DANGER_CONFIRMATION_TTL_SECONDS` | 180 | High-risk operation expiry |
| `CALLBACK_SCHEMA_VERSION` | `v1` | Callback compatibility/versioning |

Telegram callback data must remain compact. Prefer stable IDs/session IDs over embedding long repository names/paths.

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

## Callback namespace

Canonical prefix:

`gd:v1:<area>:<action>:<compact-context>`

Verified P2.3 examples/shapes:

- `gd:v1:home:open`
- `gd:v1:home:refresh`
- `gd:v1:connect:begin`
- `gd:v1:connect:info`
- `gd:v1:repos:list:<filter>:<page>`
- `gd:v1:repos:filters:<filter>:<page>`
- `gd:v1:repos:filter:<filter>`
- `gd:v1:repo:open:<filter>:<page>:<repo-id-base36>`

Future examples may add areas such as files/actions/issues, but must keep the same versioned/compact principle.

Rules:

- Never use user-supplied raw path/repository names when that risks callback-size overflow.
- P2.3 repository callbacks use GitHub numeric repository ID encoded compactly, plus filter/page navigation context.
- Resolve repository IDs server-side through the current GitDock user + active installation context; callback possession is not authorization.
- Reject unknown callback schema versions safely.
- Keep encoded callback data within Telegram's 64-byte limit; unit tests enforce this for maximum signed 64-bit repository IDs and long repository names.
- Do not place credentials, OAuth material, or private GitHub data that is unnecessary for routing into callback payloads.

## P2.3 repository filter values

Canonical filter identifiers are machine values, not translated UI labels:

- `all`
- `private`
- `public`
- `active`
- `archived`
- `source`
- `fork`

Do not invent handler-local aliases without updating callback compatibility/versioning deliberately.

## Repository/file operation limits

Initial policy values; implementation must make them configurable where appropriate.

| Constant | Initial value | Notes |
|---|---:|---|
| `TEXT_PREVIEW_MAX_BYTES` | 256 KiB | Larger files use download/limited preview flow |
| `SINGLE_UPLOAD_MAX_BYTES` | 20 MiB | Conservative application limit |
| `ZIP_EXTRACT_MAX_FILES` | 5000 | Zip-bomb guard |
| `ZIP_EXTRACT_MAX_TOTAL_BYTES` | 250 MiB | Extracted-size guard |
| `ZIP_MAX_PATH_DEPTH` | 25 | Path abuse guard |
| `DIFF_PREVIEW_MAX_FILES` | 200 | Above this, show summary/filter review |
| `DIFF_TEXT_MAX_BYTES_PER_FILE` | 512 KiB | Large diff uses metadata/download path |
| `TEMP_WORKSPACE_TTL_MINUTES` | 60 | Cleanup stale sync sessions |

These are GitDock policy limits, not claims about GitHub/Telegram hard limits.

## GitHub HTTP/retry/pagination defaults

| Constant | Value | Meaning |
|---|---:|---|
| `HTTP_CONNECT_TIMEOUT_SECONDS` | 10.0 | outbound connect timeout |
| `HTTP_READ_TIMEOUT_SECONDS` | 30.0 | outbound read/write timeout baseline |
| `GITHUB_MAX_RETRIES` | 3 | maximum transient retries after the initial attempt |
| `RETRY_BASE_DELAY_SECONDS` | 0.5 | exponential-backoff base |
| `RETRY_MAX_DELAY_SECONDS` | 8.0 | backoff ceiling |
| `GITHUB_MAX_PAGES` | 100 | pagination safety ceiling for one iterator |

P2.2 retry rules:

- GET/HEAD use safe retry mode by default for network/timeouts and HTTP 408/500/502/503/504.
- Write-like methods default to **no retry**.
- A non-read method may opt into `RetryMode.SAFE` only when a higher layer has explicitly established idempotency/retry safety.
- Redirects are not followed automatically.
- Absolute API/pagination targets are accepted only for canonical HTTPS `api.github.com`; external/protocol-relative/credentialed/fragment URLs are rejected.

Do not duplicate timeout/backoff/page-limit magic numbers in handlers.

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

Do not map permissions ad hoc in handlers. Centralize capability -> required permission mapping.

### Baseline/read capability

- Metadata: read — P2.3 repository list/detail baseline
- Contents: read when repository content browsing is enabled
- Issues: read when issue browsing is enabled
- Pull requests: read when PR browsing is enabled
- Actions: read when workflow/run inspection is enabled

### Write capability milestones

- Contents: write — file/branch/content updates
- Issues: write — issue/comment/labels/assignees operations
- Pull requests: write — PR interactions/reviews/merges as supported
- Actions: write — workflow dispatch/retry/cancel where needed
- Workflows: write — only if GitDock edits `.github/workflows/`
- Administration: write — repository create/settings/rename/delete operations that require it

Request only the minimum permissions for enabled features. P2.3 must not request write/admin permission.

## Risk tiers

| Tier | Name | Examples | Confirmation |
|---|---|---|---|
| 0 | Read | browse/search/view | none |
| 1 | Reversible write | comment, issue, branch, workflow dispatch | context confirmation where appropriate |
| 2 | High impact | merge, direct default-branch update, ZIP sync, rename/archive/visibility | dedicated confirmation screen |
| 3 | Destructive | delete repo, transfer, destructive mass delete | exact target verification + final confirm |

P2.3 home/repository list/detail is Tier 0.

## Audit operation names

Use stable machine identifiers such as:

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

Secrets and deployment configuration use uppercase `GITDOCK_*` keys where practical.

Expected groups:

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
- credential-encryption key/version settings for stored protected material

Real values must never be committed.
