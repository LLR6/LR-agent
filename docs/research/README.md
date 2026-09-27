# LR-Agent Research Program

> Research snapshot: 2026-09-27  
> Repository: `LLR6/LR-agent`  
> Status: active engineering research prototype

This directory records the research ideas, hypotheses, implementation decisions, related-work boundaries and evaluation plans behind LR-Agent.

The goal is not to decorate a coding agent with more roles. The research program asks a harder question:

> **Can a coding agent learn which strategies actually help, discover when those strategies stop helping, preserve project-level invariants, and evaluate a patch against plausible future software evolution before accepting it today?**

LR-Agent currently explores two connected systems:

1. **Causal Genome Engine** — a falsifiable strategy-memory system.
2. **ChronoForge** — a prospective software-evolution laboratory for aging patches through synthetic future repository generations.

The ideas in this directory are intentionally separated into:

- **implemented mechanisms** — code exists in the repository;
- **research hypotheses** — measurable claims that still require experiments;
- **novelty hypotheses** — claims about how the combination differs from public work found in our search;
- **future ideas** — not yet implemented and not presented as completed work.

## Research principles

### 1. Success is not causality

A strategy that appears in a successful trajectory is not automatically a useful reusable skill.

LR-Agent therefore distinguishes:

```text
successful trajectory
        !=
causally useful strategy
```

A candidate strategy enters quarantine and must survive controlled treatment-vs-control experiments before it is treated as trusted runtime knowledge.

### 2. Failure is evidence, not garbage

Negative results are first-class artifacts.

A harmful or boundary-sensitive strategy should leave behind:

- counterexamples;
- explicit exclusions;
- anti-genes;
- provenance;
- contamination relationships;
- verifier evidence.

Deleting a failed skill erases exactly the evidence future agents need.

### 3. A patch can be correct now and fragile later

Passing today's tests is necessary but often insufficient.

ChronoForge asks whether today's patch remains cheap and understandable under future maintenance pressures such as dependency upgrades, API deprecation, adjacent features and schema evolution.

### 4. Tests are evidence, not proof

Executable checks are stronger than self-reported model confidence, but they still only establish what the checks cover.

The repository therefore avoids language such as “formally proven correct” unless a future mechanism actually supplies formal proof.

### 5. Novelty claims must be falsifiable

We do **not** claim “nobody in human history has ever thought of this.”

The stronger research standard used here is:

> “Within the public literature and systems we searched as of 2026-09-27, we did not find a system with the same end-to-end mechanism. Nearby work exists and is documented.”

If a prior system is later found, the novelty document should be updated rather than defended rhetorically.

---

## Current research architecture

```text
                          ┌──────────────────────┐
                          │   Real repository    │
                          └──────────┬───────────┘
                                     │
                              coding task / bug
                                     │
                                     ▼
                        ┌────────────────────────┐
                        │ Counterfactual Forge   │
                        │ competing patch worlds │
                        └──────────┬─────────────┘
                                   │
                           evidence winner(s)
                                   │
                 ┌─────────────────┴──────────────────┐
                 │                                    │
                 ▼                                    ▼
      ┌─────────────────────┐              ┌─────────────────────┐
      │ Causal Genome       │              │ ChronoForge         │
      │ strategy experiment │              │ temporal experiment │
      └──────────┬──────────┘              └──────────┬──────────┘
                 │                                    │
       treatment vs control                  future generations
                 │                                    │
       falsification / anti-gene              maintenance agents
                 │                                    │
         proof-carrying gene               seed checks + invariants
                 │                                    │
                 └─────────────────┬──────────────────┘
                                   ▼
                         ┌──────────────────────┐
                         │  Invariant DNA       │
                         │ long-lived contracts │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         safer patch promotion
```

## Implemented research mechanisms

### Counterfactual Forge

- isolated candidate workspaces;
- multiple competing repair strategies;
- executable evidence scoring;
- evolved strategy option;
- conflict-aware promotion;
- proof-carrying patch bundle;
- real-workspace re-verification;
- rollback on failed promotion.

### Causal Genome Engine

- quarantined strategy genes;
- treatment-vs-control ablation;
- repeated evidence thresholds;
- falsification mode;
- context-specific anti-genes;
- genealogy edges;
- contamination propagation;
- executable gene verifiers;
- active-only runtime retrieval;
- Invariant DNA;
- Epistemic Tripwire.

### ChronoForge

- current-workspace or Forge-candidate seed;
- multiple future trajectories;
- sequential repository inheritance between generations;
- future-maintainer agents;
- seed verification replay;
- Invariant DNA replay;
- early temporal death;
- survival curve;
- maintenance-cost heuristic;
- maintenance option value;
- dependency robustness;
- patch-surface stability;
- repository-generation half-life;
- temporal death modes;
- persistent reality observations;
- weighted-fair future-category scheduling.

---

## Research documents

- [State of the Art and Related Work](./STATE_OF_THE_ART.md)
- [Causal Genome Engine](./CAUSAL_GENOME.md)
- [ChronoForge](./CHRONOFORGE.md)
- [Novelty Claims and Boundaries](./NOVELTY_CLAIMS.md)
- [Experimental Protocol and Benchmarks](./EXPERIMENTS.md)
- [Research Roadmap](./ROADMAP.md)
- [Bibliography](./BIBLIOGRAPHY.md)

## Core research hypotheses

### H1 — Strategy causality

A strategy selected by repeated counterfactual ablation should generalize better than a strategy admitted from success-only trajectory distillation.

### H2 — Negative memory

Explicit anti-genes and exclusions should reduce high-confidence misapplication on tasks that superficially resemble previous successes but require different actions.

### H3 — Provenance-aware contamination

When a source gene is later invalidated, genealogy-aware trust propagation should reduce downstream reuse of inherited defective strategies more effectively than deleting only the source artifact.

### H4 — Early epistemic intervention

Observable execution tripwires should reduce repeated failure loops and wasted tool steps without materially suppressing successful iterative work.

### H5 — Temporal robustness

Patches with similar current correctness can differ materially in future maintenance cost and survival under repository evolution.

### H6 — Prospective option value

ChronoForge's survival-adjusted maintenance-cost signal should correlate with later real maintenance burden better than present-time patch size or test pass/fail alone.

### H7 — Reality calibration

A future generator calibrated with later observed repository changes should produce scenario distributions that better match subsequent real work than a static uniform scenario generator.

---

## What would falsify this research direction?

The project should be willing to conclude that a mechanism is not useful.

Examples:

- treatment/control effects disappear after controlling for model stochasticity;
- genes selected by the causal pipeline do not generalize better than success-only memories;
- anti-genes cause excessive false suppression;
- temporal survival does not correlate with later maintenance outcomes;
- future scenarios are too synthetic to distinguish patch quality;
- invariant replay dominates all predictive value, making the rest of ChronoForge unnecessary;
- option-value scores are unstable across backbones or seeds;
- the cost of experiments exceeds any practical benefit.

These are not documentation problems. They are legitimate negative research results.

## Research maturity

| Area | Implementation | Evaluation maturity |
|---|---|---|
| Counterfactual Forge | working | unit/CI evidence, broader benchmark needed |
| Causal Genome store | working | unit/CI evidence, external benchmark needed |
| Ablation/Falsification | working | mechanism tests, statistical study needed |
| Anti-Gene | working | mechanism tests, behavior study needed |
| Invariant DNA | working | promotion tests, repository study needed |
| Epistemic Tripwire | working | mechanism tests, large trajectory study needed |
| ChronoForge | working prototype | mechanism tests, retrospective validation needed |
| Reality calibration | working prototype | calibration study needed |
| Chrono Tournament | planned | not implemented |
| Temporal Anti-Gene | planned | not implemented |
| Future Surprise metric | planned | not implemented |
| Counterfactual Software Archaeology | research idea | not implemented |

---

## Research ethics and reproducibility

The project should preserve:

- model/provider version;
- prompt/scaffold version;
- repository commit;
- environment/runtime versions;
- random seed when the provider exposes one;
- tool traces;
- test outputs;
- scenario definitions;
- exact candidate patches;
- failed experiments, not only successful ones.

A publishable evaluation should separate:

1. **development repositories/tasks** used while designing the method;
2. **held-out repositories/tasks** used only for final evaluation;
3. **future observations** that occurred after a forecast snapshot.

This is especially important because coding-agent systems are highly vulnerable to benchmark overfitting and retrospective leakage.

---

Author: **LLR6**
