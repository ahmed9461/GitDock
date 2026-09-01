# GitDock — Current Status / Handoff

Last updated: 2026-09-01

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅
- P2.3 — Home + repository read screens ✅
- P3.1 — GitHub repository search ✅

**Current phase:** P3 — Search & repository administration

**Current implementation item:** **P3.2 — user-context authorization/disconnect support — Active** on `feat/p3-2-user-authorization`.

## P3.1 final closeout

P3.1 feature delivery and governance are fully closed.

Verification chain:

- implementation head `4a4f00d50e886ab494e2a83f2c649cd64b7398b2` — CI `33453960817` green;
- final documentation-synchronized feature head `14e149ea307871abd8406ffc6212fe062ead9098` — branch CI `33454438202` green;
- non-draft PR #10 — PR CI `33454524953` green and `mergeable=true` on the unchanged head;
- PR #10 squash merge commit `d822338fcc1546418ed2100cc9534cdc71a6bcbe`;
- post-feature-merge `main` CI `33454619065` — green;
- governance closeout PR #11 — PR CI `33454883148` green and mergeable on unchanged head;
- closeout squash merge commit `ef2c5f618102063df8166f84b4828243f5efb5c6`;
- post-closeout `main` CI `33454972020` — green on Python 3.12, Python 3.13, and PostgreSQL 17.

The verified P3.1 suite contains **83 tests** and passes Ruff format/lint, mypy, compile, `pip-audit`, `detect-secrets`, PEP 751 lock verification, and the PostgreSQL migration round trip.

## P3.2 scope

P3.2 must complete the end-user GitHub user-context lifecycle needed by later user-scoped features without duplicating or weakening the P2.1 authentication foundation.

Target capabilities:

- surface the current user-authorization state through the application/service boundary;
- reuse existing one-time OAuth state, PKCE S256, encrypted credential storage, and token metadata;
- complete durable refresh behavior where the current foundation already preserves refresh metadata;
- provide a deliberate disconnect flow that removes local GitDock user credentials/binding state safely;
- keep installation binding semantics separate from user credential semantics;
- make disconnect/reconnect idempotent and safe under stale Telegram callbacks;
- never expose access/refresh tokens, OAuth code/state, PKCE verifier, private keys, or raw upstream auth bodies;
- preserve owner-only Telegram ingress and least-privilege GitHub App behavior.

P3.2 does **not** include repository create/settings/delete; those remain P3.3.

## Pre-implementation requirements for P3.2

Before adding code, inspect the existing P2.1 implementation and tests for:

- OAuth state lifecycle and PKCE storage;
- credential encryption/store abstractions;
- access/refresh expiry metadata;
- installation binding and disconnect-related persistence boundaries;
- runtime service composition;
- current Telegram connection UI and callback paths;
- capability mapping for user-context operations.

Prefer extending these boundaries rather than creating a second auth stack.

## Durable invariants

- GitHub remains source of truth.
- GitHub App is the primary credential model; do not introduce a broad long-lived PAT.
- Raw setup/install `installation_id` remains untrusted until dual app/user-context identity verification.
- OAuth state remains high-entropy, short-lived, user/flow-bound, restart-safe, one-time use, and stored only as a digest.
- PKCE verifier and persisted GitHub user credentials remain encrypted with versioned keys.
- Installation tokens remain short-lived and repository/permission scoped where possible.
- Installation binding and user OAuth credential state are distinct concepts; disconnect behavior must say exactly which state it removes.
- Telegram handlers stay thin and never implement OAuth/token mechanics directly.
- No auth material may enter normal logs, callbacks, repository caches, or user-facing error bodies.
- P3.1 public search remains usable independently of a linked installation/user authorization and must not regress.

## Known non-blocking maintenance warnings

The verified suite still reports the two recorded deprecation warnings:

- Starlette/FastAPI `TestClient` warning about the current `httpx` integration/future `httpx2` direction;
- Alembic warning because `alembic.ini` does not yet set explicit `path_separator` for `prepend_sys_path`.

They are maintenance debt, not hidden test failures.

## Handoff instruction

Continue only P3.2 on `feat/p3-2-user-authorization`. First reuse and extend the P2.1 secure auth foundation; do not duplicate OAuth/PKCE/encryption code. Keep P3.3 repository administration out of this branch. Before calling P3.2 complete, require synchronized governance docs, final-head CI, non-draft PR, unchanged-head merge, post-merge `main` CI, and governance closeout.
