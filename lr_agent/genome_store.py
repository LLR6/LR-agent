from __future__ import annotations

import json
import math
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_./:+-]{2,}|[\u4e00-\u9fff]{1,8}", text)
    }


class GenomeStore:
    """Persistent causal strategy genes, anti-genes, evidence and project invariants."""

    def __init__(self, database_path: Path):
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = database_path
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS genes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    instruction TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    applicability_json TEXT NOT NULL,
                    exclusions_json TEXT NOT NULL,
                    verifier_json TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 0,
                    positive_count INTEGER NOT NULL DEFAULT 0,
                    negative_count INTEGER NOT NULL DEFAULT 0,
                    neutral_count INTEGER NOT NULL DEFAULT 0,
                    average_effect REAL NOT NULL DEFAULT 0,
                    contamination_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_genes_status
                    ON genes(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_genes_kind
                    ON genes(kind, updated_at DESC);

                CREATE TABLE IF NOT EXISTS gene_edges (
                    parent_id TEXT NOT NULL,
                    child_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(parent_id, child_id, relation),
                    FOREIGN KEY(parent_id) REFERENCES genes(id),
                    FOREIGN KEY(child_id) REFERENCES genes(id)
                );

                CREATE INDEX IF NOT EXISTS idx_gene_edges_parent
                    ON gene_edges(parent_id);
                CREATE INDEX IF NOT EXISTS idx_gene_edges_child
                    ON gene_edges(child_id);

                CREATE TABLE IF NOT EXISTS gene_evidence (
                    id TEXT PRIMARY KEY,
                    gene_id TEXT NOT NULL,
                    experiment_type TEXT NOT NULL,
                    task TEXT NOT NULL,
                    tournament_id TEXT,
                    treatment_score REAL NOT NULL,
                    control_score REAL NOT NULL,
                    effect REAL NOT NULL,
                    outcome TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(gene_id) REFERENCES genes(id)
                );

                CREATE INDEX IF NOT EXISTS idx_gene_evidence_gene
                    ON gene_evidence(gene_id, created_at DESC);

                CREATE TABLE IF NOT EXISTS invariants (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    commands_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    source_gene_id TEXT,
                    last_status TEXT,
                    last_details_json TEXT,
                    last_checked_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_invariants_status
                    ON invariants(status, updated_at DESC);

                CREATE TABLE IF NOT EXISTS genome_jobs (
                    id TEXT PRIMARY KEY,
                    gene_id TEXT NOT NULL,
                    task TEXT NOT NULL,
                    experiment_type TEXT NOT NULL,
                    trials INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(gene_id) REFERENCES genes(id)
                );

                CREATE INDEX IF NOT EXISTS idx_genome_jobs_created
                    ON genome_jobs(created_at DESC);
                """
            )

    @staticmethod
    def _gene_from_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for field, fallback in (
            ("applicability_json", []),
            ("exclusions_json", []),
            ("verifier_json", []),
            ("provenance_json", {}),
        ):
            value = item.pop(field)
            item[field.removesuffix("_json")] = _loads(value, fallback)
        item["confidence"] = float(item["confidence"])
        item["average_effect"] = float(item["average_effect"])
        return item

    def create_gene(
        self,
        *,
        name: str,
        instruction: str,
        kind: str = "strategy",
        applicability: list[str] | None = None,
        exclusions: list[str] | None = None,
        verifier: list[dict[str, Any]] | None = None,
        provenance: dict[str, Any] | None = None,
        parent_ids: list[str] | None = None,
        status: str = "quarantine",
    ) -> dict[str, Any]:
        name = name.strip()
        instruction = instruction.strip()
        if not name or not instruction:
            raise ValueError("gene name and instruction are required")
        if kind not in {"strategy", "anti"}:
            raise ValueError("gene kind must be strategy or anti")
        if status not in {"quarantine", "active", "contested", "retired", "contaminated"}:
            raise ValueError("invalid gene status")

        gene_id = uuid.uuid4().hex
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO genes(
                    id, name, instruction, kind, status,
                    applicability_json, exclusions_json, verifier_json,
                    provenance_json, confidence, positive_count,
                    negative_count, neutral_count, average_effect,
                    contamination_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, NULL, ?, ?)
                """,
                (
                    gene_id,
                    name,
                    instruction,
                    kind,
                    status,
                    json.dumps(applicability or [], ensure_ascii=False),
                    json.dumps(exclusions or [], ensure_ascii=False),
                    json.dumps(verifier or [], ensure_ascii=False),
                    json.dumps(provenance or {}, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            for parent_id in parent_ids or []:
                if self._conn.execute(
                    "SELECT 1 FROM genes WHERE id = ?", (parent_id,)
                ).fetchone():
                    self._conn.execute(
                        """
                        INSERT OR IGNORE INTO gene_edges(
                            parent_id, child_id, relation, created_at
                        ) VALUES (?, ?, 'derived', ?)
                        """,
                        (parent_id, gene_id, now),
                    )
        gene = self.get_gene(gene_id)
        if gene is None:
            raise RuntimeError("created gene could not be reloaded")
        return gene

    def get_gene(self, gene_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM genes WHERE id = ?", (gene_id,)
            ).fetchone()
            if row is None:
                return None
            parents = self._conn.execute(
                """
                SELECT parent_id, relation FROM gene_edges
                WHERE child_id = ?
                ORDER BY created_at ASC
                """,
                (gene_id,),
            ).fetchall()
            children = self._conn.execute(
                """
                SELECT child_id, relation FROM gene_edges
                WHERE parent_id = ?
                ORDER BY created_at ASC
                """,
                (gene_id,),
            ).fetchall()

        item = self._gene_from_row(row)
        item["parents"] = [dict(value) for value in parents]
        item["children"] = [dict(value) for value in children]
        return item

    def list_genes(
        self,
        *,
        status: str | None = None,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(min(max(limit, 1), 500))
        with self._lock:
            rows = self._conn.execute(
                f"""
                SELECT * FROM genes
                {where}
                ORDER BY confidence DESC, updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [self._gene_from_row(row) for row in rows]

    def search_genes(
        self,
        query: str,
        *,
        limit: int = 5,
        active_only: bool = True,
    ) -> list[dict[str, Any]]:
        query_tokens = _tokens(query)
        candidates = self.list_genes(
            status="active" if active_only else None,
            limit=500,
        )
        scored: list[tuple[float, dict[str, Any]]] = []
        for gene in candidates:
            document = " ".join(
                [
                    gene["name"],
                    gene["instruction"],
                    " ".join(gene["applicability"]),
                    " ".join(gene["exclusions"]),
                ]
            )
            document_tokens = _tokens(document)
            overlap = len(query_tokens & document_tokens)
            containment = (
                overlap / max(len(query_tokens), 1)
                if query_tokens
                else 0.0
            )
            anti_penalty = 0.02 if gene["kind"] == "anti" else 0.0
            score = (
                containment * 0.65
                + min(overlap, 6) / 6.0 * 0.15
                + float(gene["confidence"]) * 0.2
                - anti_penalty
            )
            if overlap or float(gene["confidence"]) >= 0.75:
                item = dict(gene)
                item["retrieval_score"] = round(score, 4)
                scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[: min(max(limit, 1), 50)]]

    def evidence_for_gene(
        self,
        gene_id: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM gene_evidence
                WHERE gene_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (gene_id, min(max(limit, 1), 1000)),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["details"] = _loads(item.pop("details_json"), {})
            result.append(item)
        return result

    def record_evidence(
        self,
        *,
        gene_id: str,
        task: str,
        treatment_score: float,
        control_score: float,
        experiment_type: str,
        tournament_id: str | None,
        details: dict[str, Any],
        positive_threshold: float,
        negative_threshold: float,
        activation_min_experiments: int,
        activation_min_positive_rate: float,
        activation_min_average_lift: float,
    ) -> dict[str, Any]:
        gene = self.get_gene(gene_id)
        if gene is None:
            raise ValueError(f"gene not found: {gene_id}")

        effect = float(treatment_score) - float(control_score)
        if effect >= positive_threshold:
            outcome = "positive"
        elif effect <= negative_threshold:
            outcome = "negative"
        else:
            outcome = "neutral"

        evidence_id = uuid.uuid4().hex
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO gene_evidence(
                    id, gene_id, experiment_type, task, tournament_id,
                    treatment_score, control_score, effect, outcome,
                    details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    gene_id,
                    experiment_type,
                    task,
                    tournament_id,
                    float(treatment_score),
                    float(control_score),
                    effect,
                    outcome,
                    json.dumps(details, ensure_ascii=False),
                    now,
                ),
            )
            rows = self._conn.execute(
                """
                SELECT effect, outcome FROM gene_evidence
                WHERE gene_id = ?
                """,
                (gene_id,),
            ).fetchall()

            positive = sum(1 for row in rows if row["outcome"] == "positive")
            negative = sum(1 for row in rows if row["outcome"] == "negative")
            neutral = sum(1 for row in rows if row["outcome"] == "neutral")
            total = len(rows)
            average_effect = (
                sum(float(row["effect"]) for row in rows) / total
                if total
                else 0.0
            )
            positive_rate = positive / total if total else 0.0

            support = (positive + 0.5 * neutral + 1.0) / (total + 2.0)
            saturation = min(
                1.0,
                total / max(activation_min_experiments, 1),
            )
            lift_scale = max(abs(positive_threshold), 1.0)
            lift_factor = max(
                0.0,
                min(1.0, max(average_effect, 0.0) / (lift_scale * 2.0)),
            )
            confidence = max(
                0.0,
                min(
                    1.0,
                    support
                    * (0.55 + 0.45 * saturation)
                    * (0.65 + 0.35 * lift_factor),
                ),
            )

            current_status = gene["status"]
            if current_status in {"retired", "contaminated"}:
                next_status = current_status
            elif (
                total >= max(activation_min_experiments, 1)
                and positive_rate >= activation_min_positive_rate
                and average_effect >= activation_min_average_lift
            ):
                next_status = "active"
            elif negative >= 2 and negative / total >= 0.5:
                next_status = "contested"
            else:
                next_status = "quarantine"

            self._conn.execute(
                """
                UPDATE genes
                SET confidence = ?, positive_count = ?, negative_count = ?,
                    neutral_count = ?, average_effect = ?, status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    confidence,
                    positive,
                    negative,
                    neutral,
                    average_effect,
                    next_status,
                    now,
                    gene_id,
                ),
            )

        return {
            "id": evidence_id,
            "gene_id": gene_id,
            "task": task,
            "experiment_type": experiment_type,
            "treatment_score": float(treatment_score),
            "control_score": float(control_score),
            "effect": effect,
            "outcome": outcome,
            "gene": self.get_gene(gene_id),
            "details": details,
            "created_at": now,
        }

    def ensure_antigene(
        self,
        *,
        parent_gene_id: str,
        task: str,
        evidence_id: str,
        effect: float,
    ) -> dict[str, Any]:
        parent = self.get_gene(parent_gene_id)
        if parent is None:
            raise ValueError(f"parent gene not found: {parent_gene_id}")

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT child_id FROM gene_edges
                WHERE parent_id = ? AND relation = 'counterexample'
                """,
                (parent_gene_id,),
            ).fetchall()
        for row in rows:
            child = self.get_gene(row["child_id"])
            if child and task in child["applicability"]:
                return child

        anti = self.create_gene(
            name=f"Avoid blindly applying: {parent['name']}",
            instruction=(
                "Do not automatically apply the parent strategy in contexts matching this "
                "counterexample. Re-check its preconditions, exclusions and project invariants "
                "before using it. A controlled Forge ablation showed that using the parent "
                f"strategy underperformed the control by {abs(effect):.2f} evidence points."
            ),
            kind="anti",
            applicability=[task],
            exclusions=[],
            verifier=[],
            provenance={
                "source": "negative_ablation",
                "parent_gene_id": parent_gene_id,
                "evidence_id": evidence_id,
                "counterexample_task": task,
                "effect": effect,
            },
            parent_ids=[parent_gene_id],
            status="active",
        )
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE gene_edges
                SET relation = 'counterexample', created_at = ?
                WHERE parent_id = ? AND child_id = ?
                """,
                (now, parent_gene_id, anti["id"]),
            )
            self._conn.execute(
                """
                UPDATE genes
                SET confidence = 0.85, positive_count = 1, updated_at = ?
                WHERE id = ?
                """,
                (now, anti["id"]),
            )
        refreshed = self.get_gene(anti["id"])
        if refreshed is None:
            raise RuntimeError("anti-gene could not be reloaded")
        return refreshed

    def descendants(self, gene_id: str) -> list[str]:
        seen: set[str] = set()
        queue = [gene_id]
        with self._lock:
            while queue:
                parent = queue.pop(0)
                rows = self._conn.execute(
                    "SELECT child_id FROM gene_edges WHERE parent_id = ?",
                    (parent,),
                ).fetchall()
                for row in rows:
                    child = str(row["child_id"])
                    if child in seen:
                        continue
                    seen.add(child)
                    queue.append(child)
        seen.discard(gene_id)
        return sorted(seen)

    def mark_contaminated(
        self,
        gene_id: str,
        *,
        reason: str,
        propagate: bool = True,
    ) -> dict[str, Any]:
        ids = [gene_id]
        if propagate:
            ids.extend(self.descendants(gene_id))
        now = _now()
        with self._lock, self._conn:
            for target in ids:
                self._conn.execute(
                    """
                    UPDATE genes
                    SET status = 'contaminated',
                        confidence = confidence * 0.25,
                        contamination_reason = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (reason, now, target),
                )
        return {
            "root_gene_id": gene_id,
            "affected_gene_ids": ids,
            "reason": reason,
        }

    def create_invariant(
        self,
        *,
        name: str,
        description: str,
        commands: list[dict[str, Any]],
        source_gene_id: str | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        if not name.strip() or not description.strip():
            raise ValueError("invariant name and description are required")
        if status not in {"active", "disabled", "quarantine"}:
            raise ValueError("invalid invariant status")
        normalized: list[dict[str, Any]] = []
        for command in commands:
            argv = command.get("argv")
            if not isinstance(argv, list) or not argv or not all(
                isinstance(item, str) and item for item in argv
            ):
                raise ValueError("every invariant command requires a non-empty argv list")
            normalized.append(
                {
                    "argv": argv,
                    "cwd": str(command.get("cwd") or "."),
                    **(
                        {"timeout_s": float(command["timeout_s"])}
                        if command.get("timeout_s") is not None
                        else {}
                    ),
                }
            )

        invariant_id = uuid.uuid4().hex
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO invariants(
                    id, name, description, commands_json, status,
                    source_gene_id, last_status, last_details_json,
                    last_checked_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
                """,
                (
                    invariant_id,
                    name.strip(),
                    description.strip(),
                    json.dumps(normalized, ensure_ascii=False),
                    status,
                    source_gene_id,
                    now,
                    now,
                ),
            )
        invariant = self.get_invariant(invariant_id)
        if invariant is None:
            raise RuntimeError("created invariant could not be reloaded")
        return invariant

    @staticmethod
    def _invariant_from_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["commands"] = _loads(item.pop("commands_json"), [])
        item["last_details"] = _loads(item.pop("last_details_json"), None)
        return item

    def get_invariant(self, invariant_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM invariants WHERE id = ?",
                (invariant_id,),
            ).fetchone()
        return self._invariant_from_row(row) if row else None

    def list_invariants(
        self,
        *,
        status: str | None = "active",
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        with self._lock:
            if status is None:
                rows = self._conn.execute(
                    """
                    SELECT * FROM invariants
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (min(max(limit, 1), 1000),),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    """
                    SELECT * FROM invariants
                    WHERE status = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (status, min(max(limit, 1), 1000)),
                ).fetchall()
        return [self._invariant_from_row(row) for row in rows]

    def record_invariant_check(
        self,
        invariant_id: str,
        *,
        passed: bool,
        details: dict[str, Any],
    ) -> None:
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE invariants
                SET last_status = ?, last_details_json = ?,
                    last_checked_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    "passed" if passed else "failed",
                    json.dumps(details, ensure_ascii=False),
                    now,
                    now,
                    invariant_id,
                ),
            )

    def mark_interrupted_jobs(self) -> int:
        now = _now()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                UPDATE genome_jobs
                SET status = 'interrupted',
                    error = COALESCE(error, 'Service restarted before experiment finished.'),
                    updated_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (now,),
            )
        return int(cursor.rowcount)

    def create_job(
        self,
        *,
        gene_id: str,
        task: str,
        experiment_type: str,
        trials: int,
    ) -> dict[str, Any]:
        if self.get_gene(gene_id) is None:
            raise ValueError(f"gene not found: {gene_id}")
        job_id = uuid.uuid4().hex
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO genome_jobs(
                    id, gene_id, task, experiment_type, trials,
                    status, result_json, error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', NULL, NULL, ?, ?)
                """,
                (
                    job_id,
                    gene_id,
                    task,
                    experiment_type,
                    int(trials),
                    now,
                    now,
                ),
            )
        item = self.get_job(job_id)
        if item is None:
            raise RuntimeError("created genome job could not be reloaded")
        return item

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE genome_jobs
                SET status = ?, result_json = ?, error = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    json.dumps(result, ensure_ascii=False) if result is not None else None,
                    error,
                    now,
                    job_id,
                ),
            )

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM genome_jobs WHERE id = ?",
                (job_id,),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["result"] = _loads(item.pop("result_json"), None)
        return item

    def list_jobs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM genome_jobs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (min(max(limit, 1), 500),),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["result"] = _loads(item.pop("result_json"), None)
            result.append(item)
        return result

    def stats(self) -> dict[str, Any]:
        with self._lock:
            gene_counts = {
                row["status"]: int(row["count"])
                for row in self._conn.execute(
                    """
                    SELECT status, COUNT(*) AS count
                    FROM genes
                    GROUP BY status
                    """
                ).fetchall()
            }
            kinds = {
                row["kind"]: int(row["count"])
                for row in self._conn.execute(
                    """
                    SELECT kind, COUNT(*) AS count
                    FROM genes
                    GROUP BY kind
                    """
                ).fetchall()
            }
            evidence = int(
                self._conn.execute(
                    "SELECT COUNT(*) AS count FROM gene_evidence"
                ).fetchone()["count"]
            )
            invariants = int(
                self._conn.execute(
                    "SELECT COUNT(*) AS count FROM invariants WHERE status = 'active'"
                ).fetchone()["count"]
            )
        return {
            "database": str(self.database_path),
            "genes_by_status": gene_counts,
            "genes_by_kind": kinds,
            "evidence_records": evidence,
            "active_invariants": invariants,
        }
