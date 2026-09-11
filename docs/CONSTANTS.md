# GitDock — Canonical Constants

Status: authoritative executable/policy constants through P5.1 implementation. Change intentionally; meaningful architecture/security changes belong in `docs/DECISIONS.md` when they alter durable product direction.

## Product / HTTP identity

| Constant | Value |
|---|---|
| `APP_NAME` | `GitDock` |
| `APP_SLUG` | `gitdock` |
| `PRIMARY_UI_LANGUAGE` | `ar` |
| `TELEGRAM_CALLBACK_PREFIX` | `gd` |
| `CALLBACK_SCHEMA_VERSION` | `v1` |
| `HEALTH_PATH` | `/health` |
| `READINESS_PATH` | `/ready` |
| `TELEGRAM_WEBHOOK_PATH` | `/telegram/webhook` |
| `GITHUB_SETUP_CALLBACK_PATH` | `/github/setup/callback` |
| `GITHUB_OAUTH_CALLBACK_PATH` | `/github/oauth/callback` |
| `GITHUB_WEBHOOK_PATH` | `/github/webhook` |

## GitHub API identity

| Constant | Value |
|---|---|
| `GITHUB_API_BASE_URL` | `https://api.github.com` |
| `GITHUB_WEB_BASE_URL` | `https://github.com` |
| `GITHUB_REST_API_VERSION` | `2026-03-10` |
| `GITHUB_ACCEPT_HEADER` | `application/vnd.github+json` |
| `GITHUB_USER_AGENT` | `GitDock/0.1` |

## Authentication / confirmation timing

| Constant | Value | Purpose |
|---|---:|---|
| `GITHUB_APP_JWT_IAT_SKEW_SECONDS` | 60 | App JWT clock-skew tolerance |
| `GITHUB_APP_JWT_LIFETIME_SECONDS` | 540 | bounded App JWT lifetime |
| `INSTALLATION_TOKEN_REFRESH_MARGIN_SECONDS` | 300 | installation-token refresh margin |
| `USER_ACCESS_TOKEN_REFRESH_MARGIN_SECONDS` | 300 | user-token refresh margin |
| `GITHUB_AUTH_STATE_TTL_SECONDS` | 600 | durable OAuth/setup state expiry |
| `CONFIRMATION_TTL_SECONDS` | 300 | sensitive confirmation expiry |
| `CONFIRMATION_TOKEN_BYTES` | 12 | opaque confirmation-token entropy source bytes |
| `FILE_WRITE_SESSION_TTL_SECONDS` | 900 | staged one-file write lifetime |

## P5.1 webhook ingestion constants

| Constant | Value | Purpose |
|---|---:|---|
| `GITHUB_WEBHOOK_MAX_BODY_BYTES` | `25_000_000` bytes | hard raw request/persistence ceiling |
| `GITHUB_WEBHOOK_RETENTION_SECONDS` | `7 * 24 * 60 * 60` (7 days) | raw accepted-delivery retention before processed pruning |
| `GITHUB_WEBHOOK_PROCESSING_LEASE_SECONDS` | `5 * 60` (5 min) | abandoned `processing` work becomes eligible for recovery |
| `GITHUB_WEBHOOK_RETRY_DELAY_SECONDS` | `60` | default failed-work retry delay |

Webhook rules tied to these constants:

- verify `X-Hub-Signature-256` on exact raw bytes before trusted metadata processing;
- over-limit bodies are rejected before durable acceptance;
- delivery IDs are durable idempotency keys, not process-memory keys;
- successful acknowledgement occurs only after durable insert/deduplication;
- retention applies to private raw webhook payloads, not permission to log them.

## Telegram / search / file UI constants

| Constant | Value |
|---|---:|
| `DEFAULT_PAGE_SIZE` | 8 |
| `SEARCH_PAGE_SIZE` | 6 |
| `SEARCH_QUERY_MAX_CHARS` | 180 |
| `SEARCH_COMPILED_QUERY_MAX_CHARS` | 240 |
| `SEARCH_SESSION_ID_BYTES` | 6 |
| `SEARCH_OWNER_LOGIN_MAX_CHARS` | 39 |
| `SEARCH_TOPIC_MAX_CHARS` | 50 |
| `SEARCH_MIN_STARS_MAX` | 1,000,000,000 |
| `FILE_TEXT_PREVIEW_MAX_BYTES` | 256 KiB |
| `FILE_SINGLE_UPLOAD_MAX_BYTES` | 20 MiB |
| `FILE_PREVIEW_PAGE_CHARS` | 2800 |
| `FILE_PATH_MAX_CHARS` | 1024 |
| `FILE_REF_MAX_CHARS` | 255 |
| `FILE_COMMIT_MESSAGE_MAX_CHARS` | 500 |
| `FILE_BROWSE_SESSION_ID_BYTES` | 6 bytes |

## P4.3 run-assistant bounds

| Constant | Value |
|---|---:|
| `RUN_EVIDENCE_MAX_FILES` | 8 |
| `RUN_EVIDENCE_FILE_MAX_BYTES` | 128 KiB |

## GitHub HTTP/retry/pagination defaults

| Constant | Value |
|---|---:|
| `HTTP_CONNECT_TIMEOUT_SECONDS` | 10.0 |
| `HTTP_READ_TIMEOUT_SECONDS` | 30.0 |
| `GITHUB_MAX_RETRIES` | 3 |
| `RETRY_BASE_DELAY_SECONDS` | 0.5 |
| `RETRY_MAX_DELAY_SECONDS` | 8.0 |
| `GITHUB_MAX_PAGES` | 100 |
| `GITHUB_REPOSITORY_FETCH_PAGE_SIZE` | 100 |

Rules: GET/HEAD may use bounded safe retry. Write-like methods default to no retry. Redirects are not followed automatically. Absolute API/pagination targets are canonical HTTPS GitHub API only.

## Canonical navigation labels

- `🏠 الرئيسية`
- `❌ إلغاء`
- `⬅️ رجوع`
- `🔄 تحديث`

## Callback namespace

Canonical form: `gd:v1:<area>:<action>:<compact-context>`.

Callbacks carry compact transport context only. Repository paths, credentials, OAuth/PKCE material, confirmation authority details, webhook secrets/signatures, staged file bodies, and raw webhook payloads do not belong in callback data. Callback possession is never authorization proof and current shapes remain within Telegram's 64-byte limit.

## Environment variables

Canonical deployment keys include:

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
- credential-encryption key/version settings.

Real values must never be committed.

## Future archive/sync policy targets

| Policy | Value |
|---|---:|
| ZIP max files | 5000 |
| ZIP max extracted bytes | 250 MiB |
| ZIP max path depth | 25 |
| diff preview max files | 200 |
| diff text max/file | 512 KiB |
| temp workspace TTL | 60 minutes |

These remain future P8 application-policy targets, not platform-limit claims.

## Risk tiers

- Tier 0: read.
- Tier 1: reversible/sensitive local or write action with contextual/persisted confirmation where appropriate.
- Tier 2: high-impact operation with dedicated persisted confirmation.
- Tier 3: destructive operation with exact-target verification + final persisted confirmation.

Webhook delivery acceptance is an authenticated ingress workflow, not a Telegram risk-tier write action; its safety comes from signature verification, bounded durable idempotency, and downstream state transitions.
