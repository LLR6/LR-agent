# ChronoForge — Prospective Software Evolution Laboratory

> Status: implemented research prototype in LR-Agent 1.1+  
> Research question: can today's patch be evaluated by making it survive synthetic future maintenance before it is accepted today?

## 1. Motivation

Most coding-agent evaluation is present-time evaluation:

```text
task
  ↓
patch
  ↓
tests pass?
  ↓
accept / reject
```

But software is not static.

A patch can pass every test today and still create expensive future coupling.

Examples:

- a dependency major version exposes framework-specific assumptions;
- an adjacent feature forces duplicate logic;
- a schema change reveals that data boundaries were poorly chosen;
- a module split shows that state ownership is tangled;
- a stricter runtime breaks implicit behavior;
- a configuration change reveals hard-coded assumptions.

ChronoForge asks:

> If we let this patch live through several plausible repository generations, how much future work does it create and how long does its original intent survive?

---

## 2. Core concept

A ChronoForge run begins with a Seed.

Seed can be:

1. the current workspace;
2. a completed Counterfactual Forge candidate.

The Seed is copied into independent temporal trajectories.

```text
                     Seed Patch
                  /      |      \
                 /       |       \
                ↓        ↓        ↓
          Timeline A Timeline B Timeline C
              g1        g1         g1
              ↓         ↓          ↓
              g2        g2         g2
              ↓         ↓          ↓
              g3        g3         g3
```

The crucial property is **sequential inheritance**.

Generation (g_{n+1}) starts from the actual repository produced by (g_n).

It is not a collection of independent hypothetical questions.

---

## 3. Future-maintenance scenario families

Current built-in categories:

1. `dependency_upgrade`
2. `api_deprecation`
3. `adjacent_feature`
4. `schema_migration`
5. `module_refactor`
6. `platform_runtime`
7. `performance_pressure`
8. `config_contract`

A model can tailor each category using:

- project technology stack;
- project manifests;
- original patch/task intent;
- changed paths;
- reality-calibration weights.

If model scenario generation fails, ChronoForge falls back to deterministic built-in scenario templates.

This fallback is important for reproducibility and robustness.

---

## 4. Future Maintainer Agent

Each generation launches a Coder Agent in a Shadow Workspace.

Prompt contract:

- actually modify the repository;
- do not merely discuss the future;
- preserve original patch intent unless the future event legitimately requires evolution;
- inspect before editing;
- execute local checks;
- avoid remote side effects.

The Future Maintainer is not allowed to publish packages or push code.

ChronoForge reuses LR-Agent Shadow Mode.

---

## 5. Temporal survival

After every future-maintenance generation, ChronoForge checks several layers.

### Layer A — future task execution

Did the Future Maintainer complete its task without clear tool/test/reviewer failure?

### Layer B — Seed verification replay

The original patch behavior is rechecked.

For a Forge Seed, ChronoForge carries forward the candidate's recognized verification commands.

For a current-workspace Seed, ChronoForge uses `project_inspect` recommended checks when available.

### Layer C — Invariant DNA

All active project invariants are replayed inside the future workspace.

A generation survives only if critical checks remain valid.

Conceptually:

[
Alive_{t,g}
=
FutureOK_{t,g}
land
SeedChecks_{t,g}
land
Invariants_{t,g}
]

where (t) is trajectory and (g) is generation.

---

## 6. Early temporal death

If a trajectory fails at generation 2:

```text
g1 PASS
g2 FAIL
g3 ?
g4 ?
```

ChronoForge does not pretend the patch is still alive at g3 and g4.

The trajectory stops.

This models an absorbing failure state for the current implementation.

A future extension may distinguish:

- recoverable death;
- patch rewrite;
- architecture replacement;
- migration survival.

---

## 7. Survival curve

For (N) trajectories, define:

[
S(g)
=
rac{
#{	ext{trajectories alive through generation } g}
}{
N
}
]

The report begins at:

[
S(0)=1
]

Example:

```text
g0  1.00
g1  1.00
g2  0.83
g3  0.67
g4  0.50
```

This is called the **Temporal Survival Curve**.

It should not be interpreted as the probability that the patch will literally survive four calendar years.

A repository generation is an experimental maintenance step, not a time unit.

---

## 8. Predicted repository-generation half-life

ChronoForge currently reports the first generation at which:

[
S(g) le 0.5
]

If the experiment ends while survival is still above 0.5, the half-life is right-censored:

```text
> 4 repository generations
```

The word “predicted” is used operationally, but this is still a synthetic stress-test estimate.

---

## 9. Future Maintenance Cost

A future generation has observable maintenance burden.

Current heuristic combines:

- number of Agent tool steps;
- changed-file count;
- failed tool calls;
- Reviewer failure penalty.

Conceptually:

[
C
=
w_s cdot steps
+
w_f cdot changedFiles
+
w_e cdot failures
+
reviewPenalty
]

The weights are configurable.

The metric intentionally uses observable execution effort instead of asking the model:

> “How maintainable was that?”

---

## 10. Maintenance Option Value

The research intuition is borrowed from real-options thinking, but the current metric is **not financial option pricing**.

The idea:

> A design with many cheap future adaptation paths has more software option value than a design that locks future maintainers into expensive rewrites.

Current prototype:

[
OV
=
TemporalSurvival
	imes
rac{1}{1 + rac{AverageMaintenanceCost}{20}}
]

This is a heuristic.

The denominator constant and cost weights require empirical calibration.

A publishable paper should compare several definitions instead of treating the current formula as canonical.

---

## 11. Dependency Robustness

A subset of scenario categories represents ecosystem/runtime pressure:

- dependency upgrade;
- API deprecation;
- platform/runtime evolution.

ChronoForge reports the proportion of these generations that survive.

This isolates one practical type of future fragility.

---

## 12. Patch Surface Stability

If the Seed originated from a Forge patch, ChronoForge knows which paths the original patch changed.

It records whether future generations repeatedly have to touch those same paths.

Intuition:

```text
future change
  ↓
always reopens original patch files
  ↓
possible coupling / unstable abstraction boundary
```

Patch Surface Stability is therefore a local proxy for how often future evolution re-enters the original implementation surface.

It is not equivalent to maintainability.

---

## 13. Temporal Death Modes

ChronoForge counts the future categories in which trajectories die.

Example:

```text
dependency_upgrade: 4
schema_migration:   2
module_refactor:    1
```

This makes the report actionable.

Instead of:

> “Patch B scored 0.62.”

we can say:

> “Patch B repeatedly fails under dependency-boundary changes, while surviving adjacent-feature and schema evolution.”

This is a foundation for future **Temporal Anti-Genes**.

---

## 14. Reality-Calibrated Future Model

A static future generator is easy to criticize:

> Why these futures? Why these frequencies?

ChronoForge therefore stores later real repository events.

Example:

```bash
lr-agent chrono-observe dependency_upgrade "FastAPI major-version migration"
lr-agent chrono-observe schema_migration "session schema added token_family"
```

The current calibration store counts observations by category and applies Laplace smoothing.

If category counts are (n_k), then:

[
w_k
=
rac{n_k + 1}{
sum_j(n_j + 1)
}
]

These weights drive deterministic weighted-fair future scheduling.

High-weight categories occur more often, while lower-weight categories are not permanently starved.

Important:

> Historical event frequency is not assumed to be a true probability model of the future.

This is a first calibration mechanism.

---

## 15. Why weighted-fair scheduling?

Pure random sampling creates noisy experiments.

Pure highest-weight scheduling collapses diversity.

Uniform scheduling ignores calibration.

The current deterministic weighted-fair rule balances:

- historical weight;
- repeated exposure;
- category diversity;
- reproducibility.

Conceptually each next slot favors high:

[
rac{w_k}{used_k + 1}
]

This gives calibrated categories more exposure while reducing their priority after each assignment.

---

## 16. Relationship to SWE-EVO

SWE-EVO asks:

> Can an agent execute a difficult long-horizon evolution task?

ChronoForge asks:

> Which present patch remains healthier when future agents repeatedly evolve the repository?

The unit of study differs.

```text
SWE-EVO unit:
(agent, evolution task) → task success

ChronoForge unit:
(seed patch, future trajectory set) → life history
```

---

## 17. Relationship to SWE-Future

SWE-Future is highly relevant because it forecasts future task families from repository evidence and synthesizes future-oriented tasks.

ChronoForge reuses the broad insight that repository futures can be approximated by forecast-conditioned maintenance events.

The current research difference is downstream:

```text
forecast future
      ↓
apply future to a patch-containing repository
      ↓
future Agent actually maintains it
      ↓
next future inherits resulting code
      ↓
measure patch survival/cost
```

ChronoForge is therefore not claiming invention of repository forecasting.

---

## 18. Strong research hypothesis

The strongest ChronoForge hypothesis is:

> Among patches with equivalent present-time correctness, prospective temporal survival and maintenance-cost evidence can predict future maintenance burden better than present-time test success, patch size, or static complexity alone.

This hypothesis can be wrong.

That makes it scientifically useful.

---

## 19. Chrono Tournament

Planned next step.

Suppose Counterfactual Forge produces:

```text
Patch A
Patch B
Patch C
```

All pass today's tests.

Current ChronoForge can age one candidate.

Chrono Tournament should expose all candidates to the **same scenario matrix**:

```text
             Future matrix F
          /        |        \
       Patch A   Patch B   Patch C
          ↓        ↓        ↓
      same g1   same g1   same g1
      same g2   same g2   same g2
      same g3   same g3   same g3
```

This is important because candidate comparison is otherwise confounded by different future samples.

Primary metrics:

- survival area;
- half-life;
- maintenance cost;
- invariant survival;
- death-mode profile.

The goal is not to automatically declare one universal “best patch,” but to provide future-oriented evidence for human or downstream policy decisions.

---

## 20. Future Surprise and calibration error

Current calibration only changes category frequencies.

A stronger model should store forecasts made at time (T_0), then compare them with events observed later.

Possible metrics:

- Brier score for category events;
- expected calibration error;
- top-k future family recall;
- surprise score;
- missed-event taxonomy.

Then the Future Model itself becomes an object that can improve from reality.

```text
forecast
  ↓
simulate
  ↓
real time passes
  ↓
observe real event
  ↓
score forecast
  ↓
update generator
```

---

## 21. Temporal Anti-Gene

Planned.

If a design repeatedly dies under the same future pressure:

```text
Patch pattern:
  framework-specific validation coupled to business logic

Observed future:
  API/dependency migration

Repeated result:
  high maintenance cost / death
```

ChronoForge could create:

```text
Temporal Anti-Gene:
  Avoid coupling domain validation directly to framework-specific request internals
  when the boundary is likely to experience framework/API evolution.
```

This should not be created from one synthetic run.

It would need:

- repeated temporal evidence;
- provenance;
- scenario diversity;
- held-out validation.

---

## 22. Counterfactual Software Archaeology

Research proposal, not implemented.

Backward question:

> Today's bug exists. What earlier design decision could have changed so the bug class never emerged?

Proposed workflow:

```text
real history
   ↓
bug at time T
   ↓
identify candidate historical decisions
   ↓
fork alternative histories
   ↓
replay later real changes
   ↓
observe whether bug still emerges
```

This differs from locating a bug-inducing commit.

The output could be an inferred missing invariant.

Example:

```text
not:
  "commit X introduced the null bug"

but:
  "the project lacked a lifecycle ownership invariant before refactor Y;
   adding it at that boundary prevents the later bug across replayed history"
```

This is currently a research idea only.

---

## 23. Retrospective evaluation design

ChronoForge needs retrospective validation to become credible.

Protocol:

1. choose historical repository snapshot (T_0);
2. select a real patch created near (T_0);
3. hide all post-(T_0) history from ChronoForge;
4. generate future trajectories;
5. record predicted fragility/death modes;
6. reveal real repository evolution (T_1...T_n);
7. measure whether predicted pressure categories and maintenance burden correspond to reality.

Controls:

- uniform future scenarios;
- static complexity metrics;
- patch size;
- present test coverage;
- no-future baseline;
- SWE-Future-style forecast family baseline where feasible.

---

## 24. Candidate metrics for real-world validation

For the real later history, possible targets:

- number of later edits touching original patch lines/files;
- number of bug fixes associated with the patch surface;
- revert probability;
- migration effort;
- code churn;
- number of dependent changes;
- test failures after dependency updates;
- issue/PR discussion burden;
- time-to-adapt;
- number of future commits needed to repair compatibility.

Care must be taken not to confuse popularity/activity with maintainability.

---

## 25. Threats to validity

### Synthetic future realism

A scenario can be plausible but still unrealistic for that repository.

### Agent capability confounding

A weak Future Maintainer can make a good patch appear fragile.

### Strong-agent compensation

A very strong Agent can rescue a poor design, hiding future cost.

### Test-suite incompleteness

Seed behavior may already be under-specified.

### Scenario selection bias

A researcher can accidentally choose futures favorable to one design.

### Cost-model arbitrariness

Current maintenance-cost weights are heuristic.

### Environment drift

Real dependency/runtime behavior may not be reproducible without networked version installation.

### Temporal leakage

A model may have seen future real repository events in training.

A serious benchmark needs snapshot discipline and leakage analysis.

---

## 26. Reproducibility requirements

Every ChronoForge report should eventually preserve:

- Seed repository commit;
- Seed patch diff/hash;
- model ID;
- model/provider version where available;
- scenario pool;
- scenario schedule;
- calibration state;
- prompts;
- tool traces;
- generated future diffs;
- verification outputs;
- invariant outputs;
- cost weights;
- runtime/environment metadata.

Without these, a life report is not scientifically auditable.

---

## 27. End goal

ChronoForge is aiming at a different software-engineering workflow:

```text
before:
  write patch
  → tests pass
  → merge
  → discover maintainability years later

target:
  write competing patches
  → current verification
  → prospective future aging
  → inspect survival/cost/death modes
  → merge with more evidence
  → reality later calibrates the simulator
```

The ambition is not to predict the future perfectly.

It is to make **future maintainability partially testable today**.

Author: **LLR6**
