# Benchmarks and Evaluation Entry Points

LR-Agent separates engineering verification from research claims.

## Engineering checks

- candidate-workspace isolation;
- baseline conflict detection;
- promotion rollback;
- Genome lifecycle tests;
- ChronoForge sequential inheritance tests;
- research-manifest validation;
- experiment artifact fingerprinting.

## Research protocol

Start with:

- `docs/research/CLAIM_LEDGER.md`
- `docs/research/EXPERIMENTS.md`
- `docs/research/experiment-manifest.example.json`

A serious comparative run should retain:

1. repository snapshot;
2. task definition;
3. model/scaffold/configuration;
4. baseline/condition;
5. seeds/repeats;
6. candidate patches;
7. tool traces;
8. executable outcomes;
9. cost and wall time;
10. artifact fingerprints.

## Current status

The repository provides mechanisms and experiment infrastructure. It does not yet claim validated superiority over strong coding-agent baselines.
