# Community Launch Kit

> Ready-to-post copy for LR-Agent 1.1.0.  
> Keep screenshots, benchmark numbers and performance claims real. Do not fabricate stars, users, benchmark wins or “first ever” claims.

## One-line positioning

### English

**A coding agent that lets patches live through simulated future repository generations before you merge them.**

### 中文

**一个会让代码补丁先“活过未来”，再决定要不要合并的 Coding Agent。**

## Short description

### English

LR-Agent is a research-oriented coding agent with Counterfactual Forge, Causal Genome and ChronoForge. It can generate competing real patches in isolated workspaces, test reusable strategies through falsifiable treatment/control experiments, and age a current patch through sequential future repository evolution.

### 中文

LR-Agent 是一个研究型 Coding Agent：它会在隔离工作区生成多个真实补丁，用 Treatment vs Control 证伪策略记忆，还能把今天的 Patch 放进连续的“未来仓库”里经历依赖升级、API 变化、Schema 迁移和相邻功能，再输出生存曲线和维护成本。

---

# Show HN draft

## Title

`Show HN: LR-Agent – a coding agent that ages patches through simulated future repo generations`

## Body

Most coding agents stop when today's tests pass.

I wanted to explore a different question:

**If two patches are both correct today, will they still be equally easy to maintain after future dependency upgrades, API changes, schema migrations and adjacent features?**

So I built LR-Agent.

The part I'm most interested in is **ChronoForge**:

- take the current workspace or a candidate patch;
- copy it into several isolated future repository timelines;
- generation N inherits the actual code produced by generation N-1;
- future-maintainer agents make real edits and run real checks;
- after every generation, LR-Agent replays the original patch checks and project invariants;
- the result is a temporal survival curve, maintenance-cost estimate and failure/death-mode report.

There are two other experiments in the repo:

- **Counterfactual Forge** — multiple isolated coding strategies compete on the same task with executable evidence.
- **Causal Genome** — a successful trajectory does not automatically become “memory”; strategies enter quarantine and can be tested via treatment/control ablation, falsification and negative Anti-Genes.

I am deliberately **not** claiming this predicts the real future. The current goal is to make future-maintainability stress partially testable today and then validate whether those signals correlate with later real repository history.

The repo includes implementation, CI tests, a 5-minute demo, related-work notes, novelty boundaries and an experimental protocol.

GitHub:
https://github.com/LLR6/LR-agent

I'd especially value counterexamples: cases where ChronoForge produces a misleading life report or where Causal Genome learns the wrong lesson.

---

# Reddit / r/LocalLLaMA draft

## Title

`I built an open-source coding agent that lets a patch “live through the future” before you merge it`

## Body

I kept running into the same problem with coding agents:

two patches can both pass today's tests, but one may be much more painful to maintain later.

So I built an experiment called **ChronoForge** inside LR-Agent.

Instead of asking an LLM “is this maintainable?”, it copies a candidate patch into multiple shadow repositories and lets future coding agents sequentially evolve them through things like:

- dependency upgrades
- API deprecations
- adjacent features
- schema migrations
- module refactors
- runtime/platform changes

The important part is that these are **sequential**:

```text
seed → future g1 → future g2 → future g3
```

g2 inherits the real code written in g1.

After every generation LR-Agent replays the original behavior checks and any project invariants. A timeline can “die” when the original behavior no longer survives.

The report includes:

- temporal survival curve
- future maintenance cost
- maintenance option value
- invariant survival
- dependency robustness
- repository-generation half-life
- temporal death modes

I also have a second experiment called **Causal Genome**: successful Agent trajectories do not automatically become reusable skills. Candidate strategies stay in quarantine until treatment/control experiments and falsification provide evidence that the strategy actually helps.

This is still a research prototype, not a claim that synthetic futures are real predictions.

Repo + demo:
https://github.com/LLR6/LR-agent

I'd love to see adversarial examples or repos where the metric is obviously wrong.

---

# V2EX draft

## 标题

`[开源] 我做了一个会让代码 Patch 先“活过未来”再决定是否合并的 Coding Agent`

## 正文

最近一直在折腾 Coding Agent，但我越来越觉得一个问题没解决：

**“今天测试全过”和“以后好维护”不是一回事。**

所以我做了 LR-Agent，里面最想实验的功能叫 **ChronoForge**。

它不是问模型“你觉得这段代码可维护吗”，而是直接：

```text
今天的 Patch
    ↓
复制成多条 Shadow Repository
    ↓
Future g1：依赖升级
    ↓
Future g2：API / 配置变化
    ↓
Future g3：相邻功能加入
    ↓
Future g4：Schema / 模块演化
```

而且 g2 是基于 g1 真正改完的代码继续演化，不是几条互相独立的 Prompt。

每一代都会重新跑原 Patch 的行为验证和项目 Invariant。最后给出：

- Temporal Survival Curve
- Future Maintenance Cost
- Maintenance Option Value
- Invariant Survival
- Dependency Robustness
- repo-generation Half-Life
- 最常见的 Future Death Mode

项目里还有：

**Counterfactual Forge**  
同一个 Bug 开多个隔离 Agent，用不同策略真实改、真实测，再比较证据。

**Causal Genome**  
Agent 不能因为某次成功就把策略记成长久经验。候选策略先 quarantine，再做 Treatment vs Control、主动证伪、Anti-Gene、血缘污染传播。

研究相关的东西也全部公开了：相关工作、Novelty Claims、Benchmark 方案、实验设计、哪些地方还只是 hypothesis。

GitHub：
https://github.com/LLR6/LR-agent

目前最需要的不是“夸好用”，而是有人拿真实项目来打脸它：如果 ChronoForge 的未来寿命报告很离谱，欢迎直接开 Counterexample Issue。

---

# 知乎 / 掘金长文标题

**我做了一个会把代码扔进“未来”测试的 AI Agent：今天能跑，不代表以后好维护**

## 开头

现在 Coding Agent 越来越擅长解决“今天的问题”：

- 找 Bug；
- 改代码；
- 跑测试；
- 开 PR。

但有一个问题一直让我很在意：

> 两个方案今天都通过测试，哪个方案更值得合并？

传统答案通常是 code review、复杂度、经验判断。

我想试一个更奇怪的方向：

> **让这两个 Patch 先分别经历几代“未来的软件维护”，再看看谁更容易活下来。**

这就是 ChronoForge。

后续文章结构：

1. 为什么当前测试无法回答未来维护问题
2. Counterfactual Forge 怎么生成真实候选
3. ChronoForge 为什么必须“连续继承”而不是独立 Prompt
4. Temporal Survival Curve 是什么
5. Maintenance Option Value 为什么只是 heuristic
6. Reality Calibration 怎么避免未来场景永远拍脑袋
7. 哪些地方很可能是错的
8. 如何设计 retrospective benchmark 验证
9. GitHub / Demo

---

# Bilibili / YouTube video outline

## Title

### 中文

**两个 AI 方案都通过测试，我让它们分别活了 4 代“未来”**

### English

**Two AI patches pass the same tests. Which one survives the future?**

## 30–60 second hook

```text
0–4s
两个补丁今天都 PASS。

4–9s
“那哪个更好？”

9–15s
把 Patch A / B 放进隔离未来仓库。

15–25s
g1 dependency upgrade
g2 API deprecation
g3 schema migration
g4 adjacent feature

25–34s
每一代由新 Agent 真改代码、真跑测试。

34–42s
Patch A dies at g2.
Patch B survives to g4.

42–50s
显示 Survival Curve / maintenance cost。

50–60s
“这不是未来预测。我想研究的是：能不能把未来可维护性的一部分，提前变成今天可执行的压力实验？”
```

---

# X / Twitter thread draft

**1/** Most coding agents stop at “tests pass.”

I’m experimenting with a different question:

If two patches are both correct today, which one survives future repository evolution?

I built **ChronoForge** for LR-Agent.

**2/** ChronoForge copies a patch into multiple shadow repos.

Each future generation inherits the actual code from the previous one:

`seed → g1 → g2 → g3`

Future agents then handle dependency upgrades, API changes, schema migrations, adjacent features, etc.

**3/** After every generation LR-Agent replays:

- original patch checks
- project invariants
- future-maintenance verification

A timeline can die when the original behavior stops surviving.

**4/** The report contains:

- survival curve
- maintenance cost
- invariant survival
- dependency robustness
- repo-generation half-life
- future death modes

**5/** I’m not claiming it predicts the future.

The research hypothesis is narrower: prospective software-evolution stress tests may distinguish currently-correct patches that present-time tests cannot.

Repo:
https://github.com/LLR6/LR-agent

---

# What to attach to every launch post

Use at least one of:

1. a 20–40 second screen recording of Forge → ChronoForge → Patch Life Report;
2. a screenshot of the Web UI survival curve;
3. a small diagram showing sequential future inheritance;
4. a real, reproducible demo command.

Do **not** post only a README screenshot.

---

# Comment / reply strategy

Do not reply to criticism defensively.

Good response:

> That's a real confounder. The future-maintainer model can compensate for a bad patch, so I currently treat the score as an engineering heuristic. I'm planning a paired retrospective benchmark; if you have a concrete repo/task where this fails, I'd like to add it as a counterexample.

Bad response:

> You don't understand the innovation.

The project benefits from technical skepticism.

---

# Launch sequence

Recommended order:

1. finish README + demo + contribution templates;
2. publish/tag release when GitHub release tooling is available;
3. record one short real demo;
4. post Show HN;
5. post to r/LocalLLaMA or another relevant technical community;
6. publish V2EX / 掘金 / 知乎 write-up;
7. publish demo video;
8. one week later, post a concrete research result or counterexample rather than repeating the same announcement.

Do not buy stars, use star-exchange groups, or coordinate voting.
