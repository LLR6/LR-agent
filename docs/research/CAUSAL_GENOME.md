# Causal Genome Engine

> Status: implemented research prototype in LR-Agent 1.0+  
> Purpose: replace success-only skill memory with falsifiable, provenance-aware strategy hypotheses.

## 1. Problem

A common self-evolving-agent pattern is:

```text
successful trajectory
      ↓
summarize procedure
      ↓
store as reusable skill
      ↓
retrieve on similar future task
```

This pipeline has a serious epistemic weakness:

> A procedure that happened to appear in a successful run may not be the reason the run succeeded.

The success may instead come from:

- a lucky tool order;
- a strong base model compensating for a bad strategy;
- repository-specific details;
- unrelated context;
- a test suite that failed to expose the weakness;
- another step in the trajectory;
- stochastic variation.

If such a procedure is promoted into long-term memory without causal evidence, the agent can turn correlation into policy.

Causal Genome treats every reusable strategy as a **hypothesis under continuing test**.

---

## 2. Gene lifecycle

A Strategy Gene is not immediately trusted.

```text
candidate
   ↓
QUARANTINE
   ↓
repeated counterfactual experiments
   ↓
┌──────────────┬───────────────┬────────────────┐
│ positive     │ inconclusive  │ harmful        │
│ evidence     │ evidence      │ evidence       │
└──────┬───────┴───────┬───────┴────────┬───────┘
       │               │                │
       ↓               ↓                ↓
    ACTIVE         QUARANTINE        CONTESTED
                                        │
                                        ↓
                                    Anti-Gene
```

Additional terminal states:

- `retired`: intentionally no longer used;
- `contaminated`: provenance or ancestry is no longer trusted.

A Forge winner imported into the Genome begins in `quarantine`.

A single successful Forge run is provenance, not causal evidence.

---

## 3. Strategy Gene schema

Conceptually a Gene contains:

```json
{
  "id": "gene-id",
  "name": "Focused async fixture repair",
  "kind": "strategy",
  "status": "quarantine",
  "instruction": "Inspect event-loop ownership before changing fixtures.",
  "applicability": [
    "pytest-asyncio",
    "fixture lifecycle conflicts"
  ],
  "exclusions": [
    "trio backend",
    "custom anyio backend"
  ],
  "verifier": [
    {
      "argv": ["pytest", "tests/test_async.py"],
      "cwd": "."
    }
  ],
  "provenance": {
    "source": "forge_winner",
    "tournament_id": "...",
    "candidate_id": "..."
  },
  "confidence": 0.0,
  "positive_count": 0,
  "negative_count": 0,
  "neutral_count": 0,
  "average_effect": 0.0
}
```

This is deliberately richer than a Markdown “tip.”

---

## 4. Treatment vs Control ablation

The central experiment is not:

> “Can the Gene solve this task?”

It is:

> “Does giving the Gene to the Agent improve observable outcome relative to a competent Agent that solves the same task independently?”

For a task (T) and Gene (G):

```text
same project baseline
same task T
       │
 ┌─────┴─────┐
 ↓           ↓
Treatment   Control
+ Gene G    no Gene G
 ↓           ↓
real tools  real tools
real edits  real edits
real tests  real tests
 ↓           ↓
score_T     score_C
```

The observed marginal effect is:

[
Delta_G(T) = S_{	ext{treatment}} - S_{	ext{control}}
]

where (S) is LR-Agent's executable evidence score.

This is an engineering counterfactual heuristic, not formal causal identification.

Important confounders remain:

- model sampling variability;
- path dependence;
- tool-order differences;
- hidden environment state;
- benchmark leakage;
- test incompleteness.

Therefore LR-Agent requires repeated trials before activation.

---

## 5. Repeated evidence and activation

Default activation thresholds are configurable.

Current defaults:

```env
LR_AGENT_GENE_POSITIVE_LIFT_THRESHOLD=8
LR_AGENT_GENE_NEGATIVE_LIFT_THRESHOLD=-8
LR_AGENT_GENE_ACTIVATION_MIN_EXPERIMENTS=3
LR_AGENT_GENE_ACTIVATION_MIN_POSITIVE_RATE=0.67
LR_AGENT_GENE_ACTIVATION_MIN_AVERAGE_LIFT=8
```

A Gene becomes active only when it has enough accumulated support.

The intended semantics are:

```text
one good trial
≠
trusted reusable strategy
```

This protects the runtime context from one-shot luck.

---

## 6. Active falsification

A normal ablation asks whether a Gene helps.

Falsification mode asks a different question:

> “Can we find a realistic case where this Gene's assumptions fail?”

The Treatment arm receives explicit instructions to:

- inspect preconditions;
- test exclusions;
- search for edge cases;
- refuse to force the Gene when it does not apply;
- produce tool evidence for non-applicability.

This design is inspired by a Popper-style attitude toward knowledge:

> A reusable strategy should remain exposed to evidence that can invalidate or narrow it.

A Gene can therefore move from active confidence back toward contested status when new negative evidence appears.

---

## 7. Anti-Gene

Failure is preserved as a reusable negative artifact.

Example:

```text
Parent Gene:
  "Refactor the whole module before fixing local parser defects."

Task:
  "Fix a one-line parser regression."

Treatment score: 34
Control score:   71
Effect:          -37
```

Instead of deleting the parent history, LR-Agent can create:

```text
Anti-Gene:
  Avoid blindly applying the broad-refactor strategy to
  localized parser regressions. Re-check scope and root cause first.
```

An Anti-Gene is:

- context-specific;
- supported by negative experimental evidence;
- retrievable as cautionary context;
- not a universal ban.

This matters because the most valuable lesson from a failed strategy may be its boundary.

---

## 8. Proof-Carrying Gene

A Gene can carry executable success criteria.

Example:

```json
[
  {"argv":["pytest","tests/test_auth.py"],"cwd":"."},
  {"argv":["python","scripts/check_refresh_rotation.py"],"cwd":"."}
]
```

During a treatment/control experiment:

1. each candidate performs its normal task;
2. the candidate's own tests are recorded;
3. LR-Agent executes the same Gene verifier in each candidate workspace;
4. a candidate that fails the Gene verifier receives a score penalty.

This reduces a failure mode where the model claims the strategy worked while violating the very behavior the Gene is supposed to protect.

A verifier still does not prove correctness outside its assertions.

---

## 9. Genealogy

Strategies can derive from earlier strategies.

```text
async-debug-v2
   ├── fixture-isolation-v3
   │      └── loop-lifecycle-v1
   └── anyio-boundary-v2
```

The Genome stores parent/child edges.

Why?

Because learned strategy systems are not independent collections of facts.

A derived strategy may inherit:

- assumptions;
- terminology;
- unsafe shortcuts;
- poisoned provenance;
- hidden blind spots.

Genealogy makes those dependencies inspectable.

---

## 10. Contamination propagation

If a source Gene is later found untrustworthy:

```bash
lr-agent genome-contaminate <gene_id> "source trajectory was poisoned"
```

LR-Agent can:

- mark the source contaminated;
- traverse descendants;
- mark descendants contaminated;
- reduce confidence;
- preserve the historical graph.

It does not silently rewrite history.

This mechanism is a direct response to the broader research problem that bad learned skills can propagate into later learned artifacts.

A contaminated descendant is not mathematically proven wrong. Its trust is reduced because its provenance is compromised.

---

## 11. Runtime retrieval

Normal Coder / Research runs retrieve only active Genes.

Quarantined Genes are excluded from normal runtime injection.

The Agent receives structured context including:

- name;
- kind;
- instruction;
- applicability;
- exclusions;
- confidence;
- average experimental effect;
- positive/negative evidence counts.

The system prompt explicitly says:

- Genes are hypotheses, not authorities;
- applicability must be checked;
- Anti-Genes are negative evidence, not hard rules.

This is meant to prevent memory from becoming an unchallengeable second system prompt.

---

## 12. Invariant DNA

Strategy Genes answer:

> “What tends to work?”

Invariant DNA answers:

> “What must remain true?”

Example:

```text
Invariant:
  Rotating a refresh token invalidates the previous refresh token.

Executable check:
  pytest tests/test_refresh_rotation.py
```

Invariant DNA is intentionally separate from strategy memory.

A future agent may choose a completely different strategy, but the invariant should survive.

During Forge promotion:

```text
candidate
  ↓
temporary real-workspace application
  ↓
candidate verification
  ↓
Invariant DNA
  ↓
PASS → proof bundle
FAIL → automatic restore
```

ChronoForge also replays active invariants inside future generations.

---

## 13. Epistemic Tripwire

The Tripwire addresses a different layer: failure during a single run.

Current observable triggers include:

- repeated equivalent command/tool failures;
- repeated direct mutations of the same path without a recognized successful verification step.

When triggered, the runtime emits an event and injects a corrective constraint:

```text
stop mechanical repetition
→ re-read relevant state
→ challenge current hypothesis
→ prefer a discriminating diagnostic
→ switch strategy if evidence conflicts
```

This is not hidden-chain-of-thought monitoring.

It uses only observable execution behavior.

---

## 14. Confidence semantics

Current confidence is deliberately heuristic.

It is influenced by:

- positive evidence count;
- negative evidence count;
- neutral evidence;
- number of experiments;
- average observed effect.

Future versions should separate:

- epistemic confidence;
- transfer confidence;
- freshness;
- provenance trust;
- verifier coverage;
- repository-specificity.

A single scalar is convenient but insufficient for mature research.

---

## 15. Research hypotheses

### CG-H1: Marginal evidence improves skill quality

Genes admitted through repeated treatment/control evidence will outperform success-only skills on held-out tasks.

### CG-H2: Anti-Genes reduce imitation traps

Explicit negative memories will reduce wrong high-confidence reuse on superficially similar but structurally different tasks.

### CG-H3: Genealogy limits contamination damage

Provenance-aware distrust propagation will reduce reuse of inherited defective strategies compared with deleting only the source.

### CG-H4: Proof-Carrying Genes improve trust calibration

Executable Gene verifiers will reduce false-positive strategy success labels.

### CG-H5: Tripwires reduce lock-in

Early observable intervention will reduce repeated tool failures, wasted mutation steps and unrecoverable trajectories.

---

## 16. Required experiments

A publishable evaluation should include:

- success-only memory baseline;
- BASM-style boundary memory baseline;
- quarantine without ablation;
- ablation without falsification;
- ablation + falsification;
- anti-gene ablation;
- genealogy/contamination ablation;
- proof-carrying verifier ablation;
- tripwire ablation.

Metrics:

- held-out task success;
- wrong-tool confidence / wrong-action rate;
- tool steps;
- failed tool calls;
- changed-file scope;
- regression rate;
- strategy transfer accuracy;
- harmful retrieval rate;
- contamination recovery;
- token/model cost.

Repeated trials and confidence intervals are required because model stochasticity is central to the mechanism.

---

## 17. Known limitations

- Treatment and control executions are not perfectly matched randomized trials.
- Evidence scores contain design choices and weights.
- A stronger model can compensate for a harmful Gene, obscuring effect.
- A weak test suite can admit a bad Gene.
- Anti-Genes may overfit to a narrow counterexample.
- Gene retrieval can itself change Agent behavior independent of the Gene's content.
- Genealogy records derivation but cannot automatically prove semantic inheritance.
- Contamination propagation may be conservative.
- The current Tripwire only covers simple observable patterns.

---

## 18. Long-term research direction

The deeper goal is not “Agent memory.”

It is a **scientific memory layer** for software agents:

```text
claim
→ provenance
→ experiment
→ counterexample
→ boundary
→ verifier
→ genealogy
→ continued falsification
```

The Agent should remember not only what worked, but:

- why we think it worked;
- where it failed;
- how strong the evidence is;
- what would make us stop believing it.

Author: **LLR6**
