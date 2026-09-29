# LR-Agent Claim Ledger

> Purpose: separate implemented mechanisms, tested behavior, research hypotheses and future ideas.  
> This file is intentionally stricter than the project README.

## Status vocabulary

- **Implemented** — code exists in the current repository.
- **Tested** — repository tests exercise the mechanism.
- **Prototype** — implemented enough to experiment with, but not validated as a scientific claim.
- **Hypothesis** — research question; implementation may exist, but evidence is not yet sufficient.
- **Planned** — not implemented.

## Current ledger

| Claim / mechanism | Implementation | Test evidence | Research status | What would falsify or weaken it |
|---|---|---|---|---|
| Isolated candidate workspaces | **Implemented** in Counterfactual Forge | `tests/test_universes.py` | Engineering mechanism | Candidate changes leak into the real workspace |
| Evidence-scored candidate comparison | **Implemented** | `tests/test_universes.py` | Prototype | Scores fail to track executable verification |
| Baseline-conflict check before promotion | **Implemented** | `tests/test_universes.py` | Engineering mechanism | Promotion can overwrite unrelated external changes |
| Promotion rollback after failed real verification | **Implemented** | `tests/test_universes.py` | Engineering mechanism | Failed verification leaves promoted changes behind |
| Gene quarantine | **Implemented** | `tests/test_genome.py`, `tests/test_genome_store.py` | Prototype | Newly imported strategies influence runtime before admission |
| Treatment-vs-control gene ablation | **Implemented** | `tests/test_genome.py` | **Hypothesis-bearing mechanism** | Matched controls perform equivalently or better across held-out tasks |
| Anti-Gene generation from negative evidence | **Implemented** | `tests/test_genome.py` | Prototype | Anti-Genes suppress useful strategies more than they prevent harmful reuse |
| Genealogy / contamination propagation | **Implemented** | `tests/test_genome_store.py` | Prototype | Descendant trust is not meaningfully safer than source-only invalidation |
| Proof-carrying Gene verifier | **Implemented** | `tests/test_genome.py` | Prototype | Verifier gating does not reduce false-positive strategy success |
| Active-only Genome retrieval | **Implemented** | genome tests | Engineering mechanism | Quarantined/retired/contaminated genes appear in normal task context |
| Invariant DNA | **Implemented** | genome / universe tests | Prototype | Invariant replay provides no additional protection beyond ordinary tests |
| Epistemic Tripwire | **Implemented** | agent / tool tests | Prototype | It mainly stops hard-but-solvable tasks and reduces success |
| Sequential ChronoForge inheritance | **Implemented** | `tests/test_chronoforge.py` | **Hypothesis-bearing mechanism** | Independent non-inherited future prompts predict maintenance equally well |
| Seed verification replay across generations | **Implemented** | `tests/test_chronoforge.py` | Engineering mechanism | Original patch checks are not consistently replayed |
| Temporal survival curve | **Implemented** | `tests/test_chronoforge.py` | Exploratory metric | Survival does not correlate with later real maintenance outcomes |
| Repository-generation half-life | **Implemented** | `tests/test_chronoforge.py` | Exploratory metric | Adds no signal beyond simpler present-time metrics |
| Maintenance Option Value | **Implemented heuristic** | ChronoForge tests | **Exploratory only** | Scalar adds no predictive value; raw multi-objective metrics perform as well |
| Reality-observation persistence | **Implemented** | `tests/test_chronoforge.py` | Prototype | Stored observations do not change or improve scenario calibration |
| Reality-calibrated future weights | **Implemented baseline** | `tests/test_chronoforge.py` | Hypothesis | Calibration error is no better than uniform/simple-frequency baselines |
| Chrono Tournament | **Planned** | none | Planned experiment | — |
| Temporal Anti-Gene | **Planned** | none | Planned research idea | — |
| Counterfactual Software Archaeology | **Planned** | none | Planned research idea | — |
| Intent Recoverability | **Planned** | none | Planned metric | — |
| Future Regret | **Planned** | none | Planned retrospective metric | — |

## What the repository currently proves

The repository can support engineering statements such as:

- isolated candidate workspaces exist;
- treatment/control experiments can be scheduled and persisted;
- sequential synthetic repository generations inherit prior generated code;
- original checks and invariants can be replayed;
- evidence, lineage and reality observations are stored;
- the above mechanisms have automated tests.

It **does not yet prove** that:

- Causal Genome improves coding-agent generalization;
- ChronoForge predicts real future maintenance burden;
- repository-generation half-life is a useful universal software metric;
- Maintenance Option Value is a theoretically justified scalar;
- LR-Agent outperforms strong coding-agent baselines.

Those require the evaluation plan in [EXPERIMENTS.md](EXPERIMENTS.md).

## Minimum evidence before stronger claims

For a mechanism to move from **Hypothesis** toward an empirical result, require at least:

1. held-out repositories/tasks;
2. matched baselines;
3. repeated stochastic runs;
4. executable outcome metrics;
5. cost accounting;
6. failure cases and negative results;
7. confidence intervals or paired statistical analysis;
8. leakage controls;
9. artifact/version pinning;
10. enough detail for an independent reproduction attempt.

## Why keep this ledger

Research prototypes tend to blur three statements:

```text
I implemented it.
I tested that the code path works.
I demonstrated that the idea improves outcomes.
```

These are different claims.

LR-Agent should keep them separate.
