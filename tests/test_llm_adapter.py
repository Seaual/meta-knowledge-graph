from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage, SystemMessage

from mkg.llm_adapter import MKGChatModel


def test_generate_with_human_and_system():
    mock_client = MagicMock()
    mock_client.provider = "openai"
    mock_client.model = "gpt-4o"
    mock_client.complete_messages_sync.return_value = "generated text"

    model = MKGChatModel(client=mock_client)
    result = model.invoke([SystemMessage(content="sys"), HumanMessage(content="hi")])

    assert result.content == "generated text"
    mock_client.complete_messages_sync.assert_called_once()
    call_args = mock_client.complete_messages_sync.call_args
    assert call_args.kwargs["system"] == "sys"
    assert call_args.args[0] == [{"role": "user", "content": "hi"}]


def test_generate_with_tool_message():
    from langchain_core.messages import ToolMessage

    mock_client = MagicMock()
    mock_client.provider = "openai"
    mock_client.model = "gpt-4o"
    mock_client.complete_messages_sync.return_value = "tool response"

    model = MKGChatModel(client=mock_client)
    result = model.invoke([
        HumanMessage(content="question"),
        ToolMessage(content="tool result", tool_call_id="tc1"),
    ])

    assert result.content == "tool response"
    call_args = mock_client.complete_messages_sync.call_args
    assert call_args.args[0] == [
        {"role": "user", "content": "question"},
        {"role": "tool", "content": "tool result", "tool_call_id": "tc1"},
    ]


@pytest.mark.asyncio
async def test_agenerate_async():
    mock_client = MagicMock()
    mock_client.provider = "anthropic"
    mock_client.model = "claude-3-5-sonnet-latest"
    from unittest.mock import AsyncMock
    mock_client.complete_messages = AsyncMock(return_value="async result")

    model = MKGChatModel(client=mock_client)
    result = await model.ainvoke([HumanMessage(content="hi")])

    assert result.content == "async result"


def test_llm_type_and_params():
    mock_client = MagicMock()
    mock_client.provider = "openai"
    mock_client.model = "gpt-4o"

    model = MKGChatModel(client=mock_client)
    assert model._llm_type == "mkg"
    assert model._identifying_params == {"provider": "openai", "model": "gpt-4o"}
