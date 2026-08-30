# GitDock — Project Master Plan

Status: authoritative product scope

## 1. Vision

GitDock is a professional Telegram-first control center for GitHub. Routine repository work should be possible from Telegram with clear context, safe confirmations, and traceable actions, while advanced operations still respect Git/GitHub semantics.

GitDock should feel like a compact control panel, not a command dump and not a noisy notification relay.

## 2. Primary v1 user

v1 is owner-first and single-user by default. The architecture must remain ready for future multi-user installations without rewriting core domain logic.

Unauthorized Telegram users are ignored in owner-only mode unless a future explicit onboarding mode is enabled.

## 3. Core product modules

### A. Home / account

- GitHub connection status.
- Current GitHub identity/installation.
- Number of accessible repositories.
- Notification health.
- Quick access to repositories, search, notifications, activity, and settings.

### B. Repository management

- List accessible repositories with pagination and filters.
- Show public/private, archived, fork/source, language, stars, forks, default branch, updated time.
- Create repository for authenticated user.
- Create organization repository when authorized.
- Rename repository.
- Edit description/homepage/topics where supported.
- Change visibility only behind a danger confirmation flow.
- Archive/unarchive behind confirmation.
- Delete repository only behind the strongest confirmation flow.
- Copy/open canonical GitHub URL.

### C. Repository dashboard

For a selected repository show:

- owner/name
- visibility
- default branch
- latest commit summary
- stars/forks/issues/PR counts where practical
- latest release
- latest workflow state
- last push/update

Actions:

- files
- branches
- commits
- issues
- pull requests
- Actions
- releases
- clone/run commands
- notifications
- repository settings

### D. File manager

- Browse directories.
- View UTF-8 text files with safe truncation/pagination.
- Download/open supported files when practical.
- Create text file.
- Edit/replace text file.
- Delete file with confirmation.
- Upload a replacement file.
- Choose target branch.
- Show current blob/commit context to prevent blind overwrite.
- Detect and handle stale SHA/conflict conditions.
- Editing `.github/workflows/*` requires the appropriate GitHub Workflows permission.

### E. Project/ZIP synchronization

This is a signature GitDock feature.

Flow:

1. User selects repository and target/base branch.
2. User uploads a ZIP/project bundle.
3. GitDock extracts into an isolated temporary workspace.
4. Validate archive safety: no path traversal, unexpected links, oversized extraction, secret-like files, or disallowed paths.
5. Compare against selected repository tree.
6. Summarize:
   - added
   - modified
   - deleted
   - unchanged
   - binary/large files
   - sensitive-risk files
7. Allow detailed diff browsing for text files.
8. User chooses:
   - cancel
   - create/update a review branch
   - optionally create PR
   - explicitly allow direct target-branch update only when policy permits
9. Apply the batch atomically where practical using Git data/tree/commit operations, not dozens of unrelated visible commits.
10. Report resulting commit/PR.

Default policy: review branch + single commit. Direct mass update to default branch is not the default.

### F. Git/branch/commit tools

- List/search branches.
- Create branch from known base.
- Show recent commits.
- Show commit details/diff summary.
- Compare two refs.
- Generate clone/pull commands.
- No force operations in normal v1 UI.

### G. Clone/setup/run command assistant

GitDock does not silently execute commands on the user's device. It generates copyable commands.

Detect project hints from repository files, for example:

- `pyproject.toml`
- `requirements.txt`
- `package.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `Dockerfile`
- `docker-compose.yml`
- Gradle files
- Maven files
- README run instructions

Provide tabs/options for Windows PowerShell, Linux shell, and macOS shell.

Always separate:

- clone fresh
- update existing clone
- dependency setup
- run command

Never invent a run command with high confidence when repository evidence is insufficient; label inferred commands and show source files used for inference.

### H. GitHub search/discovery

Search public repositories and show:

- name/owner
- description
- stars
- forks
- language
- license when available
- archived state
- updated/pushed time
- topics when useful

Filters/sorts:

- most stars
- most forks
- recently updated
- language
- minimum stars
- owner/org
- topic
- archived/non-archived

Actions from a result:

- details
- open GitHub
- clone commands
- star/unstar if user authorization supports it
- fork where supported/allowed
- save/follow in GitDock

### I. Issues and pull requests

Issues:

- list/search/filter
- view issue + comments
- create issue
- comment
- close/reopen
- labels/assignees when permissions allow

Pull requests:

- list/filter
- details
- changed files/diff
- conversation/comments
- review status
- comment/reply
- approve/request changes where allowed
- merge only behind confirmation and policy checks
- show CI/check state before merge

### J. GitHub Actions

- list workflows
- show recent workflow runs
- show run/job/step status
- show job logs with safe truncation
- show/download artifacts where supported
- manually dispatch workflows that declare `workflow_dispatch`
- re-run failed jobs/runs
- cancel run when supported in implementation phase

Workflow dispatch must show selected ref and declared inputs before confirmation.

### K. Releases

- list releases/tags
- latest release details
- release assets metadata
- notifications for new releases
- release creation is a later milestone unless explicitly prioritized

### L. Notifications / webhooks

GitHub -> Telegram notifications should be event-driven using GitHub App webhooks.

Initial event families:

- push
- issues
- issue_comment
- pull_request
- pull_request_review
- pull_request_review_comment
- workflow_run
- release
- star
- fork
- create/delete ref where useful
- installation / installation_repositories for account state

Per-repository preferences:

- immediate on/off
- event-type toggles
- quiet mode/digest later
- mute repository

Every delivery is verified, persisted/deduplicated, transformed to a canonical event model, then rendered to Telegram.

### M. Activity/audit

Store a GitDock-side audit record for user-triggered write operations:

- who requested it
- repository
- operation
- target ref/path/issue/PR/workflow
- GitHub result identifier
- timestamp
- success/failure

Never store secret values in audit payloads.

## 4. UX principles

- Arabic-first user copy.
- Concise, information-dense messages.
- Edit the current navigation message when practical.
- Avoid repeated walls of text.
- Two primary buttons per row maximum by default.
- Consistent navigation row.
- Clear status icons: success, warning, failure, running, private/public.
- Loading state for operations that may take noticeable time.
- Empty states explain the next useful action.
- Errors explain what failed and what the user can do next without leaking internals.
- Destructive actions have visually isolated buttons and confirmation screens.

See `docs/UI_UX_SPEC.md` for exact screens and button contracts.

## 5. Authentication strategy

Use a GitHub App rather than a broad permanent PAT.

Two GitHub auth contexts are expected:

1. Installation access token (IAT)
   - repository-scoped operations on repositories granted to the app
   - expires and is refreshed by the service
2. User access token (UAT)
   - user-context operations that require the authenticated user, including creating a repository for the authenticated user and user-level interactions such as starring where required

GitDock must request the minimum permissions necessary. High-power permissions are staged and explained.

## 6. Safety tiers

### Tier 0 — Read-only

Search, list, view files, commits, issues, PRs, workflow state, releases.

### Tier 1 — Reversible write

Create issue/comment, create branch, edit file on non-default branch, trigger workflow.

Requires normal confirmation where context is clear.

### Tier 2 — High-impact

Direct default-branch changes, merge PR, mass ZIP sync, repository rename/archive, visibility change.

Requires dedicated confirmation screen.

### Tier 3 — Destructive

Repository deletion, transfer, force ref movement, destructive mass deletion.

Repository deletion requires typing the exact `owner/repo` name plus final confirmation. Force ref movement is excluded from normal v1 UI.

## 7. Data model domains

Expected durable entities:

- users
- telegram_accounts
- github_accounts
- github_installations
- repositories_cache
- repository_preferences
- notification_preferences
- webhook_deliveries
- event_inbox
- audit_log
- pending_confirmations
- saved_searches (later)
- operation_sessions / upload_sync_sessions

The GitHub source of truth remains GitHub. Local repository metadata is cache/preferences, not an authoritative duplicate.

## 8. Reliability requirements

- Webhook endpoint returns quickly after signature validation + durable enqueue/persist.
- Duplicate GitHub delivery IDs are idempotently ignored.
- Retry transient GitHub API failures with bounded exponential backoff and jitter.
- Respect GitHub rate limits and expose a friendly message when constrained.
- Persist operation state needed to recover after process restart.
- Never rely on in-memory FSM alone for high-impact multi-step operations.
- File/ZIP temporary workspaces are isolated and cleaned after completion/expiry.

## 9. Observability

- Structured logs.
- Correlation IDs for Telegram update / webhook delivery / GitHub operation.
- No secret/token values in logs.
- Health endpoint.
- Readiness checks for DB and core configuration.
- Counters/timing can be added later without redesigning the core.

## 10. Out of scope for initial implementation

Unless explicitly reprioritized:

- arbitrary shell execution on the server from Telegram
- arbitrary command execution on the user's laptop
- force-push controls
- full GitHub organization administration
- secret/Actions-secret viewing or exfiltration
- replacing GitHub's full code-review UI
- IDE-level code editing
- AI code generation as a core dependency

## 11. Success criteria for v1

v1 is successful when an owner can:

1. connect GitHub safely via GitHub App;
2. browse and search repositories;
3. create/manage a repository safely;
4. inspect and update repository files;
5. generate clone/update/run guidance;
6. inspect Issues/PRs and perform common interactions;
7. inspect/trigger/retry GitHub Actions;
8. receive reliable webhook notifications;
9. perform a safe reviewed ZIP/project sync;
10. recover from restarts without losing critical operation state;
11. understand every risky action before it happens.

## 12. Quality bar

GitDock is not accepted as production-ready based only on happy-path manual testing. Each milestone must meet the test matrix, security model, UX states, migration requirements, and documentation update protocol.