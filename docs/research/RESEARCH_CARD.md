# LR-Agent Research Card

## Question

Can coding-agent patch selection improve when evaluation considers not only present-time correctness, but also evidence, strategy provenance and synthetic future repository evolution?

## Core hypotheses

1. Present-time-passing patches can differ in future maintenance survival.
2. Strategy treatment/control experiments can identify harmful or useful reusable behaviors.
3. Sequential repository aging can expose maintenance failures that present-time tests miss.
4. Artifact and claim provenance reduce ambiguity in experimental conclusions.

## Mechanisms under study

- Counterfactual candidate workspaces
- Evidence-scored candidate comparison
- Causal Genome treatment/control
- Gene quarantine and Anti-Genes
- ChronoForge sequential future evolution
- Temporal survival / repository-generation half-life
- Reproducible run manifests
- Artifact fingerprint bundles
- Claim Ledger separating implementation from empirical evidence

## Evaluation requirements

Before making stronger empirical claims:

- held-out repositories/tasks;
- matched baselines;
- repeated stochastic runs;
- executable outcome metrics;
- cost accounting;
- leakage controls;
- failure/negative results;
- paired statistical analysis;
- pinned artifacts and manifests.

## Current evidence level

Most major mechanisms are implemented and unit/integration tested. Several research claims remain hypotheses rather than validated performance conclusions.

See [CLAIM_LEDGER.md](CLAIM_LEDGER.md) for the strict status of each claim.

## Next experiment

Run matched present-tests-only versus ChronoForge-aware patch selection across held-out repositories, preserving manifests, tool traces, patches and future-generation results for paired comparison.
