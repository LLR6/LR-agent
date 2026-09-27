# Changelog

## 0.3.0 - 2026-09-27

### Added

- Persistent background task queue metadata with queued/running/completed/failed/interrupted states.
- WebSocket live events for plan creation, run start, tool execution, review and completion.
- Background resume flow for persisted runs.
- Workspace knowledge index backed by SQLite with FTS5/BM25 when available and LIKE fallback.
- Knowledge management API and Web UI indexing control.
- Unified diff evidence for file writes and exact replacements.
- Read-only `git_status` and `git_diff` tools.
- Cancellable asyncio subprocess execution for command tools.
- Model endpoint retry and compatibility fallback tests carried forward from 0.2 hardening.

### Changed

- Web UI submits work through `/api/tasks` instead of blocking on the synchronous chat endpoint.
- Tool evidence previews retain more output so diffs and verification logs are inspectable.
- Package version, API version and documentation moved to 0.3.0.

### Safety

- Cancelling an Agent task now terminates the directly managed child process.
- GitHub write operations remain opt-in.
- Workspace path boundaries, command allowlists and private-network HTTP protections remain enabled.

## 0.2.0 - 2026-09-27

### Added

- Planner -> Executor -> Reviewer execution pipeline for Coder and Research modes.
- Reviewer-driven retry when observable verification is incomplete.
- Persistent run records in SQLite, including plan, tool calls, evidence, status and review.
- Run history API and Web UI run browser.
- Run recovery from stored evidence through Web UI, REST API and CLI.
- Native GitHub read tools for repository metadata, contents, files and Actions.
- Opt-in GitHub write tools for issues, branches, repository files and pull requests.
- Workspace full-text search.
- Expanded CI tests for planner/reviewer, persisted runs and GitHub write protections.

### Security

- GitHub write operations remain disabled by default.
- GitHub writes require both an explicit setting and a configured token.
- Existing workspace boundary, private-network protection and command allowlist remain enabled.

## 0.1.0 - 2026-09-27

- Initial local-first Agent execution loop.
- FastAPI Web UI, CLI, SQLite conversation memory and Docker support.
- File, command and public HTTP tools.
- GitHub Actions tests on Python 3.11 and 3.12.
