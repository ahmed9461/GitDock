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

**Current phase:** P3 — Search & repository administration

**Current implementation item:** **P3.2 — user-context authorization/disconnect support**.

P3.2 implementation is complete and **pre-merge verified** on branch `feat/p3-2-user-authorization`. It is not yet marked fully phase-complete because PR merge, post-merge `main` CI, and governance closeout are still required.

## P3.2 pre-merge verification

Current implementation head before this documentation synchronization:

- commit: `5068b58ec41fb5ac417408d3a535bbb5d66207fc`;
- branch CI: `33515291600` — fully green;
- Python 3.12: Ruff format/lint, mypy, **97 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock verification all passed;
- Python 3.13: the same configured quality/security/lock gates passed;
- PostgreSQL 17: Alembic upgrade -> downgrade -> upgrade passed including migration `0004_user_auth`;
- `pip-audit`: no known runtime vulnerabilities;
- no secret-scan finding;
- no PEP 751 runtime-lock drift.

The suite still reports the known non-blocking maintenance warnings:

- Starlette/FastAPI `TestClient` deprecation warning for the current `httpx` integration/future `httpx2` direction;
- Alembic warning because `alembic.ini` does not explicitly set `path_separator` for `prepend_sys_path`.

## P3.2 implemented behavior

### Durable GitHub user authorization

- GitHub user identity is established through authenticated `GET /user` rather than inferred from Telegram or installation metadata.
- Standalone user authorization reuses the P2.1 restart-safe one-time OAuth state and PKCE S256 flow; it does not require reinstalling the GitHub App.
- Successful OAuth completion persists the GitHub user account plus encrypted access/refresh credentials only for the durable user-context capability.
- Access-token and refresh-token expiry metadata remain separate from ciphertext.
- Existing versioned credential encryption/key-rotation support is reused; no second auth or crypto stack was introduced.

### Expiry-aware rotating refresh

- When the durable user access token is still safely valid, it is reused.
- Near-expiry access credentials refresh with the stored refresh token.
- GitHub's rotated access/refresh pair is persisted atomically only if the account `credential_generation` still matches the generation observed before the network request.
- Reauthorization/disconnect concurrent with refresh therefore fails closed instead of letting an older refresh overwrite newer credential state.
- `credential_generation` advances when credentials are persisted or cleared.

### Durable local disconnect confirmation

- P3.2 introduces general DB-backed `pending_confirmations` for restart-safe one-time sensitive confirmations.
- Confirmation tokens are opaque, short-lived, user/operation-bound, and single-use.
- GitHub local-disconnect confirmation fingerprints the active GitHub account identity, credential generation, and current installation IDs.
- A stale confirmation after reauthorization or installation-set change does not delete anything.
- Reused or cancelled confirmations do not execute.
- Returning Home invalidates pending GitHub disconnect confirmations so an old message button cannot remain an active destructive authorization.
- Legacy P2.3 state with a local installation binding but no durable user access token can still be disconnected safely.

### Exact disconnect scope

`🔌 قطع الربط المحلي` removes GitDock-local authorization/binding state only:

- encrypted GitHub user credentials are cleared;
- local installation bindings are removed;
- local `repositories_cache` rows are removed;
- unconsumed local OAuth/confirmation state is invalidated.

It **does not uninstall the GitHub App from GitHub and does not claim to revoke the installation remotely**. The confirmation screen states this explicitly.

### Telegram UI

- Connected Home exposes `👤 حساب GitHub`.
- Account screen shows durable user-authorization state separately from installation count.
- User can activate/re-authorize durable user context without reinstalling the App.
- Refresh is available for an authorized account.
- Local disconnect is isolated from harmless navigation and requires explicit persisted confirmation.
- Callback payloads remain compact and validated within Telegram's 64-byte callback-data limit.
- Telegram handlers remain thin; OAuth, refresh, encryption, persistence, and confirmation rules stay in services/auth boundaries.

## P3.2 non-goals

P3.2 does **not** implement:

- repository creation;
- repository rename/settings changes;
- archive/unarchive;
- visibility change;
- repository deletion;
- new broad GitHub App permissions;
- remote GitHub App uninstall/revoke behavior.

Those repository administration flows remain P3.3 and must reuse the P3.2 user-context service plus the existing capability/permission model.

## Durable invariants

- GitHub remains source of truth.
- GitHub App remains the primary credential model; no broad permanent PAT is introduced.
- Installation binding and durable user OAuth credentials remain distinct concepts.
- Raw setup/install `installation_id` remains untrusted until dual App/user-context verification.
- OAuth state remains high-entropy, short-lived, user/flow-bound, restart-safe, one-time use, and persisted only as a digest.
- PKCE verifier and durable GitHub user credentials remain encrypted with versioned keys.
- No access/refresh token, OAuth code/state, PKCE verifier, private key, or raw upstream auth body may enter Telegram copy, callback payloads, repository cache, or normal logs.
- P3.1 public search remains independent of a GitHub installation/user authorization and must not regress.
- A Telegram button is transport only; sensitive execution depends on persisted server-side confirmation state and current preconditions.

## Exact next steps

1. Commit this synchronized P3.2 documentation on `feat/p3-2-user-authorization`.
2. Require final-head branch CI to pass on the documentation-synchronized head.
3. Open a non-draft P3.2 PR.
4. Require PR CI green and `mergeable=true` on the unchanged head.
5. Squash-merge using the exact expected head SHA.
6. Require post-merge `main` CI green.
7. Record PR/merge/main verification in the normal small governance closeout and verify that closeout on `main`.
8. Only then mark P3.2 fully verified complete and move the active implementation item to **P3.3 — repository create/settings**.

Do not start P3.3 on this branch or falsely record merge/main results before they occur.
