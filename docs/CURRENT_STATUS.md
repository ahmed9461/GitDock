# GitDock — Current Status / Handoff

Last updated: 2026-09-01

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

**Current implementation item:** **P3.3 — repository create/settings**.

P3.2 feature delivery is merged and post-merge verified. This closeout branch records the final immutable delivery facts before P3.3 starts.

## P3.2 final verification chain

- complete implementation head before documentation synchronization: `5068b58ec41fb5ac417408d3a535bbb5d66207fc` — branch CI `33515291600` green;
- final documentation-synchronized feature head: `492183bfba311827a965153eff61747bfabf76ed` — branch CI `33517270731` green;
- non-draft PR #12 — PR CI `33527318485` green and `mergeable=true` on unchanged head `492183bfba311827a965153eff61747bfabf76ed`;
- PR #12 squash merge commit: `8a5d692dd875b8959b27b1b0c53bbc5b5359c7f8`;
- post-feature-merge `main` CI `33527484948` — green on Python 3.12, Python 3.13, and PostgreSQL 17.

The verified P3.2 suite contains **97 tests**. Both Python jobs pass Ruff format/lint, mypy, pytest, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff. PostgreSQL 17 passes Alembic upgrade -> downgrade -> upgrade including migration `0004_user_auth`. `pip-audit` reports no known runtime vulnerabilities; there are no secret-scan findings and no runtime-lock drift.

## P3.2 delivered behavior

### Durable GitHub user authorization

- GitHub user identity is established through authenticated `GET /user` rather than inferred from Telegram or installation metadata.
- Standalone durable user authorization reuses the P2.1 restart-safe one-time OAuth state and PKCE S256 flow; it does not require reinstalling the GitHub App.
- Successful OAuth completion persists the GitHub user account plus encrypted access/refresh credentials only for durable user-context use cases.
- Access-token and refresh-token expiry metadata remain separate from ciphertext.
- Existing versioned credential encryption/key-rotation support is reused; no second auth or crypto stack was introduced.

### Expiry-aware rotating refresh

- Safely valid durable user access tokens are reused.
- Near-expiry access credentials refresh through the stored refresh token.
- GitHub's rotated access/refresh pair is persisted only if the current account still matches the `credential_generation` observed before network I/O.
- Reauthorization/disconnect concurrent with refresh therefore fails closed instead of allowing stale refresh work to overwrite newer authorization state.
- Persisting or clearing credentials advances `credential_generation`.

### Durable local disconnect confirmation

- P3.2 introduces DB-backed `pending_confirmations` for restart-safe one-time sensitive confirmations.
- Confirmation tokens are opaque, short-lived, user/operation-bound, single-use, and represented server-side by a digest rather than secret callback material.
- GitHub local-disconnect confirmation fingerprints active account identity, credential generation, and current installation IDs.
- Reauthorization or installation-set change makes an older confirmation stale; stale/expired/reused/cancelled confirmation removes nothing.
- Returning Home invalidates pending GitHub disconnect confirmations so old Telegram message buttons cannot remain active destructive authority.
- Legacy P2.3 installation-only state can also be disconnected safely.

### Exact disconnect scope

`🔌 قطع الربط المحلي` removes **GitDock-local** authorization/binding state only:

- encrypted GitHub user credentials are cleared;
- local installation bindings are removed;
- local `repositories_cache` rows are removed;
- relevant unconsumed local OAuth/confirmation state is invalidated.

It **does not uninstall or revoke the GitHub App on GitHub**. User-facing confirmation copy must preserve this distinction.

### Telegram UI

- Connected Home exposes `👤 حساب GitHub`.
- Account screen separates durable user authorization from installation count.
- User can activate/re-authorize durable user context without reinstalling the App.
- Refresh is available for authorized user context.
- Local disconnect is isolated from harmless navigation and requires persisted confirmation.
- Callback payloads remain compact and within Telegram's 64-byte limit.
- Telegram handlers remain thin; OAuth, refresh, encryption, persistence, and confirmation rules stay in services/auth boundaries.

## P3.2 non-goals

P3.2 intentionally does **not** implement repository creation, rename/settings, archive/unarchive, visibility change, repository deletion, broad new GitHub App permissions, or remote GitHub App uninstall/revoke behavior.

Those repository administration flows are P3.3 and must reuse the verified P3.2 user-context lifecycle plus the existing central capability/permission model.

## Durable invariants

- GitHub remains source of truth.
- GitHub App remains the primary credential model; do not introduce a broad permanent PAT.
- Installation binding and durable user OAuth credential state are separate concepts.
- Raw setup/install `installation_id` remains untrusted until dual App/user-context verification.
- OAuth state remains high-entropy, short-lived, user/flow-bound, restart-safe, one-time use, and persisted only as a digest.
- PKCE verifier and durable GitHub user credentials remain encrypted with versioned keys.
- No access/refresh token, OAuth code/state, PKCE verifier, private key, or raw upstream auth body may enter Telegram copy, callback payloads, repository cache, or normal logs.
- P3.1 public search remains independent of installation/user authorization and must not regress.
- Sensitive execution depends on persisted server-side confirmation state and current preconditions; Telegram buttons are transport only.
- Do not blindly retry uncertain/destructive GitHub writes; reconcile remote state first.

## Known non-blocking maintenance warnings

The verified P3.2 suite still reports:

- Starlette/FastAPI `TestClient` deprecation warning for the current `httpx` integration/future `httpx2` direction;
- Alembic warning because `alembic.ini` does not explicitly set `path_separator` for `prepend_sys_path`.

They are recorded maintenance debt, not hidden test failures.

## Exact next task — P3.3

Implement repository create/settings administration on a new feature branch from the post-closeout `main` head.

P3.3 scope remains:

1. create personal repository;
2. optional organization repository creation where genuinely authorized;
3. edit supported repository name/description/settings;
4. archive/unarchive;
5. visibility-change Tier 2 confirmation;
6. delete Tier 3 exact-name confirmation;
7. audit every GitHub write;
8. use correct user/install token context and central capability/permission mapping;
9. never execute dangerous settings from one tap;
10. reconcile uncertain write outcomes before claiming success/failure.

Before calling P3.3 complete, require synchronized control docs, green final-head CI, non-draft PR, unchanged-head merge, post-merge `main` CI, and the normal governance closeout.
