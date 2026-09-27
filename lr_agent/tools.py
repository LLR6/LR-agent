from __future__ import annotations

import asyncio
import base64
import difflib
import hashlib
import json
import ipaddress
import os
import shutil
import socket
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import httpx

from .config import Settings
from .embeddings import EmbeddingError, OpenAICompatibleEmbeddingClient
from .knowledge import KnowledgeIndex


class ToolError(RuntimeError):
    pass


class ToolRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.workspace.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.mutation_lock = asyncio.Lock()
        self.knowledge = KnowledgeIndex(
            self.root,
            settings.knowledge_database,
            max_files=settings.knowledge_max_files,
            max_file_bytes=settings.knowledge_max_file_bytes,
        )
        self.embedder = (
            OpenAICompatibleEmbeddingClient(settings)
            if settings.knowledge_embeddings
            else None
        )

    def specs(self) -> list[dict[str, Any]]:
        return [
            self._spec(
                "list_files",
                "List files inside the agent workspace.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                        "recursive": {"type": "boolean", "default": False},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 200},
                    },
                },
            ),
            self._spec(
                "search_files",
                "Search for a text substring across UTF-8 files inside the workspace.",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "path": {"type": "string", "default": "."},
                        "glob": {"type": "string", "default": "*"},
                        "case_sensitive": {"type": "boolean", "default": False},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
                    },
                    "required": ["query"],
                },
            ),
            self._spec(
                "read_file",
                "Read a UTF-8 text file inside the agent workspace.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "start_line": {"type": "integer", "minimum": 1},
                        "end_line": {"type": "integer", "minimum": 1},
                        "max_chars": {"type": "integer", "minimum": 1, "maximum": 200000, "default": 50000},
                    },
                    "required": ["path"],
                },
            ),
            self._spec(
                "write_file",
                "Create or overwrite a UTF-8 text file inside the workspace.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "overwrite": {"type": "boolean", "default": False},
                    },
                    "required": ["path", "content"],
                },
            ),
            self._spec(
                "delete_file",
                "Delete one file inside the workspace. Directories cannot be deleted by this tool.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
            self._spec(
                "move_file",
                "Move or rename one file inside the workspace.",
                {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"},
                        "overwrite": {"type": "boolean", "default": False},
                    },
                    "required": ["source", "destination"],
                },
            ),
            self._spec(
                "make_directory",
                "Create a directory inside the workspace.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"],
                },
            ),
            self._spec(
                "replace_in_file",
                "Replace exact text in a UTF-8 file. Fails when the expected occurrence count does not match.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old": {"type": "string"},
                        "new": {"type": "string"},
                        "expected_count": {"type": "integer", "minimum": 1, "default": 1},
                    },
                    "required": ["path", "old", "new"],
                },
            ),
            self._spec(
                "project_inspect",
                "Inspect a workspace project and identify its technology stack, manifests and likely verification commands without executing them.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "default": "."},
                    },
                },
            ),
            self._spec(
                "git_status",
                "Show concise git status for a repository inside the workspace.",
                {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string", "default": "."},
                    },
                },
            ),
            self._spec(
                "git_diff",
                "Show git diff for a repository inside the workspace without changing files.",
                {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string", "default": "."},
                        "staged": {"type": "boolean", "default": False},
                        "path": {"type": "string", "default": ""},
                    },
                },
            ),
            self._spec(
                "run_command",
                "Run an allowlisted executable in the workspace without invoking a shell.",
                {
                    "type": "object",
                    "properties": {
                        "argv": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "cwd": {"type": "string", "default": "."},
                        "timeout_s": {"type": "number", "minimum": 1, "maximum": 300},
                    },
                    "required": ["argv"],
                },
            ),
            self._spec(
                "http_get",
                "Fetch a public HTTP(S) URL as text. Private/local network targets are blocked by default.",
                {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "max_chars": {"type": "integer", "minimum": 1, "maximum": 100000, "default": 30000},
                    },
                    "required": ["url"],
                },
            ),
            self._spec(
                "knowledge_index",
                "Build or rebuild a persistent searchable index of text files in the workspace.",
                {
                    "type": "object",
                    "properties": {},
                },
            ),
            self._spec(
                "knowledge_search",
                "Search the persistent workspace knowledge index. Run knowledge_index first when the index is empty or stale.",
                {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 8},
                    },
                    "required": ["query"],
                },
            ),
            self._spec(
                "knowledge_stats",
                "Return statistics about the persistent workspace knowledge index.",
                {
                    "type": "object",
                    "properties": {},
                },
            ),
            self._spec(
                "github_get_repo",
                "Read GitHub repository metadata through the GitHub REST API.",
                {
                    "type": "object",
                    "properties": {"repo": {"type": "string", "description": "owner/name"}},
                    "required": ["repo"],
                },
            ),
            self._spec(
                "github_list_contents",
                "List files/directories in a GitHub repository path without cloning it.",
                {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "owner/name"},
                        "path": {"type": "string", "default": ""},
                        "ref": {"type": "string", "default": ""},
                    },
                    "required": ["repo"],
                },
            ),
            self._spec(
                "github_read_file",
                "Read a UTF-8 text file from a GitHub repository without cloning it.",
                {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "owner/name"},
                        "path": {"type": "string"},
                        "ref": {"type": "string", "default": ""},
                        "max_chars": {"type": "integer", "minimum": 1, "maximum": 200000, "default": 50000},
                    },
                    "required": ["repo", "path"],
                },
            ),
            self._spec(
                "github_create_issue",
                "Create a GitHub issue. Disabled unless LR_AGENT_ALLOW_GITHUB_WRITE=true and a GitHub token is configured.",
                {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "owner/name"},
                        "title": {"type": "string"},
                        "body": {"type": "string", "default": ""},
                    },
                    "required": ["repo", "title"],
                },
            ),
            self._spec(
                "github_create_branch",
                "Create a GitHub branch from an existing branch/ref. GitHub writes must be enabled.",
                {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "owner/name"},
                        "branch": {"type": "string"},
                        "base_ref": {"type": "string", "default": ""},
                    },
                    "required": ["repo", "branch"],
                },
            ),
            self._spec(
                "github_put_file",
                "Create or update a UTF-8 text file through the GitHub Contents API. Read the file first and pass sha when updating an existing file.",
                {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "owner/name"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "message": {"type": "string"},
                        "branch": {"type": "string"},
                        "sha": {"type": "string", "default": ""},
                    },
                    "required": ["repo", "path", "content", "message", "branch"],
                },
            ),
            self._spec(
                "github_create_pull_request",
                "Create a GitHub pull request from head to base. GitHub writes must be enabled.",
                {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "owner/name"},
                        "title": {"type": "string"},
                        "head": {"type": "string"},
                        "base": {"type": "string"},
                        "body": {"type": "string", "default": ""},
                        "draft": {"type": "boolean", "default": False},
                    },
                    "required": ["repo", "title", "head", "base"],
                },
            ),
            self._spec(
                "github_list_workflow_runs",
                "List recent GitHub Actions workflow runs for a repository.",
                {
                    "type": "object",
                    "properties": {
                        "repo": {"type": "string", "description": "owner/name"},
                        "branch": {"type": "string", "default": ""},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                    },
                    "required": ["repo"],
                },
            ),
        ]

    @staticmethod
    def _spec(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }

    LOCAL_MUTATION_TOOLS = {
        "write_file",
        "delete_file",
        "move_file",
        "make_directory",
        "replace_in_file",
    }

    def is_local_mutation(self, name: str) -> bool:
        return name in self.LOCAL_MUTATION_TOOLS

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def _missing_parent_paths(self, target: Path) -> list[str]:
        missing: list[Path] = []
        current = target.parent
        while current != self.root and not current.exists():
            if self.root not in current.parents:
                break
            missing.append(current)
            current = current.parent
        return [self._relative(path) for path in reversed(missing)]

    def mutation_snapshot_paths(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> list[str]:
        if name not in self.LOCAL_MUTATION_TOOLS:
            return []

        paths: list[str] = []
        if name in {"write_file", "replace_in_file", "delete_file"}:
            target = self._safe_path(str(arguments.get("path", "")))
            if name == "write_file":
                paths.extend(self._missing_parent_paths(target))
            paths.append(self._relative(target))
        elif name == "make_directory":
            target = self._safe_path(str(arguments.get("path", "")))
            paths.extend(self._missing_parent_paths(target))
            paths.append(self._relative(target))
        elif name == "move_file":
            source = self._safe_path(str(arguments.get("source", "")))
            destination = self._safe_path(str(arguments.get("destination", "")))
            paths.append(self._relative(source))
            paths.extend(self._missing_parent_paths(destination))
            paths.append(self._relative(destination))

        deduped: list[str] = []
        seen: set[str] = set()
        for path in paths:
            if path not in seen:
                seen.add(path)
                deduped.append(path)
        return deduped

    def capture_path_snapshot(
        self,
        path: str,
        *,
        max_file_bytes: int,
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.exists():
            return {
                "path": path,
                "kind": "missing",
                "content": None,
                "mode": None,
                "hash": None,
            }

        stat_result = target.stat()
        mode = stat_result.st_mode & 0o7777
        if target.is_dir():
            return {
                "path": path,
                "kind": "dir",
                "content": None,
                "mode": mode,
                "hash": None,
            }
        if not target.is_file():
            raise ToolError(f"Unsupported snapshot path type: {path}")
        if stat_result.st_size > max_file_bytes:
            raise ToolError(
                f"Refusing mutation because rollback snapshot for '{path}' is "
                f"{stat_result.st_size} bytes, above LR_AGENT_SNAPSHOT_MAX_FILE_BYTES="
                f"{max_file_bytes}."
            )
        content = target.read_bytes()
        return {
            "path": path,
            "kind": "file",
            "content": content,
            "mode": mode,
            "hash": hashlib.sha256(content).hexdigest(),
        }

    def current_path_state(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.exists():
            return {"path": path, "kind": "missing", "hash": None}
        if target.is_dir():
            return {"path": path, "kind": "dir", "hash": None}
        if not target.is_file():
            return {"path": path, "kind": "other", "hash": None}
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return {"path": path, "kind": "file", "hash": digest.hexdigest()}

    def restore_path_snapshot(self, snapshot: dict[str, Any]) -> None:
        path = str(snapshot["path"])
        target = self._safe_path(path)
        original_kind = str(snapshot["original_kind"])

        if original_kind == "missing":
            if target.is_file():
                target.unlink()
            elif target.is_dir():
                try:
                    target.rmdir()
                except OSError as exc:
                    raise ToolError(
                        f"Cannot remove non-empty directory during rollback: {path}"
                    ) from exc
            elif target.exists():
                raise ToolError(f"Unsupported rollback target type: {path}")
            return

        if original_kind == "dir":
            if target.is_file():
                target.unlink()
            elif target.exists() and not target.is_dir():
                raise ToolError(f"Unsupported rollback target type: {path}")
            target.mkdir(parents=True, exist_ok=True)
            mode = snapshot.get("original_mode")
            if mode is not None:
                target.chmod(int(mode))
            return

        if original_kind == "file":
            if target.is_dir():
                try:
                    target.rmdir()
                except OSError as exc:
                    raise ToolError(
                        f"Cannot replace non-empty directory during rollback: {path}"
                    ) from exc
            elif target.exists() and not target.is_file():
                raise ToolError(f"Unsupported rollback target type: {path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            content = snapshot.get("original_content")
            if content is None:
                content = b""
            target.write_bytes(bytes(content))
            mode = snapshot.get("original_mode")
            if mode is not None:
                target.chmod(int(mode))
            return

        raise ToolError(f"Unknown snapshot kind for {path}: {original_kind}")

    def _requires_approval(self, name: str) -> bool:
        mode = self.settings.normalized_approval_mode
        if mode == "off":
            return False
        write_tools = {
            "write_file",
            "delete_file",
            "move_file",
            "make_directory",
            "replace_in_file",
            "github_create_issue",
            "github_create_branch",
            "github_put_file",
            "github_create_pull_request",
        }
        if name in write_tools:
            return True
        return mode == "all" and name == "run_command"

    def _approval_preview(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "write_file":
            path = str(arguments.get("path", ""))
            content = str(arguments.get("content", ""))
            target = self._safe_path(path)
            old = (
                target.read_text(encoding="utf-8", errors="replace")
                if target.is_file()
                else ""
            )
            diff, truncated = self._text_diff(old, content, path)
            suffix = "\n[diff truncated]" if truncated else ""
            return (diff or f"Create or replace {path} ({len(content)} chars)") + suffix

        if name == "delete_file":
            path = str(arguments.get("path", ""))
            target = self._safe_path(path)
            if target.is_file():
                old = target.read_text(encoding="utf-8", errors="replace")
                diff, truncated = self._text_diff(old, "", path)
                suffix = "\n[diff truncated]" if truncated else ""
                return (diff or f"Delete file {path}") + suffix
            return f"Delete file {path}"

        if name == "move_file":
            return json.dumps(
                {
                    "action": "move_file",
                    "source": arguments.get("source"),
                    "destination": arguments.get("destination"),
                    "overwrite": bool(arguments.get("overwrite", False)),
                },
                ensure_ascii=False,
                indent=2,
            )

        if name == "make_directory":
            return f"Create directory: {arguments.get('path', '')}"

        if name == "replace_in_file":
            path = str(arguments.get("path", ""))
            old_text = str(arguments.get("old", ""))
            new_text = str(arguments.get("new", ""))
            target = self._safe_path(path)
            if not target.is_file():
                return f"Replace text in missing file: {path}"
            text = target.read_text(encoding="utf-8", errors="replace")
            updated = text.replace(old_text, new_text)
            diff, truncated = self._text_diff(text, updated, path)
            suffix = "\n[diff truncated]" if truncated else ""
            return (diff or f"No textual diff for {path}") + suffix

        if name == "run_command":
            argv = arguments.get("argv", [])
            cwd = arguments.get("cwd", ".")
            return f"cwd={cwd}\n$ " + " ".join(str(x) for x in argv)

        safe = dict(arguments)
        if "content" in safe:
            content = str(safe["content"])
            safe["content"] = content[:2000] + ("..." if len(content) > 2000 else "")
        return json.dumps({"tool": name, "arguments": safe}, ensure_ascii=False, indent=2)[:12000]

    def _safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ToolError(f"Path escapes workspace: {relative}")
        return candidate

    async def rebuild_knowledge(self) -> dict[str, Any]:
        result = await asyncio.to_thread(self.knowledge.rebuild)
        if self.embedder is None:
            result["embedding_enabled"] = False
            return result

        chunks = await asyncio.to_thread(self.knowledge.embedding_inputs)
        if not chunks:
            result["embedding_enabled"] = True
            result["embedding_model"] = self.embedder.model
            result["embedded_chunks"] = 0
            return result

        batch_size = min(max(self.settings.embedding_batch_size, 1), 128)
        records: list[tuple[int, list[float]]] = []
        try:
            for start in range(0, len(chunks), batch_size):
                batch = chunks[start : start + batch_size]
                texts = [
                    (
                        f"FILE: {item['path']}\n"
                        f"LINES: {item['line_start']}-{item['line_end']}\n"
                        f"{item['content']}"
                    )
                    for item in batch
                ]
                vectors = await self.embedder.embed(texts)
                records.extend(
                    (int(item["id"]), vector)
                    for item, vector in zip(batch, vectors, strict=True)
                )
            stored = await asyncio.to_thread(
                self.knowledge.replace_embeddings,
                model=self.embedder.model,
                records=records,
            )
        except EmbeddingError as exc:
            result["embedding_enabled"] = True
            result["embedding_model"] = self.embedder.model
            result["embedding_error"] = str(exc)
            result["embedded_chunks"] = 0
            return result

        result["embedding_enabled"] = True
        result["embedding_model"] = self.embedder.model
        result["embedded_chunks"] = stored
        return result

    async def search_knowledge(
        self,
        query: str,
        limit: int = 8,
    ) -> dict[str, Any]:
        if self.embedder is None:
            return await asyncio.to_thread(self.knowledge.search, query, limit)

        stats = await asyncio.to_thread(self.knowledge.stats)
        models = set(stats.get("embedding_models") or [])
        if stats.get("embeddings", 0) <= 0 or self.embedder.model not in models:
            result = await asyncio.to_thread(self.knowledge.search, query, limit)
            result["embedding_fallback"] = "index has no embeddings for configured model"
            return result

        try:
            query_vector = (await self.embedder.embed([query]))[0]
        except EmbeddingError as exc:
            result = await asyncio.to_thread(self.knowledge.search, query, limit)
            result["embedding_fallback"] = str(exc)
            return result

        return await asyncio.to_thread(
            self.knowledge.hybrid_search,
            query,
            query_vector,
            model=self.embedder.model,
            limit=limit,
            vector_weight=self.settings.hybrid_vector_weight,
        )

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        approval_handler: Callable[[str, dict[str, Any], str], Awaitable[bool]] | None = None,
        event_handler: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        try:
            if self._requires_approval(name):
                preview = self._approval_preview(name, arguments)
                if approval_handler is None:
                    raise ToolError(
                        f"Tool '{name}' requires interactive approval, but no approval handler is available."
                    )
                approved = await approval_handler(name, arguments, preview)
                if not approved:
                    raise ToolError(f"Tool '{name}' was denied by the user.")
            if name == "list_files":
                value = self._list_files(**arguments)
            elif name == "search_files":
                value = self._search_files(**arguments)
            elif name == "read_file":
                value = self._read_file(**arguments)
            elif name == "write_file":
                value = self._write_file(**arguments)
            elif name == "delete_file":
                value = self._delete_file(**arguments)
            elif name == "move_file":
                value = self._move_file(**arguments)
            elif name == "make_directory":
                value = self._make_directory(**arguments)
            elif name == "replace_in_file":
                value = self._replace_in_file(**arguments)
            elif name == "project_inspect":
                value = self._project_inspect(**arguments)
            elif name == "git_status":
                value = await self._git_status(**arguments)
            elif name == "git_diff":
                value = await self._git_diff(**arguments)
            elif name == "run_command":
                value = await self._run_command(
                    **arguments,
                    event_handler=event_handler,
                )
            elif name == "http_get":
                value = await self._http_get(**arguments)
            elif name == "knowledge_index":
                value = await self.rebuild_knowledge()
            elif name == "knowledge_search":
                value = await self.search_knowledge(**arguments)
            elif name == "knowledge_stats":
                value = await asyncio.to_thread(self.knowledge.stats)
            elif name == "github_get_repo":
                value = await self._github_get_repo(**arguments)
            elif name == "github_list_contents":
                value = await self._github_list_contents(**arguments)
            elif name == "github_read_file":
                value = await self._github_read_file(**arguments)
            elif name == "github_create_issue":
                value = await self._github_create_issue(**arguments)
            elif name == "github_create_branch":
                value = await self._github_create_branch(**arguments)
            elif name == "github_put_file":
                value = await self._github_put_file(**arguments)
            elif name == "github_create_pull_request":
                value = await self._github_create_pull_request(**arguments)
            elif name == "github_list_workflow_runs":
                value = await self._github_list_workflow_runs(**arguments)
            else:
                raise ToolError(f"Unknown tool: {name}")
            return {"ok": True, "result": value}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def _list_files(
        self, path: str = ".", recursive: bool = False, limit: int = 200
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.exists():
            raise ToolError(f"Path does not exist: {path}")
        if target.is_file():
            return {"items": [target.relative_to(self.root).as_posix()], "truncated": False}

        iterator = target.rglob("*") if recursive else target.iterdir()
        items: list[str] = []
        for item in iterator:
            if len(items) >= limit:
                break
            suffix = "/" if item.is_dir() else ""
            items.append(item.relative_to(self.root).as_posix() + suffix)
        items.sort()
        return {"items": items, "truncated": len(items) >= limit}

    def _search_files(
        self,
        query: str,
        path: str = ".",
        glob: str = "*",
        case_sensitive: bool = False,
        limit: int = 100,
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.exists():
            raise ToolError(f"Path does not exist: {path}")
        if not query:
            raise ToolError("query cannot be empty")

        needle = query if case_sensitive else query.lower()
        matches: list[dict[str, Any]] = []
        candidates = [target] if target.is_file() else target.rglob(glob)
        scanned = 0

        for file in candidates:
            if not file.is_file():
                continue
            try:
                if file.stat().st_size > 2_000_000:
                    continue
                text = file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            scanned += 1
            for line_number, line in enumerate(text.splitlines(), start=1):
                haystack = line if case_sensitive else line.lower()
                if needle in haystack:
                    matches.append(
                        {
                            "path": file.relative_to(self.root).as_posix(),
                            "line": line_number,
                            "text": line[:500],
                        }
                    )
                    if len(matches) >= limit:
                        return {
                            "matches": matches,
                            "scanned_files": scanned,
                            "truncated": True,
                        }

        return {"matches": matches, "scanned_files": scanned, "truncated": False}

    def _read_file(
        self,
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
        max_chars: int = 50000,
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.is_file():
            raise ToolError(f"Not a file: {path}")
        text = target.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines(keepends=True)

        if start_line is not None or end_line is not None:
            start = (start_line or 1) - 1
            end = end_line if end_line is not None else len(lines)
            if end < start + 1:
                raise ToolError("end_line must be greater than or equal to start_line")
            selected = "".join(lines[start:end])
            actual_start = start + 1
            actual_end = min(end, len(lines))
        else:
            selected = text
            actual_start = 1
            actual_end = len(lines)

        return {
            "path": target.relative_to(self.root).as_posix(),
            "content": selected[:max_chars],
            "truncated": len(selected) > max_chars,
            "chars": len(selected),
            "total_chars": len(text),
            "line_start": actual_start,
            "line_end": actual_end,
            "total_lines": len(lines),
        }

    def _project_inspect(self, path: str = ".") -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.is_dir():
            raise ToolError(f"Project path is not a directory: {path}")

        stacks: list[str] = []
        manifests: list[str] = []
        checks: list[dict[str, Any]] = []

        def has(name: str) -> bool:
            return (target / name).exists()

        def add_check(argv: list[str], reason: str) -> None:
            item = {"argv": argv, "reason": reason}
            if item not in checks:
                checks.append(item)

        python_markers = ["pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"]
        for marker in python_markers:
            if has(marker):
                manifests.append(marker)
        if any(has(marker) for marker in python_markers) or has("tests"):
            stacks.append("python")
            if has("tests") or has("pytest.ini") or has("pyproject.toml"):
                add_check(["pytest"], "Run the Python test suite.")

        if has("package.json"):
            stacks.append("node")
            manifests.append("package.json")
            try:
                package = json.loads((target / "package.json").read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                package = {}
            scripts = package.get("scripts") if isinstance(package, dict) else {}
            if isinstance(scripts, dict):
                for script in ("test", "lint", "typecheck", "build"):
                    if script in scripts:
                        add_check(["npm", "run", script], f"Run package.json script '{script}'.")

        if has("Cargo.toml"):
            stacks.append("rust")
            manifests.append("Cargo.toml")
            add_check(["cargo", "test"], "Run Rust tests.")
            add_check(["cargo", "check"], "Run Rust type/build checks.")

        if has("go.mod"):
            stacks.append("go")
            manifests.append("go.mod")
            add_check(["go", "test", "./..."], "Run Go tests.")

        if has("pom.xml"):
            stacks.append("maven")
            manifests.append("pom.xml")
            add_check(["mvn", "test"], "Run Maven tests.")

        gradle_markers = [
            "build.gradle",
            "build.gradle.kts",
            "settings.gradle",
            "settings.gradle.kts",
            "gradlew",
            "gradlew.bat",
        ]
        for marker in gradle_markers:
            if has(marker):
                manifests.append(marker)
        if any(has(marker) for marker in gradle_markers):
            stacks.append("gradle")
            if has("gradlew"):
                add_check(["./gradlew", "test"], "Run Gradle tests using the project wrapper.")
            elif has("gradlew.bat"):
                add_check(["gradlew.bat", "test"], "Run Gradle tests using the Windows wrapper.")
            else:
                add_check(["gradle", "test"], "Run Gradle tests.")

        if has("CMakeLists.txt"):
            stacks.append("cmake")
            manifests.append("CMakeLists.txt")

        if has(".git"):
            stacks.append("git")
            add_check(["git", "status", "--short"], "Inspect the working tree before and after edits.")
            add_check(["git", "diff"], "Review unstaged changes.")

        top_level = []
        try:
            top_level = sorted(
                item.name + ("/" if item.is_dir() else "")
                for item in target.iterdir()
            )[:100]
        except OSError:
            pass

        return {
            "path": target.relative_to(self.root).as_posix() or ".",
            "stacks": stacks,
            "manifests": sorted(set(manifests)),
            "recommended_checks": checks,
            "top_level": top_level,
        }

    @staticmethod
    def _text_diff(old: str, new: str, path: str, max_chars: int = 12000) -> tuple[str, bool]:
        diff = "".join(
            difflib.unified_diff(
                old.splitlines(keepends=True),
                new.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        return diff[:max_chars], len(diff) > max_chars

    def _write_file(
        self, path: str, content: str, overwrite: bool = False
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        existed = target.exists()
        if existed and not overwrite:
            raise ToolError(f"File already exists: {path}. Set overwrite=true to replace it.")
        old = target.read_text(encoding="utf-8", errors="replace") if existed else ""
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        rel = target.relative_to(self.root).as_posix()
        diff, diff_truncated = self._text_diff(old, content, rel)
        return {
            "path": rel,
            "chars": len(content),
            "overwritten": existed,
            "diff": diff,
            "diff_truncated": diff_truncated,
        }

    def _delete_file(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.exists():
            raise ToolError(f"File does not exist: {path}")
        if not target.is_file():
            raise ToolError("delete_file only deletes files, not directories")
        size = target.stat().st_size
        rel = target.relative_to(self.root).as_posix()
        target.unlink()
        return {"path": rel, "deleted": True, "bytes": size}

    def _move_file(
        self,
        source: str,
        destination: str,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        src = self._safe_path(source)
        dst = self._safe_path(destination)
        if not src.exists() or not src.is_file():
            raise ToolError(f"Source is not a file: {source}")
        if dst.exists() and not overwrite:
            raise ToolError(
                f"Destination already exists: {destination}. Set overwrite=true to replace it."
            )
        if dst.exists() and dst.is_dir():
            raise ToolError("Destination is a directory")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            dst.unlink()
        src_rel = src.relative_to(self.root).as_posix()
        dst_rel = dst.relative_to(self.root).as_posix()
        shutil.move(str(src), str(dst))
        return {
            "source": src_rel,
            "destination": dst_rel,
            "moved": True,
        }

    def _make_directory(self, path: str) -> dict[str, Any]:
        target = self._safe_path(path)
        existed = target.exists()
        if existed and not target.is_dir():
            raise ToolError(f"Path exists and is not a directory: {path}")
        target.mkdir(parents=True, exist_ok=True)
        return {
            "path": target.relative_to(self.root).as_posix(),
            "created": not existed,
        }

    def _replace_in_file(
        self,
        path: str,
        old: str,
        new: str,
        expected_count: int = 1,
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.is_file():
            raise ToolError(f"Not a file: {path}")
        text = target.read_text(encoding="utf-8", errors="strict")
        count = text.count(old)
        if count != expected_count:
            raise ToolError(
                f"Expected {expected_count} occurrence(s), found {count}; file was not changed."
            )
        updated = text.replace(old, new)
        target.write_text(updated, encoding="utf-8")
        rel = target.relative_to(self.root).as_posix()
        diff, diff_truncated = self._text_diff(text, updated, rel)
        return {
            "path": rel,
            "replacements": count,
            "diff": diff,
            "diff_truncated": diff_truncated,
        }

    async def _git_status(self, cwd: str = ".") -> dict[str, Any]:
        return await self._run_command(["git", "status", "--short"], cwd=cwd)

    async def _git_diff(
        self,
        cwd: str = ".",
        staged: bool = False,
        path: str = "",
    ) -> dict[str, Any]:
        argv = ["git", "diff"]
        if staged:
            argv.append("--cached")
        if path:
            argv.extend(["--", path])
        return await self._run_command(argv, cwd=cwd)

    async def _run_command(
        self,
        argv: list[str],
        cwd: str = ".",
        timeout_s: float | None = None,
        event_handler: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise ToolError("argv must be a non-empty list of strings")

        run_cwd = self._safe_path(cwd)
        if not run_cwd.is_dir():
            raise ToolError(f"cwd is not a directory: {cwd}")

        executable = Path(argv[0]).name.lower()
        if executable.endswith(".exe"):
            executable = executable[:-4]
        allowed = self.settings.allowed_command_set
        if executable not in allowed:
            raise ToolError(
                f"Executable '{executable}' is not allowlisted. Allowed: {sorted(allowed)}"
            )

        resolved = shutil.which(argv[0])
        if resolved is None:
            program = Path(argv[0])
            if program.is_absolute():
                candidate = program.resolve()
            else:
                candidate = (run_cwd / program).resolve()
                if candidate != self.root and self.root not in candidate.parents:
                    raise ToolError(f"Executable escapes workspace: {argv[0]}")
            if not candidate.exists() or not candidate.is_file():
                raise ToolError(f"Executable not found: {argv[0]}")
            argv = [str(candidate), *argv[1:]]

        joined = " ".join(argv).lower()
        destructive = (
            "git reset --hard",
            "git clean ",
            "git push --force",
            "git push -f",
            "git checkout -- .",
            "git restore .",
            "pip uninstall",
        )
        if not self.settings.allow_destructive and any(x in joined for x in destructive):
            raise ToolError("Potentially destructive command blocked by policy.")

        safe_env_keys = {
            "PATH",
            "HOME",
            "USERPROFILE",
            "SYSTEMROOT",
            "WINDIR",
            "TEMP",
            "TMP",
            "LANG",
            "LC_ALL",
            "TERM",
        }
        env = {k: v for k, v in os.environ.items() if k.upper() in safe_env_keys}
        process = await asyncio.create_subprocess_exec(
            *argv,
            cwd=run_cwd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        timeout = timeout_s or self.settings.command_timeout_s
        stdout_tail = ""
        stderr_tail = ""
        stdout_chars = 0
        stderr_chars = 0

        async def emit_output(stream_name: str, text: str) -> None:
            if event_handler is None or not text:
                return
            try:
                await event_handler(
                    {
                        "type": "command_output",
                        "stream": stream_name,
                        "text": text,
                        "argv": argv,
                    }
                )
            except Exception:
                return

        async def pump(
            stream: asyncio.StreamReader | None,
            stream_name: str,
        ) -> tuple[str, int]:
            if stream is None:
                return "", 0
            tail = ""
            total = 0
            while True:
                chunk = await stream.read(2048)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                total += len(text)
                tail = (tail + text)[-20000:]
                await emit_output(stream_name, text)
            return tail, total

        stdout_task = asyncio.create_task(pump(process.stdout, "stdout"))
        stderr_task = asyncio.create_task(pump(process.stderr, "stderr"))

        try:
            stdout_result, stderr_result, _ = await asyncio.wait_for(
                asyncio.gather(stdout_task, stderr_task, process.wait()),
                timeout=timeout,
            )
            stdout_tail, stdout_chars = stdout_result
            stderr_tail, stderr_chars = stderr_result
        except asyncio.TimeoutError as exc:
            if process.returncode is None:
                process.kill()
            await process.wait()
            for task in (stdout_task, stderr_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise ToolError(f"Command timed out after {timeout} seconds") from exc
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
                await process.wait()
            for task in (stdout_task, stderr_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise

        return {
            "argv": argv,
            "cwd": run_cwd.relative_to(self.root).as_posix() or ".",
            "returncode": process.returncode,
            "stdout": stdout_tail,
            "stderr": stderr_tail,
            "output_truncated": stdout_chars > 20000 or stderr_chars > 20000,
        }

    @staticmethod
    def _validate_repo(repo: str) -> str:
        parts = repo.split("/")
        if len(parts) != 2 or not all(parts):
            raise ToolError("repo must be in owner/name form")
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.")
        if any(any(ch not in allowed for ch in part) for part in parts):
            raise ToolError("repo contains unsupported characters")
        return repo

    def _github_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "LR-Agent/0.5",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    async def _github_request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        base = self.settings.github_api_base.rstrip("/")
        url = f"{base}{path}"
        timeout = httpx.Timeout(30.0)
        async with httpx.AsyncClient(timeout=timeout, headers=self._github_headers()) as client:
            response = await client.request(method, url, json=json_body)

        if response.status_code >= 400:
            detail = response.text[:1500]
            raise ToolError(f"GitHub API HTTP {response.status_code}: {detail}")
        if response.status_code == 204:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise ToolError("GitHub API returned non-JSON data") from exc

    async def _github_get_repo(self, repo: str) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        data = await self._github_request("GET", f"/repos/{repo}")
        return {
            "full_name": data.get("full_name"),
            "private": data.get("private"),
            "default_branch": data.get("default_branch"),
            "description": data.get("description"),
            "html_url": data.get("html_url"),
            "language": data.get("language"),
            "open_issues_count": data.get("open_issues_count"),
        }

    async def _github_list_contents(
        self,
        repo: str,
        path: str = "",
        ref: str = "",
    ) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        encoded_path = quote(path.strip("/"), safe="/")
        suffix = f"/contents/{encoded_path}" if encoded_path else "/contents"
        if ref:
            suffix += "?ref=" + quote(ref, safe="")
        data = await self._github_request("GET", f"/repos/{repo}{suffix}")
        items = data if isinstance(data, list) else [data]
        return {
            "repo": repo,
            "path": path,
            "items": [
                {
                    "name": item.get("name"),
                    "path": item.get("path"),
                    "type": item.get("type"),
                    "size": item.get("size"),
                    "sha": item.get("sha"),
                    "html_url": item.get("html_url"),
                }
                for item in items
                if isinstance(item, dict)
            ],
        }

    async def _github_read_file(
        self,
        repo: str,
        path: str,
        ref: str = "",
        max_chars: int = 50000,
    ) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        encoded_path = quote(path.strip("/"), safe="/")
        suffix = f"/contents/{encoded_path}"
        if ref:
            suffix += "?ref=" + quote(ref, safe="")
        data = await self._github_request("GET", f"/repos/{repo}{suffix}")
        if not isinstance(data, dict) or data.get("type") != "file":
            raise ToolError("GitHub path is not a file")
        if data.get("encoding") != "base64":
            raise ToolError(f"Unsupported GitHub content encoding: {data.get('encoding')}")
        raw = base64.b64decode((data.get("content") or "").encode("ascii"))
        text = raw.decode("utf-8", errors="replace")
        return {
            "repo": repo,
            "path": data.get("path"),
            "sha": data.get("sha"),
            "html_url": data.get("html_url"),
            "content": text[:max_chars],
            "truncated": len(text) > max_chars,
            "chars": len(text),
        }

    def _ensure_github_write(self) -> None:
        if not self.settings.allow_github_write:
            raise ToolError(
                "GitHub writes are disabled. Set LR_AGENT_ALLOW_GITHUB_WRITE=true to enable them."
            )
        if not self.settings.github_token:
            raise ToolError("GitHub write requires LR_AGENT_GITHUB_TOKEN")

    async def _github_create_issue(
        self,
        repo: str,
        title: str,
        body: str = "",
    ) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        self._ensure_github_write()
        data = await self._github_request(
            "POST",
            f"/repos/{repo}/issues",
            json_body={"title": title, "body": body},
        )
        return {
            "number": data.get("number"),
            "title": data.get("title"),
            "html_url": data.get("html_url"),
            "state": data.get("state"),
        }

    async def _github_create_branch(
        self,
        repo: str,
        branch: str,
        base_ref: str = "",
    ) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        self._ensure_github_write()
        if not branch.strip():
            raise ToolError("branch cannot be empty")

        if not base_ref:
            metadata = await self._github_request("GET", f"/repos/{repo}")
            base_ref = str(metadata.get("default_branch") or "")
        if not base_ref:
            raise ToolError("Could not determine base branch")

        encoded_base = quote(base_ref, safe="")
        base = await self._github_request(
            "GET",
            f"/repos/{repo}/git/ref/heads/{encoded_base}",
        )
        sha = ((base.get("object") or {}).get("sha")) if isinstance(base, dict) else None
        if not sha:
            raise ToolError(f"Could not resolve base ref: {base_ref}")

        data = await self._github_request(
            "POST",
            f"/repos/{repo}/git/refs",
            json_body={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        return {
            "branch": branch,
            "base_ref": base_ref,
            "sha": ((data.get("object") or {}).get("sha")),
            "ref": data.get("ref"),
        }

    async def _github_put_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str = "",
    ) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        self._ensure_github_write()
        if not path.strip("/") or not message.strip() or not branch.strip():
            raise ToolError("path, message and branch are required")

        body: dict[str, Any] = {
            "message": message,
            "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            "branch": branch,
        }
        if sha:
            body["sha"] = sha

        encoded_path = quote(path.strip("/"), safe="/")
        data = await self._github_request(
            "PUT",
            f"/repos/{repo}/contents/{encoded_path}",
            json_body=body,
        )
        commit = data.get("commit") or {}
        item = data.get("content") or {}
        return {
            "path": item.get("path") or path,
            "content_sha": item.get("sha"),
            "commit_sha": commit.get("sha"),
            "html_url": item.get("html_url"),
        }

    async def _github_create_pull_request(
        self,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
        draft: bool = False,
    ) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        self._ensure_github_write()
        data = await self._github_request(
            "POST",
            f"/repos/{repo}/pulls",
            json_body={
                "title": title,
                "head": head,
                "base": base,
                "body": body,
                "draft": draft,
            },
        )
        return {
            "number": data.get("number"),
            "title": data.get("title"),
            "state": data.get("state"),
            "draft": data.get("draft"),
            "html_url": data.get("html_url"),
        }

    async def _github_list_workflow_runs(
        self,
        repo: str,
        branch: str = "",
        limit: int = 10,
    ) -> dict[str, Any]:
        repo = self._validate_repo(repo)
        query = f"?per_page={limit}"
        if branch:
            query += "&branch=" + quote(branch, safe="")
        data = await self._github_request(
            "GET",
            f"/repos/{repo}/actions/runs{query}",
        )
        runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
        return {
            "repo": repo,
            "runs": [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "display_title": item.get("display_title"),
                    "status": item.get("status"),
                    "conclusion": item.get("conclusion"),
                    "head_branch": item.get("head_branch"),
                    "head_sha": item.get("head_sha"),
                    "event": item.get("event"),
                    "html_url": item.get("html_url"),
                }
                for item in runs[:limit]
                if isinstance(item, dict)
            ],
        }

    async def _validate_public_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ToolError("Only http:// and https:// URLs are allowed.")
        if not parsed.hostname:
            raise ToolError("URL has no hostname.")
        if self.settings.allow_private_network:
            return

        try:
            infos = await asyncio.to_thread(
                socket.getaddrinfo,
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            raise ToolError(f"DNS resolution failed: {exc}") from exc

        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_unspecified
            ):
                raise ToolError(f"Private/local address blocked: {ip}")

    async def _http_get(self, url: str, max_chars: int = 30000) -> dict[str, Any]:
        current = url
        timeout = httpx.Timeout(30.0)
        headers = {"User-Agent": "LR-Agent/0.5 (+local research agent)"}

        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            for _ in range(6):
                await self._validate_public_url(current)
                response = await client.get(current, follow_redirects=False)
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ToolError("Redirect response had no Location header.")
                    current = urljoin(current, location)
                    continue

                content_type = response.headers.get("content-type", "")
                text = response.text
                return {
                    "url": str(response.url),
                    "status": response.status_code,
                    "content_type": content_type,
                    "content": text[:max_chars],
                    "truncated": len(text) > max_chars,
                }
        raise ToolError("Too many redirects.")
