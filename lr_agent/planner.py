from __future__ import annotations

import json
import re
from typing import Any

from .models import AgentPlan, PlanItem


def _json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty planner response")
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("planner response did not contain a JSON object")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("planner JSON must be an object")
    return value


class Planner:
    def __init__(self, llm: Any):
        self.llm = llm

    async def create(self, user_message: str, mode: str) -> AgentPlan:
        prompt = f"""Create a short execution plan for an AI agent.

Mode: {mode}
Task: {user_message}

Return JSON only with this exact shape:
{{
  "goal": "one sentence",
  "steps": [
    {{"action": "concrete observable action", "success_condition": "how to verify it"}}
  ],
  "success_criteria": ["observable criterion"]
}}

Constraints:
- 2 to 7 steps.
- Do not include hidden reasoning or chain-of-thought.
- Use actions that can be verified through tools.
- For coding tasks, include inspection before editing and verification after editing.
- If the task is simple, keep the plan small.
"""
        raw = await self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a task planner. Produce concise, externally verifiable "
                        "plans. Return JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            tools=None,
            temperature=0.1,
        )
        content = raw.get("content") or ""
        try:
            data = _json_object(content)
            steps = [
                PlanItem(
                    action=str(item.get("action", "")).strip(),
                    success_condition=str(item.get("success_condition", "")).strip(),
                )
                for item in data.get("steps", [])
                if isinstance(item, dict) and str(item.get("action", "")).strip()
            ]
            if not steps:
                raise ValueError("planner returned no usable steps")
            return AgentPlan(
                goal=str(data.get("goal") or user_message).strip(),
                steps=steps[:7],
                success_criteria=[
                    str(item).strip()
                    for item in data.get("success_criteria", [])
                    if str(item).strip()
                ][:7],
            )
        except (ValueError, json.JSONDecodeError, TypeError):
            return AgentPlan(
                goal=user_message.strip(),
                steps=[
                    PlanItem(
                        action="Inspect the relevant workspace state before making changes.",
                        success_condition="Relevant files or current state have been read.",
                    ),
                    PlanItem(
                        action="Perform the minimum changes needed to complete the task.",
                        success_condition="Requested changes are present in the workspace.",
                    ),
                    PlanItem(
                        action="Verify the result with an available check or test.",
                        success_condition="A concrete verification result is available.",
                    ),
                ],
                success_criteria=["The requested result is verifiably completed."],
            )
