# LR-Agent v1.1.0 — ChronoForge

## Headline

**Let a patch live through simulated future repository generations before you merge it.**

## What's new

### ChronoForge

LR-Agent can now age the current workspace or a completed Counterfactual Forge candidate through multiple sequential future repository trajectories.

Future-maintainer agents can evolve the shadow repository under pressures such as:

- dependency upgrades;
- API deprecation;
- adjacent features;
- schema migration;
- module-boundary changes;
- runtime/platform changes;
- performance pressure;
- configuration-contract changes.

Generation N inherits the actual code produced by generation N-1.

### Patch Life Report

ChronoForge reports:

- Temporal Survival Curve
- Future Maintenance Cost
- Maintenance Option Value
- Invariant Survival
- Dependency Robustness
- Patch Surface Stability
- repository-generation Half-Life
- Temporal Death Modes

### Reality calibration

Later real repository events can be recorded with:

```bash
lr-agent chrono-observe dependency_upgrade "framework major-version migration"
```

Those observations affect future scenario scheduling weights.

### Causal Genome research stack

v1.1.0 also includes the Causal Genome mechanisms introduced in the 1.0 line:

- quarantine-first Strategy Genes;
- Treatment vs Control ablation;
- active falsification;
- Anti-Genes;
- genealogy / contamination propagation;
- Proof-Carrying Genes;
- Invariant DNA;
- Epistemic Tripwire.

## Quick start

```bash
git clone https://github.com/LLR6/LR-agent.git
cd LR-agent
python -m venv .venv
pip install -e ".[dev]"
```

Configure an OpenAI-compatible endpoint/model in `.env`, then:

```bash
lr-agent doctor
lr-agent serve
```

Try ChronoForge:

```bash
lr-agent chrono "preserve the current core behavior" --generations 4 --trajectories 3
```

## Demo

See:

- [5-minute ChronoForge Demo](./DEMO_CHRONOFORGE.md)
- [ChronoForge research note](./research/CHRONOFORGE.md)
- [Experimental protocol](./research/EXPERIMENTS.md)

## Research status

ChronoForge is a research prototype.

Synthetic futures are stress scenarios, not guaranteed forecasts. Maintenance Option Value is an engineering heuristic, not a formal maintainability proof.

The next major research target is **Chrono Tournament**: exposing multiple present-time-correct patches to the exact same frozen Future Matrix.

## Feedback wanted

The most useful feedback is a reproducible counterexample:

- a patch ChronoForge scores highly but is clearly fragile;
- a low-scoring patch that later proves easy to maintain;
- a Causal Genome strategy that should not transfer;
- an Invariant or verifier design that exposes a blind spot.
