# Change Risk Policy

## Low risk
- typo / prose-only documentation changes;
- new examples that do not change runtime behavior;
- additive tests.

## Medium risk
- new CLI options;
- new research-manifest fields;
- new metrics that do not redefine existing metrics;
- new artifact metadata;
- additional Genome / ChronoForge observability.

Expected evidence: tests, CHANGELOG note when public behavior changes, and updated Claim Ledger when research status changes.

## High risk
- persisted SQLite schema changes;
- promotion / rollback semantics;
- shadow-workspace isolation;
- verifier / invariant semantics;
- metric redefinition;
- changes that alter experiment comparability.

Expected evidence: migration note, regression tests, failure-path tests, benchmark impact, and explicit limitation review.

## Critical review triggers
Any change that could let shadow execution affect the real workspace, weaken external-write protections, or make an exploratory research claim look validated requires explicit manual review before release.
