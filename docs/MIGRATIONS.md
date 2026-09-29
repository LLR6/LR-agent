# Migration Policy

LR-Agent persists research/runtime state and therefore treats migrations as first-class engineering changes.

## Scope

Migration-sensitive areas include:

- SQLite tables used by runs, Genome and ChronoForge;
- research-run manifests;
- artifact bundles;
- public API/CLI JSON consumed by scripts.

## Rules

1. Never mutate persisted semantics silently.
2. Schema changes must be documented in CHANGELOG.
3. Prefer additive columns/fields when possible.
4. If a destructive migration is unavoidable, provide an explicit backup/export step.
5. A migration should be restart-safe or fail before partial mutation.
6. Old research artifacts remain immutable; do not rewrite historical evidence to fit a new schema.
7. Metric redefinition requires a new metric name or schema version.

## Pre-release migration checks

- open an old fixture/database;
- run the migration;
- verify row counts / key records;
- replay representative CLI reads;
- verify rollback or backup restoration path;
- record known incompatibilities.

## Research principle

A migration must never make two historically different experiment definitions look equivalent.
