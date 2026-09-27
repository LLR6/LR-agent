from pathlib import Path

from lr_agent.memory import MemoryStore


def test_memory_roundtrip(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    session_id = store.create_session("hello")
    assert store.session_exists(session_id)

    store.add_message(session_id, "user", "one")
    store.add_message(session_id, "assistant", "two")

    assert store.recent_messages(session_id) == [
        {"role": "user", "content": "one"},
        {"role": "assistant", "content": "two"},
    ]
    sessions = store.list_sessions()
    assert sessions[0]["id"] == session_id


def test_run_persistence_roundtrip(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path / "memory.db")
    session_id = store.create_session("persist run")
    run_id = store.start_run(
        session_id,
        mode="coder",
        task="fix tests",
        plan={
            "goal": "fix tests",
            "steps": [
                {
                    "action": "run tests",
                    "success_condition": "failure is reproduced",
                }
            ],
            "success_criteria": ["tests pass"],
        },
    )
    store.add_run_step(
        run_id,
        step_index=1,
        tool="run_command",
        arguments={"argv": ["pytest"]},
        ok=True,
        preview='{"returncode": 0}',
    )
    store.finish_run(
        run_id,
        answer="tests pass",
        review={
            "passed": True,
            "summary": "verified",
            "problems": [],
            "next_actions": [],
        },
        status="completed",
    )

    item = store.get_run(run_id)
    assert item is not None
    assert item["status"] == "completed"
    assert item["plan"]["goal"] == "fix tests"
    assert item["steps"][0]["tool"] == "run_command"
    assert item["steps"][0]["ok"] is True
    assert item["review"]["passed"] is True
    assert store.list_runs()[0]["id"] == run_id
