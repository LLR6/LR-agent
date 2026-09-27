from __future__ import annotations

import math
import re
import sqlite3
import struct
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


def _pack_vector(vector: list[float]) -> bytes:
    if not vector:
        raise ValueError("embedding vector cannot be empty")
    return struct.pack(f"<{len(vector)}f", *vector)


def _unpack_vector(blob: bytes, dimensions: int) -> list[float]:
    if dimensions <= 0:
        raise ValueError("embedding dimensions must be positive")
    expected = dimensions * 4
    if len(blob) != expected:
        raise ValueError(
            f"embedding blob size mismatch: expected {expected}, got {len(blob)}"
        )
    return list(struct.unpack(f"<{dimensions}f", blob))


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return -1.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return -1.0
    return dot / (left_norm * right_norm)


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

                CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                    chunk_id INTEGER PRIMARY KEY,
                    model TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    vector BLOB NOT NULL,
                    FOREIGN KEY(chunk_id) REFERENCES knowledge_chunks(id)
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_path
                    ON knowledge_chunks(path);
                CREATE INDEX IF NOT EXISTS idx_knowledge_embeddings_model
                    ON knowledge_embeddings(model);
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
            return raw.decode("utf-8", errors="replace")

    def rebuild(self) -> dict[str, Any]:
        files = self._candidate_files()
        indexed_files = 0
        indexed_chunks = 0
        skipped_files = 0

        with self._lock, self._conn:
            self._conn.execute("DELETE FROM knowledge_embeddings")
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

                for line_start, line_end, chunk_content in _chunks(text):
                    cursor = self._conn.execute(
                        """
                        INSERT INTO knowledge_chunks(path, line_start, line_end, content)
                        VALUES (?, ?, ?, ?)
                        """,
                        (rel, line_start, line_end, chunk_content),
                    )
                    if self._fts_enabled:
                        self._conn.execute(
                            """
                            INSERT INTO knowledge_fts(path, line_start, line_end, content)
                            VALUES (?, ?, ?, ?)
                            """,
                            (rel, line_start, line_end, chunk_content),
                        )
                    if cursor.lastrowid is None:
                        raise RuntimeError("failed to allocate knowledge chunk id")
                    indexed_chunks += 1
                indexed_files += 1

        return {
            "indexed_files": indexed_files,
            "indexed_chunks": indexed_chunks,
            "skipped_files": skipped_files,
            "fts_enabled": self._fts_enabled,
            "embedded_chunks": 0,
            "root": str(self.root),
        }

    def embedding_inputs(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT id, path, line_start, line_end, content
                FROM knowledge_chunks
                ORDER BY id ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def replace_embeddings(
        self,
        *,
        model: str,
        records: list[tuple[int, list[float]]],
    ) -> int:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM knowledge_embeddings")
            for chunk_id, vector in records:
                self._conn.execute(
                    """
                    INSERT INTO knowledge_embeddings(chunk_id, model, dimensions, vector)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chunk_id, model, len(vector), _pack_vector(vector)),
                )
        return len(records)

    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = re.findall(r"[\w./:-]+", query, flags=re.UNICODE)
        tokens = [token for token in tokens if token.strip()][:20]
        if not tokens:
            cleaned = query.replace('"', " ").strip()
            return f'"{cleaned}"'
        return " OR ".join(f'"{token.replace(chr(34), " ")}"' for token in tokens)

    def _lexical_rows(self, query: str, limit: int) -> tuple[list[sqlite3.Row], str]:
        rows: list[sqlite3.Row] = []
        mode = "like"
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
        return rows, mode

    def search(self, query: str, limit: int = 8) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("query cannot be empty")
        limit = min(max(limit, 1), 50)

        with self._lock:
            rows, mode = self._lexical_rows(query, limit)

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

    def hybrid_search(
        self,
        query: str,
        query_vector: list[float],
        *,
        model: str,
        limit: int = 8,
        vector_weight: float = 0.45,
    ) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("query cannot be empty")
        if not query_vector:
            return self.search(query, limit=limit)

        limit = min(max(limit, 1), 50)
        vector_weight = min(max(float(vector_weight), 0.0), 1.0)
        lexical_limit = min(max(limit * 4, 20), 200)

        with self._lock:
            lexical_rows, lexical_mode = self._lexical_rows(query, lexical_limit)
            vector_rows = self._conn.execute(
                """
                SELECT c.id, c.path, c.line_start, c.line_end, c.content,
                       e.dimensions, e.vector
                FROM knowledge_embeddings e
                JOIN knowledge_chunks c ON c.id = e.chunk_id
                WHERE e.model = ?
                """,
                (model,),
            ).fetchall()

        lexical_scores: dict[tuple[str, int, int], float] = {}
        snippets: dict[tuple[str, int, int], str] = {}
        for rank, row in enumerate(lexical_rows, start=1):
            key = (row["path"], row["line_start"], row["line_end"])
            lexical_scores[key] = 1.0 / rank
            snippets[key] = row["snippet"]

        semantic: list[tuple[float, sqlite3.Row]] = []
        for row in vector_rows:
            if row["dimensions"] != len(query_vector):
                continue
            try:
                vector = _unpack_vector(row["vector"], row["dimensions"])
            except ValueError:
                continue
            semantic.append((_cosine_similarity(query_vector, vector), row))
        semantic.sort(key=lambda item: item[0], reverse=True)
        semantic = semantic[:lexical_limit]

        vector_scores: dict[tuple[str, int, int], float] = {}
        rows_by_key: dict[tuple[str, int, int], sqlite3.Row] = {}
        for cosine, row in semantic:
            key = (row["path"], row["line_start"], row["line_end"])
            vector_scores[key] = max(0.0, min(1.0, (cosine + 1.0) / 2.0))
            rows_by_key[key] = row
            snippets.setdefault(key, row["content"][:700])

        combined: list[tuple[float, tuple[str, int, int]]] = []
        for key in set(lexical_scores) | set(vector_scores):
            lexical_score = lexical_scores.get(key, 0.0)
            vector_score = vector_scores.get(key, 0.0)
            score = (
                (1.0 - vector_weight) * lexical_score
                + vector_weight * vector_score
            )
            combined.append((score, key))
        combined.sort(key=lambda item: item[0], reverse=True)

        results = []
        for score, key in combined[:limit]:
            path, line_start, line_end = key
            results.append(
                {
                    "path": path,
                    "line_start": line_start,
                    "line_end": line_end,
                    "snippet": snippets.get(key, ""),
                    "score": score,
                    "lexical_score": lexical_scores.get(key, 0.0),
                    "vector_score": vector_scores.get(key, 0.0),
                }
            )

        if not results:
            return self.search(query, limit=limit)

        return {
            "query": query,
            "mode": f"hybrid:{lexical_mode}+embedding",
            "embedding_model": model,
            "vector_weight": vector_weight,
            "results": results,
        }

    def stats(self) -> dict[str, Any]:
        with self._lock:
            files = self._conn.execute(
                "SELECT COUNT(*) AS count FROM knowledge_files"
            ).fetchone()["count"]
            chunks = self._conn.execute(
                "SELECT COUNT(*) AS count FROM knowledge_chunks"
            ).fetchone()["count"]
            embeddings = self._conn.execute(
                "SELECT COUNT(*) AS count FROM knowledge_embeddings"
            ).fetchone()["count"]
            models = [
                row["model"]
                for row in self._conn.execute(
                    """
                    SELECT DISTINCT model
                    FROM knowledge_embeddings
                    ORDER BY model
                    """
                ).fetchall()
            ]
        return {
            "files": int(files),
            "chunks": int(chunks),
            "embeddings": int(embeddings),
            "embedding_models": models,
            "fts_enabled": self._fts_enabled,
            "database": str(self.database_path),
        }
