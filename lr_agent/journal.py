from __future__ import annotations

from typing import Any

from .config import Settings
from .memory import MemoryStore
from .tools import ToolRegistry


class WorkspaceJournal:
    """Run-scoped snapshots for direct workspace mutation tools.

    The journal deliberately covers ToolRegistry's explicit local mutation tools.
    Side effects produced by run_command, package managers, build scripts, Git hooks
    or external programs are outside this rollback mechanism.
    """

    def __init__(
        self,
        settings: Settings,
        memory: MemoryStore,
        tools: ToolRegistry,
    ):
        self.settings = settings
        self.memory = memory
        self.tools = tools

    def capture_before(
        self,
        run_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> list[str]:
        if (
            not self.settings.enable_run_snapshots
            or not self.tools.is_local_mutation(tool_name)
        ):
            return []

        paths = self.tools.mutation_snapshot_paths(tool_name, arguments)
        for path in paths:
            snapshot = self.tools.capture_path_snapshot(
                path,
                max_file_bytes=self.settings.snapshot_max_file_bytes,
            )
            self.memory.save_run_snapshot(
                run_id,
                path=path,
                original_kind=snapshot["kind"],
                original_content=snapshot["content"],
                original_mode=snapshot["mode"],
                original_hash=snapshot["hash"],
            )
        return paths

    def capture_after(self, run_id: str, paths: list[str]) -> None:
        for path in paths:
            state = self.tools.current_path_state(path)
            self.memory.update_run_snapshot_final(
                run_id,
                path=path,
                final_kind=state["kind"],
                final_hash=state["hash"],
            )

    @staticmethod
    def _matches_expected(
        current: dict[str, Any],
        *,
        expected_kind: str | None,
        expected_hash: str | None,
    ) -> bool:
        if expected_kind is None:
            return False
        if current["kind"] != expected_kind:
            return False
        if expected_kind == "file":
            return current["hash"] == expected_hash
        return True

    async def rollback(self, run_id: str) -> dict[str, Any]:
        snapshots = self.memory.list_run_snapshots(run_id)
        if not snapshots:
            return {
                "run_id": run_id,
                "rolled_back": False,
                "restored": [],
                "conflicts": [],
                "message": (
                    "No direct-file snapshots were recorded for this run. "
                    "Command side effects are not rollback-managed."
                ),
            }

        async with self.tools.mutation_lock:
            conflicts: list[dict[str, Any]] = []
            for snapshot in snapshots:
                current = self.tools.current_path_state(snapshot["path"])
                if not self._matches_expected(
                    current,
                    expected_kind=snapshot.get("final_kind"),
                    expected_hash=snapshot.get("final_hash"),
                ):
                    conflicts.append(
                        {
                            "path": snapshot["path"],
                            "expected_kind": snapshot.get("final_kind"),
                            "expected_hash": snapshot.get("final_hash"),
                            "current_kind": current["kind"],
                            "current_hash": current["hash"],
                        }
                    )

            if conflicts:
                return {
                    "run_id": run_id,
                    "rolled_back": False,
                    "restored": [],
                    "conflicts": conflicts,
                    "message": (
                        "Rollback refused because workspace state changed after the run. "
                        "No files were modified."
                    ),
                }

            restored: list[str] = []
            for snapshot in reversed(snapshots):
                self.tools.restore_path_snapshot(snapshot)
                restored.append(snapshot["path"])

            self.memory.update_run_status(run_id, "rolled_back")
            return {
                "run_id": run_id,
                "rolled_back": True,
                "restored": restored,
                "conflicts": [],
                "message": (
                    "Direct file-tool changes were restored to their pre-run state. "
                    "Side effects from run_command or external programs are not included."
                ),
            }
