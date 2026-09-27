# State of the Art and Related Work

> Literature snapshot: 2026-09-27  
> Scope: self-evolving coding agents, agent memory/skills, failure trajectories, long-horizon software evolution, future-oriented software-engineering tasks, temporal repository reasoning.

This document records the public work we found that is closest to LR-Agent's research direction. It is intentionally written as a **boundary map**, not as a marketing comparison.

## 1. Self-evolving coding agents

### Self-Evolving Coding Agents (2026)

Zhou et al. survey self-evolving coding agents and organize the field by what evolves: memory, skills, tools, harnesses/workflows, collaboration structures and models.

Relevant takeaway for LR-Agent:

- “self-evolution” is already a recognized research area;
- simply adding a memory store, skill library or evolving scaffold is not a sufficient novelty claim;
- executable feedback and coding trajectories are already central to the field;
- benchmark overfitting, feedback reliability, safety, maintainability and generalization remain open problems.

LR-Agent therefore should not describe itself as novel merely because it “learns from past coding tasks.”

Reference: arXiv:2608.03392.

### Darwin Gödel Machine (2025)

Darwin Gödel Machine (DGM) iteratively modifies coding agents, empirically evaluates descendants and maintains an archive/tree of diverse agents.

The paper reports an increase from 20% to 50% on SWE-bench and from 14.2% to 30.7% on Polyglot in its experimental setup.

Boundary relative to LR-Agent:

- DGM evolves the **agent itself** and searches an open-ended archive of agent variants.
- LR-Agent's Causal Genome instead experiments on **reusable strategy hypotheses** attached to software tasks.
- A naive “keep winners, mutate them, benchmark again” design would overlap strongly with DGM and should not be presented as a distinct contribution.
- LR-Agent's differentiating hypothesis is that strategy admission should require counterfactual marginal evidence, explicit negative evidence, provenance and continued falsifiability.

Reference: arXiv:2505.22954.

---

## 2. Skill memory and boundary-aware reuse

### Boundary-Aware Skill Memory (BASM, 2026)

“When Not to Imitate” directly challenges success-only skill memory.

It reports that on tasks resembling prior successes but requiring different tools, procedure skills can increase confidence in the wrong tool call; the paper reports a 47% increase in wrong-tool margin over a memory-free baseline in its probe analysis.

BASM adds:

- applicability conditions;
- risk cues;
- avoidance rules;
- recovery notes.

This is highly relevant to LR-Agent.

Boundary:

- LR-Agent must not claim that “skills need boundaries” is novel.
- Anti-Genes, applicability and exclusions should be described as building on the same broad problem class.
- LR-Agent's additional hypothesis is that boundaries can be learned and revised from explicit treatment-vs-control experiments rather than only distilled from trajectories.

Reference: arXiv:2608.22339.

---

## 3. Skill poisoning and contamination

### SkillJack (2026)

SkillJack studies attacks on the experience-to-skill pipeline in self-evolving agents.

The key result for our design is conceptual: a transient poisoned experience can be transformed into a durable skill artifact, and deleting the original source record does not necessarily eliminate the behavior.

The paper reports persistent skill-mediated attacks after source-record deletion and motivates provenance-aware protection across the skill lifecycle.

Implications for LR-Agent:

- never treat a distilled skill as detached from its origin;
- preserve provenance edges;
- avoid “delete source = delete effect” assumptions;
- quarantine new skills before runtime use;
- support trust reduction through descendants.

Reference: arXiv:2608.03509.

### When Self-Evolution Backfires (2026)

This work studies capability contamination in growing skill pools and argues that defective skills can become reference material for later skills, producing cross-round contamination chains.

It proposes pre-commit gating and a progressive trust hierarchy.

Boundary:

- pre-admission gating of learned skills is already researched;
- “we verify skills before adding them” is not by itself a novel claim;
- LR-Agent's distinct research question is whether **counterfactual marginal contribution**, anti-genes and genealogy-aware trust propagation improve skill admission beyond static or critic-only gating.

Reference: arXiv:2608.05810.

---

## 4. Coding-agent failure as a temporal process

### Failure as a Process (2026)

Zhao et al. analyze CLI coding-agent trajectories as processes rather than only final pass/fail outcomes.

The study reports that many failures begin early, are driven by epistemic errors and can remain hidden until recovery becomes difficult.

This is the closest public motivation for LR-Agent's Epistemic Tripwire.

Boundary:

- early failure detection is not novel;
- “failures start early” is not an LR-Agent discovery;
- LR-Agent's research contribution, if validated, would be an **operational runtime intervention** based on observable execution patterns such as repeated failures and repeated unverified mutations.

Reference: arXiv:2607.09510.

---

## 5. Long-horizon software evolution

### SWE-EVO (2025/2026)

SWE-EVO evaluates coding agents on long-horizon software evolution rather than isolated issue repair.

The benchmark contains multi-step tasks drawn from mature open-source projects. The arXiv abstract reports:

- 48 evolution tasks;
- changes spanning an average of 21 files;
- test suites averaging 874 tests per task;
- a large capability gap relative to single-issue SWE-bench-style tasks.

Why it matters:

ChronoForge should not claim “software evolution has never been benchmarked.”

The distinction is:

- SWE-EVO asks an agent to **perform a known long-horizon evolution task**.
- ChronoForge asks whether a **candidate patch created today** remains cheap/correct across multiple synthetic future maintenance trajectories before we accept it today.

Reference: arXiv:2512.18470.

---

## 6. Forecast-conditioned future software tasks

### SWE-Future (2026)

SWE-Future uses repository evidence available at a forecast snapshot to predict families of future repository work, validates those forecasts against later PRs, and uses forecast families to synthesize future-oriented coding tasks.

This is extremely close to one half of ChronoForge.

Boundary:

- forecasting future task families from repository history is not novel;
- future-oriented synthetic coding tasks are not novel;
- using later real work to validate forecasts is not novel.

ChronoForge's open research distinction is the **unit of evaluation**:

```text
SWE-Future:
repository at T0
    ↓
forecast future task families
    ↓
synthesize future tasks
    ↓
evaluate agents on those tasks

ChronoForge:
candidate patch P at T0
    ↓
generate/calibrate future maintenance events
    ↓
sequentially evolve copies containing P
    ↓
measure whether P survives and how expensive it is to maintain
    ↓
use future-life evidence in today's patch decision
```

The novelty hypothesis is not “we forecast future work,” but “we prospectively age a present patch through inherited future repository trajectories and use that life history as patch-selection evidence.”

Reference: arXiv:2606.18733.

---

## 7. Temporal reasoning over repository history

### AgenticSZZ / Beyond Blame (2026)

AgenticSZZ builds a Temporal Knowledge Graph over commit history and uses an LLM agent to search for bug-inducing commits beyond traditional blame candidates.

Boundary:

- temporal repository reasoning already exists;
- causal language around commit history is not unique to LR-Agent;
- using repository history to locate past bug causes is a different question from ChronoForge's forward simulation.

This distinction motivates a future LR-Agent idea called **Counterfactual Software Archaeology**:

> Given a bug observed today, replay alternate historical branches to identify the earliest design decision or invariant whose presence would have prevented the bug class from emerging.

That idea is not implemented and should currently be described as a research proposal.

Reference: arXiv:2602.02934.

---

## 8. Closest-neighbor comparison

| Research/system | Evolves agent | Learns reusable skills | Explicit skill boundaries | Skill provenance/contamination | Counterfactual treatment-control | Active falsification | Long-horizon repo evolution | Forecasts future work | Ages today's patch through synthetic future | Reality-calibrates future generator |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DGM | yes | indirectly | not primary | archive lineage | empirical agent comparison | open-ended search | no | no | no | no |
| BASM | no | yes | yes | not primary | no | no | no | no | no | no |
| SkillJack | no | studies skill pipeline | no | yes, security focus | no | attack evaluation | no | no | no | no |
| VaG / contamination work | no | yes | gating | yes | marginal selection | critic-based | no | no | no | no |
| Failure as a Process | no | no | no | no | no | no | trajectory analysis | no | no | no |
| SWE-EVO | no | no | no | no | no | no | yes | no | no | no |
| SWE-Future | no | no | no | no | no | no | task synthesis | yes | no | yes, forecast validation |
| AgenticSZZ | no | no | no | no | causal/temporal search | no | history analysis | no | no | no |
| LR-Agent Causal Genome | no | yes | yes | yes | yes | yes | indirectly | no | no | no |
| LR-Agent ChronoForge | no | no | n/a | n/a | patch comparison planned | future stress | yes, simulated | scenario generation | **yes** | **yes** |

This table is a research map, not a claim that the systems were designed for identical goals.

---

## 9. What LR-Agent must not overclaim

The following statements are **not** defensible novelty claims:

- “We invented self-evolving coding agents.”
- “We are the first to store reusable skills.”
- “We are the first to give skills applicability boundaries.”
- “We are the first to validate skills before admission.”
- “We are the first to analyze early coding-agent failure.”
- “We are the first to benchmark long-horizon software evolution.”
- “We are the first to forecast future repository work.”
- “We are the first to use temporal repository graphs.”
- “We are the first multi-agent coding system.”

The research value must instead come from a more precise combination and measurable hypothesis.

---

## 10. Current strongest novelty hypotheses

As of the literature search captured here, we did not find a public end-to-end coding-agent runtime that combines all of the following:

### Causal Genome chain

```text
strategy candidate
→ quarantine
→ treatment/control shadow worlds
→ repeated marginal evidence
→ active falsification
→ negative anti-gene
→ genealogy / contamination propagation
→ proof-carrying executable verifier
→ active-only runtime retrieval
```

### ChronoForge chain

```text
today's candidate patch
→ copied future repository trajectories
→ generation N inherits N-1's actual code
→ future-maintainer agents make real edits
→ original patch checks replay every generation
→ Invariant DNA replay every generation
→ temporal death / survival curve
→ maintenance-cost / option-value report
→ later real project events recalibrate future scenarios
```

The phrase **“did not find”** is deliberate. This remains a search-based novelty hypothesis, not proof that no unpublished, proprietary or differently named system exists.

---

## 11. Search methodology and limitations

Our search included combinations of terms around:

- self-evolving coding agents;
- agent skill memory;
- boundary-aware skill memory;
- skill poisoning / contamination;
- coding-agent failure trajectories;
- long-horizon software evolution;
- future-oriented coding benchmarks;
- repository forecasting;
- temporal knowledge graphs;
- bug-inducing commit search.

Primary references were preferred when discoverable, especially arXiv pages and project repositories.

Limitations:

- arXiv/preprint literature changes quickly;
- titles and versions can change;
- proprietary systems may not be public;
- patents and non-English publications were not exhaustively searched;
- “no matching result found” is not equivalent to universal novelty.

This file should be updated before any paper submission, public novelty statement or patent-related claim.
