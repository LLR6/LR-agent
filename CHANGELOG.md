# Changelog

## 1.1.0 - 2026-09-27

### ChronoForge

- Added Prospective Software Evolution Laboratory for aging current code or completed Forge candidates through sequential future repository generations.
- Future generation N inherits the actual repository produced by generation N-1 instead of using independent hypothetical prompts.
- Added tailored future-maintenance scenarios for dependency upgrades, API deprecation, adjacent features, schema migration, module refactors, platform/runtime changes, performance pressure and configuration-contract changes.
- Added seed verification replay after every future-maintenance generation.
- Added active Invariant DNA replay inside every future generation.
- Added early trajectory death when seed behavior or invariants no longer survive.
- Added Patch Life Report metrics: Temporal Survival, Future Maintenance Cost, Maintenance Option Value, Invariant Survival, Dependency Robustness, Patch Surface Stability and repository-generation half-life.
- Added category-specific temporal death modes and survival curves.
- Added Web UI ChronoForge control center and a “let Forge winner live through the future first” path.
- Added CLI commands `chrono`, `chrono-list`, `chrono-show` and `chrono-observe`.
- Added REST APIs for starting, inspecting, cancelling and calibrating ChronoForge runs.

### Reality calibration

- Added persistent real-future observations to `chronoforge.db`.
- Added Laplace-smoothed category calibration weights so recorded real project evolution changes future-scenario priority.
- Future observations are explicitly treated as calibration evidence, not guaranteed predictions.

### Reliability and safety

- ChronoForge runs persist as queued/running/completed/failed/cancelled/interrupted instead of disappearing after restart.
- All future-maintainer Agents execute in shadow workspaces with GitHub writes and common external publication side effects disabled.
- Project inspector recommended checks are replayed for current-workspace seeds.
- Forge candidate verification commands are retained when aging a completed candidate.
- Synthetic future scenarios and maintenance-option scores are explicitly documented as engineering heuristics, not formal forecasts or proofs.

### Tests

- Added sequential temporal-survival tests with real pytest replay.
- Added repository-generation half-life assertions.
- Added reality-observation calibration tests.
- Added interrupted-run recovery tests.

### Changed

- Package and API version updated to 1.1.0.


## 1.0.0 - 2026-09-27

### Causal Genome Engine

- Added persistent Strategy Genes with quarantine, active, contested, retired and contaminated states.
- Added Treatment-vs-Control counterfactual ablation across isolated Forge workspaces.
- Added repeated-trial activation thresholds so one successful run does not become trusted memory.
- Added falsification mode that explicitly attacks a Gene's applicability, exclusions and assumptions.
- Added context-specific Anti-Genes from harmful ablation evidence.
- Added Gene genealogy edges and contamination propagation through descendants.
- Added persistent causal evidence records with treatment/control scores, effect and experiment provenance.
- Added persistent background Genome experiment jobs with interrupted recovery semantics.

### Proof and long-term project constraints

- Added Proof-Carrying Genes with executable verifier commands.
- Gene verifiers run independently in both treatment and control shadow workspaces.
- Added Invariant DNA for executable long-lived project properties.
- Forge promotion now replays winner checks and then all active Invariant DNA in the real workspace.
- Invariant failure automatically restores the pre-promotion workspace.
- Proof-Carrying Patch bundles now include Invariant DNA verification evidence.

### Agent behavior

- Active Genes and Anti-Genes can be retrieved into Coder / Research context.
- Quarantined Genes are not injected into normal Agent context.
- Added Epistemic Tripwire detection for repeated failures and repeated unverified mutation loops.
- Tripwire events are observable over the existing task event stream and Web UI.

### Interfaces

- Added Causal Genome REST APIs, background experiment APIs and Invariant DNA APIs.
- Added Web UI Causal Genome panel with A/B ablation, falsification and invariant checks.
- Added Forge-to-quarantine-Gene import control.
- Added CLI commands: `genome-stats`, `genome-list`, `genome-add`, `genome-import`,
  `genome-ablate`, `genome-falsify`, `genome-contaminate`, `invariant-list`,
  `invariant-add`, and `invariant-check`.

### Safety and epistemic limits

- A Forge win is treated as provenance only, not causal proof.
- Causal Genome activation requires repeated evidence thresholds.
- Counterfactual ablation is an engineering evidence heuristic, not a randomized statistical or formal causal proof.
- Shadow external-write protections remain active during Gene experiments.
- Contaminated ancestry can reduce trust across descendants instead of deleting provenance history.
- Package and API version updated to 1.0.0.


## 0.9.0 - 2026-09-27

### Added

- Counterfactual Forge: 2–4 isolated shadow workspaces can solve the same coding task with different strategies.
- Evidence-based candidate ranking using Reviewer outcome, real verification exit codes, tool failures and change scope.
- Optional evolved strategy synthesized from first-round observable evidence.
- Conflict-aware candidate promotion against the original workspace baseline.
- Proof-Carrying Patch bundles containing strategy, hashes, applied changes, verification evidence and a SHA-256 proof digest.
- Real-workspace verification replay after promotion.
- Automatic restoration of promoted files when real-workspace verification fails.
- Web UI Forge control center and winner promotion flow.
- CLI `forge`, `forge-list` and `forge-promote` commands.
- REST endpoints for starting, inspecting and promoting Forge tournaments.

### Safety

- Shadow universes never mutate the source workspace during candidate execution.
- Shadow mode blocks common remote side effects such as `git push`, GitHub creation commands and package publishing/deployment.
- Promotion refuses to overwrite paths changed in the real workspace since the tournament baseline.
- Promotion verification runs with GitHub writes disabled.
- A failed real-workspace verification automatically restores backed-up files instead of leaving a partially accepted candidate.

### Changed

- Package and API version updated to 0.9.0.


## 0.8.0 - 2026-09-27

### Added

- Optional OpenAI-compatible `/embeddings` client with retry handling.
- Persistent float32 embeddings for workspace knowledge chunks in SQLite.
- Hybrid RAG ranking that fuses lexical FTS5/LIKE retrieval with cosine semantic similarity.
- Automatic hybrid retrieval for Coder / Research context when embeddings are enabled.
- Embedding index status in the Web UI and CLI.
- Tests for semantic retrieval, stale-vector invalidation, embedding ordering and retry behavior.

### Reliability

- Embeddings are opt-in and disabled by default.
- Rebuilding the text index clears stale vectors before re-embedding.
- If the embedding endpoint is unavailable, LR-Agent preserves the lexical index and falls back to FTS5/LIKE search.
- Query embeddings must match the stored model and dimensions before semantic scores are used.

### Changed

- Package and API version updated to 0.8.0.


## 0.7.0 - 2026-09-27

### Added

- Run-scoped workspace snapshots for direct local file mutation tools.
- Original file bytes, mode and SHA-256 plus final kind/hash persistence.
- Conflict-aware rollback journal that refuses to overwrite workspace changes made after a run.
- Web UI rollback control for historical runs.
- REST endpoints to inspect run snapshots and request rollback.
- CLI `rollback <run_id>` command with confirmation and conflict reporting.
- Workspace mutation lock so direct file mutations and rollback do not race each other.

### Safety

- Snapshot creation happens before a direct file mutation and can block a mutation
  when the existing file exceeds the configured snapshot size limit.
- Rollback is all-or-nothing with respect to detected final-state conflicts: if any
  path differs from the run's recorded final state, no rollback path is changed.
- Directory deletion remains limited to empty directories created through tracked
  direct file operations.
- Rollback does not claim to undo `run_command`, build-script, package-manager,
  Git hook, external-process or remote GitHub side effects.

### Changed

- Package and API version updated to 0.7.0.

## 0.6.0 - 2026-09-27

### Added

- Live stdout/stderr streaming from allowlisted command subprocesses into the Agent event stream and Web UI.
- Web UI cancellation control for running or queued background tasks.
- `project_inspect` tool for Python, Node, Rust, Go, Maven, Gradle, CMake and Git projects.
- Safe `delete_file`, `move_file`, `make_directory` tools.
- Line-ranged `read_file` support.
- Common build/test executables in the default command allowlist.
- CI Python bytecode compilation and Web UI JavaScript syntax validation.

### Changed

- Workspace-relative executables are resolved against the requested command cwd.
- Coder system guidance now explicitly prefers stack inspection, relevant verification
  commands and Git diff/status evidence.
- Tool event forwarding now carries live command output before the final tool result.
- Package and API version updated to 0.6.0.

### Safety

- New file mutation tools participate in the existing interactive approval system.
- `delete_file` intentionally refuses directory deletion.
- Command cancellation continues to terminate the directly managed child process.
- Retrieved files, tool output and project context remain explicitly untrusted data.

## 0.5.0 - 2026-09-27

### Added

- Bounded background task concurrency with queued-task cancellation.
- Automatic project-context retrieval for Coder and Research modes.
- CONTEXT events in the live execution stream and Web UI.
- CLI commands for background tasks and project knowledge: `tasks`, `index`, `search`.
- Optional Bearer-token authentication for REST APIs and task WebSockets.
- Browser token handling through session-scoped storage.

### Security

- Retrieved project context is explicitly marked as untrusted data before it reaches
  the planner or executor to reduce prompt-injection risk.
- Non-loopback `lr-agent serve` bindings are refused without a Web token unless
  the user explicitly opts into unauthenticated remote binding.
- Docker Compose publishes the Web port on host loopback by default.
- Docker Compose explicitly permits the service's internal `0.0.0.0` bind while
  retaining the loopback-only host mapping.
- Expanded SECURITY.md deployment, approval, subprocess and retrieval guidance.

### Changed

- Queue concurrency is configurable through `LR_AGENT_MAX_CONCURRENT_TASKS`.
- Automatic retrieval can be configured through `LR_AGENT_AUTO_CONTEXT` and
  `LR_AGENT_AUTO_CONTEXT_RESULTS`.
- Package and API version updated to 0.5.0.

## 0.4.0 - 2026-09-27

### Added

- Optional interactive approval modes: `off`, `writes`, and `all`.
- Persistent approval records tied to background tasks.
- WebSocket `approval_required` / `approval_resolved` events.
- Web UI approval panel with Diff/command preview and approve/deny actions.
- Approval decision REST API.
- CLI y/N approval prompts for chat and run resume.
- Approval timeout and restart expiration semantics.

### Safety

- Denied actions are not executed.
- Write approvals can cover local file mutations and GitHub write tools.
- `all` mode can additionally require approval for `run_command`.
- Pending approvals from a previous process are expired on restart.

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
