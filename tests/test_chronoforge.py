from pathlib import Path

import pytest

from lr_agent.chrono_store import ChronoStore
from lr_agent.chronoforge import ChronoForge
from lr_agent.config import Settings
from lr_agent.models import ChatResponse, ReviewReport


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        workspace=tmp_path / "workspace",
        database=tmp_path / "memory.db",
        knowledge_database=tmp_path / "knowledge.db",
        genome_database=tmp_path / "genome.db",
        universe_root=tmp_path / "universes",
        chronoforge_root=tmp_path / "chronoforge",
        chronoforge_database=tmp_path / "chronoforge.db",
        chronoforge_generations=2,
        chronoforge_trajectories=2,
        enable_planning=False,
        enable_review=False,
    )


async def aging_runner(settings: Settings, prompt: str) -> ChatResponse:
    app = settings.workspace / "app.py"
    if "FUTURE CATEGORY: dependency_upgrade" in prompt:
        app.write_text("value = 'broken-by-future'\n", encoding="utf-8")

    return ChatResponse(
        session_id="session",
        run_id="future-run",
        status="completed",
        answer="future maintenance applied",
        steps=[],
        plan=None,
        review=ReviewReport(
            passed=True,
            summary="future task completed",
            problems=[],
            next_actions=[],
        ),
    )


@pytest.mark.asyncio
async def test_chronoforge_builds_sequential_survival_curve(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    settings.ensure_dirs()
    workspace = settings.workspace
    (workspace / "app.py").write_text("value = 'stable'\n", encoding="utf-8")
    (workspace / "test_app.py").write_text(
        "import app\n\ndef test_value():\n    assert app.value == 'stable'\n",
        encoding="utf-8",
    )
    (workspace / "pyproject.toml").write_text(
        "[build-system]\nrequires=[]\n",
        encoding="utf-8",
    )

    engine = ChronoForge(settings, agent_runner=aging_runner)

    async def fixed_scenarios(**_kwargs):
        return [
            {
                "category": "dependency_upgrade",
                "name": "dependency breaks assumption",
                "instruction": "apply dependency stress",
                "weight": 0.5,
                "source": "test",
            },
            {
                "category": "api_deprecation",
                "name": "API remains compatible",
                "instruction": "perform harmless future maintenance",
                "weight": 0.5,
                "source": "test",
            },
            {
                "category": "adjacent_feature",
                "name": "adjacent feature",
                "instruction": "perform harmless adjacent change",
                "weight": 0.1,
                "source": "test",
            },
        ]

    engine._generate_scenarios = fixed_scenarios  # type: ignore[method-assign]

    report = await engine.run(
        task="preserve value behavior",
        generations=2,
        trajectories=2,
    )

    assert report["format"] == "lr-agent-chronoforge-report/v1"
    assert report["survival_curve"] == [
        {"generation": 0, "survival_rate": 1.0},
        {"generation": 1, "survival_rate": 0.5},
        {"generation": 2, "survival_rate": 0.5},
    ]
    assert report["metrics"]["temporal_survival"] == 0.5
    assert report["metrics"]["predicted_half_life"] == {
        "generation": 1.0,
        "censored": False,
    }
    assert report["death_modes"]["dependency_upgrade"] == 1

    stored = engine.list(5)[0]
    assert stored["status"] == "completed"
    assert stored["report"]["metrics"]["temporal_survival"] == 0.5


def test_reality_observations_recalibrate_future_category_weights(tmp_path: Path) -> None:
    store = ChronoStore(tmp_path / "chronoforge.db")
    before = store.calibration()["weights"]

    for index in range(4):
        store.add_observation(
            category="dependency_upgrade",
            note=f"real dependency event {index}",
        )
    store.add_observation(
        category="schema_migration",
        note="one schema event",
    )

    after = store.calibration()
    assert after["observations"]["dependency_upgrade"] == 4
    assert after["weights"]["dependency_upgrade"] > before["dependency_upgrade"]
    assert (
        after["weights"]["dependency_upgrade"]
        > after["weights"]["schema_migration"]
    )


def test_interrupted_chronoforge_run_is_not_marked_completed(tmp_path: Path) -> None:
    path = tmp_path / "chronoforge.db"
    store = ChronoStore(path)
    item = store.create_run(
        source_type="workspace",
        source_ref=None,
        task="age patch",
        generations=4,
        trajectories=3,
    )
    store.update_run(item["id"], status="running")

    reopened = ChronoStore(path)
    loaded = reopened.get_run(item["id"])
    assert loaded is not None
    assert loaded["status"] == "interrupted"
    assert "restarted" in loaded["error"].lower()


def test_reality_weights_change_future_scenario_frequency() -> None:
    scenarios = [
        {
            "category": "dependency_upgrade",
            "name": "dependency",
            "instruction": "x",
            "weight": 0.8,
        },
        {
            "category": "api_deprecation",
            "name": "api",
            "instruction": "x",
            "weight": 0.1,
        },
        {
            "category": "schema_migration",
            "name": "schema",
            "instruction": "x",
            "weight": 0.1,
        },
    ]
    schedule = ChronoForge._scenario_schedule(
        scenarios,
        generations=4,
        trajectories=3,
    )
    categories = [
        item["category"]
        for trajectory in schedule
        for item in trajectory
    ]

    assert categories.count("dependency_upgrade") > categories.count("api_deprecation")
    assert categories.count("dependency_upgrade") > categories.count("schema_migration")
    assert "api_deprecation" in categories
    assert "schema_migration" in categories
