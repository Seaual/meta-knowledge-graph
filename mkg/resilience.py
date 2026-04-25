"""Shared retry and logging utilities for external service calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryableExternalError(Exception):
    """Raised when an external call should be retried."""


def call_with_retries(
    operation: str,
    func: Callable[[], T],
    *,
    logger: logging.Logger,
    retries: int = 2,
    retry_delay: float = 1.0,
    retry_exceptions: tuple[type[BaseException], ...] = (RetryableExternalError,),
) -> T:
    """Run a callable with retry logging around retryable failures."""
    attempt = 0
    started_at = time.perf_counter()
    last_error: BaseException | None = None

    while attempt <= retries:
        attempt += 1
        try:
            result = func()
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "external_call_success operation=%s attempts=%s elapsed_ms=%s",
                operation,
                attempt,
                elapsed_ms,
            )
            return result
        except retry_exceptions as exc:
            last_error = exc
            logger.warning(
                "external_call_retry operation=%s attempt=%s retries=%s error=%s",
                operation,
                attempt,
                retries,
                exc,
            )
            if attempt > retries:
                break
            time.sleep(retry_delay * attempt)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "external_call_failure operation=%s attempt=%s elapsed_ms=%s",
                operation,
                attempt,
                elapsed_ms,
            )
            raise

    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.error(
        "external_call_exhausted operation=%s attempts=%s elapsed_ms=%s error=%s",
        operation,
        attempt,
        elapsed_ms,
        last_error,
    )
    raise last_error if last_error else RuntimeError(f"{operation} failed")
