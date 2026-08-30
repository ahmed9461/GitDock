# Changelog

All meaningful changes to GitDock are recorded here.

The project follows an `Unreleased` section during active development. Versioning/release policy will be finalized before the first tagged release.

## Unreleased

### Added

- Initial GitDock product definition and repository governance.
- Root `AGENTS.md` with mandatory pre-flight, Definition of Done, and post-success documentation protocol.
- Master plan covering repository management, search, file operations, Issues/PRs, Actions, notifications, command generation, and safe ZIP/project synchronization.
- Durable project memory and current handoff state.
- Canonical constants, callback/risk conventions, and GitHub capability groups.
- Async Python/FastAPI/aiogram/PostgreSQL baseline architecture.
- Arabic-first Telegram UI/UX screen and interaction specification.
- Security model for GitHub App credentials, webhook validation, destructive confirmations, archive safety, stale-state protection, and audit logging.
- Build/development protocol.
- Phased implementation roadmap.
- Architectural/product decision log.
- Comprehensive test matrix and live-smoke expectations.

### Security

- Established least-privilege GitHub App authentication as the primary credential model.
- Established HMAC-SHA256 GitHub webhook verification and delivery deduplication requirements.
- Established exact-name + final confirmation requirement for repository deletion.
- Established safe archive extraction and reviewed batch-update policy for ZIP/project synchronization.