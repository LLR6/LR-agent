# LR-Agent

**A research-oriented coding agent that asks not only “does this patch work today?” — but “can it survive tomorrow?”**

[中文 README](./README.md) · [5-minute ChronoForge demo](./docs/DEMO_CHRONOFORGE.md) · [Research](./docs/research/README.md) · [Contributing](./CONTRIBUTING.md)

![CI](https://github.com/LLR6/LR-agent/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.1.0-8b5cf6)

## Why LR-Agent exists

Most coding agents stop at:

```text
task → patch → tests pass → done
```

LR-Agent experiments with a longer loop:

```text
                         ┌─ Patch A ─┐
task → Counterfactual   ├─ Patch B ─┼→ executable evidence
       Forge             └─ Patch C ─┘
                               │
                               ▼
                        Causal Genome
                strategies must earn evidence
                               │
                               ▼
                          ChronoForge
              age a patch through future repos
                               │
                replay seed checks + invariants
                               │
                               ▼
                        PATCH LIFE REPORT
```

Two patches can both pass today's tests and still have very different future maintenance costs.

## Three ideas to look at first

### ⚡ Counterfactual Forge

Run competing coding strategies in isolated shadow workspaces. Candidates make real edits and run real checks. Promotion is conflict-aware and re-verifies in the real workspace; failed promotion is rolled back.

### 🧬 Causal Genome

A successful trajectory does **not** automatically become long-term memory.

Candidate strategies enter `quarantine`, then can be tested through Treatment vs Control ablation, active falsification, Anti-Genes, genealogy/contamination tracking and executable Gene verifiers.

### ⏳ ChronoForge

Copy the current workspace or a Forge candidate into several future repository trajectories.

Generation N inherits the actual code produced by generation N-1. Future-maintainer agents evolve the repository under pressures such as:

- dependency upgrades;
- API deprecation;
- adjacent features;
- schema migration;
- module refactors;
- runtime/platform changes;
- performance pressure;
- configuration-contract changes.

After every generation, LR-Agent replays the seed behavior checks and active Invariant DNA.

The resulting Patch Life Report includes:

- Temporal Survival Curve
- Future Maintenance Cost
- Maintenance Option Value
- Invariant Survival
- Dependency Robustness
- Patch Surface Stability
- repository-generation Half-Life
- Temporal Death Modes

ChronoForge is an experimental stress-testing system, **not a literal future predictor**.

## Quick start

Python 3.11+ is required.

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

Configure an OpenAI-compatible endpoint/model in `.env`, then:

```bash
lr-agent doctor
lr-agent serve
```

Try the interesting parts:

```bash
# Competing isolated patch universes
lr-agent forge "fix the failing tests and verify the real root cause" --evolve

# Prospective patch aging
lr-agent chrono "preserve the current core behavior" --generations 4 --trajectories 3
```

For a guided example:

**[→ 5-minute ChronoForge Demo](./docs/DEMO_CHRONOFORGE.md)**

## Research program

The research documentation is intentionally separated from marketing claims:

- [Research Program](./docs/research/README.md)
- [State of the Art / Related Work](./docs/research/STATE_OF_THE_ART.md)
- [Causal Genome](./docs/research/CAUSAL_GENOME.md)
- [ChronoForge](./docs/research/CHRONOFORGE.md)
- [Novelty Claims & Boundaries](./docs/research/NOVELTY_CLAIMS.md)
- [Experimental Protocol](./docs/research/EXPERIMENTS.md)
- [Research Roadmap](./docs/research/ROADMAP.md)
- [Implementation Map](./docs/research/IMPLEMENTATION_MAP.md)

The repository uses conservative novelty language: “we did not find an equivalent public end-to-end system in the literature we searched” is treated as a **search-based novelty hypothesis**, not a claim that nobody has ever explored the idea.

## Good first places to contribute

The most useful next steps are not “add another Agent role.” They are:

1. **Chrono Tournament** — expose several currently-correct patches to the same frozen future matrix.
2. **Retrospective benchmark runner** — evaluate ChronoForge forecasts against later real repository history.
3. **Cost and reproducibility telemetry** — model/tool/token/environment manifests for every experiment.
4. **Future Surprise / calibration error** — score past forecasts against later reality.
5. **Demo repositories** — small reproducible examples that isolate temporal fragility.

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## Safety

LR-Agent can execute allowlisted commands and modify files inside configured workspaces. Shadow workspaces reduce risk but are **not** kernel/VM sandboxes.

For untrusted repositories or prompts, use Docker or a disposable VM.

See [SECURITY.md](./SECURITY.md).

## Status

LR-Agent is a research engineering project. Mechanisms have unit/CI coverage, but broad external benchmark claims still require systematic evaluation.

If the idea is useful to you, a ⭐ helps other developers discover the project — but issues, counterexamples and failed experiments are even more valuable.

## License

MIT.

Author: **LLR6**
