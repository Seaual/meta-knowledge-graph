import asyncio

import httpx

DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-latest"
DEFAULT_OPENAI_MODEL = "gpt-4o"


class LLMClient:
    def __init__(
        self,
        api_key: str,
        provider: str,
        base_url: str = "",
        model: str = "",
        timeout: float = 120.0,
    ):
        self.api_key = api_key
        self.provider = provider.lower()
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=self.timeout)
        self._async_client = httpx.AsyncClient(timeout=self.timeout)

    def close(self) -> None:
        self._client.close()
        asyncio.get_event_loop().run_until_complete(self._async_client.aclose())

    async def complete(self, prompt: str) -> str:
        return await self.complete_messages(
            [{"role": "user", "content": prompt}],
            system=None,
        )

    async def complete_messages(self, messages: list[dict], system: str | None = None) -> str:
        if self.provider == "anthropic":
            return await self._call_anthropic(messages, system)
        if self.provider == "openai":
            return await self._call_openai(messages, system)
        raise ValueError(f"Unknown provider: {self.provider}")

    def complete_sync(self, prompt: str) -> str:
        return self.complete_messages_sync(
            [{"role": "user", "content": prompt}],
            system=None,
        )

    def complete_messages_sync(
        self, messages: list[dict], system: str | None = None
    ) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic_sync(messages, system)
        if self.provider == "openai":
            return self._call_openai_sync(messages, system)
        raise ValueError(f"Unknown provider: {self.provider}")

    async def _call_openai(self, messages: list[dict], system: str | None = None) -> str:
        url = (
            f"{self.base_url}/v1/chat/completions"
            if self.base_url
            else "https://api.openai.com/v1/chat/completions"
        )
        model = self.model or DEFAULT_OPENAI_MODEL
        msgs = list(messages)
        if system is not None:
            msgs.insert(0, {"role": "system", "content": system})

        last_err = None
        for attempt in range(3):
            try:
                resp = await self._async_client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": msgs,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError) as err:
                    raise RuntimeError(f"Unexpected OpenAI response format: {data}") from err
            except httpx.ReadTimeout as e:
                last_err = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"LLM API timeout after {attempt + 1} attempts") from e
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code == 429 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        assert last_err is not None
        raise last_err

    async def _call_anthropic(self, messages: list[dict], system: str | None = None) -> str:
        url = (
            f"{self.base_url}/v1/messages"
            if self.base_url
            else "https://api.anthropic.com/v1/messages"
        )
        model = self.model or DEFAULT_ANTHROPIC_MODEL
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system is not None:
            payload["system"] = system

        last_err = None
        for attempt in range(3):
            try:
                resp = await self._async_client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                try:
                    return data["content"][0]["text"]
                except (KeyError, IndexError) as err:
                    raise RuntimeError(f"Unexpected Anthropic response format: {data}") from err
            except httpx.ReadTimeout as e:
                last_err = e
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"LLM API timeout after {attempt + 1} attempts") from e
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code == 429 and attempt < 2:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        assert last_err is not None
        raise last_err

    def _call_openai_sync(
        self, messages: list[dict], system: str | None = None
    ) -> str:
        url = (
            f"{self.base_url}/v1/chat/completions"
            if self.base_url
            else "https://api.openai.com/v1/chat/completions"
        )
        model = self.model or DEFAULT_OPENAI_MODEL
        msgs = list(messages)
        if system is not None:
            msgs.insert(0, {"role": "system", "content": system})

        resp = self._client.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": msgs,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as err:
            raise RuntimeError(f"Unexpected OpenAI response format: {data}") from err

    def _call_anthropic_sync(
        self, messages: list[dict], system: str | None = None
    ) -> str:
        url = (
            f"{self.base_url}/v1/messages"
            if self.base_url
            else "https://api.anthropic.com/v1/messages"
        )
        model = self.model or DEFAULT_ANTHROPIC_MODEL
        payload: dict = {
            "model": model,
            "max_tokens": 4096,
            "messages": messages,
        }
        if system is not None:
            payload["system"] = system

        resp = self._client.post(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError) as err:
            raise RuntimeError(f"Unexpected Anthropic response format: {data}") from err
