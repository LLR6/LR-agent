from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from .config import Settings


class ToolError(RuntimeError):
    pass


class ToolRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.workspace.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

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
            elif name == "run_command":
                value = await asyncio.to_thread(self._run_command, **arguments)
            elif name == "http_get":
                value = await self._http_get(**arguments)
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

    def _write_file(
        self, path: str, content: str, overwrite: bool = False
    ) -> dict[str, Any]:
        target = self._safe_path(path)
        if target.exists() and not overwrite:
            raise ToolError(f"File already exists: {path}. Set overwrite=true to replace it.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {
            "path": target.relative_to(self.root).as_posix(),
            "chars": len(content),
            "overwritten": overwrite,
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
        return {
            "path": target.relative_to(self.root).as_posix(),
            "replacements": count,
        }

    def _run_command(
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
        result = subprocess.run(
            argv,
            cwd=run_cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s or self.settings.command_timeout_s,
            shell=False,
            errors="replace",
        )
        stdout = result.stdout[-20000:]
        stderr = result.stderr[-20000:]
        return {
            "argv": argv,
            "cwd": run_cwd.relative_to(self.root).as_posix() or ".",
            "returncode": result.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "output_truncated": len(result.stdout) > 20000 or len(result.stderr) > 20000,
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
