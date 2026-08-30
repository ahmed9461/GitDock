# GitDock — Canonical Constants

Status: authoritative initial constants. Change intentionally and record meaningful changes in `docs/DECISIONS.md`.

## Product identity

| Key | Value |
|---|---|
| `APP_NAME` | `GitDock` |
| `APP_SLUG` | `gitdock` |
| `TELEGRAM_CALLBACK_PREFIX` | `gd` |
| `PRIMARY_UI_LANGUAGE` | `ar` |
| `DEFAULT_GITHUB_API_VERSION` | implementation must use the current supported pinned GitHub API version selected during P1 |

Do not duplicate these literals throughout handlers/services.

## Telegram UI constants

| Constant | Initial value | Purpose |
|---|---:|---|
| `DEFAULT_PAGE_SIZE` | 8 | General Telegram list pagination |
| `SEARCH_PAGE_SIZE` | 6 | Richer repository search cards/rows |
| `MAX_PRIMARY_BUTTONS_PER_ROW` | 2 | Default keyboard density |
| `TEXT_PAGE_TARGET_CHARS` | 3500 | Safe target for paginated long text/log rendering |
| `CONFIRMATION_TTL_SECONDS` | 300 | General confirmation expiry |
| `DANGER_CONFIRMATION_TTL_SECONDS` | 180 | High-risk operation expiry |
| `CALLBACK_SCHEMA_VERSION` | `v1` | Callback compatibility/versioning |

Telegram callback data must remain compact and within Telegram limits. Prefer opaque short IDs/session IDs over embedding long repository names/paths.

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

Canonical shape:

`gd:v1:<area>:<action>:<short-id-or-page>`

Examples:

- `gd:v1:home:open`
- `gd:v1:repos:list:2`
- `gd:v1:repo:open:a7f3`
- `gd:v1:file:view:k91p`
- `gd:v1:act:runs:p1`

Rules:

- Never use user-supplied raw path/repository names when that risks callback-size overflow.
- Resolve short IDs through a persisted/expiring interaction context when needed.
- Callback handlers must reject unknown schema versions safely.

## Repository/file operation limits

Initial policy values; implementation must make them configurable.

| Constant | Initial value | Notes |
|---|---:|---|
| `TEXT_PREVIEW_MAX_BYTES` | 256 KiB | Larger files use download/limited preview flow |
| `SINGLE_UPLOAD_MAX_BYTES` | 20 MiB | Conservative bot-side initial application limit; may be adjusted after transport verification |
| `ZIP_EXTRACT_MAX_FILES` | 5000 | Zip-bomb guard |
| `ZIP_EXTRACT_MAX_TOTAL_BYTES` | 250 MiB | Extracted-size guard |
| `ZIP_MAX_PATH_DEPTH` | 25 | Path abuse/accidental giant trees guard |
| `DIFF_PREVIEW_MAX_FILES` | 200 | Above this, show summary + filtered review instead of rendering everything |
| `DIFF_TEXT_MAX_BYTES_PER_FILE` | 512 KiB | Large diff uses metadata/download path |
| `TEMP_WORKSPACE_TTL_MINUTES` | 60 | Cleanup stale sync sessions |

These are GitDock application policy limits, not claims about GitHub/Telegram hard limits.

## HTTP/retry defaults

| Constant | Initial value |
|---|---:|
| `HTTP_CONNECT_TIMEOUT_SECONDS` | 10 |
| `HTTP_READ_TIMEOUT_SECONDS` | 30 |
| `GITHUB_MAX_RETRIES` | 3 |
| `RETRY_BASE_DELAY_SECONDS` | 0.5 |
| `RETRY_MAX_DELAY_SECONDS` | 8 |

Retry only operations safe to retry or protected by idempotency/preconditions. Do not blindly retry destructive writes.

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

- Metadata: read
- Contents: read when repository content browsing is enabled
- Issues: read when issue browsing is enabled
- Pull requests: read when PR browsing is enabled
- Actions: read when workflow/run inspection is enabled

### Write capability milestones

- Contents: write — file/branch/content updates
- Issues: write — issue/comment/labels/assignees operations
- Pull requests: write — PR interactions/reviews/merges as supported
- Actions: write — workflow dispatch/retry/cancel where needed
- Workflows: write — only if GitDock edits files under `.github/workflows/`
- Administration: write — repository create/settings/rename/delete operations that require it

Request only the minimum permissions for enabled features.

## Risk tiers

| Tier | Name | Examples | Confirmation |
|---|---|---|---|
| 0 | Read | browse/search/view | none |
| 1 | Reversible write | comment, issue, branch, workflow dispatch | context confirmation where appropriate |
| 2 | High impact | merge, direct default-branch update, ZIP sync, rename/archive/visibility | dedicated confirmation screen |
| 3 | Destructive | delete repo, transfer, destructive mass delete | exact target verification + final confirm |

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
- `GITDOCK_GITHUB_CLIENT_ID`
- `GITDOCK_GITHUB_CLIENT_SECRET`
- `GITDOCK_GITHUB_PRIVATE_KEY_PATH`
- `GITDOCK_GITHUB_WEBHOOK_SECRET`
- encryption/key-management setting for stored user credentials/tokens

Real values must never be committed.