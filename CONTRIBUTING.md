# Contributing to LR-Agent

Thanks for considering a contribution.

LR-Agent is a research-engineering project. The most valuable contributions are not necessarily new features; counterexamples, reproducible failures, benchmark tasks and clearer evidence are especially useful.

## Good contribution areas

### ChronoForge

- reproducible demo repositories;
- retrospective time-split datasets;
- future-scenario quality checks;
- Chrono Tournament implementation;
- maintenance-cost telemetry;
- calibration metrics;
- misleading Patch Life Report counterexamples.

### Causal Genome

- near-neighbor tasks where a learned strategy should **not** transfer;
- Anti-Gene false-positive/false-negative cases;
- contamination/genealogy experiments;
- verifier coverage;
- confidence calibration.

### Runtime

- Windows/Linux portability;
- safer tool execution;
- tests;
- typed interfaces;
- provider compatibility;
- UI observability.

## Before opening a PR

Run:

```bash
python -m compileall lr_agent
pytest
```

If you changed the Web UI, also make sure the JavaScript still parses and the relevant workflow passes.

## Research claims

Please separate:

- implemented behavior;
- experimental result;
- hypothesis;
- novelty claim.

Do not use phrases like “first ever” without strong evidence.

A useful pattern is:

> “In the public literature we searched, we did not find an equivalent end-to-end mechanism.”

If you find prior work that overlaps with a claim in `docs/research/`, opening an issue or PR to correct the record is welcome.

## Pull requests

A good PR explains:

1. what problem it addresses;
2. what changed;
3. what executable evidence supports the change;
4. what could still be wrong;
5. whether research docs need updating.

Keep unrelated refactors separate from behavior changes when practical.

## Counterexamples are first-class contributions

If LR-Agent:

- promotes a bad Forge winner;
- learns a harmful Gene;
- misses a contamination path;
- produces a misleading ChronoForge survival report;
- triggers a noisy Epistemic Tripwire;
- fails to reproduce a claimed behavior;

please open an issue with the smallest reproducible example you can provide.

A failed research hypothesis is still useful.

## Security

Do not open public issues containing:

- API keys;
- private repository code;
- access tokens;
- sensitive infrastructure details.

See [SECURITY.md](./SECURITY.md).

## Style

- Python 3.11+.
- Prefer small, testable functions.
- Keep safety boundaries explicit.
- Avoid silent fallback when it would make a result look successful.
- Preserve provenance for experimental evidence.

## Authorship

Repository-facing project authorship is maintained by **LLR6**. Contributors are naturally credited through Git history and GitHub contribution records.

## License

By contributing, you agree that your contribution may be distributed under the repository's MIT License.
