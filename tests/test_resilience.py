import logging

import pytest

from mkg.resilience import RetryableExternalError, call_with_retries


def test_call_with_retries_retries_then_succeeds():
    attempts = {"count": 0}

    def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RetryableExternalError("temporary timeout")
        return "ok"

    result = call_with_retries(
        "test.flaky",
        flaky,
        logger=logging.getLogger("tests.resilience"),
        retries=2,
        retry_delay=0,
    )

    assert result == "ok"
    assert attempts["count"] == 3


def test_call_with_retries_raises_after_retry_exhausted():
    attempts = {"count": 0}

    def always_fail():
        attempts["count"] += 1
        raise RetryableExternalError("still failing")

    with pytest.raises(RetryableExternalError):
        call_with_retries(
            "test.exhausted",
            always_fail,
            logger=logging.getLogger("tests.resilience"),
            retries=1,
            retry_delay=0,
        )

    assert attempts["count"] == 2


def test_call_with_retries_does_not_retry_non_retryable_errors():
    attempts = {"count": 0}

    def fail_fast():
        attempts["count"] += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError):
        call_with_retries(
            "test.fail_fast",
            fail_fast,
            logger=logging.getLogger("tests.resilience"),
            retries=3,
            retry_delay=0,
        )

    assert attempts["count"] == 1
