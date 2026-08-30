# GitDock — Decision Log

Purpose: preserve why important choices were made so later sessions do not reverse them accidentally.

Format:

- **Status:** Accepted / Superseded / Proposed
- **Context**
- **Decision**
- **Consequences**

---

## D-001 — Product name is GitDock

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** The project needs a stable identity before code and bot copy are built.

**Decision:** Product name is `GitDock`; canonical slug/prefix is `gitdock` / `gd` where compact identifiers are required.

**Consequences:** Rename only through an explicit cross-project decision because callbacks/config/docs/branding may depend on it.

---

## D-002 — Telegram-first product, Arabic-first UI

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** GitDock is intended to make GitHub management practical from Telegram rather than recreate GitHub as a web application.

**Decision:** Telegram is the primary UI. v1 user-facing copy is Arabic. GitHub names, refs, paths, commands, and code remain in their native technical form.

**Consequences:** UI workflows are designed around compact messages, inline keyboards, pagination, and message editing.

---

## D-003 — GitHub App is the primary credential model

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Broad long-lived PATs create unnecessary blast radius and poor permission transparency.

**Decision:** Use a GitHub App with least-privilege permissions. Use installation tokens for installation/repository operations and user access tokens only where user-context operations require them.

**Consequences:** GitHub App setup, token provider, permission mapping, OAuth/setup callbacks, and encrypted token storage are first-class architecture components.

References:

- https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation

---

## D-004 — Python async stack

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** The application is event-driven and needs Telegram, HTTP webhook ingress, GitHub API calls, and database I/O.

**Decision:** Baseline stack is Python 3.12+, aiogram 3.x, FastAPI, httpx, async SQLAlchemy 2.x, and Alembic. Exact dependency versions are selected/pinned during P1 using current maintained releases.

**Consequences:** Do not freeze guessed library versions in planning docs. Keep network/database paths async.

---

## D-005 — PostgreSQL production, SQLite development only

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Durable webhook inbox, confirmations, OAuth state, audit records, and future multi-user concurrency need production-grade persistence.

**Decision:** PostgreSQL is the production database. SQLite may be used for local tests/development only where behavior remains portable.

**Consequences:** Schema/query design must not rely on SQLite-specific behavior. Alembic migrations are mandatory.

---

## D-006 — Durable DB-backed webhook/event processing

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** An in-memory asyncio queue can lose accepted GitHub webhook events during process restart.

**Decision:** After signature verification, persist webhook delivery/work state before background processing. Use GitHub delivery ID for idempotency.

**Consequences:** Initial deployment does not require Redis/Celery merely to be reliable. Worker boundaries remain separable so another queue can be introduced later if scale requires it.

---

## D-007 — Multi-file/ZIP updates are reviewable batch changes

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Replacing many files individually creates noisy history and dangerous partial-state failure modes.

**Decision:** ZIP/project synchronization creates a diff plan, reviews it, then applies a coherent batch commit on a review branch by default; optional PR follows. Direct default-branch mass update is an explicit Tier 2 exception.

**Consequences:** Sync engine needs base commit snapshots, Git tree/commit support, stale-base detection, and persistent operation sessions.

---

## D-008 — No arbitrary remote shell execution in v1

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** The user wants GitDock to provide commands for cloning/updating/running projects. Turning that into arbitrary server/device execution would dramatically increase risk and scope.

**Decision:** GitDock generates copyable OS-specific commands based on repository evidence. It does not silently execute repository commands on the user's device or expose a generic remote shell.

**Consequences:** Project run detection uses trusted templates and labels uncertainty. Arbitrary README commands remain untrusted text.

---

## D-009 — Risk-tiered confirmation model

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Telegram buttons make powerful GitHub actions convenient, which also makes accidental destructive actions easier.

**Decision:** Operations are classified from Tier 0 read to Tier 3 destructive. Tier 2/3 use persisted one-time confirmations; repository deletion additionally requires exact repository-name entry.

**Consequences:** Confirmation service is a domain/security component rather than ad hoc per-handler code.

---

## D-010 — Thin Telegram handlers and centralized GitHub gateway

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Direct GitHub calls from button handlers would make behavior difficult to test, audit, and refactor.

**Decision:** Telegram handlers collect/render input only. Application services perform use cases. All GitHub HTTP details live behind a GitHub gateway/client layer.

**Consequences:** Tests can mock GitHub at the gateway boundary; permission/error/retry behavior remains consistent.

---

## D-011 — Project state documentation is part of Definition of Done

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Long-running agent-assisted projects can lose architectural intent and current progress across sessions even when code commits exist.

**Decision:** `CURRENT_STATUS`, `PROJECT_MEMORY`, `ROADMAP`, `CHANGELOG`, and affected specs must be updated after successful implementation as required by `AGENTS.md` and `BUILD_PROTOCOL.md`.

**Consequences:** A feature with green tests but stale project control files is not Done.

---

## D-012 — Owner-only v1, multi-user-ready core

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Initial use does not need a full SaaS account/role model, but tightly coupling all services to one hardcoded user would make later expansion expensive.

**Decision:** v1 enforces one configured Telegram owner at the ingress/middleware boundary while persistence/service interfaces retain explicit user/account ownership.

**Consequences:** Unauthorized users are blocked early; future multi-user authorization can replace the boundary policy without rewriting core GitHub services.

---

## D-013 — GitHub remains source of truth

**Date:** 2026-08-31  
**Status:** Accepted

**Context:** Mirroring repository/issue/PR state deeply into a local database increases synchronization complexity.

**Decision:** GitHub is authoritative for GitHub resources. GitDock stores identity bindings, preferences, audit, operation state, webhook processing state, and minimal cache metadata only.

**Consequences:** Refresh critical state before writes; local cached repository metadata must never override GitHub truth.

---

## Adding future decisions

Never rewrite history to make an old decision disappear. Add a new decision with `Supersedes D-xxx`, then mark the older decision Superseded.