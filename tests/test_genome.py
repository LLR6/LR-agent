from pathlib import Path

import pytest

from lr_agent.config import Settings
from lr_agent.genome import CausalGenomeEngine
from lr_agent.genome_store import GenomeStore


class FakeUniverseLab:
    def __init__(self, treatment_scores: list[float], control_scores: list[float]):
        self.treatment_scores = list(treatment_scores)
        self.control_scores = list(control_scores)
        self.calls = 0
        self.saved = {}

    async def run_strategies(self, task, strategies, evolve=False):
        index = self.calls
        self.calls += 1
        treatment = self.treatment_scores[min(index, len(self.treatment_scores) - 1)]
        control = self.control_scores[min(index, len(self.control_scores) - 1)]
        tournament = {
            "id": f"tournament-{self.calls}",
            "task": task,
            "status": "completed",
            "winner_id": "treatment" if treatment >= control else "control",
            "candidates": [
                {
                    "id": "treatment",
                    "strategy": strategies[0],
                    "status": "completed",
                    "review": {"passed": True},
                    "evidence": {
                        "score": treatment,
                        "verification_passes": 1,
                        "verification_failures": 0,
                        "tool_failures": 0,
                        "changed_files": 1,
                    },
                    "changes": [{"path": "a.py", "status": "modified"}],
                    "verification_commands": [{"argv": ["pytest"]}],
                },
                {
                    "id": "control",
                    "strategy": strategies[1],
                    "status": "completed",
                    "review": {"passed": True},
                    "evidence": {
                        "score": control,
                        "verification_passes": 1,
                        "verification_failures": 0,
                        "tool_failures": 0,
                        "changed_files": 1,
                    },
                    "changes": [{"path": "a.py", "status": "modified"}],
                    "verification_commands": [{"argv": ["pytest"]}],
                },
            ],
        }
        self.saved[tournament["id"]] = tournament
        return tournament

    def get(self, tournament_id):
        return self.saved[tournament_id]


def settings_for(tmp_path: Path) -> Settings:
    return Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        genome_database=tmp_path / "genome.db",
        universe_root=tmp_path / "universes",
        gene_activation_min_experiments=3,
        gene_activation_min_positive_rate=0.67,
        gene_activation_min_average_lift=8.0,
        gene_positive_lift_threshold=8.0,
        gene_negative_lift_threshold=-8.0,
    )


@pytest.mark.asyncio
async def test_ablation_activates_gene_only_after_repeated_causal_lift(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    settings.ensure_dirs()
    store = GenomeStore(settings.genome_database)
    lab = FakeUniverseLab(
        treatment_scores=[92, 90, 94],
        control_scores=[70, 72, 71],
    )
    engine = CausalGenomeEngine(settings, store=store, universe_lab=lab)
    gene = engine.create_gene(
        name="focused repair",
        instruction="Prefer a minimal verified patch.",
        applicability=["localized regression"],
    )

    result = await engine.ablate(
        gene["id"],
        "repair localized regression",
        trials=3,
    )

    assert result["trials_completed"] == 3
    assert result["average_trial_effect"] > 8
    assert result["gene"]["status"] == "active"
    assert result["gene"]["positive_count"] == 3


@pytest.mark.asyncio
async def test_falsification_creates_antigene_for_harmful_strategy(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    settings.ensure_dirs()
    store = GenomeStore(settings.genome_database)
    lab = FakeUniverseLab(
        treatment_scores=[30],
        control_scores=[70],
    )
    engine = CausalGenomeEngine(settings, store=store, universe_lab=lab)
    gene = engine.create_gene(
        name="rewrite everything",
        instruction="Perform a broad rewrite before diagnosing the bug.",
    )

    result = await engine.falsify(
        gene["id"],
        "fix a tiny parser bug",
        trials=1,
    )

    assert result["experiments"][0]["outcome"] == "negative"
    assert result["anti_genes"]
    anti = result["anti_genes"][0]
    assert anti["kind"] == "anti"
    assert anti["status"] == "active"


def test_imported_forge_winner_stays_quarantined_until_ablation(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    settings.ensure_dirs()
    store = GenomeStore(settings.genome_database)
    lab = FakeUniverseLab([90], [70])
    lab.saved["forge-1"] = {
        "id": "forge-1",
        "task": "fix auth",
        "status": "completed",
        "winner_id": "winner",
        "candidates": [
            {
                "id": "winner",
                "strategy": {
                    "id": "winner",
                    "name": "Auth Surgeon",
                    "instruction": "Trace token ownership before editing.",
                },
                "evidence": {"score": 95},
                "verification_commands": [
                    {"argv": ["pytest", "tests/test_auth.py"], "cwd": "."}
                ],
            }
        ],
    }
    engine = CausalGenomeEngine(settings, store=store, universe_lab=lab)

    gene = engine.import_forge_winner("forge-1")

    assert gene["status"] == "quarantine"
    assert gene["provenance"]["source"] == "forge_winner"
    assert gene["verifier"][0]["argv"][0] == "pytest"
