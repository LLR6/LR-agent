# Bibliography and Research Links

> Snapshot: 2026-09-27  
> This is a focused working bibliography, not an exhaustive literature review.  
> Most 2026 entries are arXiv preprints and may not yet have completed peer review.

## Self-evolving coding agents

### Self-Evolving Coding Agents

Hao Zhou, Haichuan Hu, Ye Shang, Quanjun Zhang. 2026.

Systematic survey of self-evolving coding agents, covering evolution of memory, skills, tools, harnesses/workflows, collaboration structures and models.

- arXiv: https://arxiv.org/abs/2608.03392
- Relevance: broad field map; prevents overclaiming basic self-evolution as novel.

### Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents

Jenny Zhang, Shengran Hu, Cong Lu, Robert Lange, Jeff Clune. 2025.

Maintains an archive/tree of coding-agent variants and empirically evaluates self-modifications.

- arXiv: https://arxiv.org/abs/2505.22954
- Relevance: closest warning against claiming novelty for “mutate Agent, benchmark descendants, keep winners.”

---

## Skill memory and boundaries

### When Not to Imitate: Boundary-Aware Skill Memory for Reliable Tool-Use LLM Agents

Zihan Lin, Zhenyu Chen, Jiawen Wei, Xiaohan Wang, Jie Cao, Jiajun Chai, Wei Lin, Guojun Yin, Ran He. 2026.

Studies the “Skill Imitation Trap” and introduces applicability conditions, risk cues, avoidance rules and recovery notes.

- arXiv: https://arxiv.org/abs/2608.22339
- Relevance: direct related work for Causal Genome applicability/exclusions and Anti-Gene motivation.

---

## Skill poisoning and contamination

### SkillJack: Persistent Skill Backdoors in Self-Evolving Agents

Zonghao Ying, Xiangfan Wu, Huiyu Wu, Xing Zheng, Huangsheng Cheng, Xiaorong Shi, Jing Guo. 2026.

Studies how poisoned experiences can be transformed into persistent reusable skills and remain harmful after source removal.

- arXiv: https://arxiv.org/abs/2608.03509
- Code/project link reported by paper: https://github.com/Tencent/AI-Infra-Guard/tree/main/Research/SkillJack
- Relevance: provenance, quarantine, persistent contamination.

### When Self-Evolution Backfires: Pre-Commit Gating against Skill Contamination in LLM Agents

Linfang Shang, Ming Xu, Yiding Sun, Tianle Xia, Lingxiang Hu, Lan Xu, Ning Zheng. 2026.

Studies capability contamination and cross-round contamination chains; proposes verifier-based pre-commit gating.

- arXiv: https://arxiv.org/abs/2608.05810
- Relevance: skill admission, contamination propagation, limits of post-hoc deletion.

---

## Coding-agent failure trajectories

### Failure as a Process: An Anatomy of CLI Coding Agent Trajectories

Xiangxin Zhao, Han Li, Shuaiting Li, Tianyi Zhao, Earl T. Barr, Federica Sarro, He Ye. 2026.

Large empirical study of CLI coding-agent failure trajectories emphasizing onset, lock-in and observability of failure.

- arXiv: https://arxiv.org/abs/2607.09510
- Relevance: Epistemic Tripwire motivation; early failures and recovery windows.

---

## Long-horizon software evolution

### SWE-EVO: Benchmarking Coding Agents in Long-Horizon Software Evolution Scenarios

Minh V. T. Thai, Tue Le, Dung Nguyen Manh, Huy Phan Nhat, Nghi D. Q. Bui. 2025/2026.

Benchmark for long-horizon, multi-step software evolution across mature Python projects.

- arXiv: https://arxiv.org/abs/2512.18470
- GitHub organization: https://github.com/SWE-EVO
- Relevance: demonstrates that long-horizon evolution is already a benchmarked research problem and motivates ChronoForge evaluation.

---

## Forecast-oriented software engineering

### SWE-Future: Forecast-Conditioned Data Synthesis for Future-Oriented Software Engineering Agents

Qiao Zhao, JianYing Qu, Jun Zhang, Yehua Yang, Hanwen Du, Zhongkai Sun. 2026.

Forecasts future repository task families from pre-snapshot evidence, validates forecasts against later PRs and synthesizes future-oriented coding tasks.

- arXiv: https://arxiv.org/abs/2606.18733
- Relevance: closest work to Future Model / reality calibration; ChronoForge must clearly distinguish forecasting future work from aging a present patch through inherited future repository trajectories.

---

## Temporal repository reasoning

### AgenticSZZ / Beyond Blame: Rethinking SZZ with Knowledge Graph Search

Yu Shi, Hao Li, Bram Adams, Ahmed E. Hassan. 2026.

Uses Temporal Knowledge Graphs and an LLM agent to search for bug-inducing commits beyond traditional blame candidates.

- arXiv: https://arxiv.org/abs/2602.02934
- Relevance: temporal/causal reasoning over repository history; important boundary for Counterfactual Software Archaeology.

---

# Additional bodies of literature to review before publication

The following areas need deeper systematic review before strong novelty claims.

## Software architecture and real options

Search topics:

- software architecture option value;
- real options in software engineering;
- architectural flexibility;
- changeability metrics;
- economic models of technical debt.

Reason:

ChronoForge's “Maintenance Option Value” has conceptual overlap with established option-value thinking even though its operational metric is different.

## Software aging and decay

Search topics:

- software aging;
- code decay;
- architecture erosion;
- design erosion;
- software half-life;
- maintainability degradation.

Reason:

Do not claim invention of “software aging” or “software half-life” as broad ideas.

## Counterfactual causal inference in software engineering

Search topics:

- causal inference software engineering;
- counterfactual defect analysis;
- causal program repair;
- causal debugging;
- alternate histories software evolution.

Reason:

Counterfactual Software Archaeology needs a much deeper literature review.

## Mutation testing and metamorphic testing

Reason:

Future stress generation and invariant validation may overlap with principles from mutation testing, fuzzing and metamorphic testing.

## Proof-carrying code and executable specifications

Reason:

“Proof-Carrying Gene” is project terminology, not a claim to invent proof-carrying artifacts.

## Process mining and software repository mining

Reason:

Reality-calibrated Future Models may overlap with change prediction, process mining and repository-evolution forecasting beyond SWE-Future.

---

# Citation policy for LR-Agent docs

When discussing related work:

- cite the original paper when possible;
- distinguish paper claims from LR-Agent conclusions;
- do not reproduce benchmark numbers without checking the current paper version;
- mark preprints as preprints;
- avoid “first ever” wording unless the cited paper itself makes a narrowly defined claim and LR-Agent is merely reporting it;
- update this file when a paper changes title/version.

---

# Search log summary

Research searches used combinations of:

```text
self-evolving coding agents
coding agent skill memory
boundary-aware skill memory
skill contamination agent
persistent skill backdoor
coding agent failure trajectories
long-horizon software evolution benchmark
future-oriented software engineering agents
forecast repository future tasks
temporal knowledge graph software evolution
bug-inducing commit agent
```

The strongest current LR-Agent novelty hypothesis remains the **end-to-end combination**, not ownership of each individual ingredient.

Author: **LLR6**
