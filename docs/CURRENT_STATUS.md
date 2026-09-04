# GitDock — Current Status / Handoff

Last updated: 2026-09-04

## Project state

**Verified complete:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅
- P2.3 — Home + repository read screens ✅
- P3.1 — GitHub repository search ✅
- P3.2 — durable GitHub user-context authorization/disconnect ✅

**Current phase:** P3 — Search & repository administration

**Current implementation item:** **P3.3 — repository create/settings — implementation verified; merge/governance closeout pending**.

P3.3 must not be promoted to the verified-complete list until the documentation-synchronized feature head is green, the non-draft PR is green on an unchanged head, the feature is merged, post-merge `main` CI is green, and the normal governance closeout is completed.

## P3.3 implementation verification

Implementation head before documentation synchronization:

- commit: `4e71d7f1c962e61584d6532d03c913703dc5295a`;
- branch CI: `33890407945` — green;
- Python 3.12 and Python 3.13 both passed Ruff format, Ruff lint, mypy, pytest, compile, `pip-audit`, `detect-secrets`, and PEP 751 runtime-lock regeneration/diff;
- pytest collected **117 tests** and all 117 passed;
- mypy reported no issues in 72 source files;
- `pip-audit` reported no known runtime vulnerabilities;
- no secret-scan findings;
- no PEP 751 runtime-lock drift;
- PostgreSQL 17 passed Alembic upgrade -> downgrade -> upgrade including migration `0005_audit_log`.

Known non-blocking warnings remain visible rather than suppressed:

- Starlette/FastAPI `TestClient` deprecation toward `httpx2`;
- AnyIO `BlockingPortal` alias deprecation surfaced through Starlette tests;
- Alembic `prepend_sys_path` warning because `alembic.ini` does not yet set `path_separator` explicitly.

## P3.3 delivered behavior

### Repository creation

- Personal repository creation uses durable GitHub user OAuth context rather than an installation token.
- Organization repository creation is supported when the caller explicitly supplies an organization and the current durable user authorization can perform the request.
- Create uses a server-side persisted Tier 1 confirmation before the GitHub write.
- Telegram exposes an Arabic creation wizard for repository name, optional description, visibility, preview, confirm, edit, and cancel.

### Repository settings

Supported update fields in the current P3.3 scope:

- repository name;
- description;
- public/private visibility;
- archive/unarchive;
- default branch.

Update/delete repository selection is resolved from current GitHub-backed repository context. The service re-fetches current repository state before sensitive execution and fails closed on stale preconditions.

Repository update/delete writes use a repository-scoped installation token requesting `administration: write` for the selected GitHub repository only.

### Risk and confirmation model

- create: Tier 1 persisted confirmation;
- repository update: Tier 2 persisted confirmation;
- repository delete: Tier 3 persisted confirmation plus exact typed `owner/name` match;
- confirmation tokens are opaque, short-lived, user/operation-bound, single-use, and server-side authoritative;
- Telegram callbacks carry only compact transport data; a Telegram button is never sufficient authority by itself;
- confirmation cancellation is persisted and one-time: cancel/edit/back consumes the pending confirmation so an old Telegram button cannot execute later;
- stale, expired, reused, cancelled, wrong-target, and wrong-name paths fail closed.

### Uncertain write reconciliation

GitDock does not blindly retry repository administration writes whose outcome may be uncertain.

- create reconciles against current remote state before deciding the final result;
- update reconciles the refreshed repository state against the requested mutation;
- delete reconciles by checking whether the target repository still exists;
- a reconciled-applied write is represented separately from an ordinary direct success;
- an outcome that remains genuinely uncertain is surfaced as uncertain rather than falsely recorded as success or failure.

### Audit and persistence

- migration `0005_audit_log` introduces durable repository-administration audit records;
- create/update/delete success, failure, reconciliation outcome, user/repository context, and safe request metadata are auditable;
- credentials/tokens are not written to audit details;
- successful update refreshes repository cache state;
- successful/reconciled delete removes the deleted repository from local cache.

### Telegram UI

- connected Home exposes repository creation;
- repository detail exposes repository settings;
- repository administration has centralized renderers, keyboards, callbacks, and FSM states;
- callbacks use compact repository IDs/tokens and remain within Telegram callback-data limits;
- delete is visually isolated and requires exact-name typed confirmation;
- update/create previews do not execute a write by themselves;
- stale/expired confirmation callbacks fail closed;
- Back/Cancel/Home behavior is explicit and destructive confirmations are invalidated rather than merely hidden.

## P3.3 verified test coverage

The 117-test suite includes P3.3 coverage for:

- canonical personal create, organization create, update, and delete gateway endpoints;
- no blind write retry behavior;
- personal creation user-context authorization;
- repository-scoped administration installation tokens for update/delete;
- create/update/delete single-use confirmation behavior;
- stale repository snapshot rejection;
- delete exact-name requirement;
- delete expired confirmation;
- delete reused confirmation;
- delete wrong-name rejection;
- delete permission failure;
- organization creation path;
- uncertain create/update/delete reconciliation;
- audit behavior;
- confirmation cancellation one-time semantics;
- Telegram callback parsing/size, keyboards, renderers, and repository administration UI behavior.

## Durable invariants

- GitHub remains source of truth.
- GitHub App remains the primary credential model; do not introduce a broad permanent PAT.
- Installation binding and durable user OAuth credential state remain separate concepts.
- Raw setup/install `installation_id` remains untrusted until dual App/user-context verification.
- OAuth state remains high-entropy, short-lived, user/flow-bound, restart-safe, one-time use, and persisted only as a digest.
- PKCE verifier and durable GitHub user credentials remain encrypted with versioned keys.
- No access/refresh token, OAuth code/state, PKCE verifier, private key, installation token, or raw upstream auth body may enter Telegram copy, callback payloads, repository cache, audit details, or normal logs.
- P3.1 public search remains independent of installation/user authorization and must not regress.
- Sensitive execution depends on persisted server-side confirmation state and current preconditions; Telegram buttons are transport only.
- Do not blindly retry uncertain/destructive GitHub writes; reconcile remote state first.
- Repository delete remains Tier 3 and requires exact repository-name entry.

## Previous verified phase

P3.2 was fully merged and post-merge verified before P3.3 began. Its final feature merge was `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`; its verified suite contained 97 tests and established durable user authorization, encrypted rotating credentials, `credential_generation`, and DB-backed `pending_confirmations` that P3.3 now reuses.

## Exact next task — finish P3.3 governance chain

1. synchronize `ROADMAP.md`, `CHANGELOG.md`, and truth-bearing architecture/security/UI/test documentation with the verified implementation;
2. run CI on the documentation-synchronized feature head and require all Python 3.12/3.13/PostgreSQL gates green;
3. open a non-draft P3.3 PR to `main`;
4. require PR CI green on the unchanged feature head and confirm mergeability;
5. squash-merge with expected-head protection;
6. require post-feature-merge `main` CI green;
7. perform the normal governance closeout so repository control docs point to P4.1 as the next implementation item.

Do not call P3.3 ✅ before that chain is complete.
