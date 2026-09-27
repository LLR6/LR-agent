# Changelog

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
