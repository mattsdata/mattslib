# ==================================================================================================
# 📜 mattslib :: retry
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/retry.py
#  Author       : Mathew Varghese
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    Networks drop packets, APIs return 503s and databases fail over. Most of these failures
#    are transient: the same call succeeds a second later. This module retries such calls in a
#    controlled way instead of letting a blip turn into an outage.
#
#  🔧 WHAT IT DOES
#    - @retry        : decorator for normal (sync) functions.
#    - @async_retry  : the same behaviour for async functions, without blocking the event loop.
#    - backoff_delay : computes the wait between attempts (exponential backoff + full jitter).
#
#  🧠 DESIGN NOTES
#    - Only the exceptions you list are retried. Retrying a ValueError or a 400 response just
#      repeats a bug, so the default should be narrowed by the caller for real services.
#    - "Full jitter" (random wait between 0 and the backoff ceiling) prevents a thundering herd:
#      when a dependency recovers, a thousand clients do not all retry at the same millisecond.
#    - The final exception is re-raised unchanged so the original traceback is never lost.
#    - `sleep` is injectable, so tests run instantly and can assert the exact wait sequence.
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial release of the retry module.
#      - Added @retry (sync) and @async_retry (async) decorators.
#      - Exponential backoff with full jitter, capped by max_delay.
#      - Injectable sleep for instant, deterministic tests.
# ==================================================================================================
"""Retry calls that can fail transiently, with exponential backoff and jitter.

Example:
    >>> from mattslib.retry import retry
    >>> @retry(attempts=3, exceptions=(ConnectionError,))
    ... def fetch() -> str:
    ...     return "ok"
    >>> fetch()
    'ok'
"""

# ========================================
# 📂 Imports
# ========================================
from __future__ import annotations

import asyncio
import functools
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

# ========================================
# 📂 Types & Logger
# ========================================
# ParamSpec keeps the decorated function's exact signature visible to type checkers and IDEs.
P = ParamSpec("P")
R = TypeVar("R")

log = logging.getLogger(__name__)


# ========================================
# 📂 Backoff Calculation
# ========================================
def backoff_delay(attempt: int, base: float, cap: float, jitter: bool) -> float:
    """Return the wait in seconds before retry number ``attempt`` (1-based).

    Uses "full jitter": a random value between 0 and the exponential delay,
    which spreads retries from many clients instead of synchronising them.
    """
    # Exponential growth: base, 2*base, 4*base ... but never beyond the cap.
    delay: float = min(cap, base * (2 ** (attempt - 1)))
    return random.uniform(0, delay) if jitter else delay


# ========================================
# 📂 Sync Retry
# ========================================
def retry(
    *,
    attempts: int = 3,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorate a function so it is retried when it raises one of ``exceptions``.

    The final failure is re-raised unchanged, so callers keep the original traceback.
    """
    # Validate at decoration time, so a misconfiguration fails on import, not in production.
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    # Out of attempts: bare `raise` preserves the original traceback.
                    if attempt == attempts:
                        raise
                    wait = backoff_delay(attempt, base_delay, max_delay, jitter)
                    # Log every retry: silent retries hide degrading dependencies from on-call.
                    log.warning(
                        "%s failed (%s), retry %d/%d in %.2fs",
                        func.__qualname__,
                        exc,
                        attempt,
                        attempts - 1,
                        wait,
                    )
                    sleep(wait)
            raise AssertionError("unreachable")  # pragma: no cover

        return wrapper

    return decorator


# ========================================
# 📂 Async Retry
# ========================================
def async_retry(
    *,
    attempts: int = 3,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    base_delay: float = 0.5,
    max_delay: float = 30.0,
    jitter: bool = True,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Async version of :func:`retry`; waits with ``asyncio.sleep`` so the loop is never blocked."""
    if attempts < 1:
        raise ValueError("attempts must be >= 1")

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        raise
                    wait = backoff_delay(attempt, base_delay, max_delay, jitter)
                    log.warning(
                        "%s failed (%s), retry %d/%d in %.2fs",
                        func.__qualname__,
                        exc,
                        attempt,
                        attempts - 1,
                        wait,
                    )
                    # asyncio.sleep yields to other tasks; time.sleep here would freeze the server.
                    await asyncio.sleep(wait)
            raise AssertionError("unreachable")  # pragma: no cover

        return wrapper

    return decorator
