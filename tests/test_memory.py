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
