from types import SimpleNamespace

import pytest

import mkg.llm as llm_module
from mkg.resilience import RetryableExternalError


class FakeModel:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_generate_retries_retryable_errors(monkeypatch):
    fake_model = FakeModel(
        [
            Exception("timeout while calling upstream"),
            SimpleNamespace(content="ok"),
        ]
    )
    monkeypatch.setattr(llm_module, "_llm_instance", fake_model)

    assert llm_module.generate("hello") == "ok"
    assert fake_model.calls == 2


def test_generate_raises_after_retry_exhausted(monkeypatch):
    fake_model = FakeModel(
        [
            Exception("429 rate limit"),
            Exception("429 rate limit"),
            Exception("429 rate limit"),
        ]
    )
    monkeypatch.setattr(llm_module, "_llm_instance", fake_model)

    with pytest.raises(RetryableExternalError):
        llm_module.generate("hello")

    assert fake_model.calls == 3
