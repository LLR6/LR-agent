from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FUTURE_CATEGORIES = (
    "dependency_upgrade",
    "api_deprecation",
    "adjacent_feature",
    "schema_migration",
    "module_refactor",
    "platform_runtime",
    "performance_pressure",
    "config_contract",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


class ChronoStore:
    """Persistent ChronoForge runs plus reality-calibration observations."""

    def __init__(self, database_path: Path):
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = database_path
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._init_schema()
        self.mark_interrupted()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS chrono_runs (
                    id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_ref TEXT,
                    task TEXT NOT NULL,
                    generations INTEGER NOT NULL,
                    trajectories INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    scenario_json TEXT,
                    report_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chrono_runs_created
                    ON chrono_runs(created_at DESC);

                CREATE TABLE IF NOT EXISTS future_observations (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    note TEXT NOT NULL,
                    source TEXT NOT NULL,
                    observed_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_future_observations_category
                    ON future_observations(category, observed_at DESC);
                """
            )

    def mark_interrupted(self) -> int:
        now = _now()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                UPDATE chrono_runs
                SET status = 'interrupted',
                    error = COALESCE(error, 'Service restarted before ChronoForge finished.'),
                    updated_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (now,),
            )
        return int(cursor.rowcount)

    def create_run(
        self,
        *,
        source_type: str,
        source_ref: str | None,
        task: str,
        generations: int,
        trajectories: int,
    ) -> dict[str, Any]:
        run_id = uuid.uuid4().hex
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO chrono_runs(
                    id, source_type, source_ref, task,
                    generations, trajectories, status,
                    scenario_json, report_json, error,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'queued', NULL, NULL, NULL, ?, ?)
                """,
                (
                    run_id,
                    source_type,
                    source_ref,
                    task,
                    int(generations),
                    int(trajectories),
                    now,
                    now,
                ),
            )
        item = self.get_run(run_id)
        if item is None:
            raise RuntimeError("ChronoForge run could not be reloaded.")
        return item

    def update_run(
        self,
        run_id: str,
        *,
        status: str,
        scenarios: list[dict[str, Any]] | None = None,
        report: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE chrono_runs
                SET status = ?,
                    scenario_json = COALESCE(?, scenario_json),
                    report_json = COALESCE(?, report_json),
                    error = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    (
                        json.dumps(scenarios, ensure_ascii=False)
                        if scenarios is not None
                        else None
                    ),
                    (
                        json.dumps(report, ensure_ascii=False)
                        if report is not None
                        else None
                    ),
                    error,
                    now,
                    run_id,
                ),
            )

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["scenarios"] = _loads(item.pop("scenario_json"), [])
        item["report"] = _loads(item.pop("report_json"), None)
        return item

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM chrono_runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        return self._run_from_row(row) if row else None

    def list_runs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM chrono_runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (min(max(limit, 1), 500),),
            ).fetchall()
        return [self._run_from_row(row) for row in rows]

    def add_observation(
        self,
        *,
        category: str,
        note: str,
        source: str = "reality",
    ) -> dict[str, Any]:
        if category not in FUTURE_CATEGORIES:
            raise ValueError(f"unsupported future category: {category}")
        observation_id = uuid.uuid4().hex
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO future_observations(
                    id, category, note, source, observed_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    observation_id,
                    category,
                    note.strip(),
                    source.strip() or "reality",
                    now,
                ),
            )
        return {
            "id": observation_id,
            "category": category,
            "note": note.strip(),
            "source": source.strip() or "reality",
            "observed_at": now,
        }

    def calibration(self) -> dict[str, Any]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT category, COUNT(*) AS count
                FROM future_observations
                GROUP BY category
                """
            ).fetchall()
        observed = {str(row["category"]): int(row["count"]) for row in rows}
        posterior_counts = {
            category: 1 + observed.get(category, 0)
            for category in FUTURE_CATEGORIES
        }
        total = sum(posterior_counts.values())
        weights = {
            category: posterior_counts[category] / total
            for category in FUTURE_CATEGORIES
        }
        return {
            "observations": observed,
            "weights": weights,
            "method": "laplace-smoothed categorical posterior",
            "note": (
                "Weights summarize recorded real-world project events. "
                "They are calibration priors, not probabilities guaranteed to match the future."
            ),
        }

    def observations(self, limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM future_observations
                ORDER BY observed_at DESC
                LIMIT ?
                """,
                (min(max(limit, 1), 1000),),
            ).fetchall()
        return [dict(row) for row in rows]
