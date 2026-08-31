# GitDock — Current Status / Handoff

Last updated: 2026-08-31

## Project state

**Completed phases/items:**

- P0 — Planning and governance foundation ✅
- P1 — Project skeleton & quality gates ✅
- P2.1 — GitHub App authentication foundation ✅
- P2.2 — GitHub gateway foundation ✅

**Current phase:** P2 — GitHub App connection & read-only core

**Current item:** P2.3 — Home + repository read screens — active on `feat/p2-repository-read`.

## P2.2 final verification

P2.2 was squash-merged through non-draft PR #7 into `main` as commit `4bffdcc8322857aaa16e94aaafe8b5a9d52e69c2`.

Verification evidence:

- implementation-head CI `33406986504` — green;
- synchronized Draft PR #6 CI `33409265057` — green;
- replacement PR #7 CI `33409418512` — green;
- final PR #7 head `153e30cc86499918f300a74e074213affd92f319` CI `33409670775` — green;
- post-merge `main` CI `33409825480` — green.

Python 3.12 and 3.13 each passed Ruff format/lint, mypy, **49 pytest tests**, compile, `pip-audit`, `detect-secrets`, and PEP 751 lock regeneration/diff. PostgreSQL 17 migration upgrade -> downgrade -> upgrade also passed.

P2.2 durable invariants remain mandatory:

- `GitHubRestClient` is the canonical REST transport boundary;
- normal Telegram/application code does not issue raw GitHub HTTP;
- pagination targets are restricted to canonical HTTPS `api.github.com`;
- raw GitHub bodies/tokens are not exposed through gateway errors;
- GET/HEAD may retry bounded transient failures; writes do not retry by default;
- GitHub remains source of truth.

## Active P2.3 scope

Implement only the read-only home/repository experience:

- [~] GitHub connection/home state model and screen.
- [ ] accessible installed-repository list.
- [ ] pagination with stable page behavior.
- [ ] basic repository filters required by the v1 repository-list screen.
- [ ] repository dashboard metadata.
- [ ] refresh actions.
- [ ] empty/not-connected/auth/permission/not-found/rate/transient states.
- [ ] Telegram renderers/keyboards/callback handlers with thin handlers.
- [ ] tests across gateway/service/renderer/keyboard/handler boundaries.

### P2.3 boundaries

- Tier 0 read-only only.
- No repository creation/settings/admin writes.
- No file browsing; that belongs to P4.
- No GitHub public search; that belongs to P3.1.
- No Issues/PR/Actions/release deep screens; later milestones own those flows.
- Do not request write permissions.
- Repository callbacks must not embed arbitrary long `owner/name` values when compact server-resolved context is needed.
- GitHub API methods must build on the P2.2 gateway.

## Required P2.3 verification

Before P2.3 is complete:

- repository API payloads are parsed into typed read models;
- only repositories available to the bound installation are listed;
- pagination/empty/error/rate-limit states are covered;
- public/private/archived/fork/default-branch/language/stars/forks/update metadata is rendered safely where available;
- home/not-connected state does not expose secrets or internal auth material;
- owner middleware still blocks unauthorized message/callback paths;
- Ruff, mypy, full pytest, compile, `pip-audit`, `detect-secrets`, PEP 751 locks, and PostgreSQL migration CI remain green;
- project-control documentation is synchronized on the exact merge head;
- PR is merged from an unchanged green head and post-merge `main` CI is verified.

## Rules that remain in force

- GitHub App remains the primary credential model.
- A setup/install `installation_id` is untrusted until dual-context verification.
- GitHub remains source of truth.
- Telegram handlers stay thin; services own use cases; gateway owns GitHub HTTP.
- No secrets/tokens/private keys/OAuth material are committed, logged, or rendered to Telegram.
- P2.3 introduces no write/admin feature.

## Handoff instruction

Read `AGENTS.md` and the mandatory pre-flight documents. Continue only P2.3 on `feat/p2-repository-read` until its full CI/documentation/merge closeout is green. The next milestone after verified P2.3 is P3.1 — GitHub repository search.
