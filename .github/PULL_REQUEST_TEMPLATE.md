# GitDock Pull Request

## Scope

Describe the single coherent outcome of this PR.

## Roadmap / status

- Roadmap item: `P?.?`
- Risk tier: `0 / 1 / 2 / 3`

## What changed

- 

## Verification

List exact checks run and their results.

```text
<commands/results>
```

## Required checklist

### Correctness

- [ ] Acceptance criteria for the roadmap/task are satisfied.
- [ ] Relevant unit tests pass.
- [ ] Relevant integration/contract tests pass.
- [ ] Error/empty/loading/permission states are handled where applicable.
- [ ] No known regression is hidden or deferred without being recorded.

### Architecture

- [ ] Telegram handlers remain thin.
- [ ] GitHub API details stay behind the GitHub gateway/client layer.
- [ ] Domain/business rules are not duplicated in UI handlers.
- [ ] Database changes include an Alembic migration and migration tests.
- [ ] Constants/config/callback names are centralized rather than scattered.

### Security

- [ ] No secrets/tokens/private keys are committed or logged.
- [ ] GitHub permission requirements are the minimum needed and centrally mapped.
- [ ] GitHub webhook/signature logic remains fail-closed if touched.
- [ ] Tier 2/3 operations use persisted, expiring, single-use confirmation.
- [ ] Stale SHA/ref/resource state is handled for relevant writes.
- [ ] Audit records exist for user-triggered GitHub writes.
- [ ] Archive/path safety tests pass if upload/sync code changed.

### Telegram UX

- [ ] UI follows `docs/UI_UX_SPEC.md`.
- [ ] Arabic user copy is clear and consistent.
- [ ] Navigation uses Home/Cancel/Back consistently.
- [ ] Destructive action buttons are isolated.
- [ ] Callback payloads use versioned short IDs/context and stay compact.

### Project memory / handoff

- [ ] `docs/CURRENT_STATUS.md` updated.
- [ ] `docs/ROADMAP.md` updated accurately.
- [ ] `CHANGELOG.md` updated under `Unreleased`.
- [ ] `docs/PROJECT_MEMORY.md` updated if durable knowledge changed.
- [ ] `docs/DECISIONS.md` updated if a meaningful decision changed.
- [ ] Architecture/UX/security/constants/test docs updated if their truth changed.
- [ ] The exact next task/handoff point is explicit.

## Notes / known limitations

- 
