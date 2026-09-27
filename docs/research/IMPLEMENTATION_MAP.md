# Research-to-Implementation Map

> Purpose: make every research mechanism traceable to repository code and tests.

This file prevents a common research-repository problem: the paper/document says one thing while the implementation quietly does something else.

Paths below refer to the current LR-Agent source tree.

## Counterfactual Forge

### Core implementation

- `lr_agent/universes.py`
  - workspace manifest/copy;
  - isolated candidates;
  - strategy normalization;
  - candidate execution;
  - evidence scoring;
  - evolved strategy;
  - candidate verification;
  - promotion;
  - conflict detection;
  - proof bundle;
  - Invariant DNA promotion gate.

### CLI

- `lr_agent/__main__.py`
  - `forge`
  - `forge-list`
  - `forge-promote`

### API

- `lr_agent/api.py`
  - `POST /api/universes`
  - `GET /api/universes/{id}`
  - `POST /api/universes/{id}/promote`

### Tests

- `tests/test_universes.py`
  - isolation;
  - evidence ranking;
  - conflict-aware promotion;
  - proof verification;
  - rollback;
  - Shadow Mode;
  - Invariant DNA veto.

---

# Causal Genome

## Persistent store

- `lr_agent/genome_store.py`
  - Strategy Gene records;
  - Anti-Gene records;
  - genealogy edges;
  - causal evidence;
  - confidence/status;
  - contamination;
  - Invariant DNA;
  - persistent experiment jobs.

## Experimental engine

- `lr_agent/genome.py`
  - Forge winner import;
  - treatment/control strategy construction;
  - ablation;
  - falsification;
  - Anti-Gene creation;
  - proof-carrying Gene verifier;
  - contamination API;
  - invariant checks;
  - background experiments.

## Runtime Agent integration

- `lr_agent/agent.py`
  - active Gene retrieval;
  - active Invariant DNA injection;
  - quarantine exclusion;
  - Epistemic Tripwire.

## Configuration

- `lr_agent/config.py`
  - Genome database;
  - activation thresholds;
  - evidence lift thresholds;
  - Invariant DNA switch;
  - Tripwire thresholds.

## CLI

- `lr_agent/__main__.py`
  - `genome-stats`
  - `genome-list`
  - `genome-add`
  - `genome-import`
  - `genome-ablate`
  - `genome-falsify`
  - `genome-contaminate`
  - `invariant-list`
  - `invariant-add`
  - `invariant-check`

## API

- `lr_agent/api.py`
  - Gene CRUD/query;
  - experiment start/status/cancel;
  - contamination;
  - Forge → Gene import;
  - invariant registration/check.

## Tests

- `tests/test_genome_store.py`
  - repeated-evidence activation;
  - Anti-Gene;
  - genealogy contamination;
  - invariant persistence;
  - job persistence.

- `tests/test_genome.py`
  - causal ablation;
  - falsification;
  - Forge winner quarantine.

- `tests/test_agent.py`
  - active-only Genome context;
  - Epistemic Tripwire.

---

# ChronoForge

## Persistence and calibration

- `lr_agent/chrono_store.py`
  - ChronoForge Run lifecycle;
  - interruption recovery;
  - real-future observations;
  - future-category calibration weights.

## Core prospective evolution engine

- `lr_agent/chronoforge.py`
  - Seed resolution;
  - Forge candidate aging;
  - current workspace aging;
  - project profile;
  - seed verification extraction;
  - future scenario generation;
  - fallback scenario templates;
  - weighted-fair scenario schedule;
  - sequential trajectory inheritance;
  - Future Maintainer Agent;
  - future verification;
  - Invariant DNA replay;
  - maintenance-cost calculation;
  - survival curve;
  - half-life;
  - option value;
  - dependency robustness;
  - patch-surface stability;
  - temporal death modes;
  - background runs;
  - reality observations.

## Configuration

- `lr_agent/config.py`
  - ChronoForge root/database;
  - default/max generations;
  - default/max trajectories;
  - scenario count;
  - maintenance-cost weights.

## CLI

- `lr_agent/__main__.py`
  - `chrono`
  - `chrono-list`
  - `chrono-show`
  - `chrono-observe`

## API

- `lr_agent/api.py`
  - run creation;
  - run listing;
  - run status;
  - cancel;
  - calibration;
  - future observations.

## Web UI

- `lr_agent/web/index.html`
  - Chrono button;
  - Forge-winner aging;
  - Patch Life Report;
  - temporal survival bars;
  - maintenance metrics.

## Tests

- `tests/test_chronoforge.py`
  - sequential survival behavior;
  - real pytest seed-check replay;
  - temporal half-life;
  - reality-observation calibration;
  - interrupted-run semantics;
  - weighted future scheduling.

---

# Shared safety mechanisms

- `lr_agent/tools.py`
  - command allowlist;
  - shell-free execution;
  - Shadow Mode remote-write protections;
  - file path confinement;
  - project inspection;
  - command execution evidence.

- `SECURITY.md`
  - command-runner limits;
  - Counterfactual Forge boundaries;
  - Causal Genome epistemic boundaries;
  - ChronoForge forecasting boundaries.

---

# Research documentation

- `docs/research/README.md` — research program.
- `docs/research/STATE_OF_THE_ART.md` — related work and boundaries.
- `docs/research/CAUSAL_GENOME.md` — falsifiable strategy memory.
- `docs/research/CHRONOFORGE.md` — prospective patch aging.
- `docs/research/NOVELTY_CLAIMS.md` — defensible novelty statements.
- `docs/research/EXPERIMENTS.md` — evaluation protocol.
- `docs/research/ROADMAP.md` — future research.
- `docs/research/BIBLIOGRAPHY.md` — working references/search log.
- `docs/research/IMPLEMENTATION_MAP.md` — this file.

---

# Status vocabulary

Research docs should use these terms consistently.

## Implemented

Code exists and is tested at mechanism level.

## Prototype

Code exists but the research claim has not received broad external evaluation.

## Planned

Design described, no completed implementation.

## Research proposal

Open idea that may require substantial new methods.

## Search-based novelty hypothesis

No matching public end-to-end mechanism was found in the documented search. This is not a universal first-ever claim.

---

# Rule for future changes

When a research mechanism changes:

1. update the implementation;
2. add/modify tests;
3. update the relevant research document;
4. update this map if paths/semantics changed;
5. do not leave old research claims describing behavior that no longer exists.

Author: **LLR6**
