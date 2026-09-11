# GitDock — Architecture Specification

Status: verified architecture through P4.2 branch/commit implementation; P4.2 governance/merge chain in progress.

## 1. Architectural goals

- Clear separation between Telegram UI, GitHub transport/auth, domain rules, persistence, and background processing.
- Restart-safe handling for important multi-step operations, confirmations, staged writes, and future webhook work.
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

Shared persistence: PostgreSQL + Alembic
```

## 3. Runtime modes

### Development

- Telegram long polling allowed.
- GitHub webhook testing may use secure tunnel/replay fixtures.
- SQLite may be used for portable tests/development.

### Production

- FastAPI serves Telegram webhook, GitHub webhook, setup/OAuth callbacks, health/readiness.
- PostgreSQL required.
- Deployment remains suitable for systemd.
- HTTPS terminates at a trusted reverse proxy/application deployment layer.
- Future event worker may initially share deployment but remains a distinct DB-backed component.

## 4. Source layout through P4.2

```text
gitdock/
├── app.py
├── core/
├── http/routes/
├── telegram/
│   ├── bot.py
│   ├── callbacks.py
│   ├── file_callbacks.py
│   ├── git_callbacks.py
│   ├── routers/
│   │   ├── repositories.py
│   │   ├── repository_admin.py
│   │   ├── files.py
│   │   └── git_tools.py
│   ├── keyboards/
│   │   ├── repositories.py
│   │   ├── repository_admin.py
│   │   ├── files.py
│   │   └── git_tools.py
│   ├── renderers/
│   │   ├── repository_admin.py
│   │   ├── files.py
│   │   └── git_tools.py
│   ├── states/
│   │   ├── repository_admin.py
│   │   ├── files.py
│   │   └── git_tools.py
│   └── middleware/
├── github/
│   ├── auth*.py
│   ├── client.py
│   ├── contents.py
│   ├── credentials.py
│   ├── errors.py
│   ├── pagination.py
│   ├── permissions.py
│   ├── repositories.py
│   ├── repository_admin.py
│   ├── git_tools.py
│   └── token_provider.py
├── domain/
│   └── files.py
├── services/
│   ├── confirmations.py
│   ├── identity.py
│   ├── repositories.py
│   ├── repository_admin*.py
│   ├── file_*.py
│   ├── git_tools.py
│   ├── runtime.py
│   └── user_authorization.py
├── db/
│   ├── migrations/versions/
│   │   ├── 0005_audit_log.py
│   │   └── 0006_file_write_sessions.py
│   └── models/
└── workers/

tests/
├── unit/
├── integration/
├── contract/
└── fixtures/
```

Exact filenames may evolve; layer boundaries are intentional.

## 5. Layer responsibilities

### Telegram layer

Receives updates, renders Arabic screens, builds keyboards, collects input, and maps user actions to application services.

It must not:

- issue raw GitHub HTTP;
- contain raw DB queries;
- construct OAuth/token flows;
- infer write authority from callback possession;
- own durable confirmation/staging/risk rules.

P3.3 administration, P4.1 files, and P4.2 Git tools follow the same split: callbacks/keyboards/renderers/FSM/routers are presentation/transport; services own authority, revalidation, credential selection, reconciliation, and audit.

### Application services

Verified service boundaries include:

- owner identity resolution;
- `RepositoryReadService` for installed repository navigation/cache sync;
- public search service;
- `GitHubUserAuthorizationService` for durable user auth/refresh/local disconnect;
- `ConfirmationService` for restart-safe one-time confirmations;
- `RepositoryAdminService` plus reconciliation helpers;
- P4.1 file browser/read/write/store/audit helpers;
- `GitToolsService` for P4.2 branch/commit reads and branch-create orchestration;
- runtime composition wiring clients/providers/services/gateways/DB factories once.

### Domain layer

Pure rules belong here or in narrow pure helpers: risk classification, path/ref/branch validation, text/binary classification, diff/hash planning, future sync planning, state transitions, event normalization, and confirmation requirements.

### GitHub transport/auth boundaries

`GitHubRestClient` is the canonical ordinary REST transport. Authentication-specific App/OAuth endpoints remain behind auth clients.

Verified transport invariants:

- centralized GitHub headers/API version/User-Agent;
- `SecretStr` materialized only at outbound boundary;
- canonical HTTPS `api.github.com` absolute targets only;
- hostile pagination target rejection and loop/page guards;
- redirects not automatically followed;
- stable safe error categories without raw-body echo;
- typed rate-limit metadata;
- bounded GET/HEAD retry;
- write-like methods no retry by default.

Feature gateways on this transport include:

- repository read/search;
- P3.3 repository administration;
- P4.1 `GitHubContentsGateway`;
- P4.2 `GitHubGitToolsGateway` for branches, commits, compare, and create-ref.

No feature creates a parallel raw HTTP stack.

## 6. Authentication and capability contexts

### Telegram owner authentication

`GITDOCK_TELEGRAM_OWNER_ID` is the v1 ingress allowlist. Middleware rejects/ignores unauthorized users before sensitive routing.

### GitHub App installation binding

Setup `installation_id` is untrusted candidate data. Binding occurs only after App-context and authenticated-user-context identity match and suspension/conflict checks pass.

### Durable GitHub user authorization — P3.2

OAuth state + PKCE S256, authenticated `GET /user`, encrypted versioned credential storage, expiry metadata, and `credential_generation` remain authoritative. Refresh writes only if current durable generation/account/preconditions still match.

### Repository administration — P3.3

- personal/org create: durable GitHub user OAuth context;
- repository update/delete: repository-scoped installation token with `administration: write`.

### File browser/write — P4.1

- repository browsing/file reads: repository-scoped installation context with contents read;
- ordinary one-file writes: repository-scoped installation token with `contents: write`;
- `.github/workflows/*` writes additionally require `workflows: write`.

### Branch/commit tools — P4.2

- reads resolve the current installed repository through the established repository/file context resolver and canonical REST gateway;
- branch creation obtains `contents: write` only after persisted confirmation is consumed and current base/target preconditions are revalidated;
- write token is scoped to the selected GitHub repository ID;
- cache/callback presence never grants branch-write authority.

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

P4.2 introduces **no new migration**. Branch creation reuses `pending_confirmations` plus `audit_log`; ordinary branch/commit read state stays transient/server-side.

GitHub remains source of truth for repository resources.

## 8. Confirmation/staging architecture

A Telegram callback is transport, not durable authorization.

### P3.2 local disconnect

Persist one-time confirmation bound to current account/generation/installation set. Home/Cancel/Confirm consumes authority. Stale state removes nothing.

### P3.3 repository administration

Persist user/operation-bound, expiring, single-use, target-fingerprinted confirmation. Update/delete refresh remote state before mutation; delete additionally requires exact current `owner/name`.

### P4.1 one-file writes

Validate → read current branch/file → stage reviewed intent → persisted confirmation → consume once → re-resolve/revalidate → scoped token → single Contents API write → reconcile uncertainty → audit/scrub content.

### P4.2 branch creation

1. resolve current installed repository context;
2. validate target branch and base ref;
3. resolve base ref to a concrete current commit SHA;
4. verify target branch does not currently exist;
5. persist a Tier 1 confirmation whose fingerprint binds repository ID + target branch + base ref + base SHA;
6. render explicit preview showing repository, target branch, base ref, and base SHA;
7. on confirm, atomically consume the one-time authority;
8. re-resolve repository context;
9. re-resolve the base ref and require exact staged base SHA;
10. re-check target branch absence;
11. obtain repository-scoped `contents: write` token;
12. issue one GitHub create-ref POST;
13. if outcome may be uncertain, re-read target branch instead of replaying POST;
14. exact target SHA may prove applied; otherwise retain explicit `UNCERTAIN`;
15. audit safe result metadata.

Duplicate target, missing base, stale base, cancelled/reused/invalid confirmation all produce no new GitHub write.

## 9. P4.2 read lifecycle

### Branches

1. resolve current installed repository context;
2. fetch branch pages through `GitHubGitToolsGateway`;
3. optionally filter fetched names case-insensitively;
4. render names/protection/SHA summary in Arabic UI;
5. keep repository/session authority server-side; compact callback only carries navigation context.

### Commits

1. select default branch or validated explicit branch/tag/SHA ref;
2. fetch recent commits through typed gateway;
3. store short commit SHA list only as transient FSM navigation context;
4. commit detail re-fetches requested SHA/ref from GitHub;
5. canonical GitHub commit URL is validated before rendering a link.

### Compare

Base/head refs are validated and percent-encoded as path components before the canonical REST request. Telegram output presents status, ahead/behind, commit count, returned file count, and at most ten file rows to keep the message bounded.

## 10. P4.1 read/write lifecycle

P4.1 remains unchanged: directory/file reads resolve current repository + validated path/ref through Contents gateway. One-file writes bind branch-head/file SHA and reviewed content digests in restart-safe staging before any write.

## 11. GitHub write strategy

- P3.3 repository administration: persisted confirmation + operation-specific credentials + refreshed remote preconditions + one write + reconciliation + audit.
- P4.1 one-file writes: Contents API + durable staging + branch/file SHA protection + one write + reconciliation + audit.
- P4.2 branch create: explicit target/base + persisted confirmation + exact base SHA/target absence revalidation + repository-scoped `contents: write` + one create-ref request + reconciliation + audit.
- P8 multi-file/ZIP synchronization: future coherent reviewable tree/commit operation, normally on review branch + optional PR.
- Direct default-branch mass replacement is not default.
- No normal v1 force-push/branch force-update UI.

## 12. Webhook ingestion pipeline

Future P5 pipeline remains: raw bytes → HMAC verification → delivery/event validation → idempotent durable insert → quick ACK → worker normalization/enrichment/preferences → Telegram render → processed/retry state. Duplicate delivery IDs never create duplicate notifications.

## 13. Clone/setup/run inference

P4.3 must generate commands only. It must not execute repository instructions automatically. Detect project metadata, construct commands from trusted templates, quote per OS, and label confidence/source. README/script content is untrusted text.

## 14. Error model / retry semantics

Transport categories include authentication, missing permission, not found/inaccessible, conflict/precondition, validation, rate limited, transient, and unexpected shape/GitHub failure.

Higher layers add domain states:

- repository administration: applied/stale/invalid/uncertain;
- P4.1 files: applied/stale/invalid/uncertain;
- P4.2 branch create: `APPLIED`, `INVALID`, `STALE`, `EXISTS`, `UNCERTAIN`.

GET/HEAD may bounded-retry transient failures. Write-like calls are issued once unless higher-level semantics have independently proven replay safety; P3.3/P4.1/P4.2 reconcile uncertain outcomes instead of blindly retrying.

## 15. Observability/audit

Safe correlation may include Telegram update/user ID, GitHub request/delivery ID, operation ID, repository ID/full name, branch/ref/path, commit SHA, and status. Structured logging redacts credentials/auth headers/OAuth/PKCE/private keys and avoids raw upstream auth/error bodies.

P4.2 branch-create audit may include operation, repository, target branch, base ref, base SHA, risk tier, request ID, and status. It never contains token material.

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
- P3.3: 117-test repository-administration implementation.
- P4.1: 148 tests, mypy 87 source files, all gates green through final feature delivery.
- P4.2 implementation head `5a4f7aa4eb557e69665a7311f32c8060e38b1518`: CI `34647181024` green with **165 tests** on Python 3.12/3.13, mypy clean on **94 source files**, format/lint/compile/audit/secrets/PEP 751 locks green, and PostgreSQL 17 migration round-trip through `0006_file_write_sessions` green.

P4.2 remains in governance closeout until documentation-head CI, non-draft PR CI, protected merge, post-feature `main` CI, and final handoff are complete.

## 18. Known non-blocking maintenance warnings

- Starlette/FastAPI `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

## 19. Source references for security/auth assumptions

- GitHub App permissions: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- Installation authentication: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation
- Webhook validation: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- Repository contents: https://docs.github.com/en/rest/repos/contents
- Branches: https://docs.github.com/en/rest/branches/branches
- Commits: https://docs.github.com/en/rest/commits/commits
- Git refs: https://docs.github.com/en/rest/git/refs
- Compare: https://docs.github.com/en/rest/commits/commits#compare-two-commits
- Actions workflows: https://docs.github.com/en/rest/actions/workflows
