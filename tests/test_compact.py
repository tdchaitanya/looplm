from datetime import datetime

from looplm.chat.session import ChatSession, Message


def make_session():
    session = ChatSession()
    session.set_system_prompt("You are LoopLM, a helpful assistant.")
    session.messages.append(
        Message("user", "How do I use the API?", timestamp=datetime.now())
    )
    session.messages.append(
        Message("assistant", "You can use the API by ...", timestamp=datetime.now())
    )
    session.messages.append(
        Message("user", "Show me an example.", timestamp=datetime.now())
    )
    session.messages.append(
        Message("assistant", "Here is an example: ...", timestamp=datetime.now())
    )
    return session


def test_normal_flow():
    session = make_session()
    msgs = session.get_messages_for_api()
    assert len(msgs) == 5  # system + 4
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "user"
    assert msgs[-1]["role"] == "assistant"
    assert not session.is_compacted


def test_compact_and_context():
    session = make_session()
    summary = "[SUMMARY] User asked about API usage and examples."
    session.set_compact_summary(summary)
    msgs = session.get_messages_for_api()
    # Should be: system, summary (assistant), nothing after compact
    assert msgs[0]["role"] == "system"
    assert msgs[1]["role"] == "assistant"
    assert summary in msgs[1]["content"]
    assert len(msgs) == 2
    assert session.is_compacted


def test_add_after_compact():
    session = make_session()
    summary = "[SUMMARY] User asked about API usage and examples."
    session.set_compact_summary(summary)
    session.messages.append(
        Message("user", "How do I authenticate?", timestamp=datetime.now())
    )
    msgs = session.get_messages_for_api()
    # Should be: system, summary, new user message
    assert len(msgs) == 3
    assert msgs[2]["role"] == "user"
    assert "authenticate" in msgs[2]["content"]


def test_reset_compact():
    session = make_session()
    summary = "[SUMMARY] User asked about API usage and examples."
    session.set_compact_summary(summary)
    session.reset_compact()
    msgs = session.get_messages_for_api()
    # Should be full history again
    assert len(msgs) == 5
    assert not session.is_compacted


def test_persistence():
    session = make_session()
    summary = "[SUMMARY] User asked about API usage and examples."
    session.set_compact_summary(summary)
    d = session.to_dict()
    loaded = ChatSession.from_dict(d)
    assert loaded.is_compacted
    assert loaded.compact_summary == summary
    # Add after reload
    loaded.messages.append(
        Message("user", "Another question", timestamp=datetime.now())
    )
    msgs = loaded.get_messages_for_api()
    assert msgs[-1]["role"] == "user"
    assert "Another question" in msgs[-1]["content"]
