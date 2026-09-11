# GitDock — Project Memory

Purpose: durable facts future sessions must remember. This is not a task list.

Last updated: 2026-09-12

## Identity and product direction

- Product: **GitDock**.
- Repository: `ahmed9461/GitDock`.
- Telegram-first GitHub management/control bot.
- v1 user-facing language: Arabic; code/technical identifiers remain English/native.
- v1 boundary: one configured Telegram owner, while services/persistence remain multi-user-ready.
- Planned v1 covers repository search/administration, repository contents/file writes, branches/commits, clone/setup/run command generation, webhooks/notifications, Issues/PRs, Actions, releases, and safe ZIP/project synchronization.

## Canonical architecture

- Python 3.12+; CI verifies Python 3.12 and 3.13.
- aiogram 3.x Telegram UI.
- FastAPI HTTP ingress.
- httpx behind GitHub auth/gateway boundaries.
- async SQLAlchemy 2.x + Alembic.
- PostgreSQL production; SQLite only for portable tests/development.
- GitHub is source of truth.
- Telegram handlers stay thin; auth/token/DB/risk/business rules belong in services/auth/persistence.
- Important multi-step confirmation/write/event state is durable when restart safety matters.
- GitHub App installation/user tokens with minimum permissions are preferred over broad long-lived PATs.
- Ordinary feature code uses the canonical `GitHubRestClient`; do not build parallel raw HTTP stacks.

## Verified phase history

### P1 — foundation ✅

- Async app skeleton, owner middleware, persistence/migrations, CI/security/reproducibility foundation.
- Durable invariant: create a fresh aiogram Router for each Dispatcher; never reuse a module-global Router across Dispatcher instances.

### P2 — GitHub App/read core ✅

Durable facts:

- GitHub App is primary auth; RS256 App JWT and short-lived installation tokens.
- OAuth + PKCE S256 provides durable authenticated user context when needed.
- Raw OAuth state is not persisted; PKCE verifier/user credentials are encrypted with versioned keys.
- Installation identity is not trusted until App and authenticated-user identities agree and ownership/suspension checks pass.
- `GitHubRestClient` is the canonical REST transport with centralized headers/version/User-Agent, canonical HTTPS API target checks, safe error modeling, bounded GET/HEAD retries, and no blind write retries.
- `repositories_cache` is navigation/context state only, never authorization or source of truth.

### P3 — search and repository administration ✅

Durable facts:

- Public search works without installation and is isolated from installed authorization/cache state.
- Opaque active search sessions bind pagination/detail context; stale search sessions fail closed.
- Durable user OAuth credentials are encrypted, refresh-aware, and guarded by `credential_generation` against stale concurrency.
- `pending_confirmations` is the general DB-backed one-time confirmation store.
- Local disconnect removes GitDock-local credentials/bindings/cache/pending state and does not claim remote App uninstall.
- `RepositoryAdminService` owns repository create/settings/delete planning, confirmation, credential selection, refreshed preconditions, reconciliation, cache synchronization, and audit.
- Personal/org create uses durable GitHub user context; settings/delete use repository-scoped installation authority.
- Create is Tier 1; settings Tier 2; repository delete Tier 3 + exact typed `owner/name`.
- Sensitive confirmation cancellation/edit/back consumes pending authority.
- No blind write replay; uncertain outcomes reconcile remote state and remain `UNCERTAIN` if proof is unavailable.
- `audit_log` stores safe metadata only, never credentials or raw auth response bodies.

### P4.1 — file browser + stale-safe single-file writes ✅

Final feature delivery included directory/ref browsing, preview/download, create/upload/edit/replace/delete, durable one-file staging, exact branch/file stale checks, scoped `contents: write` and workflow permission handling, one-write reconciliation, audit, and staged-content scrubbing.

Durable facts:

- `file_write_sessions` is restart-safe one-file staging.
- Temporary staged create/update bytes are bounded to the staging lifecycle and scrubbed on consume/cancel/supersede/expiry/prune.
- Create requires target absence; update/delete require exact expected file SHA; branch HEAD must match staged snapshot.
- `.github/workflows/*` additionally requires `workflows: write`.
- File bodies never enter audit logs.
- Verified baseline: **148 tests**, mypy **87 source files**.

### P4.2 — branch/commit tools ✅

Durable facts:

- `GitHubGitToolsGateway` is the typed branch/commit/compare/create-ref boundary on `GitHubRestClient`.
- `GitToolsService` owns GitHub-backed reads and branch-create confirmation/stale checks/scoped credentials/reconciliation/audit.
- Branch creation is Tier 1: explicit target/base → resolved base SHA → persisted preview → confirm-time base/target revalidation → repository-scoped `contents: write` → one create-ref request → reconciliation → audit.
- Moved base returns `STALE`; duplicate target/missing base performs no write.
- Create-ref is never blindly replayed; exact target SHA is required to prove an uncertain request applied.
- No normal v1 force-push, force branch update, or branch-delete UI.
- Verified baseline: **165 tests**, mypy **94 source files**.

### P4.3 — clone/setup/run assistant ✅

Final feature-delivery chain:

- implementation head `fba538e3c6071365361def7d5970ff7b19b5819c` — CI `34650497474` green;
- documentation-synchronized head `989e826f8e845934b9255a78c91bfeca48f10538` — CI `34650840434` green;
- non-draft PR #20 — PR CI `34650940874` green and mergeable;
- protected squash merge `0f0750388a1a919917ba81586fad42ae2ab11336`;
- post-feature `main` CI `34651051039` green.

Verified contract:

- **182 tests** on Python 3.12 and 3.13;
- Ruff format/lint green on **167 files**;
- mypy clean on **100 source files**;
- compile, audit, secret scan, PEP 751 locks, and PostgreSQL 17 migration round-trip green.

Durable P4.3 facts:

- `RunAssistantService` collects bounded repository evidence and builds an OS-specific command plan.
- `gitdock.domain.run_assistant` is a pure inference/command-generation layer testable without Telegram/live GitHub.
- Command generation only: GitDock never executes shell commands.
- Fresh clone and update-existing clone are separated from setup/run suggestions.
- Targets: Windows PowerShell, Linux, macOS.
- Evidence-driven baseline detection: Python, Node.js, Docker, Gradle, Maven.
- Inference exposes confidence and evidence sources.
- Public repositories use unauthenticated read-only Contents access; installed/private repositories reuse installation read context.
- P4.3 extends read-only Contents access only; write methods retain existing permission/token requirements.
- Public-search command generation remains bound to the active opaque search session; stale sessions fail closed.
- README is untrusted evidence and its shell snippets are never copied/executed.
- Node script bodies are not copied; only safe script names may produce `npm run <name>`.
- Python entry-point/script names are constrained to safe identifiers.
- Generated command arguments use target-shell-aware quoting where applicable.
- Generated output never contains GitHub tokens, OAuth material, installation secrets, or credentials.
- Evidence collection is bounded to known candidates and bounded reads, not arbitrary repository crawling.
- UI warns that setup/run commands may execute repository-controlled hooks/build logic/scripts when the user runs them locally.

## P4 overall status ✅

P4 repository files, Git tools, and clone/setup/run command generation are delivered and post-merge verified. Do not reopen P4 unless a real regression is found.

## Active phase — P5 Webhooks & notification engine

### Active milestone: P5.1 Secure webhook ingestion

Durable design direction before implementation:

- Webhook handling belongs in the existing FastAPI ingress and existing persistence/runtime composition.
- Verify `X-Hub-Signature-256` using HMAC-SHA256 over the **exact raw HTTP body** before trusting/parsing event content.
- Missing or invalid signatures fail closed.
- GitHub delivery ID is the durable idempotency key; duplicate delivery must not create duplicate work.
- Accepted deliveries must be persisted durably before successful acknowledgement when durability is claimed.
- HTTP acknowledgement must remain fast; event normalization/notification work belongs behind ingestion.
- Persist explicit processing state so worker retries and restart recovery are possible.
- Payload size/retention/logging must be bounded; do not overlog private webhook payloads or any secret material.
- P5.1 is ingestion/durability only. Event-specific normalization is P5.2; Telegram notification UX/preferences are P5.3.

P5.1 acceptance targets:

- valid signed delivery accepted;
- forged/missing signature rejected;
- duplicate delivery idempotent;
- accepted inbox item survives restart;
- failed processing state is retryable without duplicate acceptance;
- endpoint acknowledges quickly after validation + durable acceptance;
- migration and unit/integration/contract coverage verify all above.

## Dependency reproducibility

- `requirements.txt`: exact direct runtime pins.
- `requirements-dev.txt`: exact development/test pins.
- PEP 751 runtime locks: `pylock.py312-linux.toml`, `pylock.py313-linux.toml`.
- CI regenerates and diffs locks; drift fails the build.
- Never weaken lock/audit/secret checks to obtain green CI.

## GitHub Actions operational memory

- Zero-step hosted-runner failures can be infrastructure/quota issues; inspect runner steps before calling them code failures.
- Legitimate lock drift must be fixed, never bypassed.
- CI push branches include `main`, `feat/**`, `fix/**`, `refactor/**`, and `security/**`; docs-only closeout branches use `feat/**` so CI runs.
- Do not bypass PR/branch protections to close a phase.

## Known non-blocking maintenance warnings

- FastAPI/Starlette `TestClient` deprecation toward future httpx2 integration.
- AnyIO deprecated `anyio.abc.BlockingPortal` alias through Starlette tests.
- Alembic warning because `alembic.ini` lacks explicit `path_separator` for `prepend_sys_path`.

These are maintenance debt, not hidden failures.

## GitHub write strategy

- One-file writes: durable staging + branch/file SHA protection + one scoped write + reconciliation + audit.
- Branch create: target/base preview + persisted confirmation + revalidation + scoped write + one create-ref request + reconciliation + audit.
- Repository administration: operation-specific credentials + persisted confirmation + refreshed preconditions + one write + reconciliation + audit.
- Multi-file/ZIP sync remains a future coherent batch commit, review branch by default.
- Direct default-branch mass replacement is not default.
- Never blindly replay uncertain/destructive writes.
- No normal v1 force-push UI.

## Telegram UX memory

- Telegram is a control panel, not a command console by default.
- Prefer editing current navigation message where practical.
- Use compact inline keyboards and consistent Home/Cancel/Back.
- Long paths and sensitive authority do not belong in callback data.
- Home/start invalidates transient flows where continuing would surprise the user.
- Back/Edit/Cancel after sensitive preview invalidates staged/pending authority.
- Long logs/files use pagination or document delivery.

## Safety memory

- Never expose/commit tokens, keys, client/webhook secrets, OAuth code/state, PKCE verifiers, encryption keys, or raw auth response bodies.
- Do not implement arbitrary shell execution as normal bot capability.
- Repository/README/script text is untrusted input.
- No normal v1 force-push/force-update UI.
- High-impact multi-step operations must not depend only on volatile FSM state.
- Audit GitHub writes without secret/file-body material.
- GitHub remains source of truth.
- Pagination/download helpers must not become arbitrary outbound URL fetchers.
- Stale callbacks/preconditions fail closed.
- Uncertain writes remain uncertain unless reconciliation proves final state.
- Webhook signature verification must use raw bytes and constant-time comparison via standard cryptographic primitives.
- Do not log webhook secrets or unbounded raw webhook bodies.

## Development governance memory

`AGENTS.md` is mandatory. Green tests with stale project state are not Done. Successful work updates the relevant control documentation and leaves an explicit handoff.

P4 feature work is complete. This governance closeout activates **P5.1 Secure webhook ingestion** as the next implementation item.

## Do not forget later

- Notification preferences are per repository/event type.
- Actions includes status/jobs/steps/logs/artifacts/dispatch/retry where authorized.
- ZIP sync shows added/modified/deleted/unchanged counts and requires review before write.
- Every risky action shows repository, branch/ref, target resource, and consequence.
