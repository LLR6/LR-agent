from __future__ import annotations

import asyncio
import json
import re
import shutil
from collections import Counter, defaultdict
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .agent import Agent
from .chrono_store import ChronoStore, FUTURE_CATEGORIES
from .config import Settings
from .genome_store import GenomeStore
from .llm import OpenAICompatibleClient
from .memory import MemoryStore
from .models import ChatResponse
from .tools import ToolRegistry
from .universes import UniverseError, UniverseLab


class ChronoForgeError(RuntimeError):
    pass


AgentRunner = Callable[[Settings, str], Awaitable[ChatResponse]]


DEFAULT_FUTURES: list[dict[str, str]] = [
    {
        "category": "dependency_upgrade",
        "name": "Major dependency generation",
        "instruction": (
            "Evolve the project as if a central dependency received a major-version upgrade "
            "that removes one convenient compatibility behavior. Make the repository locally "
            "consistent without network access, preserve the original feature intent, and add "
            "or adapt tests that expose compatibility assumptions."
        ),
    },
    {
        "category": "api_deprecation",
        "name": "API deprecation pressure",
        "instruction": (
            "Evolve the project as if an API used near the changed behavior is deprecated and "
            "a narrower replacement contract is now preferred. Refactor only what is needed, "
            "preserve observable behavior, and verify callers."
        ),
    },
    {
        "category": "adjacent_feature",
        "name": "Adjacent feature arrives",
        "instruction": (
            "Add a plausible adjacent feature that shares the same state, data model, or public "
            "interface as the original change. The goal is to test whether the current design "
            "leaves room for extension without rewriting the patch."
        ),
    },
    {
        "category": "schema_migration",
        "name": "Data/schema evolution",
        "instruction": (
            "Evolve a relevant stored/configured data shape by adding one required field or "
            "version transition. Preserve backward handling where the current repository implies "
            "it, and verify migration/compatibility behavior without external services."
        ),
    },
    {
        "category": "module_refactor",
        "name": "Module boundary split",
        "instruction": (
            "Perform a realistic local module-boundary refactor around the original change: "
            "separate one responsibility or move one boundary while preserving public behavior. "
            "Use this to expose hidden coupling in the patch."
        ),
    },
    {
        "category": "platform_runtime",
        "name": "Runtime/platform generation",
        "instruction": (
            "Evolve the repository for a newer runtime/platform generation with stricter defaults "
            "or validation. Make only repository-local edits; do not fetch packages. Preserve the "
            "original task's behavior and verify compatibility-sensitive paths."
        ),
    },
    {
        "category": "performance_pressure",
        "name": "Scale and performance pressure",
        "instruction": (
            "Introduce a realistic local scale/performance requirement near the original change. "
            "Improve the implementation only when needed, add a deterministic regression check "
            "where practical, and preserve correctness rather than optimizing speculatively."
        ),
    },
    {
        "category": "config_contract",
        "name": "Configuration contract changes",
        "instruction": (
            "Evolve a relevant configuration or environment contract: rename, split, or tighten "
            "one setting while preserving a clear compatibility path. Verify startup or config "
            "behavior and expose hard-coded assumptions."
        ),
    },
]


class ChronoForge:
    """
    Prospective software-evolution laboratory.

    A seed patch/project is copied into multiple temporal trajectories. Each trajectory evolves
    sequentially: generation N starts from the actual repository produced by generation N-1.
    After every future-maintenance task, ChronoForge replays the seed verification commands and
    active Invariant DNA in that future workspace. The resulting report measures temporal
    survival and maintenance burden from observable tool evidence.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        agent_runner: AgentRunner | None = None,
        store: ChronoStore | None = None,
        universe_lab: UniverseLab | None = None,
    ):
        self.settings = settings
        self.root = settings.chronoforge_root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.store = store or ChronoStore(settings.chronoforge_database)
        self.universes = universe_lab or UniverseLab(settings)
        self.genome = GenomeStore(settings.genome_database)
        self._agent_runner = agent_runner
        self._jobs: dict[str, asyncio.Task[Any]] = {}

    @staticmethod
    def _clean_json(text: str) -> Any:
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"(\[.*\]|\{.*\})", text, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(1))

    def _run_dir(self, run_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise ChronoForgeError("Invalid ChronoForge run id.")
        return self.root / run_id

    def _trajectory_dir(self, run_id: str, trajectory: int) -> Path:
        return self._run_dir(run_id) / "trajectories" / f"t{trajectory:02d}"

    def _generation_dir(
        self,
        run_id: str,
        trajectory: int,
        generation: int,
    ) -> Path:
        return self._trajectory_dir(run_id, trajectory) / f"g{generation:02d}"

    def _resolve_seed(
        self,
        *,
        tournament_id: str | None,
        candidate_id: str | None,
    ) -> dict[str, Any]:
        if not tournament_id:
            return {
                "source_type": "workspace",
                "source_ref": None,
                "workspace": self.settings.workspace.resolve(),
                "task": "",
                "candidate_id": None,
                "verification_commands": [],
                "changed_paths": [],
            }

        tournament = self.universes.get(tournament_id)
        if tournament.get("status") != "completed":
            raise ChronoForgeError("Only completed Forge tournaments can be aged.")
        selected = candidate_id or str(tournament.get("winner_id") or "")
        candidate = next(
            (
                item
                for item in tournament.get("candidates", [])
                if item.get("id") == selected
            ),
            None,
        )
        if candidate is None:
            raise ChronoForgeError(f"Forge candidate not found: {selected}")

        workspace = (
            self.settings.universe_root.resolve()
            / tournament_id
            / "candidates"
            / selected
            / "workspace"
        )
        if not workspace.is_dir():
            raise ChronoForgeError(f"Forge candidate workspace is missing: {workspace}")

        return {
            "source_type": "forge_candidate",
            "source_ref": f"{tournament_id}:{selected}",
            "workspace": workspace,
            "task": str(tournament.get("task") or ""),
            "candidate_id": selected,
            "verification_commands": list(
                candidate.get("verification_commands") or []
            ),
            "changed_paths": [
                str(item.get("path"))
                for item in candidate.get("changes") or []
                if item.get("path")
            ],
        }

    async def _project_profile(
        self,
        workspace: Path,
    ) -> dict[str, Any]:
        child = self.settings.model_copy(
            deep=True,
            update={
                "workspace": workspace,
                "approval_mode": "off",
                "allow_github_write": False,
                "shadow_mode": True,
            },
        )
        child.ensure_dirs()
        result = await ToolRegistry(child).execute("project_inspect", {"path": "."})
        if not result.get("ok"):
            return {"stacks": [], "manifests": [], "checks": []}
        payload = result.get("result") or {}
        return {
            "stacks": list(payload.get("stacks") or []),
            "manifests": list(payload.get("manifests") or []),
            "checks": list(
                payload.get("recommended_checks")
                or payload.get("checks")
                or []
            ),
        }

    @staticmethod
    def _normalize_command(command: dict[str, Any]) -> dict[str, Any] | None:
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(
            isinstance(item, str) and item for item in argv
        ):
            return None
        item: dict[str, Any] = {
            "argv": list(argv),
            "cwd": str(command.get("cwd") or "."),
        }
        if command.get("timeout_s") is not None:
            item["timeout_s"] = command["timeout_s"]
        return item

    async def _seed_verification_commands(
        self,
        seed: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw in [
            *list(seed.get("verification_commands") or []),
            *list(profile.get("checks") or []),
        ]:
            item = self._normalize_command(raw)
            if item is None:
                continue
            key = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            commands.append(item)
        return commands[:4]

    async def _generate_scenarios(
        self,
        *,
        task: str,
        profile: dict[str, Any],
        changed_paths: list[str],
    ) -> list[dict[str, Any]]:
        calibration = self.store.calibration()
        weights = calibration["weights"]
        defaults = [
            {
                **item,
                "weight": float(weights.get(item["category"], 0.0)),
                "source": "fallback",
            }
            for item in DEFAULT_FUTURES
        ]

        llm = OpenAICompatibleClient(self.settings)
        prompt = {
            "task_or_patch_intent": task,
            "project_stacks": profile.get("stacks", []),
            "manifests": profile.get("manifests", []),
            "changed_paths": changed_paths[:40],
            "allowed_categories": list(FUTURE_CATEGORIES),
            "reality_calibration_weights": weights,
        }
        try:
            response = await llm.chat(
                [
                    {
                        "role": "system",
                        "content": (
                            "You design prospective software-maintenance stress scenarios. "
                            "Return JSON only. Do not provide hidden reasoning. Scenarios must be "
                            "implementable with repository-local edits and tests, without network "
                            "access or destructive remote side effects."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Create exactly one concise future-maintenance scenario for each "
                            "allowed category, tailored to this project. Each item must contain "
                            "category, name, instruction. The instruction tells a future coding "
                            "agent to actually evolve the repository, not merely discuss it.\n\n"
                            + json.dumps(prompt, ensure_ascii=False)
                        ),
                    },
                ],
                tools=None,
                temperature=0.25,
            )
            data = self._clean_json(str(response.get("content") or ""))
            if not isinstance(data, list):
                raise ValueError("scenario response must be a list")
            by_category: dict[str, dict[str, Any]] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                category = str(item.get("category") or "").strip()
                name = str(item.get("name") or "").strip()
                instruction = str(item.get("instruction") or "").strip()
                if category not in FUTURE_CATEGORIES or not name or not instruction:
                    continue
                by_category[category] = {
                    "category": category,
                    "name": name[:160],
                    "instruction": instruction[:6000],
                    "weight": float(weights.get(category, 0.0)),
                    "source": "model-tailored",
                }
            scenarios = [
                by_category.get(item["category"], item)
                for item in defaults
            ]
        except Exception:
            scenarios = defaults

        scenarios.sort(
            key=lambda item: (
                -float(item.get("weight", 0.0)),
                list(FUTURE_CATEGORIES).index(item["category"]),
            )
        )
        return scenarios[: min(max(self.settings.chronoforge_scenario_count, 1), 8)]

    @staticmethod
    def _scenario_schedule(
        scenarios: list[dict[str, Any]],
        *,
        generations: int,
        trajectories: int,
    ) -> list[list[dict[str, Any]]]:
        if not scenarios:
            raise ChronoForgeError("No future scenarios are available.")
        schedule: list[list[dict[str, Any]]] = []
        for trajectory in range(trajectories):
            row: list[dict[str, Any]] = []
            for generation in range(generations):
                index = (trajectory + generation) % len(scenarios)
                row.append(dict(scenarios[index]))
            schedule.append(row)
        return schedule

    def _child_settings(
        self,
        workspace: Path,
        *,
        run_id: str,
        trajectory: int,
        generation: int,
    ) -> Settings:
        generation_root = self._generation_dir(
            run_id,
            trajectory,
            generation,
        )
        return self.settings.model_copy(
            deep=True,
            update={
                "workspace": workspace,
                "database": generation_root / "agent.db",
                "knowledge_database": generation_root / "knowledge.db",
                "universe_root": generation_root / "nested-universes",
                "chronoforge_root": generation_root / "nested-chronoforge",
                "allow_github_write": False,
                "shadow_mode": True,
                "approval_mode": "off",
                "web_token": "",
                "enable_run_snapshots": False,
                "auto_context": False,
            },
        )

    async def _execute_agent(
        self,
        settings: Settings,
        prompt: str,
    ) -> ChatResponse:
        if self._agent_runner is not None:
            return await self._agent_runner(settings, prompt)
        settings.ensure_dirs()
        return await Agent(
            settings,
            OpenAICompatibleClient(settings),
            MemoryStore(settings.database),
            ToolRegistry(settings),
        ).run(prompt, mode="coder")

    async def _run_commands(
        self,
        workspace: Path,
        commands: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not commands:
            return {"passed": None, "status": "unverified", "commands": []}
        settings = self.settings.model_copy(
            deep=True,
            update={
                "workspace": workspace,
                "approval_mode": "off",
                "shadow_mode": True,
                "allow_github_write": False,
            },
        )
        settings.ensure_dirs()
        tools = ToolRegistry(settings)
        results: list[dict[str, Any]] = []
        passed = True
        for command in commands:
            outcome = await tools.execute("run_command", dict(command))
            payload = outcome.get("result") or {}
            returncode = payload.get("returncode") if outcome.get("ok") else None
            ok = bool(outcome.get("ok")) and returncode == 0
            results.append(
                {
                    "command": command,
                    "passed": ok,
                    "returncode": returncode,
                    "result": outcome,
                }
            )
            if not ok:
                passed = False
                break
        return {
            "passed": passed,
            "status": "passed" if passed else "failed",
            "commands": results,
        }

    async def _run_invariants(self, workspace: Path) -> dict[str, Any]:
        if not self.settings.invariants_enabled:
            return {"passed": None, "status": "disabled", "results": []}
        invariants = self.genome.list_invariants(status="active", limit=500)
        if not invariants:
            return {"passed": True, "status": "passed", "results": []}

        results: list[dict[str, Any]] = []
        overall = True
        for invariant in invariants:
            check = await self._run_commands(
                workspace,
                list(invariant.get("commands") or []),
            )
            invariant_passed = check.get("passed") is not False
            results.append(
                {
                    "id": invariant["id"],
                    "name": invariant["name"],
                    "passed": invariant_passed,
                    "verification": check,
                }
            )
            if not invariant_passed:
                overall = False
                break
        return {
            "passed": overall,
            "status": "passed" if overall else "failed",
            "results": results,
        }

    def _maintenance_cost(
        self,
        response: ChatResponse,
        changed_files: int,
    ) -> dict[str, Any]:
        failed_tools = sum(1 for step in response.steps if not step.ok)
        tool_steps = len(response.steps)
        cost = (
            tool_steps * self.settings.chronoforge_cost_step_weight
            + changed_files * self.settings.chronoforge_cost_change_weight
            + failed_tools * self.settings.chronoforge_cost_failure_weight
        )
        if response.review is not None and not response.review.passed:
            cost += 8.0
        return {
            "score": round(float(cost), 3),
            "tool_steps": tool_steps,
            "failed_tools": failed_tools,
            "changed_files": changed_files,
        }

    async def _run_generation(
        self,
        *,
        run_id: str,
        trajectory: int,
        generation: int,
        previous_workspace: Path,
        scenario: dict[str, Any],
        patch_intent: str,
        changed_paths: list[str],
        seed_verification: list[dict[str, Any]],
    ) -> dict[str, Any]:
        generation_dir = self._generation_dir(run_id, trajectory, generation)
        workspace = generation_dir / "workspace"
        previous_manifest, _ = await asyncio.to_thread(
            self.universes._scan_manifest,
            previous_workspace,
        )
        await asyncio.to_thread(
            self.universes._copy_manifest,
            previous_workspace,
            workspace,
            previous_manifest,
        )

        prompt = (
            "You are a FUTURE MAINTAINER inside ChronoForge. This is an isolated shadow "
            "workspace representing a later repository generation. Actually evolve the code "
            "for the future maintenance event below. Do not merely describe a hypothetical. "
            "Do not push/publish or use remote side effects. Preserve the original patch intent "
            "unless the future requirement explicitly forces a compatible evolution. Inspect "
            "before editing and run repository-local verification.\n\n"
            f"ORIGINAL PATCH/TASK INTENT:\n{patch_intent or 'Preserve current behavior.'}\n\n"
            f"ORIGINAL PATCH SURFACE:\n{json.dumps(changed_paths[:60], ensure_ascii=False)}\n\n"
            f"FUTURE GENERATION: {generation}\n"
            f"FUTURE CATEGORY: {scenario['category']}\n"
            f"FUTURE EVENT: {scenario['name']}\n"
            f"REQUIRED EVOLUTION:\n{scenario['instruction']}\n"
        )
        child = self._child_settings(
            workspace,
            run_id=run_id,
            trajectory=trajectory,
            generation=generation,
        )
        response = await self._execute_agent(child, prompt)
        current_manifest, scan = await asyncio.to_thread(
            self.universes._scan_manifest,
            workspace,
        )
        changes = self.universes._changes(previous_manifest, current_manifest)
        evidence = self.universes.score_candidate(response, changes)
        seed_check = await self._run_commands(workspace, seed_verification)
        invariants = await self._run_invariants(workspace)

        internal_ok = (
            response.status == "completed"
            and (response.review is None or response.review.passed)
            and int(evidence.get("verification_failures", 0)) == 0
        )
        survived = (
            internal_ok
            and seed_check.get("passed") is not False
            and invariants.get("passed") is not False
        )
        cost = self._maintenance_cost(response, len(changes))
        overlap = sorted(
            {
                str(item.get("path"))
                for item in changes
                if item.get("path") in set(changed_paths)
            }
        )

        return {
            "trajectory": trajectory,
            "generation": generation,
            "scenario": scenario,
            "status": response.status,
            "survived": survived,
            "answer": response.answer,
            "run_id": response.run_id,
            "review": response.review.model_dump() if response.review else None,
            "evidence": evidence,
            "seed_verification": seed_check,
            "invariant_dna": invariants,
            "maintenance_cost": cost,
            "changes": changes,
            "patch_surface_touched": overlap,
            "scan": scan,
            "workspace": str(workspace),
        }

    @staticmethod
    def _half_life(survival_curve: list[dict[str, Any]]) -> dict[str, Any]:
        for point in survival_curve:
            if point["generation"] == 0:
                continue
            if float(point["survival_rate"]) <= 0.5:
                return {
                    "generation": float(point["generation"]),
                    "censored": False,
                }
        last = max(
            (int(point["generation"]) for point in survival_curve),
            default=0,
        )
        return {
            "generation": float(last),
            "censored": True,
        }

    def _aggregate_report(
        self,
        *,
        run_id: str,
        seed: dict[str, Any],
        generations: int,
        trajectories: int,
        scenarios: list[dict[str, Any]],
        trajectory_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        by_generation: dict[int, list[bool]] = defaultdict(list)
        costs: list[float] = []
        invariant_checks = 0
        invariant_passes = 0
        patch_touches = 0
        patch_touch_generations = 0
        category_survival: dict[str, list[bool]] = defaultdict(list)
        deaths: Counter[str] = Counter()

        for trajectory in trajectory_results:
            alive = True
            generation_map = {
                int(item["generation"]): item
                for item in trajectory.get("generations", [])
            }
            for generation in range(1, generations + 1):
                item = generation_map.get(generation)
                if item is None:
                    by_generation[generation].append(False if not alive else False)
                    alive = False
                    continue
                survived = bool(item["survived"])
                alive = alive and survived
                by_generation[generation].append(alive)
                costs.append(float(item["maintenance_cost"]["score"]))
                category = str(item["scenario"]["category"])
                category_survival[category].append(survived)
                if not survived:
                    deaths[category] += 1

                inv = item.get("invariant_dna") or {}
                for check in inv.get("results") or []:
                    invariant_checks += 1
                    if check.get("passed"):
                        invariant_passes += 1

                patch_touch_generations += 1
                if item.get("patch_surface_touched"):
                    patch_touches += 1

        survival_curve = [{"generation": 0, "survival_rate": 1.0}]
        for generation in range(1, generations + 1):
            values = by_generation.get(generation, [])
            survival_curve.append(
                {
                    "generation": generation,
                    "survival_rate": (
                        sum(1 for value in values if value) / trajectories
                        if trajectories
                        else 0.0
                    ),
                }
            )

        temporal_survival = (
            sum(
                float(point["survival_rate"])
                for point in survival_curve
                if point["generation"] > 0
            )
            / max(generations, 1)
        )
        average_cost = sum(costs) / len(costs) if costs else 0.0
        normalized_cost = 1.0 / (1.0 + average_cost / 20.0)
        option_value = temporal_survival * normalized_cost

        resilience_categories = {
            "dependency_upgrade",
            "api_deprecation",
            "platform_runtime",
        }
        resilience_values = [
            survived
            for category, values in category_survival.items()
            if category in resilience_categories
            for survived in values
        ]
        dependency_robustness = (
            sum(1 for value in resilience_values if value) / len(resilience_values)
            if resilience_values
            else None
        )
        invariant_survival = (
            invariant_passes / invariant_checks
            if invariant_checks
            else None
        )
        patch_surface_stability = (
            1.0 - patch_touches / patch_touch_generations
            if patch_touch_generations and seed.get("changed_paths")
            else None
        )

        return {
            "format": "lr-agent-chronoforge-report/v1",
            "run_id": run_id,
            "source_type": seed["source_type"],
            "source_ref": seed["source_ref"],
            "patch_intent": seed.get("task") or "",
            "generations": generations,
            "trajectories": trajectories,
            "scenario_pool": scenarios,
            "metrics": {
                "temporal_survival": round(temporal_survival, 4),
                "future_maintenance_cost": round(average_cost, 4),
                "maintenance_option_value": round(option_value, 4),
                "invariant_survival": (
                    round(invariant_survival, 4)
                    if invariant_survival is not None
                    else None
                ),
                "dependency_robustness": (
                    round(dependency_robustness, 4)
                    if dependency_robustness is not None
                    else None
                ),
                "patch_surface_stability": (
                    round(patch_surface_stability, 4)
                    if patch_surface_stability is not None
                    else None
                ),
                "predicted_half_life": self._half_life(survival_curve),
            },
            "survival_curve": survival_curve,
            "category_survival": {
                category: round(
                    sum(1 for value in values if value) / len(values),
                    4,
                )
                for category, values in sorted(category_survival.items())
                if values
            },
            "death_modes": dict(deaths.most_common()),
            "trajectory_results": trajectory_results,
            "calibration": self.store.calibration(),
            "limitations": [
                "Future scenarios are synthetic stress tests, not guaranteed forecasts.",
                "Maintenance cost is an observable engineering heuristic based on tool steps, failures and changed-file scope.",
                "Temporal survival means the seed checks/invariants remained valid under simulated repository evolution; it is not a formal proof of future correctness.",
            ],
        }

    async def _execute(
        self,
        run_id: str,
        *,
        seed: dict[str, Any],
        task: str,
        generations: int,
        trajectories: int,
    ) -> dict[str, Any]:
        self.store.update_run(run_id, status="running")
        try:
            seed_manifest, seed_scan = await asyncio.to_thread(
                self.universes._scan_manifest,
                seed["workspace"],
            )
            seed_root = self._run_dir(run_id) / "seed"
            await asyncio.to_thread(
                self.universes._copy_manifest,
                seed["workspace"],
                seed_root,
                seed_manifest,
            )
            profile = await self._project_profile(seed_root)
            seed_verification = await self._seed_verification_commands(seed, profile)
            patch_intent = task.strip() or str(seed.get("task") or "").strip()
            scenarios = await self._generate_scenarios(
                task=patch_intent,
                profile=profile,
                changed_paths=list(seed.get("changed_paths") or []),
            )
            schedule = self._scenario_schedule(
                scenarios,
                generations=generations,
                trajectories=trajectories,
            )
            self.store.update_run(
                run_id,
                status="running",
                scenarios=scenarios,
                report={
                    "phase": "aging",
                    "seed_scan": seed_scan,
                    "profile": profile,
                    "seed_verification": seed_verification,
                    "completed_generations": 0,
                    "total_generations": generations * trajectories,
                },
            )

            trajectory_results: list[dict[str, Any]] = []
            completed = 0
            for trajectory in range(1, trajectories + 1):
                previous = seed_root
                items: list[dict[str, Any]] = []
                alive = True
                for generation in range(1, generations + 1):
                    if not alive:
                        break
                    scenario = schedule[trajectory - 1][generation - 1]
                    item = await self._run_generation(
                        run_id=run_id,
                        trajectory=trajectory,
                        generation=generation,
                        previous_workspace=previous,
                        scenario=scenario,
                        patch_intent=patch_intent,
                        changed_paths=list(seed.get("changed_paths") or []),
                        seed_verification=seed_verification,
                    )
                    items.append(item)
                    completed += 1
                    alive = bool(item["survived"])
                    previous = Path(item["workspace"])
                    self.store.update_run(
                        run_id,
                        status="running",
                        report={
                            "phase": "aging",
                            "seed_scan": seed_scan,
                            "profile": profile,
                            "seed_verification": seed_verification,
                            "completed_generations": completed,
                            "total_generations": generations * trajectories,
                            "active_trajectory": trajectory,
                            "active_generation": generation,
                            "last_result": {
                                "scenario": item["scenario"],
                                "survived": item["survived"],
                                "maintenance_cost": item["maintenance_cost"],
                            },
                        },
                    )
                trajectory_results.append(
                    {
                        "trajectory": trajectory,
                        "survived_all_generations": alive and len(items) == generations,
                        "generations": items,
                    }
                )

            report = self._aggregate_report(
                run_id=run_id,
                seed={**seed, "task": patch_intent},
                generations=generations,
                trajectories=trajectories,
                scenarios=scenarios,
                trajectory_results=trajectory_results,
            )
            self.store.update_run(
                run_id,
                status="completed",
                scenarios=scenarios,
                report=report,
                error=None,
            )
            return report
        except asyncio.CancelledError:
            self.store.update_run(
                run_id,
                status="cancelled",
                error="ChronoForge run cancelled.",
            )
            raise
        except Exception as exc:
            self.store.update_run(
                run_id,
                status="failed",
                error=f"{type(exc).__name__}: {exc}",
            )
            raise

    def start(
        self,
        *,
        task: str = "",
        tournament_id: str | None = None,
        candidate_id: str | None = None,
        generations: int | None = None,
        trajectories: int | None = None,
    ) -> dict[str, Any]:
        if not self.settings.chronoforge_enabled:
            raise ChronoForgeError("ChronoForge is disabled by configuration.")
        generations = min(
            max(generations or self.settings.chronoforge_generations, 1),
            self.settings.chronoforge_max_generations,
        )
        trajectories = min(
            max(trajectories or self.settings.chronoforge_trajectories, 1),
            self.settings.chronoforge_max_trajectories,
        )
        seed = self._resolve_seed(
            tournament_id=tournament_id,
            candidate_id=candidate_id,
        )
        run = self.store.create_run(
            source_type=seed["source_type"],
            source_ref=seed["source_ref"],
            task=task.strip() or str(seed.get("task") or ""),
            generations=generations,
            trajectories=trajectories,
        )
        run_id = str(run["id"])
        job = asyncio.create_task(
            self._execute(
                run_id,
                seed=seed,
                task=task,
                generations=generations,
                trajectories=trajectories,
            )
        )
        self._jobs[run_id] = job
        job.add_done_callback(
            lambda _task, rid=run_id: self._jobs.pop(rid, None)
        )
        return run

    async def run(
        self,
        *,
        task: str = "",
        tournament_id: str | None = None,
        candidate_id: str | None = None,
        generations: int | None = None,
        trajectories: int | None = None,
    ) -> dict[str, Any]:
        generations = min(
            max(generations or self.settings.chronoforge_generations, 1),
            self.settings.chronoforge_max_generations,
        )
        trajectories = min(
            max(trajectories or self.settings.chronoforge_trajectories, 1),
            self.settings.chronoforge_max_trajectories,
        )
        seed = self._resolve_seed(
            tournament_id=tournament_id,
            candidate_id=candidate_id,
        )
        item = self.store.create_run(
            source_type=seed["source_type"],
            source_ref=seed["source_ref"],
            task=task.strip() or str(seed.get("task") or ""),
            generations=generations,
            trajectories=trajectories,
        )
        return await self._execute(
            str(item["id"]),
            seed=seed,
            task=task,
            generations=generations,
            trajectories=trajectories,
        )

    def get(self, run_id: str) -> dict[str, Any] | None:
        return self.store.get_run(run_id)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.store.list_runs(limit)

    async def cancel(self, run_id: str) -> bool:
        item = self.store.get_run(run_id)
        if item is None:
            return False
        task = self._jobs.get(run_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    def observe_future(
        self,
        *,
        category: str,
        note: str,
        source: str = "reality",
    ) -> dict[str, Any]:
        return self.store.add_observation(
            category=category,
            note=note,
            source=source,
        )

    def calibration(self) -> dict[str, Any]:
        return self.store.calibration()
