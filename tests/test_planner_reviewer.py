import pytest

from lr_agent.models import AgentPlan, AgentStep, PlanItem
from lr_agent.planner import Planner
from lr_agent.reviewer import Reviewer


class StaticLLM:
    def __init__(self, content: str):
        self.content = content

    async def chat(self, messages, tools=None, temperature=0.2):
        return {"content": self.content}


@pytest.mark.asyncio
async def test_planner_parses_json_object() -> None:
    planner = Planner(
        StaticLLM(
            'prefix {"goal":"ship fix","steps":['
            '{"action":"inspect","success_condition":"state known"},'
            '{"action":"verify","success_condition":"tests pass"}'
            '],"success_criteria":["tests pass"]} suffix'
        )
    )
    plan = await planner.create("fix it", "coder")
    assert plan.goal == "ship fix"
    assert len(plan.steps) == 2
    assert plan.steps[1].success_condition == "tests pass"


@pytest.mark.asyncio
async def test_planner_falls_back_on_invalid_output() -> None:
    planner = Planner(StaticLLM("not-json"))
    plan = await planner.create("fix it", "coder")
    assert plan.goal == "fix it"
    assert len(plan.steps) == 3


@pytest.mark.asyncio
async def test_reviewer_parses_verdict() -> None:
    reviewer = Reviewer(
        StaticLLM(
            '{"passed":false,"summary":"tests were not run",'
            '"problems":["missing verification"],'
            '"next_actions":["run pytest"]}'
        )
    )
    report = await reviewer.review(
        task="fix it",
        plan=AgentPlan(
            goal="fix it",
            steps=[
                PlanItem(
                    action="run tests",
                    success_condition="tests pass",
                )
            ],
            success_criteria=["tests pass"],
        ),
        steps=[
            AgentStep(
                index=1,
                tool="write_file",
                arguments={"path": "x.py"},
                ok=True,
                preview="written",
            )
        ],
        proposed_answer="done",
    )
    assert report.passed is False
    assert report.next_actions == ["run pytest"]
