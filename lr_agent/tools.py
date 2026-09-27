from __future__ import annotations

import asyncio
import base64
import difflib
import ipaddress
import json
import os
import shutil
import socket
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import httpx

from .config import Settings
from .knowledge import KnowledgeIndex


class ToolError(RuntimeError):
    pass


class ToolRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.workspace.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.knowledge = KnowledgeIndex(
            self.root,
            settings.knowledge_database,
            max_files=settings.knowledge_max_files,
            max_file_bytes=settings.knowledge_max_file_bytes,
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

    def _safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ToolError(f"Path escapes workspace: {relative}")
        return candidate

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "list_files":
                value = self._list_files(**arguments)
            elif name == "search_files":
                value = self._search_files(**arguments)
            elif name == "read_file":
                value = self._read_file(**arguments)
            elif name == "write_file":
                value = self._write_file(**arguments)
            elif name == "replace_in_file":
                value = self._replace_in_file(**arguments)
            elif name == "git_status":
                value = await self._git_status(**arguments)
            elif name == "git_diff":
                value = await self._git_diff(**arguments)
            elif name == "run_command":
                value = await self._run_command(**arguments)
            elif name == "http_get":
                value = await self._http_get(**arguments)
            elif name == "knowledge_index":
                value = await asyncio.to_thread(self.knowledge.rebuild)
            elif name == "knowledge_search":
                value = await asyncio.to_thread(self.knowledge.search, **arguments)
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

    def _read_file(self, path: str, max_chars: int = 50000) -> dict[str, Any]:
        target = self._safe_path(path)
        if not target.is_file():
            raise ToolError(f"Not a file: {path}")
        text = target.read_text(encoding="utf-8", errors="replace")
        return {
            "path": target.relative_to(self.root).as_posix(),
            "content": text[:max_chars],
            "truncated": len(text) > max_chars,
            "chars": len(text),
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
    ) -> dict[str, Any]:
        if not argv or not all(isinstance(item, str) and item for item in argv):
            raise ToolError("argv must be a non-empty list of strings")

        executable = Path(argv[0]).name.lower()
        if executable.endswith(".exe"):
            executable = executable[:-4]
        allowed = self.settings.allowed_command_set
        if executable not in allowed:
            raise ToolError(
                f"Executable '{executable}' is not allowlisted. Allowed: {sorted(allowed)}"
            )
        if shutil.which(argv[0]) is None and not Path(argv[0]).exists():
            raise ToolError(f"Executable not found: {argv[0]}")

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

        run_cwd = self._safe_path(cwd)
        if not run_cwd.is_dir():
            raise ToolError(f"cwd is not a directory: {cwd}")

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
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise ToolError(f"Command timed out after {timeout} seconds") from exc
        except asyncio.CancelledError:
            if process.returncode is None:
                process.kill()
                await process.wait()
            raise

        stdout_full = stdout_bytes.decode("utf-8", errors="replace")
        stderr_full = stderr_bytes.decode("utf-8", errors="replace")
        stdout = stdout_full[-20000:]
        stderr = stderr_full[-20000:]
        return {
            "argv": argv,
            "cwd": run_cwd.relative_to(self.root).as_posix() or ".",
            "returncode": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "output_truncated": len(stdout_full) > 20000 or len(stderr_full) > 20000,
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
            "User-Agent": "LR-Agent/0.2",
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
        headers = {"User-Agent": "LR-Agent/0.1 (+local research agent)"}

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
