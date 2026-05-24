import pytest
from langchain_core.messages import AIMessage

from mkg.agent.streaming import convert_chunk_to_sse


class TestConvertChunkToSSE:
    def test_todo_event(self):
        chunk = {
            "type": "updates",
            "data": {"todos": [{"id": "1", "title": "Search papers", "status": "running"}]},
        }
        event = convert_chunk_to_sse(chunk)
        assert event is not None
        assert event["type"] == "todo"

    def test_token_event(self):
        chunk = {
            "type": "messages",
            "data": (AIMessage(content="Hello"), {}),
        }
        event = convert_chunk_to_sse(chunk)
        assert event is not None
        assert event["type"] == "token"
        assert event["content"] == "Hello"

    def test_unknown_chunk_returns_none(self):
        chunk = {"type": "unknown", "data": {}}
        assert convert_chunk_to_sse(chunk) is None
