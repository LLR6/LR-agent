from pathlib import Path

from lr_agent.genome_store import GenomeStore


def _positive_evidence(store: GenomeStore, gene_id: str, task: str, index: int) -> dict:
    return store.record_evidence(
        gene_id=gene_id,
        task=task,
        treatment_score=90 + index,
        control_score=70,
        experiment_type="ablation",
        tournament_id=f"t{index}",
        details={"trial": index},
        positive_threshold=8.0,
        negative_threshold=-8.0,
        activation_min_experiments=3,
        activation_min_positive_rate=0.67,
        activation_min_average_lift=8.0,
    )


def test_gene_requires_repeated_positive_ablation_before_activation(tmp_path: Path) -> None:
    store = GenomeStore(tmp_path / "genome.db")
    gene = store.create_gene(
        name="minimal async repair",
        instruction="Inspect event-loop ownership before changing fixtures.",
        applicability=["pytest-asyncio", "event loop fixture"],
        exclusions=["trio backend"],
    )

    assert gene["status"] == "quarantine"

    _positive_evidence(store, gene["id"], "fix async test", 1)
    _positive_evidence(store, gene["id"], "fix async test", 2)
    still_quarantined = store.get_gene(gene["id"])
    assert still_quarantined is not None
    assert still_quarantined["status"] == "quarantine"

    _positive_evidence(store, gene["id"], "fix async test", 3)
    active = store.get_gene(gene["id"])
    assert active is not None
    assert active["status"] == "active"
    assert active["positive_count"] == 3
    assert active["average_effect"] > 8
    assert active["confidence"] > 0

    results = store.search_genes("pytest async event loop", active_only=True)
    assert results
    assert results[0]["id"] == gene["id"]


def test_negative_ablation_creates_counterexample_antigene(tmp_path: Path) -> None:
    store = GenomeStore(tmp_path / "genome.db")
    gene = store.create_gene(
        name="broad refactor",
        instruction="Refactor the entire module before fixing the local bug.",
    )
    evidence = store.record_evidence(
        gene_id=gene["id"],
        task="fix a one-line parser regression",
        treatment_score=35,
        control_score=70,
        experiment_type="falsification",
        tournament_id="bad1",
        details={"reason": "larger change failed verification"},
        positive_threshold=8.0,
        negative_threshold=-8.0,
        activation_min_experiments=3,
        activation_min_positive_rate=0.67,
        activation_min_average_lift=8.0,
    )
    assert evidence["outcome"] == "negative"

    anti = store.ensure_antigene(
        parent_gene_id=gene["id"],
        task="fix a one-line parser regression",
        evidence_id=evidence["id"],
        effect=evidence["effect"],
    )

    assert anti["kind"] == "anti"
    assert anti["status"] == "active"
    assert "fix a one-line parser regression" in anti["applicability"]
    assert anti["parents"][0]["relation"] == "counterexample"


def test_contamination_propagates_through_genealogy(tmp_path: Path) -> None:
    store = GenomeStore(tmp_path / "genome.db")
    parent = store.create_gene(
        name="parent",
        instruction="parent strategy",
        status="active",
    )
    child = store.create_gene(
        name="child",
        instruction="derived strategy",
        parent_ids=[parent["id"]],
        status="active",
    )
    grandchild = store.create_gene(
        name="grandchild",
        instruction="derived again",
        parent_ids=[child["id"]],
        status="active",
    )

    result = store.mark_contaminated(
        parent["id"],
        reason="parent provenance was poisoned",
        propagate=True,
    )

    assert set(result["affected_gene_ids"]) == {
        parent["id"],
        child["id"],
        grandchild["id"],
    }
    assert store.get_gene(parent["id"])["status"] == "contaminated"
    assert store.get_gene(child["id"])["status"] == "contaminated"
    assert store.get_gene(grandchild["id"])["status"] == "contaminated"


def test_invariant_dna_roundtrip(tmp_path: Path) -> None:
    store = GenomeStore(tmp_path / "genome.db")
    invariant = store.create_invariant(
        name="auth refresh invariant",
        description="Rotating a refresh token must invalidate the previous token.",
        commands=[{"argv": ["pytest", "tests/test_auth.py"], "cwd": "."}],
    )

    assert invariant["status"] == "active"
    assert invariant["commands"][0]["argv"][0] == "pytest"

    store.record_invariant_check(
        invariant["id"],
        passed=False,
        details={"returncode": 1},
    )
    reloaded = store.get_invariant(invariant["id"])
    assert reloaded is not None
    assert reloaded["last_status"] == "failed"
    assert reloaded["last_details"]["returncode"] == 1


def test_genome_jobs_survive_as_persisted_records(tmp_path: Path) -> None:
    store = GenomeStore(tmp_path / "genome.db")
    gene = store.create_gene(name="gene", instruction="strategy")
    job = store.create_job(
        gene_id=gene["id"],
        task="fix parser",
        experiment_type="ablation",
        trials=2,
    )
    store.update_job(
        job["id"],
        status="completed",
        result={"average_trial_effect": 12.5},
    )

    loaded = store.get_job(job["id"])
    assert loaded is not None
    assert loaded["status"] == "completed"
    assert loaded["result"]["average_trial_effect"] == 12.5
