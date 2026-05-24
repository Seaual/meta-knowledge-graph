from unittest.mock import AsyncMock, MagicMock, patch

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
    mock_client_instance.request.return_value = mock_response

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
    mock_client_instance.request.return_value = mock_response

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
    mock_client_instance.request.return_value = mock_response

    with patch("mkg.llm_client.httpx.Client", return_value=mock_client_instance):
        client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")
        with pytest.raises(httpx.HTTPStatusError):
            client.complete_sync("say hi")


def test_llm_client_anthropic_http_error_sync():
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
    mock_client_instance.request.return_value = mock_response

    with patch("mkg.llm_client.httpx.Client", return_value=mock_client_instance):
        client = LLMClient(api_key="sk-test", provider="anthropic", model="claude-3-5-sonnet-latest")
        with pytest.raises(httpx.HTTPStatusError):
            client.complete_sync("say hi")


@pytest.mark.asyncio
async def test_llm_client_openai_async():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "async hello"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.request = AsyncMock(return_value=mock_response)

    with patch("mkg.llm_client.httpx.AsyncClient", return_value=mock_client_instance) as MockClient:
        client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")
        assert MockClient.call_count == 1
        result = await client.complete("say hi")
        assert result == "async hello"


@pytest.mark.asyncio
async def test_llm_client_retry_on_429():
    error_response = MagicMock()
    error_response.status_code = 429
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429", request=MagicMock(), response=error_response
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {
        "choices": [{"message": {"content": "retry success"}}]
    }
    success_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.request = AsyncMock(side_effect=[error_response, success_response])

    with patch("mkg.llm_client.httpx.AsyncClient", return_value=mock_client_instance):
        client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")
        with patch("asyncio.sleep", return_value=None):
            result = await client.complete("say hi")
            assert result == "retry success"
            assert mock_client_instance.request.call_count == 2


@pytest.mark.asyncio
async def test_llm_client_timeout_eventually_fails():
    mock_client_instance = MagicMock()
    mock_client_instance.request = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))

    with patch("mkg.llm_client.httpx.AsyncClient", return_value=mock_client_instance):
        client = LLMClient(api_key="sk-test", provider="openai", model="gpt-4o")
        with patch("asyncio.sleep", return_value=None):
            with pytest.raises(RuntimeError, match="LLM API timeout"):
                await client.complete("say hi")
            assert mock_client_instance.request.call_count == 3


def test_llm_client_close_sync():
    mock_sync_instance = MagicMock()
    mock_async_instance = MagicMock()
    mock_async_instance.aclose = AsyncMock()

    with patch("mkg.llm_client.httpx.Client", return_value=mock_sync_instance) as MockSyncClient:
        with patch("mkg.llm_client.httpx.AsyncClient", return_value=mock_async_instance) as MockAsyncClient:
            client = LLMClient(api_key="sk-test", provider="openai")
            assert MockSyncClient.call_count == 1
            assert MockAsyncClient.call_count == 1
            client.close()
            assert mock_sync_instance.close.call_count == 1
            # aclose should be called via run_until_complete
            assert mock_async_instance.aclose.call_count == 1


@pytest.mark.asyncio
async def test_llm_client_aclose_async():
    mock_sync_instance = MagicMock()
    mock_async_instance = MagicMock()
    mock_async_instance.aclose = AsyncMock()

    with patch("mkg.llm_client.httpx.Client", return_value=mock_sync_instance):
        with patch("mkg.llm_client.httpx.AsyncClient", return_value=mock_async_instance):
            client = LLMClient(api_key="sk-test", provider="openai")
            await client.aclose()
            assert mock_sync_instance.close.call_count == 1
            assert mock_async_instance.aclose.call_count == 1


@pytest.mark.asyncio
async def test_llm_client_close_in_async_context_raises():
    mock_sync_instance = MagicMock()
    mock_async_instance = MagicMock()
    mock_async_instance.aclose = AsyncMock()

    with patch("mkg.llm_client.httpx.Client", return_value=mock_sync_instance):
        with patch("mkg.llm_client.httpx.AsyncClient", return_value=mock_async_instance):
            client = LLMClient(api_key="sk-test", provider="openai")
            with pytest.raises(RuntimeError, match=r"close\(\) cannot be called inside an async context"):
                client.close()
