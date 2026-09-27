# 5-Minute ChronoForge Demo

This walkthrough is designed for people who want to understand the core idea before reading the full research docs.

## What you will see

You start with a tiny Python project whose tests pass today.

ChronoForge then copies it into several shadow repositories and lets future-maintainer agents evolve those copies through sequential maintenance events.

```text
today
  ↓
seed workspace
  ├─ future timeline A: g1 → g2 → g3
  ├─ future timeline B: g1 → g2 → g3
  └─ future timeline C: g1 → g2 → g3
                         ↑
         each generation inherits the previous code
```

After each generation LR-Agent replays the original behavior checks and active Invariant DNA.

The result is a Patch Life Report rather than a one-shot “looks good to me” review.

---

## 1. Install LR-Agent

From a terminal:

```bash
git clone https://github.com/LLR6/LR-agent.git
cd LR-agent
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Configure an OpenAI-compatible model in `.env`.

Then check the endpoint:

```bash
lr-agent doctor
```

---

## 2. Inspect the demo project

The example workspace is:

```text
examples/chronoforge-demo/
├── app.py
├── test_app.py
├── pyproject.toml
└── README.md
```

Run today's tests:

```bash
cd examples/chronoforge-demo
pytest
cd ../..
```

The current contract is intentionally easy to understand:

```python
build_client_config({
    "api_url": "https://example.test/",
    "timeout_s": 15,
})
```

Today, this is enough.

The research question is what happens after future configuration/API requirements accumulate.

---

## 3. Point LR-Agent at the demo

In `.env`:

```env
LR_AGENT_WORKSPACE=./examples/chronoforge-demo
```

Recommended small demo settings:

```env
LR_AGENT_CHRONOFORGE_GENERATIONS=3
LR_AGENT_CHRONOFORGE_TRAJECTORIES=3
```

This caps the demo at roughly nine future-maintainer runs before early trajectory death.

---

## 4. Run ChronoForge

```bash
lr-agent chrono "Keep current client configuration behavior stable while allowing future configuration evolution" --generations 3 --trajectories 3
```

Or start the Web UI:

```bash
lr-agent serve
```

Then use the **⏳ Chrono** control.

---

## 5. What ChronoForge actually does

The Future Model creates a scenario pool around categories such as:

- configuration-contract change;
- API deprecation;
- dependency upgrade;
- adjacent feature;
- schema/data evolution;
- module-boundary refactor.

A trajectory may look like:

```text
Seed
  ↓
g1: configuration contract changes
  ↓
future maintainer edits real files
  ↓
replay seed tests
  ↓
g2: adjacent feature arrives
  ↓
future maintainer inherits g1 code
  ↓
replay seed tests
  ↓
g3: API deprecation pressure
  ↓
replay seed tests
```

If the original behavior or an active invariant fails, that trajectory dies at that generation.

This is the key distinction from asking three independent hypothetical questions.

---

## 6. Read the Patch Life Report

A report contains metrics like:

```text
Temporal Survival        0.67
Future Maintenance Cost  10.8
Maintenance Option Value 0.44
Invariant Survival       1.00
Dependency Robustness    0.75
Predicted Half-Life      3 repository generations
```

And a survival curve:

```text
g0 ████████████████████ 100%
g1 ████████████████████ 100%
g2 █████████████░░░░░░░  67%
g3 █████████████░░░░░░░  67%
```

Exact values depend on:

- the model;
- generated future scenarios;
- repository state;
- Agent trajectory;
- verification quality.

Do not compare numbers from different scenario matrices as if they were controlled experiments.

---

## 7. Inspect the future repositories

ChronoForge keeps its experimental workspaces:

```text
data/chronoforge/<run_id>/
├── seed/
└── trajectories/
    ├── t01/
    │   ├── g01/workspace/
    │   ├── g02/workspace/
    │   └── g03/workspace/
    ├── t02/
    └── t03/
```

Open them.

The most useful question is often not the final score, but:

> **What future pressure forced the implementation to reopen or rewrite the original patch surface?**

---

## 8. Feed later reality back into the Future Model

If a real project later experiences a dependency upgrade:

```bash
lr-agent chrono-observe dependency_upgrade "framework major-version migration"
```

If a schema evolves:

```bash
lr-agent chrono-observe schema_migration "session record gained a new lineage field"
```

ChronoForge stores those events and changes future-category scheduling weights.

This is deliberately simple calibration, not a claim of perfect forecasting.

---

## 9. Try the stronger workflow

ChronoForge becomes more interesting after Counterfactual Forge.

First create competing patches:

```bash
lr-agent forge "fix the current bug and verify the root cause" --evolve
```

Then age the Forge winner:

```bash
lr-agent chrono --tournament-id <tournament_id> --generations 4 --trajectories 3
```

Now the question changes from:

> “Does the patch work?”

to:

> “The candidate works today — what maintenance pressures make it die later?”

---

## 10. What this demo does **not** prove

ChronoForge does not prove future correctness.

It does not know future requirements with certainty.

Synthetic scenarios can be unrealistic, and a strong/weak future Agent can change the measured maintenance cost.

The current research hypothesis is narrower:

> **Prospective repository-evolution stress tests may reveal differences between currently-correct patches that present-time tests alone do not show.**

That hypothesis needs retrospective and prospective benchmark validation.

For the full protocol see:

- [ChronoForge research note](./research/CHRONOFORGE.md)
- [Experimental protocol](./research/EXPERIMENTS.md)
- [Novelty boundaries](./research/NOVELTY_CLAIMS.md)

---

If you find a case where ChronoForge gives a misleading life report, please open an issue. Counterexamples are useful research data, not just bug reports.
