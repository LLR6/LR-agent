# Novelty Claims and Boundaries

> Snapshot: 2026-09-27  
> This file is intentionally conservative.

## Why this document exists

Research projects often become misleading when implementation novelty, research novelty and historical priority are mixed together.

LR-Agent therefore distinguishes four different statements:

1. **Implemented:** this repository contains the mechanism.
2. **Research hypothesis:** the mechanism may improve an outcome and can be tested.
3. **Search-based novelty hypothesis:** we did not find the same end-to-end mechanism in the public work searched so far.
4. **Universal priority claim:** nobody has ever done it before.

LR-Agent should use (1)–(3) where justified.

It should **not** use (4) without a much broader literature/patent/system review.

---

## Claim N1 — Success-only memory is insufficient

### Not novel

Prior work already shows that success-derived skill memory can mislead agents when surface similarity hides different action requirements.

Boundary-Aware Skill Memory explicitly studies this problem.

### LR-Agent research extension

LR-Agent asks whether **counterfactual marginal contribution** can become a skill-admission signal:

```text
did strategy G appear in a successful run?
              ↓
             weak

did treatment(+G) repeatedly outperform control(-G)
on matched project/task baselines?
              ↓
          stronger evidence
```

### Current status

Implemented as treatment-vs-control Causal Genome ablation.

### Novelty wording

Acceptable:

> “We explore counterfactual treatment-control evidence as an admission mechanism for reusable coding-agent strategies.”

Avoid:

> “We invented reliable skill memory.”

---

## Claim N2 — Skills should remain falsifiable after admission

### Nearby prior work

- skill-boundary research;
- verifier/gating research;
- self-evolving agent evaluation;
- memory poisoning and skill contamination research.

### LR-Agent hypothesis

An active skill should not become permanent policy.

It should support:

- repeated later challenges;
- explicit falsification runs;
- confidence reduction;
- boundary expansion;
- contested state;
- retirement/contamination.

### Search-based novelty hypothesis

In the work reviewed so far, we did not find the exact lifecycle:

```text
quarantine
→ treatment/control evidence
→ active
→ active falsification
→ counterexample anti-gene
→ confidence/status revision
```

as one coding-agent runtime.

This needs continued literature review.

---

## Claim N3 — Negative strategy memory as Anti-Gene

### Not novel in broad sense

Learning from failures, negative examples, avoidance rules and counterexamples is not novel.

### LR-Agent formulation

A harmful strategy produces a first-class reusable negative artifact with:

- parent strategy relation;
- triggering task/context;
- measured negative effect;
- provenance;
- active cautionary retrieval.

### Search-based novelty hypothesis

We did not find an identical “anti-gene” mechanism driven specifically by repeated coding-agent counterfactual ablation.

The name itself is project terminology and is not evidence of novelty.

---

## Claim N4 — Genealogy-aware contamination propagation

### Nearby prior work

SkillJack and later skill-contamination work show that learned skills can preserve or propagate bad behavior, and that deleting a source record/skill may not repair descendants.

### LR-Agent hypothesis

Represent derivation explicitly:

```text
parent strategy
  ↓
derived strategy
  ↓
derived strategy
```

When parent provenance becomes untrusted, propagate distrust metadata through descendants rather than deleting history.

### Boundary

Provenance graphs and taint propagation are longstanding concepts in computer science.

The potentially novel part is their operational use in a self-evolving coding-agent strategy genome together with causal ablation and runtime retrieval.

---

## Claim N5 — Proof-Carrying Gene

### Not novel in broad concept

Proof-carrying code, executable specifications, tests-as-contracts and verifier-gated agent behavior all have substantial prior art.

### LR-Agent formulation

A learned strategy carries executable checks that are replayed in both:

- Treatment world;
- Control world.

The verifier becomes part of the strategy's evidence artifact rather than just a repository test suite.

### Novelty wording

Prefer:

> “LR-Agent attaches executable verification evidence to reusable strategy genes.”

Avoid:

> “LR-Agent invented proof-carrying software knowledge.”

---

## Claim N6 — Invariant DNA

### Not novel in broad concept

Software invariants, regression tests, contracts and executable specifications are established ideas.

### LR-Agent formulation

Invariant DNA is a persistent agent-facing layer independent from strategy memory.

It is replayed during:

- Forge promotion;
- ChronoForge future generations.

### Research question

Does an explicit long-lived invariant layer reduce regression during agent-driven evolution relative to ordinary task-local tests?

---

## Claim N7 — Epistemic Tripwire

### Nearby prior work

Failure-as-a-Process studies early epistemic errors and failure lock-in in coding-agent trajectories.

### LR-Agent extension

Use observable runtime events to intervene before final failure.

Current signals:

- repeated equivalent failures;
- repeated mutation of the same path without recognized verification.

### Boundary

Early anomaly detection and stuck-loop detection are not novel.

The research question is whether lightweight execution-level tripwires reduce coding-agent lock-in at acceptable false-positive cost.

---

# ChronoForge novelty boundaries

## Claim C1 — Long-horizon software evolution

Not novel.

SWE-EVO explicitly evaluates coding agents on long-horizon software evolution.

LR-Agent must not claim otherwise.

---

## Claim C2 — Forecasting future repository work

Not novel.

SWE-Future forecasts future task families using repository evidence and validates them against later real PRs.

ChronoForge builds on the same broad motivation.

---

## Claim C3 — Temporal repository reasoning

Not novel.

AgenticSZZ uses Temporal Knowledge Graphs and agentic search over repository history for bug-inducing commit identification.

Temporal reasoning over software history is an active field.

---

## Claim C4 — Prospective patch aging

### Research object

ChronoForge treats the **present patch** as the experimental subject.

The question is not just:

> what future task may happen?

It is:

> if this patch exists in the repository, what happens to it when plausible future tasks are repeatedly applied?

### Mechanism

```text
patch P
  ↓
future trajectory 1
  g1 → g2 → g3 → ...
  each generation inherits actual previous code

future trajectory 2
  g1 → g2 → g3 → ...

after every generation:
  replay P's original checks
  replay project invariants
  measure maintenance burden
```

### Search-based novelty hypothesis

Within the public systems and papers reviewed so far, we did not find an end-to-end coding-agent runtime whose primary evaluation object is a current candidate patch and which:

1. injects that patch into multiple synthetic future repository trajectories;
2. makes future coding agents perform real sequential maintenance edits;
3. carries resulting code from generation to generation;
4. replays the original patch's behavioral evidence after every future generation;
5. builds a temporal survival/maintenance profile for today's patch;
6. feeds later real repository events back into future-scenario calibration.

This is currently LR-Agent's strongest novelty hypothesis.

It is still not a universal priority claim.

---

## Claim C5 — Software patch half-life

### Existing related ideas

Software aging, code decay, defect survival and maintenance metrics are established areas.

### LR-Agent formulation

Repository-generation half-life is defined over ChronoForge's experimental survival curve:

[
g_{1/2} = min{g : S(g) le 0.5}
]

This is not calendar time.

### Novelty wording

Acceptable:

> “We introduce a repository-generation half-life metric for prospective patch-aging experiments.”

Avoid:

> “We invented software half-life.”

---

## Claim C6 — Maintenance Option Value

### Existing intellectual roots

Real options, option value, architectural flexibility and software maintainability have prior literature.

### LR-Agent formulation

Use actual future Agent maintenance work in synthetic temporal trajectories to estimate how much adaptation flexibility a patch preserves.

Current heuristic:

[
OV = S cdot (1 + C/20)^{-1}
]

where (S) is temporal survival and (C) is observed maintenance cost.

### Boundary

The current metric is exploratory.

It should not be advertised as theoretically derived finance mathematics.

The possible contribution is the **experimental operationalization** of future adaptation cost through agent-maintained repository trajectories.

---

## Claim C7 — Reality-calibrated patch aging

SWE-Future already validates future-work forecasts against later reality.

Therefore “reality calibration” by itself is not novel.

ChronoForge's narrower hypothesis is:

> Later real repository events can calibrate the distribution of future stressors used specifically for patch-aging experiments.

Current implementation uses category observations and smoothed weights.

Future research should measure actual forecast calibration error.

---

# Proposed future novelty hypotheses

The following are not implemented yet.

## F1 — Chrono Tournament

Expose multiple present-time-correct patches to exactly the same future scenario matrix.

```text
patch A ─┐
patch B ─┼─ same future matrix → comparative life histories
patch C ─┘
```

Research question:

> Can future-life evidence discriminate between patches that are indistinguishable on current tests?

---

## F2 — Temporal Anti-Gene

Create strategy/design cautions only after repeated failure across future evolution pressure.

Example:

```text
pattern:
framework-specific domain coupling

future stress:
dependency/API migrations

repeated observation:
high repair cost
```

Output:

```text
Temporal Anti-Gene:
avoid this coupling pattern when ecosystem boundary volatility is high
```

This must require cross-scenario evidence to avoid synthetic overfitting.

---

## F3 — Counterfactual Software Archaeology

Instead of asking which commit introduced a bug:

> What earlier design/invariant change would have prevented the later bug class while allowing subsequent real history to continue?

Proposed method:

- choose historical decision points;
- fork alternate histories;
- inject candidate invariants/design changes;
- replay real subsequent changes;
- test whether the later defect still emerges.

This is distinct from ordinary SZZ-style culprit identification, but it has not yet been implemented or exhaustively compared against causal software-evolution literature.

---

## F4 — Intent Recoverability

A future maintainer may preserve behavior while losing the original design intent.

Potential experiment:

1. hide original task text from a future Agent;
2. give only evolved code/tests;
3. ask it to infer the original constraint;
4. compare inference with ground truth.

Metric:

[
IR = 	ext{recoverability of original intent after } g 	ext{ generations}
]

Hypothesis:

patches with clearer architecture preserve intent better over time.

Not implemented.

---

## F5 — Future Regret

After real time passes, compare:

- patch selected at (T_0);
- alternatives rejected at (T_0);
- actual later maintenance history.

Define retrospective regret based on observed later cost.

Then ask:

> Would ChronoForge have selected lower-regret patches?

This would be stronger evidence than synthetic survival alone.

Not implemented.

---

# Evidence required before strong publication claims

A strong paper should demonstrate:

1. statistically significant improvement over strong baselines;
2. held-out repositories;
3. multiple model backbones;
4. multiple Agent harnesses where feasible;
5. prompt/scenario sensitivity analysis;
6. cost analysis;
7. leakage controls;
8. negative results;
9. retrospective real-history validation;
10. reproducible artifacts.

Without this, LR-Agent is an interesting prototype, not proof of a new scientific paradigm.

---

# Recommended public wording

## Short

> LR-Agent explores falsifiable strategy memory and prospective patch aging for coding agents.

## More specific

> LR-Agent's Causal Genome treats reusable coding strategies as hypotheses that require repeated counterfactual evidence, while ChronoForge stress-tests present patches through sequential synthetic future repository evolution.

## Novelty-safe

> In our literature search as of 2026-09-27, we did not find a public coding-agent runtime combining counterfactual strategy admission, anti-gene/provenance lifecycle management, and sequential future patch-aging with reality-calibrated maintenance scenarios. We treat this as a testable novelty hypothesis, not a universal priority claim.

Author: **LLR6**
