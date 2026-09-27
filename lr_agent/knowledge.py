from __future__ import annotations

import re
import sqlite3
import threading
from pathlib import Path
from typing import Any


DEFAULT_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "data",
}


def _looks_binary(sample: bytes) -> bool:
    return b"\x00" in sample


def _chunks(text: str, *, max_chars: int = 8000) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    if not lines:
        return [(1, 1, "")]

    result: list[tuple[int, int, str]] = []
    start = 0
    while start < len(lines):
        end = start
        size = 0
        while end < len(lines):
            line_size = len(lines[end]) + 1
            if end > start and size + line_size > max_chars:
                break
            size += line_size
            end += 1
        content = "\n".join(lines[start:end])
        result.append((start + 1, end, content))
        start = end
    return result


class KnowledgeIndex:
    def __init__(
        self,
        root: Path,
        database_path: Path,
        *,
        max_files: int = 3000,
        max_file_bytes: int = 1_000_000,
    ):
        self.root = root.resolve()
        self.database_path = database_path
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._fts_enabled = False
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS knowledge_files (
                    path TEXT PRIMARY KEY,
                    mtime_ns INTEGER NOT NULL,
                    size INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT NOT NULL,
                    line_start INTEGER NOT NULL,
                    line_end INTEGER NOT NULL,
                    content TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_path
                    ON knowledge_chunks(path);
                """
            )
            try:
                self._conn.execute(
                    """
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
                    USING fts5(
                        path UNINDEXED,
                        line_start UNINDEXED,
                        line_end UNINDEXED,
                        content,
                        tokenize='unicode61'
                    )
                    """
                )
                self._fts_enabled = True
            except sqlite3.OperationalError:
                self._fts_enabled = False

    def _candidate_files(self) -> list[Path]:
        candidates: list[Path] = []
        for path in self.root.rglob("*"):
            if len(candidates) >= self.max_files:
                break
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(self.root)
            except ValueError:
                continue
            if any(part in DEFAULT_EXCLUDES for part in rel.parts):
                continue
            try:
                if path.stat().st_size > self.max_file_bytes:
                    continue
            except OSError:
                continue
            candidates.append(path)
        return candidates

    def _read_text(self, path: Path) -> str | None:
        try:
            raw = path.read_bytes()
        except OSError:
            return None
        if _looks_binary(raw[:4096]):
            return None
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return raw.decode("utf-8", errors="replace")
            except Exception:
                return None

    def rebuild(self) -> dict[str, Any]:
        files = self._candidate_files()
        indexed_files = 0
        indexed_chunks = 0
        skipped_files = 0

        with self._lock, self._conn:
            self._conn.execute("DELETE FROM knowledge_files")
            self._conn.execute("DELETE FROM knowledge_chunks")
            if self._fts_enabled:
                self._conn.execute("DELETE FROM knowledge_fts")

            for path in files:
                text = self._read_text(path)
                if text is None:
                    skipped_files += 1
                    continue
                try:
                    stat = path.stat()
                    rel = path.relative_to(self.root).as_posix()
                except (OSError, ValueError):
                    skipped_files += 1
                    continue

                self._conn.execute(
                    """
                    INSERT INTO knowledge_files(path, mtime_ns, size)
                    VALUES (?, ?, ?)
                    """,
                    (rel, stat.st_mtime_ns, stat.st_size),
                )

                chunks = _chunks(text)
                for line_start, line_end, content in chunks:
                    self._conn.execute(
                        """
                        INSERT INTO knowledge_chunks(path, line_start, line_end, content)
                        VALUES (?, ?, ?, ?)
                        """,
                        (rel, line_start, line_end, content),
                    )
                    if self._fts_enabled:
                        self._conn.execute(
                            """
                            INSERT INTO knowledge_fts(path, line_start, line_end, content)
                            VALUES (?, ?, ?, ?)
                            """,
                            (rel, line_start, line_end, content),
                        )
                    indexed_chunks += 1
                indexed_files += 1

        return {
            "indexed_files": indexed_files,
            "indexed_chunks": indexed_chunks,
            "skipped_files": skipped_files,
            "fts_enabled": self._fts_enabled,
            "root": str(self.root),
        }

    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = re.findall(r"[\w./:-]+", query, flags=re.UNICODE)
        tokens = [token for token in tokens if token.strip()][:20]
        if not tokens:
            cleaned = query.replace('"', " ").strip()
            return f'"{cleaned}"'
        return " OR ".join(f'"{token.replace(chr(34), " ")}"' for token in tokens)

    def search(self, query: str, limit: int = 8) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("query cannot be empty")
        limit = min(max(limit, 1), 50)

        rows: list[sqlite3.Row] = []
        mode = "like"
        with self._lock:
            if self._fts_enabled:
                try:
                    rows = self._conn.execute(
                        """
                        SELECT path, line_start, line_end,
                               snippet(knowledge_fts, 3, '[', ']', ' … ', 24) AS snippet,
                               bm25(knowledge_fts) AS score
                        FROM knowledge_fts
                        WHERE knowledge_fts MATCH ?
                        ORDER BY score
                        LIMIT ?
                        """,
                        (self._fts_query(query), limit),
                    ).fetchall()
                    mode = "fts5"
                except sqlite3.OperationalError:
                    rows = []

            if not rows:
                rows = self._conn.execute(
                    """
                    SELECT path, line_start, line_end,
                           substr(content, 1, 700) AS snippet,
                           NULL AS score
                    FROM knowledge_chunks
                    WHERE content LIKE ?
                    LIMIT ?
                    """,
                    (f"%{query}%", limit),
                ).fetchall()
                mode = "like"

        return {
            "query": query,
            "mode": mode,
            "results": [
                {
                    "path": row["path"],
                    "line_start": row["line_start"],
                    "line_end": row["line_end"],
                    "snippet": row["snippet"],
                    "score": row["score"],
                }
                for row in rows
            ],
        }

    def stats(self) -> dict[str, Any]:
        with self._lock:
            files = self._conn.execute(
                "SELECT COUNT(*) AS count FROM knowledge_files"
            ).fetchone()["count"]
            chunks = self._conn.execute(
                "SELECT COUNT(*) AS count FROM knowledge_chunks"
            ).fetchone()["count"]
        return {
            "files": int(files),
            "chunks": int(chunks),
            "fts_enabled": self._fts_enabled,
            "database": str(self.database_path),
        }
