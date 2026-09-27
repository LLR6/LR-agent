from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import stat
import tempfile
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agent import Agent
from .config import Settings
from .genome_store import GenomeStore
from .llm import OpenAICompatibleClient
from .memory import MemoryStore
from .models import AgentStep, ChatResponse
from .tools import ToolRegistry


class UniverseError(RuntimeError):
    pass


AgentRunner = Callable[[Settings, str], Awaitable[ChatResponse]]


DEFAULT_STRATEGIES = [
    {
        "id": "surgical",
        "name": "Surgical Minimalist",
        "instruction": (
            "Prefer the smallest coherent fix. Preserve public behavior and interfaces. "
            "Inspect before editing, avoid broad refactors, and verify the exact regression."
        ),
    },
    {
        "id": "root-cause",
        "name": "Root-Cause Hunter",
        "instruction": (
            "Trace the failure to its underlying cause instead of patching symptoms. "
            "Use targeted diagnostics, then verify both the direct failure and nearby behavior."
        ),
    },
    {
        "id": "adversarial",
        "name": "Adversarial Breaker",
        "instruction": (
            "Challenge assumptions and actively look for edge cases that a straightforward "
            "fix would miss. Keep the final patch practical and prove it with executable checks."
        ),
    },
    {
        "id": "architecture",
        "name": "Architecture Gardener",
        "instruction": (
            "Look for a local design improvement that removes the class of bug while keeping "
            "scope controlled. Prefer maintainability only when evidence shows it helps."
        ),
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_json_dump(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UniverseError(f"Could not read universe metadata: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise UniverseError(f"Universe metadata must be an object: {path}")
    return value


class UniverseLab:
    """
    Counterfactual coding lab.

    Each candidate gets a real isolated copy of the current workspace. Candidates can
    make different edits and run checks without touching the source workspace. The lab
    compares observable evidence, then promotion performs a conflict check against the
    original baseline before copying any winning changes back.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        agent_runner: AgentRunner | None = None,
    ):
        self.settings = settings
        self.source = settings.workspace.resolve()
        self.root = settings.universe_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._agent_runner = agent_runner
        self.genome = (
            GenomeStore(settings.genome_database)
            if settings.invariants_enabled
            else None
        )
        self._jobs: dict[str, asyncio.Task[Any]] = {}
        self._promotion_lock = asyncio.Lock()
        self._mark_interrupted()

    @property
    def excludes(self) -> set[str]:
        return self.settings.universe_exclude_set

    def _tournament_dir(self, tournament_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", tournament_id):
            raise UniverseError("Invalid tournament id")
        return self.root / tournament_id

    def _meta_path(self, tournament_id: str) -> Path:
        return self._tournament_dir(tournament_id) / "tournament.json"

    def _baseline_path(self, tournament_id: str) -> Path:
        return self._tournament_dir(tournament_id) / "baseline.json"

    def _candidate_dir(self, tournament_id: str, candidate_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9-]{1,80}", candidate_id):
            raise UniverseError("Invalid candidate id")
        return self._tournament_dir(tournament_id) / "candidates" / candidate_id

    def _mark_interrupted(self) -> None:
        for metadata in self.root.glob("*/tournament.json"):
            try:
                value = _read_json(metadata)
            except UniverseError:
                continue
            if value.get("status") in {"queued", "running"}:
                value["status"] = "interrupted"
                value["updated_at"] = _now()
                value["error"] = "Service restarted before counterfactual tournament finished."
                _safe_json_dump(metadata, value)

    def _scan_manifest(self, root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
        root = root.resolve()
        manifest: dict[str, dict[str, Any]] = {}
        scanned = 0
        skipped_large: list[str] = []
        skipped_symlinks: list[str] = []

        for path in sorted(root.rglob("*")):
            if not path.is_file() and not path.is_symlink():
                continue
            rel = path.relative_to(root)
            if any(part in self.excludes for part in rel.parts):
                continue
            if path.is_symlink():
                skipped_symlinks.append(rel.as_posix())
                continue

            scanned += 1
            if scanned > self.settings.universe_max_files:
                raise UniverseError(
                    "Workspace exceeds LR_AGENT_UNIVERSE_MAX_FILES. "
                    "Increase the limit or exclude large dependency/output directories."
                )
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size > self.settings.universe_max_file_bytes:
                skipped_large.append(rel.as_posix())
                continue

            manifest[rel.as_posix()] = {
                "kind": "file",
                "sha256": _sha256(path),
                "size": size,
                "mode": stat.S_IMODE(path.stat().st_mode),
            }

        return manifest, {
            "tracked_files": len(manifest),
            "skipped_large": skipped_large,
            "skipped_symlinks": skipped_symlinks,
        }

    @staticmethod
    def _copy_manifest(
        source: Path,
        destination: Path,
        manifest: dict[str, dict[str, Any]],
    ) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        for rel in manifest:
            src = source / rel
            dst = destination / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    @staticmethod
    def _changes(
        baseline: dict[str, dict[str, Any]],
        current: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        changes: list[dict[str, Any]] = []
        for path in sorted(set(baseline) | set(current)):
            before = baseline.get(path)
            after = current.get(path)
            if before == after:
                continue
            if before is None:
                status = "added"
            elif after is None:
                status = "deleted"
            else:
                status = "modified"
            changes.append(
                {
                    "path": path,
                    "status": status,
                    "before": before,
                    "after": after,
                }
            )
        return changes

    @staticmethod
    def _is_verification_command(step: AgentStep) -> bool:
        if step.tool != "run_command":
            return False
        argv = step.arguments.get("argv")
        if not isinstance(argv, list) or not argv:
            return False
        parts = [str(item).lower() for item in argv]
        exe = Path(parts[0]).name
        joined = " ".join(parts)
        return (
            exe in {"pytest", "ctest"}
            or (exe in {"python", "python3"} and "-m pytest" in joined)
            or (exe in {"npm", "pnpm", "yarn"} and "test" in parts[1:])
            or (exe == "cargo" and "test" in parts[1:])
            or (exe == "go" and "test" in parts[1:])
            or (exe in {"mvn", "mvnw"} and any(x in parts[1:] for x in {"test", "verify"}))
            or (
                exe in {"gradle", "gradlew", "gradlew.bat"}
                and any(x in parts[1:] for x in {"test", "check", "build"})
            )
        )

    @staticmethod
    def _return_code(step: AgentStep) -> int | None:
        try:
            payload = json.loads(step.preview)
            result = payload.get("result") or {}
            value = result.get("returncode")
            return int(value) if value is not None else None
        except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
            return None

    @classmethod
    def verification_commands(cls, response: ChatResponse) -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []
        seen: set[str] = set()
        for step in response.steps:
            if not cls._is_verification_command(step):
                continue
            argv = step.arguments.get("argv")
            if not isinstance(argv, list) or not argv:
                continue
            item = {
                "argv": [str(value) for value in argv],
                "cwd": str(step.arguments.get("cwd", ".")),
                "timeout_s": step.arguments.get("timeout_s"),
            }
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            commands.append(item)
        return commands

    @classmethod
    def score_candidate(
        cls,
        response: ChatResponse,
        changes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        review_passed = bool(response.review and response.review.passed)
        tool_failures = sum(1 for step in response.steps if not step.ok)
        verification_steps = [
            step for step in response.steps if cls._is_verification_command(step)
        ]
        verification_passes = sum(
            1 for step in verification_steps if cls._return_code(step) == 0
        )
        verification_failures = sum(
            1
            for step in verification_steps
            if cls._return_code(step) not in {None, 0}
        )

        components = {
            "review": 35.0 if review_passed else (-15.0 if response.review else 0.0),
            "completion": 20.0 if response.status == "completed" else -10.0,
            "verification": min(verification_passes, 2) * 20.0
            - verification_failures * 10.0,
            "tool_reliability": -tool_failures * 4.0,
            "scope": -min(len(changes), 40) * 0.2,
            "unverified_change": -10.0
            if changes and verification_passes == 0
            else 0.0,
            "no_effect": -5.0 if not changes else 0.0,
        }
        score = round(sum(components.values()), 2)
        return {
            "score": score,
            "components": components,
            "review_passed": review_passed,
            "verification_passes": verification_passes,
            "verification_failures": verification_failures,
            "tool_failures": tool_failures,
            "changed_files": len(changes),
        }

    def _new_tournament(
        self,
        task: str,
        *,
        strategies: list[dict[str, str]],
        evolve: bool,
    ) -> str:
        tournament_id = uuid.uuid4().hex
        path = self._tournament_dir(tournament_id)
        path.mkdir(parents=True, exist_ok=False)
        now = _now()
        _safe_json_dump(
            self._meta_path(tournament_id),
            {
                "id": tournament_id,
                "task": task,
                "status": "queued",
                "created_at": now,
                "updated_at": now,
                "strategies": strategies,
                "evolve": evolve,
                "winner_id": None,
                "candidates": [],
                "promotions": [],
                "error": None,
            },
        )
        return tournament_id

    def get(self, tournament_id: str) -> dict[str, Any]:
        return _read_json(self._meta_path(tournament_id))

    def list(self, limit: int = 30) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for path in self.root.glob("*/tournament.json"):
            try:
                result.append(_read_json(path))
            except UniverseError:
                continue
        result.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return result[: min(max(limit, 1), 100)]

    @staticmethod
    def _normalize_strategies(
        strategies: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if len(strategies) < 2 or len(strategies) > 6:
            raise UniverseError("Custom tournaments require 2 to 6 strategies.")
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in strategies:
            candidate_id = str(item.get("id", "")).strip().lower()
            name = str(item.get("name", "")).strip()
            instruction = str(item.get("instruction", "")).strip()
            if not re.fullmatch(r"[a-z0-9-]{1,80}", candidate_id):
                raise UniverseError(f"Invalid strategy id: {candidate_id}")
            if candidate_id in seen:
                raise UniverseError(f"Duplicate strategy id: {candidate_id}")
            if not name or not instruction:
                raise UniverseError("Strategy name and instruction are required.")
            seen.add(candidate_id)
            normalized.append(
                {
                    "id": candidate_id,
                    "name": name[:120],
                    "instruction": instruction[:6000],
                }
            )
        return normalized

    async def run_strategies(
        self,
        task: str,
        strategies: list[dict[str, str]],
        *,
        evolve: bool = False,
    ) -> dict[str, Any]:
        normalized = self._normalize_strategies(strategies)
        tournament_id = self._new_tournament(
            task,
            strategies=normalized,
            evolve=evolve,
        )
        return await self._execute_tournament(
            tournament_id,
            task=task,
            strategies=normalized,
            evolve=evolve,
        )

    def start_strategies(
        self,
        task: str,
        strategies: list[dict[str, str]],
        *,
        evolve: bool = False,
    ) -> dict[str, Any]:
        normalized = self._normalize_strategies(strategies)
        tournament_id = self._new_tournament(
            task,
            strategies=normalized,
            evolve=evolve,
        )
        job = asyncio.create_task(
            self._execute_tournament(
                tournament_id,
                task=task,
                strategies=normalized,
                evolve=evolve,
            )
        )
        self._jobs[tournament_id] = job
        job.add_done_callback(
            lambda _task, tid=tournament_id: self._jobs.pop(tid, None)
        )
        return self.get(tournament_id)

    def start(
        self,
        task: str,
        *,
        candidates: int | None = None,
        evolve: bool = False,
    ) -> dict[str, Any]:
        count = min(max(candidates or self.settings.universe_candidates, 2), 4)
        strategies = [dict(item) for item in DEFAULT_STRATEGIES[:count]]
        tournament_id = self._new_tournament(task, strategies=strategies, evolve=evolve)
        job = asyncio.create_task(
            self._execute_tournament(
                tournament_id,
                task=task,
                strategies=strategies,
                evolve=evolve,
            )
        )
        self._jobs[tournament_id] = job
        job.add_done_callback(lambda _task, tid=tournament_id: self._jobs.pop(tid, None))
        return self.get(tournament_id)

    async def run(
        self,
        task: str,
        *,
        candidates: int | None = None,
        evolve: bool = False,
    ) -> dict[str, Any]:
        count = min(max(candidates or self.settings.universe_candidates, 2), 4)
        strategies = [dict(item) for item in DEFAULT_STRATEGIES[:count]]
        tournament_id = self._new_tournament(task, strategies=strategies, evolve=evolve)
        return await self._execute_tournament(
            tournament_id,
            task=task,
            strategies=strategies,
            evolve=evolve,
        )

    async def verify_candidate_commands(
        self,
        tournament_id: str,
        candidate_id: str,
        commands: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not commands:
            return {
                "status": "unverified",
                "passed": None,
                "commands": [],
            }
        workspace = self._candidate_dir(tournament_id, candidate_id) / "workspace"
        if not workspace.is_dir():
            raise UniverseError(
                f"Candidate workspace not found: {tournament_id}/{candidate_id}"
            )
        settings = self.settings.model_copy(
            deep=True,
            update={
                "workspace": workspace,
                "database": self._candidate_dir(tournament_id, candidate_id)
                / "verifier-agent.db",
                "knowledge_database": self._candidate_dir(tournament_id, candidate_id)
                / "verifier-knowledge.db",
                "approval_mode": "off",
                "shadow_mode": True,
                "allow_github_write": False,
                "enable_run_snapshots": False,
            },
        )
        settings.ensure_dirs()
        tools = ToolRegistry(settings)
        results: list[dict[str, Any]] = []
        passed = True
        for command in commands:
            arguments = {
                "argv": [str(value) for value in command.get("argv", [])],
                "cwd": str(command.get("cwd") or "."),
            }
            if not arguments["argv"]:
                results.append(
                    {
                        "command": command,
                        "passed": False,
                        "error": "empty argv",
                    }
                )
                passed = False
                break
            if command.get("timeout_s") is not None:
                arguments["timeout_s"] = command["timeout_s"]
            outcome = await tools.execute("run_command", arguments)
            payload = outcome.get("result") or {}
            returncode = payload.get("returncode") if outcome.get("ok") else None
            command_passed = bool(outcome.get("ok")) and returncode == 0
            results.append(
                {
                    "command": command,
                    "passed": command_passed,
                    "returncode": returncode,
                    "result": outcome,
                }
            )
            if not command_passed:
                passed = False
                break
        return {
            "status": "passed" if passed else "failed",
            "passed": passed,
            "commands": results,
        }

    async def _execute_agent(self, child_settings: Settings, prompt: str) -> ChatResponse:
        if self._agent_runner is not None:
            return await self._agent_runner(child_settings, prompt)

        child_settings.ensure_dirs()
        memory = MemoryStore(child_settings.database)
        tools = ToolRegistry(child_settings)
        agent = Agent(
            child_settings,
            OpenAICompatibleClient(child_settings),
            memory,
            tools,
        )
        return await agent.run(prompt, mode="coder")

    async def _run_candidate(
        self,
        tournament_id: str,
        *,
        task: str,
        strategy: dict[str, str],
        baseline: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        candidate_id = strategy["id"]
        candidate_dir = self._candidate_dir(tournament_id, candidate_id)
        workspace = candidate_dir / "workspace"
        await asyncio.to_thread(self._copy_manifest, self.source, workspace, baseline)

        child_settings = self.settings.model_copy(
            deep=True,
            update={
                "workspace": workspace,
                "database": candidate_dir / "agent.db",
                "knowledge_database": candidate_dir / "knowledge.db",
                "universe_root": candidate_dir / "nested-universes",
                "allow_github_write": False,
                "shadow_mode": True,
                "approval_mode": "off",
                "web_token": "",
                "auto_context": False,
                "enable_run_snapshots": False,
            },
        )
        prompt = (
            "You are a candidate inside LR-Agent Counterfactual Forge. "
            "This is an isolated SHADOW WORKSPACE. Do not push, publish, open remote PRs, "
            "or create remote issues. Work only inside this shadow copy.\n\n"
            f"STRATEGY: {strategy['name']}\n"
            f"{strategy['instruction']}\n\n"
            "Complete the task, inspect before editing, run relevant executable verification, "
            "and report only claims supported by actual tool evidence.\n\n"
            f"ORIGINAL TASK:\n{task}"
        )

        started = _now()
        try:
            response = await self._execute_agent(child_settings, prompt)
            candidate_manifest, scan = await asyncio.to_thread(
                self._scan_manifest,
                workspace,
            )
            changes = self._changes(baseline, candidate_manifest)
            evidence = self.score_candidate(response, changes)
            result = {
                "id": candidate_id,
                "strategy": strategy,
                "status": response.status,
                "started_at": started,
                "finished_at": _now(),
                "run_id": response.run_id,
                "answer": response.answer,
                "review": response.review.model_dump() if response.review else None,
                "evidence": evidence,
                "verification_commands": self.verification_commands(response),
                "changes": changes,
                "scan": scan,
                "error": None,
            }
        except Exception as exc:
            result = {
                "id": candidate_id,
                "strategy": strategy,
                "status": "failed",
                "started_at": started,
                "finished_at": _now(),
                "run_id": None,
                "answer": "",
                "review": None,
                "evidence": {
                    "score": -100.0,
                    "components": {"candidate_failure": -100.0},
                    "review_passed": False,
                    "verification_passes": 0,
                    "verification_failures": 0,
                    "tool_failures": 1,
                    "changed_files": 0,
                },
                "verification_commands": [],
                "changes": [],
                "scan": {},
                "error": f"{type(exc).__name__}: {exc}",
            }

        _safe_json_dump(candidate_dir / "candidate.json", result)
        return result

    async def _evolve_strategy(
        self,
        task: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, str] | None:
        summary = [
            {
                "strategy": item["strategy"]["name"],
                "score": item["evidence"]["score"],
                "status": item["status"],
                "review": item.get("review"),
                "changed_files": item["evidence"]["changed_files"],
                "verification_passes": item["evidence"]["verification_passes"],
                "error": item.get("error"),
            }
            for item in candidates
        ]
        llm = OpenAICompatibleClient(self.settings)
        try:
            response = await llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "Design one next-generation coding strategy from counterfactual "
                            "experiment evidence. Do not provide hidden reasoning. Return JSON only."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Create a new strategy that combines evidence-backed strengths and "
                            "avoids observed failures. It must be meaningfully different from the "
                            "existing candidates. Return exactly "
                            '{"name":"...","instruction":"..."}.' + "\n\n"
                            + json.dumps(
                                {"task": task, "candidates": summary},
                                ensure_ascii=False,
                            )
                        ),
                    },
                ],
                tools=None,
                temperature=0.3,
            )
            text = str(response.get("content") or "").strip()
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            data = json.loads(match.group(0) if match else text)
            name = str(data.get("name", "")).strip()
            instruction = str(data.get("instruction", "")).strip()
            if not name or not instruction:
                return None
            return {
                "id": "evolved",
                "name": name[:120],
                "instruction": instruction[:2000],
            }
        except Exception:
            return None

    async def _execute_tournament(
        self,
        tournament_id: str,
        *,
        task: str,
        strategies: list[dict[str, str]],
        evolve: bool,
    ) -> dict[str, Any]:
        metadata = self.get(tournament_id)
        metadata["status"] = "running"
        metadata["updated_at"] = _now()
        _safe_json_dump(self._meta_path(tournament_id), metadata)

        try:
            baseline, scan = await asyncio.to_thread(self._scan_manifest, self.source)
            _safe_json_dump(
                self._baseline_path(tournament_id),
                {"manifest": baseline, "scan": scan},
            )
            results = await asyncio.gather(
                *[
                    self._run_candidate(
                        tournament_id,
                        task=task,
                        strategy=strategy,
                        baseline=baseline,
                    )
                    for strategy in strategies
                ]
            )

            if evolve:
                evolved = await self._evolve_strategy(task, list(results))
                if evolved is not None:
                    results = [
                        *results,
                        await self._run_candidate(
                            tournament_id,
                            task=task,
                            strategy=evolved,
                            baseline=baseline,
                        ),
                    ]
                    metadata["evolved_strategy"] = evolved

            winner = max(
                results,
                key=lambda item: (
                    float(item["evidence"]["score"]),
                    -int(item["evidence"]["changed_files"]),
                ),
            )
            metadata = self.get(tournament_id)
            metadata.update(
                {
                    "status": "completed",
                    "updated_at": _now(),
                    "baseline_scan": scan,
                    "candidates": results,
                    "winner_id": winner["id"],
                    "error": None,
                }
            )
            _safe_json_dump(self._meta_path(tournament_id), metadata)
            return metadata
        except Exception as exc:
            metadata = self.get(tournament_id)
            metadata["status"] = "failed"
            metadata["updated_at"] = _now()
            metadata["error"] = f"{type(exc).__name__}: {exc}"
            _safe_json_dump(self._meta_path(tournament_id), metadata)
            return metadata

    def _state_for_source(
        self,
        rel: str,
    ) -> dict[str, Any] | None:
        path = self.source / rel
        if not path.exists() and not path.is_symlink():
            return None
        if path.is_symlink():
            return {"kind": "symlink", "target": os.readlink(path)}
        if not path.is_file():
            return {"kind": "unsupported"}
        return {
            "kind": "file",
            "sha256": _sha256(path),
            "size": path.stat().st_size,
            "mode": stat.S_IMODE(path.stat().st_mode),
        }

    async def _verify_real_workspace(
        self,
        commands: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not commands:
            return {
                "status": "unverified",
                "passed": None,
                "commands": [],
            }

        verify_settings = self.settings.model_copy(
            deep=True,
            update={
                "approval_mode": "off",
                "shadow_mode": False,
                "allow_github_write": False,
            },
        )
        tools = ToolRegistry(verify_settings)
        results: list[dict[str, Any]] = []
        passed = True

        for command in commands:
            arguments = {
                "argv": list(command["argv"]),
                "cwd": str(command.get("cwd") or "."),
            }
            if command.get("timeout_s") is not None:
                arguments["timeout_s"] = command["timeout_s"]
            outcome = await tools.execute("run_command", arguments)
            returncode = None
            if outcome.get("ok"):
                payload = outcome.get("result") or {}
                returncode = payload.get("returncode")
            command_passed = bool(outcome.get("ok")) and returncode == 0
            results.append(
                {
                    "arguments": arguments,
                    "passed": command_passed,
                    "returncode": returncode,
                    "result": outcome,
                }
            )
            if not command_passed:
                passed = False
                break

        return {
            "status": "passed" if passed else "failed",
            "passed": passed,
            "commands": results,
        }

    async def _verify_invariant_dna(self) -> dict[str, Any]:
        if self.genome is None:
            return {
                "enabled": False,
                "passed": None,
                "results": [],
            }

        invariants = self.genome.list_invariants(status="active", limit=500)
        if not invariants:
            return {
                "enabled": True,
                "passed": True,
                "results": [],
            }

        verify_settings = self.settings.model_copy(
            deep=True,
            update={
                "approval_mode": "off",
                "shadow_mode": False,
                "allow_github_write": False,
            },
        )
        tools = ToolRegistry(verify_settings)
        overall = True
        results: list[dict[str, Any]] = []

        for invariant in invariants:
            checks: list[dict[str, Any]] = []
            invariant_passed = True
            for command in invariant["commands"]:
                outcome = await tools.execute("run_command", dict(command))
                payload = outcome.get("result") or {}
                returncode = payload.get("returncode") if outcome.get("ok") else None
                passed = bool(outcome.get("ok")) and returncode == 0
                checks.append(
                    {
                        "command": command,
                        "passed": passed,
                        "returncode": returncode,
                        "result": outcome,
                    }
                )
                if not passed:
                    invariant_passed = False
                    overall = False
                    break

            details = {
                "name": invariant["name"],
                "description": invariant["description"],
                "checks": checks,
            }
            self.genome.record_invariant_check(
                invariant["id"],
                passed=invariant_passed,
                details=details,
            )
            results.append(
                {
                    "id": invariant["id"],
                    "name": invariant["name"],
                    "description": invariant["description"],
                    "passed": invariant_passed,
                    "checks": checks,
                }
            )

        return {
            "enabled": True,
            "passed": overall,
            "results": results,
        }

    @staticmethod
    def _restore_promotion(
        source: Path,
        backup_root: Path,
        created_paths: list[Path],
    ) -> None:
        for path in reversed(created_paths):
            try:
                if path.exists() or path.is_symlink():
                    path.unlink()
            except OSError:
                pass
        for backup in sorted(backup_root.rglob("*")):
            if not backup.is_file():
                continue
            rel = backup.relative_to(backup_root)
            destination = source / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, destination)

    def _write_proof_bundle(
        self,
        tournament_id: str,
        *,
        candidate: dict[str, Any],
        applied: list[str],
        verification: dict[str, Any],
        invariant_verification: dict[str, Any],
    ) -> dict[str, str]:
        import hashlib

        payload = {
            "format": "lr-agent-proof-carrying-patch/v1",
            "generated_at": _now(),
            "tournament_id": tournament_id,
            "candidate_id": candidate["id"],
            "strategy": candidate["strategy"],
            "evidence_score": candidate["evidence"],
            "changes": candidate.get("changes") or [],
            "applied": applied,
            "verification": verification,
            "invariant_dna": invariant_verification,
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        proof_sha256 = hashlib.sha256(canonical).hexdigest()
        payload["proof_sha256"] = proof_sha256
        proof_path = (
            self._tournament_dir(tournament_id)
            / "proofs"
            / f"{candidate['id']}-{uuid.uuid4().hex[:8]}.json"
        )
        _safe_json_dump(proof_path, payload)
        return {
            "proof_path": str(proof_path),
            "proof_sha256": proof_sha256,
        }

    async def promote(
        self,
        tournament_id: str,
        *,
        candidate_id: str | None = None,
        verify: bool = True,
    ) -> dict[str, Any]:
        async with self._promotion_lock:
            metadata = self.get(tournament_id)
            if metadata.get("status") != "completed":
                raise UniverseError("Only completed tournaments can be promoted.")
            candidate_id = candidate_id or str(metadata.get("winner_id") or "")
            candidates = {
                item["id"]: item for item in metadata.get("candidates", [])
            }
            if candidate_id not in candidates:
                raise UniverseError(f"Candidate not found: {candidate_id}")

            baseline_data = _read_json(self._baseline_path(tournament_id))
            baseline = baseline_data.get("manifest") or {}
            if not isinstance(baseline, dict):
                raise UniverseError("Baseline manifest is invalid.")

            candidate = candidates[candidate_id]
            changes = candidate.get("changes") or []
            candidate_workspace = self._candidate_dir(
                tournament_id, candidate_id
            ) / "workspace"

            conflicts: list[dict[str, Any]] = []
            for change in changes:
                rel = str(change["path"])
                before = baseline.get(rel)
                target = change.get("after")
                current = self._state_for_source(rel)
                if current == target:
                    continue
                if current != before:
                    conflicts.append(
                        {
                            "path": rel,
                            "baseline": before,
                            "current": current,
                            "candidate": target,
                        }
                    )
                if target is not None and target.get("kind") != "file":
                    conflicts.append(
                        {
                            "path": rel,
                            "reason": "unsupported candidate path kind",
                            "candidate": target,
                        }
                    )

            if conflicts:
                return {
                    "ok": False,
                    "tournament_id": tournament_id,
                    "candidate_id": candidate_id,
                    "conflicts": conflicts,
                    "applied": [],
                }

            backup_root = (
                self._tournament_dir(tournament_id)
                / "promotion-backups"
                / f"{candidate_id}-{uuid.uuid4().hex[:8]}"
            )
            backup_root.mkdir(parents=True, exist_ok=False)
            applied: list[str] = []
            created_paths: list[Path] = []

            try:
                for change in changes:
                    rel = str(change["path"])
                    before = baseline.get(rel)
                    target = change.get("after")
                    source_path = self.source / rel
                    if self._state_for_source(rel) == target:
                        continue

                    if before is not None and source_path.is_file():
                        backup_path = backup_root / rel
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, backup_path)

                    if target is None:
                        if source_path.exists() or source_path.is_symlink():
                            source_path.unlink()
                    else:
                        candidate_path = candidate_workspace / rel
                        if not candidate_path.is_file() or candidate_path.is_symlink():
                            raise UniverseError(
                                f"Candidate promotion source is not a regular file: {rel}"
                            )
                        source_path.parent.mkdir(parents=True, exist_ok=True)
                        if before is None:
                            created_paths.append(source_path)
                        fd, temp_name = tempfile.mkstemp(
                            prefix=source_path.name + ".",
                            suffix=".promote",
                            dir=source_path.parent,
                        )
                        os.close(fd)
                        try:
                            shutil.copy2(candidate_path, temp_name)
                            os.replace(temp_name, source_path)
                        finally:
                            try:
                                os.unlink(temp_name)
                            except FileNotFoundError:
                                pass
                        if target.get("mode") is not None:
                            os.chmod(source_path, int(target["mode"]))
                    applied.append(rel)
            except Exception:
                self._restore_promotion(
                    self.source,
                    backup_root,
                    created_paths,
                )
                raise

            verification = {
                "status": "skipped",
                "passed": None,
                "commands": [],
            }
            if verify:
                verification = await self._verify_real_workspace(
                    list(candidate.get("verification_commands") or [])
                )
                if verification.get("passed") is False:
                    self._restore_promotion(
                        self.source,
                        backup_root,
                        created_paths,
                    )
                    return {
                        "ok": False,
                        "tournament_id": tournament_id,
                        "candidate_id": candidate_id,
                        "conflicts": [],
                        "applied": [],
                        "verification": verification,
                        "rolled_back": True,
                        "message": (
                            "Winner changes were applied temporarily, but real-workspace "
                            "verification failed. Promotion was automatically rolled back."
                        ),
                    }

            invariant_verification = {
                "enabled": False,
                "passed": None,
                "results": [],
            }
            if verify and self.settings.invariants_enabled:
                invariant_verification = await self._verify_invariant_dna()
                if invariant_verification.get("passed") is False:
                    self._restore_promotion(
                        self.source,
                        backup_root,
                        created_paths,
                    )
                    return {
                        "ok": False,
                        "tournament_id": tournament_id,
                        "candidate_id": candidate_id,
                        "conflicts": [],
                        "applied": [],
                        "verification": verification,
                        "invariant_verification": invariant_verification,
                        "rolled_back": True,
                        "message": (
                            "Winner passed its own verification, but violated active "
                            "Invariant DNA. Promotion was automatically rolled back."
                        ),
                    }

            proof = self._write_proof_bundle(
                tournament_id,
                candidate=candidate,
                applied=applied,
                verification=verification,
                invariant_verification=invariant_verification,
            )

            promotion = {
                "candidate_id": candidate_id,
                "promoted_at": _now(),
                "applied": applied,
                "backup_root": str(backup_root),
                "verification": verification,
                "invariant_verification": invariant_verification,
                **proof,
            }
            metadata = self.get(tournament_id)
            metadata.setdefault("promotions", []).append(promotion)
            metadata["updated_at"] = _now()
            _safe_json_dump(self._meta_path(tournament_id), metadata)
            return {
                "ok": True,
                "tournament_id": tournament_id,
                "candidate_id": candidate_id,
                "conflicts": [],
                "applied": applied,
                "backup_root": str(backup_root),
                "verification": verification,
                **proof,
            }
