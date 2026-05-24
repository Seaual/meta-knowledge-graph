from unittest.mock import MagicMock, patch

import httpx
import pytest

from mkg.llm_client import LLMClient


def test_llm_client_openai_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "hello from openai"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response

    with patch("mkg.llm_client.httpx.Client", return_value=mock_client_instance) as MockClient:
        client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")
        assert MockClient.call_count == 1
        result = client.complete_sync("say hi")
        assert result == "hello from openai"


def test_llm_client_anthropic_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": [{"text": "hello from anthropic"}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response

    with patch("mkg.llm_client.httpx.Client", return_value=mock_client_instance) as MockClient:
        client = LLMClient(api_key="sk-test", provider="anthropic", model="claude-3-5-sonnet-latest")
        assert MockClient.call_count == 1
        result = client.complete_sync("say hi")
        assert result == "hello from anthropic"


def test_llm_client_unknown_provider():
    client = LLMClient(api_key="sk-test", provider="unknown")

    with pytest.raises(ValueError, match="Unknown provider"):
        client.complete_sync("say hi")


def test_llm_client_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response,
        )
    )

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response

    with patch("mkg.llm_client.httpx.Client", return_value=mock_client_instance):
        client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")
        with pytest.raises(httpx.HTTPStatusError):
            client.complete_sync("say hi")
