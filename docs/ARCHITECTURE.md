# GitDock — Architecture Specification

Status: verified architecture through P5.1 implementation; P5.1 delivery closeout pending.

## 1. Architectural goals

- Separate Telegram UI, HTTP ingress, GitHub transport/auth, domain rules, persistence, and background work.
- Make important confirmations, staged writes, and accepted webhook work restart-safe.
- Keep normal CI independent of real Telegram/GitHub network calls.
- Use least-privilege authentication and repository-scoped authority.
- GitHub remains authoritative for GitHub resources; local persistence exists for identity/auth, navigation/cache, preferences, audit, confirmation/staging, and durable work queues.
- Do not introduce parallel HTTP/persistence stacks when an existing boundary already fits the feature.

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
     +------+---------------------+
     |                            |
     v                            v
aiogram UI               raw GitHub webhook verifier
     |                            |
     v                            v
Application Services       durable webhook inbox
     |                            |
     |                            v
     |                     future event worker
     |                            |
     +-------------+--------------+
                   |
                   v
             GitHub Gateway
              REST/Auth
                   |
                   v
                 GitHub

Shared persistence: PostgreSQL + Alembic
```

## 3. Runtime modes

### Development/test

- Telegram long polling allowed.
- GitHub webhook testing may use local TestClient/replay fixtures/secure tunnel as needed.
- SQLite may be used for portable tests/development.

### Production

- FastAPI serves Telegram webhook, GitHub webhook, setup/OAuth callbacks, health/readiness.
- PostgreSQL required.
- HTTPS terminates at a trusted reverse proxy/application layer.
- Event workers may share deployment initially but consume DB-backed work rather than depending on in-process request memory.

## 4. Source layout through P5.1

```text
gitdock/
├── app.py
├── core/
│   ├── config.py
│   └── constants.py
├── http/routes/
│   ├── github.py
│   ├── github_webhook.py
│   ├── health.py
│   └── telegram.py
├── telegram/
├── github/
│   ├── auth*.py
│   ├── client.py
│   ├── contents.py
│   ├── git_tools.py
│   ├── repositories.py
│   ├── repository_admin.py
│   ├── search.py
│   ├── token_provider.py
│   └── webhooks.py
├── domain/
├── services/
│   ├── confirmations.py
│   ├── file_*.py
│   ├── git_tools.py
│   ├── repositories.py
│   ├── repository_admin*.py
│   ├── run_assistant.py
│   ├── runtime.py
│   └── webhooks.py
├── db/
│   ├── migrations/versions/
│   │   └── 0007_github_webhook_inbox.py
│   └── models/
│       └── webhook.py
└── workers/

tests/
├── unit/
├── integration/
├── contract/
└── fixtures/
```

Exact filenames may evolve; layer boundaries are intentional.

## 5. Layer responsibilities

### HTTP / Telegram transport

HTTP routes and Telegram routers collect transport input, enforce ingress-specific validation, call services, and render bounded output. They do not own durable authority/workflow logic or raw DB queries.

For P5.1, `github_webhook.py` owns only the HTTP boundary: bounded raw-body read, signature gate ordering, bounded header extraction, service call, and safe status response.

### Application services

Services own durable workflow/business state. Verified boundaries include repository reads/search/admin, durable GitHub user authorization, confirmations, file staging/writes, Git tools, run assistant, and `GitHubWebhookIngestionService`.

P5.1 service responsibilities:

- durable insert/idempotency/conflict semantics;
- worker claim state;
- attempt/retry processing state;
- processing lease recovery;
- completion/failure transitions;
- retention pruning;
- DB-dialect timestamp normalization.

### Domain / pure helpers

Pure validation/inference belongs in domain or narrow helper modules. `gitdock.github.webhooks` contains side-effect-free signature/metadata validation so it is directly testable.

### GitHub transport/auth

`GitHubRestClient` remains the canonical ordinary REST transport. P5.1 webhook verification is inbound cryptographic validation and does not create a second outbound HTTP client.

## 6. Authentication/capability contexts

- Telegram owner ID is the v1 UI allowlist.
- GitHub App installation identity is bound only after App/user identity checks.
- OAuth + PKCE provides durable user context when required.
- Repository writes request operation-specific scoped permission only after confirmation/precondition checks.
- P5.1 inbound webhook authenticity is independent of repository API token authority: it uses the configured GitHub webhook secret against the exact request bytes.

## 7. Persistence model

Persisted concepts now include:

- users/Telegram identities;
- GitHub accounts/installations/encrypted durable credentials;
- OAuth state;
- repository cache;
- pending confirmations;
- audit log;
- file-write staging;
- **GitHub webhook delivery inbox**.

P5.1 migration `0007_github_webhook_inbox` introduces `github_webhook_deliveries` with unique delivery identity, payload digest/size/raw bytes, processing/retry state, and retention timestamps.

GitHub remains source of truth for repository resources. The webhook inbox is source of truth only for GitDock's accepted-delivery processing lifecycle.

## 8. Existing write/confirmation architecture

A Telegram callback is transport, not durable authorization. Repository administration, one-file writes, and branch creation persist reviewed authority/preconditions, revalidate current GitHub state, issue at most the intended write, reconcile ambiguity, and audit safe metadata.

No normal v1 force-push/force branch-update UI exists.

## 9. P5.1 webhook ingestion lifecycle

1. FastAPI receives `POST /github/webhook`.
2. If webhook secret is not configured, endpoint is unavailable rather than accepting unverifiable work.
3. Body is consumed as raw bytes with a 25 MiB ceiling; over-limit input is rejected before persistence.
4. `X-Hub-Signature-256` is verified using HMAC-SHA256 over those exact raw bytes with constant-time comparison.
5. Only after successful authentication are `X-GitHub-Delivery` and `X-GitHub-Event` treated as trusted transport metadata and syntax/length validated.
6. Service hashes the raw body and checks durable delivery identity.
7. Exact duplicate ID/event/body returns duplicate without creating new work.
8. Same delivery ID with different content raises explicit conflict.
9. New delivery is committed to `github_webhook_deliveries` as `pending` before HTTP 202 is returned.
10. Request path ends; event-specific parsing/notification does not run in the HTTP acknowledgement path.

This keeps acknowledgement bounded and ensures accepted work survives process restart.

## 10. P5.1 worker-state lifecycle

`pending -> processing -> processed`

or

`pending -> processing -> failed -> processing ... -> processed`

Rules:

- claiming increments `attempt_count`;
- claim records `processing_started_at`;
- `failed` work has `next_attempt_at` and bounded `last_error_code`;
- stale `processing` rows older than the processing lease become claimable again after a worker crash/restart;
- processed rows keep raw payload only through a bounded retention window and can then be pruned;
- no notification is emitted by P5.1 itself.

PostgreSQL workers use row locking with skip-locked semantics to avoid normal concurrent double claims. SQLite remains portable test/dev storage and is not the production concurrency target.

## 11. P5.2/P5.3 boundary

Future pipeline after P5.1:

```text
durable authenticated delivery
  -> P5.2 event normalization
  -> repository/event preference evaluation
  -> P5.3 Telegram rendering/delivery
  -> processed/retry state
```

Event-specific normalization must consume the persisted authenticated raw payload, not re-trust arbitrary external input. Duplicate delivery identity must never create duplicate downstream work.

## 12. Clone/setup/run inference

P4.3 remains command generation only. Repository/README/script content is untrusted and never automatically executed. Evidence collection is bounded and output is credential-free.

## 13. Error/retry model

Outbound GitHub GET/HEAD may bounded-retry known transient failures; write-like calls are not blindly replayed.

P5.1 inbound errors are intentionally simple:

- unavailable config → 503;
- body too large → 413;
- signature failure → 403;
- authenticated invalid metadata → 400;
- delivery identity/content conflict → 409;
- accepted or exact duplicate → 202.

Downstream processing retries are represented durably in the inbox rather than by keeping the HTTP request open.

## 14. Observability/audit

Safe correlation may include Telegram user/update IDs, GitHub request/delivery IDs, repository IDs/names, branch/ref/path/SHA, operation state, and webhook event name/status.

Never log credentials, auth headers, webhook secret/signature values, OAuth/PKCE/private-key material, or unbounded raw private webhook payloads.

## 15. Dependency direction

```text
telegram -> services -> domain/github/persistence
http setup/oauth -> connection/auth services -> github auth/binding
http github webhook -> signature helper -> webhook service -> persistence
future worker -> webhook service/persistence -> normalization -> notification
```

Domain/pure helpers do not import Telegram or concrete DB/network clients.

## 16. Verified progression

- P3.3: 117 tests.
- P4.1: 148 tests; mypy 87 source files.
- P4.2: 165 tests; mypy 94 source files.
- P4.3: 182 tests; mypy 100 source files.
- P5.1 implementation head `e55c6e99001bb657ed2064459e92caca1f2e3481`, CI `34652564335`: **213 tests**, mypy **104 source files**, Ruff **176 files**, compile/audit/secrets/PEP 751/PostgreSQL round-trip all green through `0007_github_webhook_inbox`.

P5.1 is not formally complete until documentation-head CI, non-draft PR CI, protected squash merge, post-feature `main` CI, and governance closeout complete.

## 17. Known non-blocking maintenance warnings

- Starlette/FastAPI `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

## 18. Source references for security/auth assumptions

- GitHub webhook validation: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- GitHub webhook events/payloads: https://docs.github.com/en/webhooks/webhook-events-and-payloads
- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- Installation authentication: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
- Repository contents: https://docs.github.com/en/rest/repos/contents
- Git refs: https://docs.github.com/en/rest/git/refs
