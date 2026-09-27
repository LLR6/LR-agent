from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
    def __init__(self, database_path: Path):
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_id
                    ON messages(session_id, id);

                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    task TEXT NOT NULL,
                    plan_json TEXT,
                    status TEXT NOT NULL,
                    answer TEXT,
                    review_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS run_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    tool TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    preview TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES runs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_runs_session_id
                    ON runs(session_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_run_steps_run_id
                    ON run_steps(run_id, step_index);

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    session_id TEXT,
                    run_id TEXT,
                    status TEXT NOT NULL,
                    error TEXT,
                    result_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_created_at
                    ON tasks(created_at DESC);
                """
            )

    def create_session(self, title: str) -> str:
        session_id = uuid.uuid4().hex
        now = _now()
        clean_title = title.strip().replace("\n", " ")[:80] or "New session"
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO sessions(id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, clean_title, now, now),
            )
        return session_id

    def session_exists(self, session_id: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return row is not None

    def add_message(self, session_id: str, role: str, content: str) -> None:
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO messages(session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now),
            )
            self._conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )

    def recent_messages(self, session_id: str, limit: int = 12) -> list[dict[str, str]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT role, content FROM (
                    SELECT id, role, content
                    FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                )
                ORDER BY id ASC
                """,
                (session_id, limit),
            ).fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def get_messages(self, session_id: str, limit: int = 200) -> list[dict[str, str]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT role, content, created_at
                FROM messages
                WHERE session_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def start_run(
        self,
        session_id: str,
        *,
        mode: str,
        task: str,
        plan: dict[str, Any] | None,
    ) -> str:
        run_id = uuid.uuid4().hex
        now = _now()
        plan_json = json.dumps(plan, ensure_ascii=False) if plan is not None else None
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO runs(
                    id, session_id, mode, task, plan_json, status,
                    answer, review_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 'running', NULL, NULL, ?, ?)
                """,
                (run_id, session_id, mode, task, plan_json, now, now),
            )
        return run_id

    def add_run_step(
        self,
        run_id: str,
        *,
        step_index: int,
        tool: str,
        arguments: dict[str, Any],
        ok: bool,
        preview: str,
    ) -> None:
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO run_steps(
                    run_id, step_index, tool, arguments_json, ok, preview, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    step_index,
                    tool,
                    json.dumps(arguments, ensure_ascii=False),
                    1 if ok else 0,
                    preview,
                    now,
                ),
            )
            self._conn.execute(
                "UPDATE runs SET updated_at = ? WHERE id = ?",
                (now, run_id),
            )

    def finish_run(
        self,
        run_id: str,
        *,
        answer: str,
        review: dict[str, Any] | None,
        status: str = "completed",
    ) -> None:
        now = _now()
        review_json = json.dumps(review, ensure_ascii=False) if review is not None else None
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE runs
                SET status = ?, answer = ?, review_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, answer, review_json, now, run_id),
            )

    def list_runs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, session_id, mode, task, status, created_at, updated_at
                FROM runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, session_id, mode, task, plan_json, status,
                       answer, review_json, created_at, updated_at
                FROM runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            steps = self._conn.execute(
                """
                SELECT step_index, tool, arguments_json, ok, preview, created_at
                FROM run_steps
                WHERE run_id = ?
                ORDER BY step_index ASC
                """,
                (run_id,),
            ).fetchall()

        result = dict(row)
        plan_json = result.pop("plan_json")
        review_json = result.pop("review_json")
        result["plan"] = json.loads(plan_json) if plan_json else None
        result["review"] = json.loads(review_json) if review_json else None
        result["steps"] = [
            {
                "index": step["step_index"],
                "tool": step["tool"],
                "arguments": json.loads(step["arguments_json"]),
                "ok": bool(step["ok"]),
                "preview": step["preview"],
                "created_at": step["created_at"],
            }
            for step in steps
        ]
        return result


    def create_task_record(
        self,
        *,
        message: str,
        mode: str,
        session_id: str | None,
    ) -> str:
        task_id = uuid.uuid4().hex
        now = _now()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO tasks(
                    id, message, mode, session_id, run_id, status,
                    error, result_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, NULL, 'queued', NULL, NULL, ?, ?)
                """,
                (task_id, message, mode, session_id, now, now),
            )
        return task_id

    def update_task_record(
        self,
        task_id: str,
        *,
        status: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        error: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> None:
        updates: list[str] = []
        values: list[Any] = []
        if status is not None:
            updates.append("status = ?")
            values.append(status)
        if session_id is not None:
            updates.append("session_id = ?")
            values.append(session_id)
        if run_id is not None:
            updates.append("run_id = ?")
            values.append(run_id)
        if error is not None:
            updates.append("error = ?")
            values.append(error)
        if result is not None:
            updates.append("result_json = ?")
            values.append(json.dumps(result, ensure_ascii=False))
        updates.append("updated_at = ?")
        values.append(_now())
        values.append(task_id)

        with self._lock, self._conn:
            self._conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                values,
            )

    def get_task_record(self, task_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT id, message, mode, session_id, run_id, status,
                       error, result_json, created_at, updated_at
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        raw = result.pop("result_json")
        result["result"] = json.loads(raw) if raw else None
        return result

    def list_task_records(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, message, mode, session_id, run_id, status,
                       error, created_at, updated_at
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_incomplete_tasks_interrupted(self) -> int:
        now = _now()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                """
                UPDATE tasks
                SET status = 'interrupted',
                    error = COALESCE(error, 'Process restarted before task completed.'),
                    updated_at = ?
                WHERE status IN ('queued', 'running')
                """,
                (now,),
            )
        return int(cursor.rowcount)

    def list_sessions(self, limit: int = 50) -> list[dict[str, str]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM sessions
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
