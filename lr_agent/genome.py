from __future__ import annotations

import json
from typing import Any

from .config import Settings
from .genome_store import GenomeStore
from .tools import ToolRegistry
from .universes import UniverseLab


class GenomeError(RuntimeError):
    pass


class CausalGenomeEngine:
    """
    Turns counterfactual coding experiments into persistent, falsifiable strategy genes.

    A gene starts in quarantine. It becomes active only after repeated treatment-vs-control
    evidence clears configured thresholds. Harmful evidence can create an anti-gene that
    carries the counterexample forward instead of simply deleting the failed strategy.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        store: GenomeStore | None = None,
        universe_lab: UniverseLab | None = None,
    ):
        self.settings = settings
        self.store = store or GenomeStore(settings.genome_database)
        self.universes = universe_lab or UniverseLab(settings)

    def create_gene(
        self,
        *,
        name: str,
        instruction: str,
        applicability: list[str] | None = None,
        exclusions: list[str] | None = None,
        verifier: list[dict[str, Any]] | None = None,
        parent_ids: list[str] | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.store.create_gene(
            name=name,
            instruction=instruction,
            kind="strategy",
            applicability=applicability,
            exclusions=exclusions,
            verifier=verifier,
            provenance=provenance,
            parent_ids=parent_ids,
            status="quarantine",
        )

    def import_forge_winner(
        self,
        tournament_id: str,
        *,
        candidate_id: str | None = None,
        parent_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        tournament = self.universes.get(tournament_id)
        if tournament.get("status") != "completed":
            raise GenomeError("Only completed Forge tournaments can become genes.")

        selected_id = candidate_id or str(tournament.get("winner_id") or "")
        candidate = next(
            (
                item
                for item in tournament.get("candidates", [])
                if item.get("id") == selected_id
            ),
            None,
        )
        if candidate is None:
            raise GenomeError(f"Forge candidate not found: {selected_id}")

        strategy = candidate.get("strategy") or {}
        task = str(tournament.get("task") or "").strip()
        evidence = candidate.get("evidence") or {}
        return self.create_gene(
            name=str(strategy.get("name") or selected_id),
            instruction=str(strategy.get("instruction") or "").strip()
            or "Use the imported Forge strategy only when its observed preconditions hold.",
            applicability=[task] if task else [],
            exclusions=[],
            verifier=list(candidate.get("verification_commands") or []),
            parent_ids=parent_ids,
            provenance={
                "source": "forge_winner",
                "tournament_id": tournament_id,
                "candidate_id": selected_id,
                "forge_evidence": evidence,
                "note": (
                    "Imported Forge success is provenance, not causal evidence. "
                    "The gene remains quarantined until ablation experiments validate it."
                ),
            },
        )

    @staticmethod
    def _candidate(
        tournament: dict[str, Any],
        candidate_id: str,
    ) -> dict[str, Any]:
        candidate = next(
            (
                item
                for item in tournament.get("candidates", [])
                if item.get("id") == candidate_id
            ),
            None,
        )
        if candidate is None:
            raise GenomeError(f"Candidate missing from tournament: {candidate_id}")
        return candidate

    def _strategies_for_gene(
        self,
        gene: dict[str, Any],
        *,
        falsification: bool,
    ) -> list[dict[str, str]]:
        boundaries = {
            "applicability": gene["applicability"],
            "exclusions": gene["exclusions"],
            "verifier": gene["verifier"],
            "confidence": gene["confidence"],
            "status": gene["status"],
        }
        if falsification:
            treatment_instruction = (
                "You are the TREATMENT arm of a falsification experiment. "
                "The candidate gene below is a hypothesis, not an instruction that must be true. "
                "Actively try to disprove its applicability: inspect preconditions, exclusions, "
                "edge cases and project invariants first. If it survives those checks, apply it "
                "faithfully and verify the result. If it does not apply, demonstrate that with "
                "tool evidence instead of forcing it.\n\n"
                f"GENE: {gene['name']}\n"
                f"INSTRUCTION: {gene['instruction']}\n"
                f"BOUNDARIES: {json.dumps(boundaries, ensure_ascii=False)}"
            )
        else:
            treatment_instruction = (
                "You are the TREATMENT arm of a controlled strategy ablation. "
                "Use the following strategy gene only after checking its applicability and "
                "exclusions against the project. Follow it as the primary strategy, then run "
                "real verification.\n\n"
                f"GENE: {gene['name']}\n"
                f"INSTRUCTION: {gene['instruction']}\n"
                f"BOUNDARIES: {json.dumps(boundaries, ensure_ascii=False)}"
            )

        control_instruction = (
            "You are the CONTROL arm of a controlled strategy ablation. Solve the task from "
            "project evidence without using, reconstructing or imitating the treatment gene. "
            "Inspect before editing, minimize unsupported assumptions, and run real verification. "
            "The comparison is about whether the gene adds value beyond an independent competent "
            "coding-agent baseline."
        )
        return [
            {
                "id": "treatment",
                "name": f"Gene treatment · {gene['name']}"[:120],
                "instruction": treatment_instruction,
            },
            {
                "id": "control",
                "name": "Independent control",
                "instruction": control_instruction,
            },
        ]

    async def ablate(
        self,
        gene_id: str,
        task: str,
        *,
        trials: int = 1,
        falsification: bool = False,
    ) -> dict[str, Any]:
        gene = self.store.get_gene(gene_id)
        if gene is None:
            raise GenomeError(f"Gene not found: {gene_id}")
        if gene["status"] in {"retired", "contaminated"}:
            raise GenomeError(
                f"Gene status {gene['status']} cannot enter new ablation experiments."
            )
        trials = min(max(int(trials), 1), 5)

        experiments: list[dict[str, Any]] = []
        anti_genes: list[dict[str, Any]] = []
        for trial in range(1, trials + 1):
            tournament = await self.universes.run_strategies(
                task,
                self._strategies_for_gene(
                    gene,
                    falsification=falsification,
                ),
                evolve=False,
            )
            if tournament.get("status") != "completed":
                experiments.append(
                    {
                        "trial": trial,
                        "status": "failed",
                        "tournament_id": tournament.get("id"),
                        "error": tournament.get("error"),
                    }
                )
                continue

            treatment = self._candidate(tournament, "treatment")
            control = self._candidate(tournament, "control")
            treatment_score = float(treatment["evidence"]["score"])
            control_score = float(control["evidence"]["score"])
            evidence = self.store.record_evidence(
                gene_id=gene_id,
                task=task,
                treatment_score=treatment_score,
                control_score=control_score,
                experiment_type="falsification" if falsification else "ablation",
                tournament_id=str(tournament["id"]),
                details={
                    "trial": trial,
                    "treatment": {
                        "status": treatment["status"],
                        "evidence": treatment["evidence"],
                        "review": treatment.get("review"),
                        "changes": treatment.get("changes"),
                    },
                    "control": {
                        "status": control["status"],
                        "evidence": control["evidence"],
                        "review": control.get("review"),
                        "changes": control.get("changes"),
                    },
                },
                positive_threshold=self.settings.gene_positive_lift_threshold,
                negative_threshold=self.settings.gene_negative_lift_threshold,
                activation_min_experiments=self.settings.gene_activation_min_experiments,
                activation_min_positive_rate=self.settings.gene_activation_min_positive_rate,
                activation_min_average_lift=self.settings.gene_activation_min_average_lift,
            )
            experiments.append(
                {
                    "trial": trial,
                    "status": "completed",
                    "tournament_id": tournament["id"],
                    "treatment_score": treatment_score,
                    "control_score": control_score,
                    "effect": evidence["effect"],
                    "outcome": evidence["outcome"],
                    "evidence_id": evidence["id"],
                }
            )

            if evidence["outcome"] == "negative":
                anti = self.store.ensure_antigene(
                    parent_gene_id=gene_id,
                    task=task,
                    evidence_id=evidence["id"],
                    effect=float(evidence["effect"]),
                )
                anti_genes.append(anti)

            gene = self.store.get_gene(gene_id) or gene

        completed = [item for item in experiments if item["status"] == "completed"]
        effects = [float(item["effect"]) for item in completed]
        return {
            "gene": self.store.get_gene(gene_id),
            "task": task,
            "experiment_type": "falsification" if falsification else "ablation",
            "trials_requested": trials,
            "trials_completed": len(completed),
            "average_trial_effect": (
                sum(effects) / len(effects) if effects else None
            ),
            "experiments": experiments,
            "anti_genes": anti_genes,
        }

    async def falsify(
        self,
        gene_id: str,
        task: str,
        *,
        trials: int = 1,
    ) -> dict[str, Any]:
        return await self.ablate(
            gene_id,
            task,
            trials=trials,
            falsification=True,
        )

    def contaminate(
        self,
        gene_id: str,
        *,
        reason: str,
        propagate: bool = True,
    ) -> dict[str, Any]:
        return self.store.mark_contaminated(
            gene_id,
            reason=reason,
            propagate=propagate,
        )

    def context_for_task(
        self,
        task: str,
        *,
        limit: int | None = None,
    ) -> dict[str, Any]:
        genes = self.store.search_genes(
            task,
            limit=limit or self.settings.genome_context_results,
            active_only=True,
        )
        invariants = (
            self.store.list_invariants(status="active", limit=100)
            if self.settings.invariants_enabled
            else []
        )
        return {
            "genes": genes,
            "invariants": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "description": item["description"],
                    "commands": item["commands"],
                    "last_status": item["last_status"],
                }
                for item in invariants
            ],
        }

    async def check_invariants(self) -> dict[str, Any]:
        if not self.settings.invariants_enabled:
            return {
                "enabled": False,
                "passed": None,
                "results": [],
            }

        invariants = self.store.list_invariants(status="active", limit=500)
        tools = ToolRegistry(
            self.settings.model_copy(
                deep=True,
                update={
                    "approval_mode": "off",
                    "allow_github_write": False,
                },
            )
        )
        overall = True
        results: list[dict[str, Any]] = []

        for invariant in invariants:
            command_results: list[dict[str, Any]] = []
            invariant_passed = True
            for command in invariant["commands"]:
                outcome = await tools.execute("run_command", dict(command))
                payload = outcome.get("result") or {}
                passed = bool(outcome.get("ok")) and payload.get("returncode") == 0
                command_results.append(
                    {
                        "command": command,
                        "passed": passed,
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
                "commands": command_results,
            }
            self.store.record_invariant_check(
                invariant["id"],
                passed=invariant_passed,
                details=details,
            )
            results.append(
                {
                    "id": invariant["id"],
                    "name": invariant["name"],
                    "passed": invariant_passed,
                    "commands": command_results,
                }
            )

        return {
            "enabled": True,
            "passed": overall,
            "results": results,
        }

    def register_invariant(
        self,
        *,
        name: str,
        description: str,
        commands: list[dict[str, Any]],
        source_gene_id: str | None = None,
    ) -> dict[str, Any]:
        return self.store.create_invariant(
            name=name,
            description=description,
            commands=commands,
            source_gene_id=source_gene_id,
            status="active",
        )

    def stats(self) -> dict[str, Any]:
        return self.store.stats()
