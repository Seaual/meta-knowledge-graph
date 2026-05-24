from unittest.mock import MagicMock, patch

from mkg.llm_client import LLMClient


def test_llm_client_openai_success():
    client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "hello from openai"}}]
    }

    with patch("mkg.llm_client.httpx.Client.post", return_value=mock_response):
        result = client.complete_sync("say hi")
        assert result == "hello from openai"
