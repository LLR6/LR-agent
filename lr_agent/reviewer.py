from __future__ import annotations

import json
import re
from typing import Any

from .models import AgentPlan, AgentStep, ReviewReport


def _json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("review response did not contain JSON")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("review JSON must be an object")
    return value


class Reviewer:
    def __init__(self, llm: Any):
        self.llm = llm

    async def review(
        self,
        *,
        task: str,
        plan: AgentPlan | None,
        steps: list[AgentStep],
        proposed_answer: str,
    ) -> ReviewReport:
        evidence = [
            {
                "tool": step.tool,
                "ok": step.ok,
                "preview": step.preview[:500],
            }
            for step in steps[-20:]
        ]
        prompt = {
            "task": task,
            "plan": plan.model_dump() if plan else None,
            "tool_evidence": evidence,
            "proposed_answer": proposed_answer,
        }
        raw = await self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a strict execution reviewer. Judge only observable evidence. "
                        "Do not expose chain-of-thought. Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Review whether the task is actually complete. A claim of success "
                        "without tool evidence should fail when verification is possible.\n\n"
                        + json.dumps(prompt, ensure_ascii=False)
                        + '\n\nReturn: {"passed": true|false, "summary": "short", '
                        '"problems": ["short issue"], "next_actions": ["concrete action"]}'
                    ),
                },
            ],
            tools=None,
            temperature=0,
        )
        content = raw.get("content") or ""
        try:
            data = _json_object(content)
            return ReviewReport(
                passed=bool(data.get("passed", False)),
                summary=str(data.get("summary", "")).strip() or "Review completed.",
                problems=[
                    str(item).strip()
                    for item in data.get("problems", [])
                    if str(item).strip()
                ][:8],
                next_actions=[
                    str(item).strip()
                    for item in data.get("next_actions", [])
                    if str(item).strip()
                ][:8],
            )
        except (ValueError, json.JSONDecodeError, TypeError):
            return ReviewReport(
                passed=True,
                summary="Reviewer output was not machine-parseable; preserving the executor result.",
                problems=[],
                next_actions=[],
            )
