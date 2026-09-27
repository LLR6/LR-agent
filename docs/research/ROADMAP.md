# Research Roadmap

> This roadmap separates engineering work from research claims.  
> Items marked **implemented** exist in the repository.  
> Items marked **planned** are design directions only.

## Phase A — Counterfactual coding foundation

### A1. Counterfactual Forge — implemented

Goal: generate multiple real candidate patches in isolated workspaces and compare observable evidence.

Completed mechanisms:

- multiple strategies;
- isolated workspaces;
- executable checks;
- evidence scoring;
- evolved strategy;
- proof-carrying patch;
- conflict-aware promotion;
- real-workspace verification;
- rollback on failure.

Research debt:

- matched future scenario comparison across candidates;
- stronger candidate score calibration;
- more repository/language coverage.

---

## Phase B — Causal Genome — implemented prototype

### B1. Quarantine-first strategy memory — implemented

No one-shot automatic skill admission.

### B2. Treatment vs Control ablation — implemented

Estimate strategy marginal effect.

### B3. Active falsification — implemented

Try to disprove a Gene rather than only accumulate confirming evidence.

### B4. Anti-Gene — implemented

Preserve negative strategy evidence.

### B5. Genealogy / contamination propagation — implemented

Track inherited trust.

### B6. Proof-Carrying Gene — implemented

Attach executable success evidence to strategy artifacts.

### B7. Invariant DNA — implemented

Separate long-lived project contracts from strategy memory.

### B8. Epistemic Tripwire — implemented prototype

Interrupt obvious repeated failure/mutation loops.

### B9. Better confidence decomposition — planned

Replace one scalar confidence with:

- empirical support;
- transfer confidence;
- freshness;
- provenance trust;
- verifier coverage;
- repository specificity.

### B10. Gene lifetime / decay — planned

A Gene can become stale as:

- dependencies change;
- project architecture changes;
- model/tool capabilities change.

Proposed state:

```text
active
  ↓ time/environment drift
stale
  ↓ revalidation
active / contested / retired
```

---

# Phase C — ChronoForge — implemented prototype

### C1. Sequential future repository generations — implemented

Each future generation inherits the previous generation's actual code.

### C2. Seed verification replay — implemented

Current behavior must survive future evolution.

### C3. Invariant replay — implemented

Long-lived project contracts survive the future too.

### C4. Temporal survival curve — implemented

### C5. Maintenance-cost heuristic — implemented

### C6. Repository-generation half-life — implemented

### C7. Reality observations — implemented

### C8. Weighted-fair future scheduling — implemented

---

# Phase D — Chrono Tournament — next major target

## D1. Same Future Matrix for multiple patches

Problem:

Running Patch A and Patch B through different futures makes comparison noisy.

Target:

```text
                    Frozen Future Matrix
              F11 F12 F13 ... / F21 F22 ...
                    │
       ┌────────────┼────────────┐
       ↓            ↓            ↓
    Patch A      Patch B      Patch C
```

All candidates receive the same:

- scenario categories;
- scenario details;
- generation order;
- verifier suite;
- Invariant DNA;
- model/harness configuration where feasible.

Outputs:

- paired temporal survival;
- paired maintenance cost;
- paired death modes;
- paired invariant survival.

Research question:

> Can future-life evidence differentiate patches that all pass present-time tests?

---

# Phase E — Temporal learning

## E1. Temporal Anti-Gene — planned

If a patch/design pattern repeatedly creates future maintenance burden:

```text
pattern
+ future pressure
+ repeated temporal failure
    ↓
Temporal Anti-Gene
```

Admission should require multiple independent trajectories.

Potential fields:

```json
{
  "pattern": "...",
  "future_pressure": "...",
  "observed_cost_lift": 0.0,
  "death_rate_lift": 0.0,
  "repositories": [],
  "provenance": []
}
```

---

## E2. Temporal Gene — planned

Positive equivalent.

A design pattern that repeatedly reduces later adaptation cost could become:

```text
Temporal Gene:
  under boundary-volatility condition X,
  abstraction pattern Y preserved option value.
```

Important:

Do not let synthetic-only temporal evidence automatically enter the normal Causal Genome.

Use a separate trust channel until real-history validation supports transfer.

---

## E3. Future Surprise — planned

Today:

```text
Future Model predicts category distribution
```

Later:

```text
real repository events arrive
```

Store the original forecast and compute calibration error.

Candidate measures:

- Brier score;
- log loss;
- expected calibration error;
- category recall;
- semantic surprise.

This upgrades calibration from:

> “we saw dependency upgrades often”

to:

> “our prior future model assigned 0.12 but reality happened; update based on forecast error.”

---

# Phase F — Counterfactual Software Archaeology

## F1. Alternate-history replay — research proposal

Question:

> What earlier design decision would have prevented today's bug class?

Pipeline:

```text
real history H
    ↓
bug B at time T
    ↓
candidate historical decision points D1..Dn
    ↓
alternate branch at Di
    ↓
inject invariant/design change
    ↓
replay later real commits/events
    ↓
does B still emerge?
```

This differs from standard “find bug-inducing commit.”

Potential output:

```text
Missing Invariant:
  ownership of refresh-token lineage must remain single-source.

Earliest useful insertion:
  before auth module split.

Observed:
  bug disappears in 4/5 alternate-history replays.
```

Major challenges:

- replaying historical commits after alternate code changes;
- merge conflicts;
- semantic drift;
- identifying equivalent later edits;
- avoiding hindsight leakage.

---

# Phase G — Intent and knowledge survival

## G1. Intent Recoverability — planned

Question:

> After several repository generations, can a fresh maintainer infer why the original patch exists?

Experiment:

1. hide original issue/task description;
2. provide evolved repository;
3. ask a fresh Agent to infer original behavioral/design intent;
4. compare with ground truth.

Possible metric:

[
IR(g) = similarity(hat{intent}_g, intent_0)
]

Why this matters:

Some code keeps passing tests while becoming semantically mysterious.

---

## G2. Invariant discovery from repeated history — planned

Instead of manually registering every invariant:

```text
multiple bugs
+ repeated regression fixes
+ alternate-history experiments
       ↓
candidate missing invariant
       ↓
human/verifier approval
       ↓
Invariant DNA
```

The system should never silently invent a high-authority invariant from model opinion alone.

---

# Phase H — Cross-project strategy transfer

## H1. Project-private vs transferable Genes

Classify Genes:

- project-private;
- framework-local;
- language-local;
- architecture-general;
- universal tooling strategy.

Research question:

> Which kinds of strategy evidence transfer without increasing harmful imitation?

Need controlled cross-repository experiments.

---

## H2. Transfer quarantine

A Gene active in repository A should not automatically be active in repository B.

Proposed:

```text
active@repoA
    ↓ transfer
quarantine@repoB
    ↓ local ablation
active@repoB
```

This preserves local evidence.

---

# Phase I — Benchmark and paper artifact

## I1. LR-GenomeBench — planned

A controlled benchmark for:

- success-only imitation traps;
- strategy applicability;
- counterexamples;
- contamination;
- genealogy;
- verifier coverage.

Each task family contains near-neighbor tasks with intentionally different correct strategies.

---

## I2. LR-ChronoBench — planned

Time-split benchmark for prospective patch aging.

Each instance contains:

- repository snapshot T0;
- current issue/patch candidates;
- information legally available at T0;
- hidden later repository evolution;
- real later maintenance targets.

Evaluation:

```text
ChronoForge at T0
      vs
actual evolution after T0
```

---

## I3. Live prospective study — long-term

Strongest possible ChronoForge study:

1. select active repositories today;
2. freeze forecasts and patch-life reports;
3. publish timestamped artifacts;
4. do not modify them after observing future events;
5. revisit months later.

This avoids retrospective story-fitting.

---

# Phase J — Research-quality tooling

## J1. Experiment manifest

Every run should become exportable as a stable manifest.

## J2. Deterministic scenario matrix

Chrono Tournament requires frozen shared scenario definitions.

## J3. Provider/model metadata

Record exact model identifiers and configuration.

## J4. Cost telemetry

Token/tool/runtime cost must be first-class.

## J5. Dataset split enforcement

Prevent accidental use of hidden future data.

## J6. Reproduction command

One command should recreate a recorded experiment where provider determinism permits.

---

# Suggested paper sequence

## Paper 1 — Causal Genome

Working title:

**Beyond Success Memory: Falsifiable Strategy Evolution for Coding Agents**

Core contribution:

- treatment/control strategy admission;
- active falsification;
- anti-gene;
- provenance genealogy;
- contamination experiments.

Do not overload with ChronoForge initially.

---

## Paper 2 — ChronoForge

Working title:

**ChronoForge: Prospective Patch Aging through Agentic Software Evolution**

Core contribution:

- patch as experimental subject;
- sequential future repository trajectories;
- temporal survival;
- maintenance burden;
- retrospective validation.

---

## Paper 3 — Alternate software histories

Working title:

**Counterfactual Software Archaeology: Testing Which Past Design Constraints Would Have Prevented Future Defects**

Only pursue if alternate-history replay becomes technically robust.

---

# Priority order

Current recommended priority:

```text
1. Chrono Tournament
2. retrospective ChronoForge benchmark
3. cost/reproducibility telemetry
4. causal-genome held-out benchmark
5. Future Surprise calibration
6. Temporal Anti-Gene
7. Counterfactual Software Archaeology
8. Intent Recoverability
```

Reason:

The biggest research risk is no longer implementation.

It is whether the proposed metrics predict anything real.

Therefore evaluation infrastructure is more valuable now than adding more Agent roles.

Author: **LLR6**
