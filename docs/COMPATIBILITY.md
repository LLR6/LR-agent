# Compatibility

## Runtime

- Python: **3.11+**
- CI: Python **3.11 / 3.12**
- Operating systems: development is primarily validated on GitHub-hosted Linux runners; local use on other platforms may require platform-specific adjustments.

## Persisted data

The following data formats are versioned or schema-sensitive:

- research run manifest: `lr-agent-research-run/v1`
- research artifact bundle: `lr-agent-artifact-bundle/v1`
- ChronoForge / Genome SQLite data: treat database migrations as compatibility-sensitive.

## Compatibility policy

- Patch releases should not intentionally break public CLI/API behavior.
- Minor releases may add fields to JSON/API responses.
- Persisted-data schema changes must be documented in CHANGELOG.
- Research metrics may evolve, but renamed or redefined metrics must be called out explicitly.

## Not guaranteed

- identical behavior across different LLM providers/models;
- identical stochastic outcomes without controlled seeds/configuration;
- forward compatibility of unversioned experimental internal tables.
