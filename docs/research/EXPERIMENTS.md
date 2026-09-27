# Experimental Protocol and Benchmark Plan

> Goal: turn LR-Agent from an interesting prototype into a falsifiable research system.

This document defines what should be measured, which baselines are required, how to avoid misleading conclusions, and what evidence would count as support or failure for the project hypotheses.

---

## 1. General evaluation philosophy

LR-Agent contains several mechanisms that can easily create impressive demos without proving anything:

- multiple Agents;
- memory;
- counterfactual workspaces;
- future scenarios;
- self-evaluation;
- learned strategies.

A credible evaluation must therefore prefer:

- executable outcomes over model opinion;
- held-out tasks over development tasks;
- matched baselines over before/after anecdotes;
- repeated runs over one cherry-picked trajectory;
- confidence intervals over raw means;
- explicit failure cases over success-only reporting.

---

# Part I — Causal Genome experiments

## 2. Main Causal Genome question

Does a strategy admitted by repeated counterfactual marginal evidence generalize better than a strategy admitted from a successful trajectory alone?

### Experimental unit

```text
repository snapshot
+ task
+ candidate strategy
+ model/scaffold
```

### Treatment

Agent receives the candidate Gene, including boundaries and verifier when available.

### Control

Same task and project baseline, but the Agent is explicitly instructed not to use/reconstruct the Gene.

### Outcome

Primary:

- verified task success.

Secondary:

- evidence score;
- tool-step count;
- failed tool calls;
- files changed;
- regression count;
- verifier result;
- token/model cost.

---

## 3. Causal Genome baselines

At minimum compare:

### B0 — No memory

Normal coding Agent with no retrieved skill.

### B1 — Success-only skill

A concise strategy distilled from a successful prior trajectory.

### B2 — Boundary memory

Success skill plus applicability/exclusion fields.

### B3 — Verifier-gated success skill

Skill is admitted if one or more critics/verifiers approve it.

### B4 — LR-Agent quarantine only

No causal ablation; skills wait a fixed number of successful observations.

### B5 — LR-Agent causal ablation

Treatment/control evidence determines admission.

### B6 — Causal ablation + falsification

Full positive and negative testing.

### B7 — Full Causal Genome

Includes:

- anti-genes;
- genealogy;
- contamination propagation;
- proof-carrying verifier;
- active-only retrieval.

---

## 4. Strategy transfer benchmark construction

Need pairs of tasks with surface similarity but different optimal behavior.

Example family:

```text
Task A:
pytest-asyncio fixture ownership bug

Task B:
Trio backend lifecycle bug
```

A success-only memory may over-transfer from A to B.

Dataset should include:

- same library, different root cause;
- same error string, different cause;
- same file type, different tool;
- same architectural symptom, different ownership;
- same framework, different version;
- same module, incompatible constraints.

The benchmark should explicitly label:

- applicable;
- partially applicable;
- non-applicable;
- harmful.

This allows measurement of skill calibration, not just success rate.

---

## 5. Anti-Gene evaluation

Question:

> Does negative strategy memory reduce harmful reuse without over-suppressing useful behavior?

Metrics:

- harmful retrieval rate;
- harmful application rate;
- false suppression rate;
- task success;
- intervention count.

Study design:

```text
same task set
  ├─ positive memory only
  ├─ positive + boundaries
  └─ positive + boundaries + anti-gene
```

Important failure mode:

An Anti-Gene can become overbroad and prevent a strategy in cases where it actually works.

Therefore report both:

- avoided harm;
- blocked benefit.

---

## 6. Genealogy contamination evaluation

Construct a controlled lineage:

```text
G0
├─ G1
│  └─ G3
└─ G2
```

Inject a defective assumption into G0.

Allow descendants to be created using G0 as reference.

Compare remediation:

### R0 — delete source only

Delete G0.

### R1 — mark source untrusted

G0 no longer retrieved.

### R2 — genealogy propagation

G0 and descendants have trust reduced/contaminated.

Measure:

- harmful descendant retrieval;
- downstream task success;
- false contamination rate;
- recovery cost.

---

## 7. Proof-Carrying Gene evaluation

Construct tasks where:

- Agent claims success;
- broad project tests pass;
- a narrow behavioral verifier exposes the strategy violation.

Compare:

- no Gene verifier;
- verifier only in Treatment;
- verifier in Treatment and Control.

Primary metric:

- false-positive “Gene helped” rate.

---

## 8. Epistemic Tripwire evaluation

Dataset should contain:

- tasks that naturally require several iterations;
- tasks that produce repeated identical failures;
- tasks with misleading initial hypotheses;
- tasks where repeated editing is legitimate.

Compare:

```text
Agent without Tripwire
vs
Agent with Tripwire
```

Metrics:

- final success;
- tool steps;
- failed tool calls;
- repeated mutation count;
- time/token cost;
- false-positive Tripwire rate;
- recovery after Tripwire;
- percentage of trajectories rescued.

Important:

A Tripwire that simply stops difficult work may reduce cost while reducing success. Both must be reported.

---

# Part II — ChronoForge experiments

## 9. Main ChronoForge question

Can prospective patch-aging evidence predict later maintenance burden better than present-time metrics alone?

This requires **retrospective time-split evaluation**.

---

## 10. Retrospective repository protocol

For each repository:

### Step 1 — choose forecast snapshot

Select date/commit (T_0).

Everything after (T_0) must be hidden from the ChronoForge generation process.

### Step 2 — identify candidate patches near T0

Sources may include:

- competing historical patch variants if available;
- generated alternatives for a historical issue;
- refactor alternatives;
- accepted patch vs synthetically equivalent implementation.

### Step 3 — run present-time checks

Record:

- tests;
- patch size;
- complexity;
- touched files;
- static metrics.

### Step 4 — run ChronoForge

Generate synthetic future trajectories using only information available at (T_0).

Record:

- survival curve;
- half-life;
- maintenance cost;
- option value;
- death modes;
- patch-surface stability.

### Step 5 — reveal real future

Observe repository history after (T_0).

### Step 6 — compute real maintenance outcomes

Possible targets:

- future edits touching patch surface;
- later regressions;
- revert;
- compatibility fixes;
- dependency-migration burden;
- bug-fix count;
- churn;
- number of future PRs that must modify the patch;
- time/commit count until replacement;
- future test breakage linked to the patch surface.

### Step 7 — compare predictors

Does ChronoForge add predictive value beyond present-time metrics?

---

## 11. ChronoForge baselines

### C0 — current tests only

Binary pass/fail.

### C1 — patch size

Added/deleted lines, files touched.

### C2 — static complexity

Cyclomatic complexity / dependency fan-out / coupling where available.

### C3 — current Agent reviewer score

Model-based maintainability/review opinion.

### C4 — independent future prompts

Ask several future questions but do not inherit repository state between generations.

This isolates the value of sequential future inheritance.

### C5 — uniform ChronoForge

All future categories equally scheduled.

### C6 — calibrated ChronoForge

Reality-calibrated weighted scheduling.

### C7 — no Invariant DNA

Tests only.

### C8 — full ChronoForge

Sequential inheritance + seed checks + invariants + calibration.

---

## 12. Sequential inheritance ablation

Core claim:

> Future g2 should inherit actual g1 code.

Ablation:

### Independent

```text
Seed → g1
Seed → g2
Seed → g3
```

### Sequential

```text
Seed → g1 → g2 → g3
```

Compare:

- death rate;
- maintenance cost;
- repeated coupling;
- correlation with real future maintenance.

If independent prompts perform equally well, the core temporal mechanism is weakened.

---

## 13. Future-scenario realism evaluation

Human/software-engineering expert annotation can score each generated scenario:

- plausible for repository;
- technically coherent;
- actionable without hidden information;
- likely/unlikely;
- redundant with other scenarios;
- impossible at snapshot T0.

Additionally compare generated categories with later real PR categories.

Metrics:

- semantic relevance;
- future-family recall;
- calibration;
- diversity;
- invalid-scenario rate.

---

## 14. Reality calibration evaluation

At (T_0), freeze future-category weights.

Observe events over subsequent windows:

```text
T0 → T1 → T2 → T3
```

Compare:

- static uniform weights;
- cumulative frequency;
- decayed frequency;
- Bayesian/smoothed categorical;
- learned repository-specific predictor.

Metrics:

- Brier score;
- log loss;
- expected calibration error;
- top-k family recall.

Current implementation uses a simple Laplace-smoothed categorical model and should be treated as baseline-level calibration.

---

## 15. Chrono Tournament experiment

Planned.

Generate multiple valid patches for the same current task.

All candidates receive **exactly the same future matrix**.

Example:

```text
                   scenario matrix
                 F1 F2 F3 F4 F5 F6
                  │  │  │  │  │  │
Patch A ──────────┼──┼──┼──┼──┼──┤
Patch B ──────────┼──┼──┼──┼──┼──┤
Patch C ──────────┼──┼──┼──┼──┼──┤
```

Pairwise outcomes:

- which survives longer;
- which costs less to maintain;
- which preserves invariants;
- which has lower real later maintenance burden.

This design reduces future-sampling confounding.

---

## 16. Maintenance Option Value validation

The current formula is heuristic.

We should test whether it predicts anything useful.

Candidate alternatives:

### V1 — current

[
OV_1 = S cdot (1 + C/20)^{-1}
]

### V2 — area under survival curve per cost

[
OV_2 = rac{AUC(S)}{1+C}
]

### V3 — expected remaining generations per cost

[
OV_3 = rac{E[L]}{1+C}
]

### V4 — multi-objective Pareto ranking

Do not collapse metrics to one scalar.

Compare correlation with real future maintenance targets.

If scalar option value adds no predictive power, the project should retain the raw metrics instead.

---

## 17. Patch Surface Stability validation

Hypothesis:

Frequent re-entry into original patch files may indicate coupling.

But some central files are expected to be touched frequently.

Controls:

- file historical churn before T0;
- file ownership/activity;
- centrality;
- module size.

Possible normalized metric:

[
PSS =
1 -
rac{
futurePatchSurfaceTouches / totalFutureTouches
}{
historicalPatchSurfaceChurn / historicalTotalChurn
}
]

This is more defensible than an unnormalized raw touch frequency.

Not yet implemented.

---

# Part III — Statistical methodology

## 18. Repeated runs

LLM agents are stochastic.

For each condition:

- at least 5–10 runs for early experiments;
- more for final claims where affordable;
- same model temperature/configuration;
- paired seeds when possible.

Report:

- mean;
- median;
- standard deviation;
- bootstrap confidence intervals.

---

## 19. Paired comparisons

Prefer paired tests because Treatment and Control share:

- repository;
- task;
- snapshot;
- model.

Candidate analyses:

- paired bootstrap;
- Wilcoxon signed-rank;
- McNemar for paired binary success;
- mixed-effects logistic regression for multiple repositories/tasks.

Repository/task should be treated as grouping factors.

---

## 20. Multiple comparisons

The project may test many metrics and ablations.

Pre-register or clearly label:

- primary metrics;
- secondary/exploratory metrics.

Correct or contextualize multiple hypothesis testing where appropriate.

---

## 21. Cost accounting

Every experiment should report:

- model calls;
- input tokens;
- output tokens;
- tool calls;
- wall-clock time;
- number of future-maintainer runs;
- storage consumed.

A method that adds 3% success at 20× cost may not be practically useful.

---

# Part IV — Dataset integrity and leakage

## 22. Time-split discipline

For future-oriented experiments, all data after (T_0) must be hidden from:

- prompt construction;
- scenario generator;
- retrieval index;
- examples;
- manually authored context.

This includes:

- later issues;
- later PRs;
- release notes;
- changed tests;
- docs added later.

---

## 23. Model pretraining leakage

A frontier model may have seen the repository's later history during training.

This cannot always be eliminated.

Mitigations:

- use private or newly created repositories;
- synthetic but realistic repositories;
- post-training-cutoff events;
- open-weight models with known training cutoff where possible;
- compare with repository-obscured variants;
- include contamination analysis in limitations.

---

## 24. Benchmark development leakage

Do not repeatedly tune prompts on the final evaluation set.

Maintain:

- dev repositories;
- validation repositories;
- held-out test repositories.

ChronoForge future generators should not be manually patched after seeing final outcomes.

---

# Part V — Reproducibility artifact

## 25. Minimum experiment record

Each run should eventually record:

```json
{
  "repository": "...",
  "snapshot_commit": "...",
  "task_id": "...",
  "patch_hash": "...",
  "model": "...",
  "provider": "...",
  "scaffold_version": "...",
  "prompt_version": "...",
  "seed": "...",
  "future_scenarios": [],
  "calibration_state": {},
  "tool_trace": [],
  "verification": [],
  "invariants": [],
  "metrics": {},
  "cost": {},
  "result": "..."
}
```

---

## 26. Suggested benchmark suite

A mature paper should combine:

### Existing public tasks

- SWE-bench-style issue repair;
- SWE-EVO long-horizon tasks;
- Terminal-Bench-style CLI tasks where suitable.

### Time-sliced repositories

Projects with:

- frequent dependency updates;
- clear test suites;
- multiple releases;
- meaningful API/schema evolution.

### Controlled microbenchmarks

Small repositories designed to isolate:

- wrong skill transfer;
- contamination;
- invariant preservation;
- temporal coupling;
- dependency fragility.

### Newly created holdout repositories

Reduce memorization/leakage risk.

---

# Part VI — Success criteria

## 27. Minimum evidence for Causal Genome value

Strong support would require:

- higher held-out success than success-only memory;
- lower harmful retrieval;
- stable gains across at least two model families;
- acceptable added cost;
- successful negative-memory ablations;
- contamination benefit under controlled injection.

---

## 28. Minimum evidence for ChronoForge value

Strong support would require:

- temporal metrics correlate with real later maintenance outcomes;
- correlation remains after controlling for patch size/static complexity;
- sequential inheritance outperforms independent future prompts;
- calibrated scenarios improve over uniform scenarios;
- Chrono Tournament ranks future-maintainable candidates better than current tests alone.

---

## 29. Negative-result thresholds

The project should explicitly consider abandoning or redesigning a mechanism if:

- effect sizes collapse on held-out repositories;
- gains exist only for one model;
- false Tripwire rate is high;
- Anti-Genes hurt more than they help;
- ChronoForge metrics fail to correlate with real maintenance;
- future scenario generation is too noisy;
- experiment cost is prohibitive.

---

## 30. Research milestone ladder

### Level 0 — mechanism correctness

Unit tests, CI, no false claims.

### Level 1 — controlled microbenchmarks

Demonstrate intended causal behavior.

### Level 2 — existing coding benchmarks

Show external-task usefulness.

### Level 3 — multi-repository held-out study

Generalization.

### Level 4 — retrospective temporal study

ChronoForge vs real later repository evolution.

### Level 5 — prospective live study

Freeze forecasts and patch-life reports now, wait for real project evolution, evaluate later without hindsight.

Level 5 is the strongest evidence for the core ChronoForge research idea.

Author: **LLR6**
