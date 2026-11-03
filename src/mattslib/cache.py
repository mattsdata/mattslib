# ==================================================================================================
# 📜 mattslib :: cache
# --------------------------------------------------------------------------------------------------
#  File         : src/mattslib/cache.py
#  Author       : Mathew Varghese <removed@example.invalid>
#  Created      : 2026-11-03
#  Version      : V1.0
#  License      : MIT (see LICENSE)
# --------------------------------------------------------------------------------------------------
#  🎯 PURPOSE
#    functools.lru_cache is excellent but never forgets: a cached exchange rate, feature flag or
#    access token stays forever, even after it is wrong. This module provides an in-memory cache
#    whose entries expire after a time-to-live (TTL) and whose size is bounded.
#
#  🔧 WHAT IT DOES
#    - @ttl_cache(seconds, maxsize) : caches a function's results per argument set.
#    - TTLCached                    : the wrapper returned; supports cache_clear() and len().
#
#  🧠 DESIGN NOTES
#    - time.monotonic is the default clock. Wall-clock time can jump (NTP sync, DST changes),
#      which would expire entries early or keep them alive far too long.
#    - Bounded with LRU eviction, so a cache keyed on user input cannot grow until the
#      process runs out of memory.
#    - Thread-safe. The lock is NOT held while the wrapped function runs, so one slow call
#      never blocks every other caller. The trade-off: two threads missing the same key at the
#      same moment may both compute it. For idempotent lookups that is the right trade.
#    - The clock is injectable, so expiry is tested by moving time forward, not by sleeping.
#
#  📂 VERSION HISTORY
#
#    V1.0 (2026-11-03) - Mathew Varghese
#      - Initial release of the cache module.
#      - Added @ttl_cache with expiry, LRU size limit and cache_clear().
#      - Thread-safe; clock injectable for testing.
# ==================================================================================================
"""An in-memory cache decorator whose entries expire after a time-to-live (TTL).

``functools.lru_cache`` never expires entries; this does, which suits API lookups,
config fetches and other values that go stale.

Example:
    >>> from mattslib.cache import ttl_cache
    >>> @ttl_cache(seconds=60)
    ... def exchange_rate(currency: str) -> float:
    ...     return 1.17
    >>> exchange_rate("EUR")
    1.17
"""

# ========================================
# 📂 Imports
# ========================================
from __future__ import annotations

import functools
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from typing import Generic, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


# ========================================
# 📂 Cache Wrapper
# ========================================
class TTLCached(Generic[P, R]):
    """Callable wrapper returned by :func:`ttl_cache`; exposes ``cache_clear()``."""

    def __init__(
        self, func: Callable[P, R], seconds: float, maxsize: int, clock: Callable[[], float]
    ) -> None:
        self._func = func
        self._seconds = seconds
        self._maxsize = maxsize
        self._clock = clock
        # OrderedDict gives O(1) "move to most recent" and "pop least recent" for LRU eviction.
        # Each value is stored as (expires_at, result).
        self._data: OrderedDict[Hashable, tuple[float, R]] = OrderedDict()
        self._lock = threading.Lock()
        functools.update_wrapper(self, func)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        # Sort kwargs so f(a=1, b=2) and f(b=2, a=1) share one cache entry.
        key: Hashable = (args, tuple(sorted(kwargs.items())))
        now = self._clock()
        with self._lock:
            hit = self._data.get(key)
            if hit is not None and hit[0] > now:
                self._data.move_to_end(key)  # mark as recently used
                return hit[1]
        # Cache miss or expired: compute OUTSIDE the lock (see DESIGN NOTES above).
        value = self._func(*args, **kwargs)
        with self._lock:
            self._data[key] = (now + self._seconds, value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)  # evict least recently used
        return value

    def cache_clear(self) -> None:
        """Remove every cached entry, e.g. after a known upstream change."""
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


# ========================================
# 📂 Decorator
# ========================================
def ttl_cache(
    seconds: float, *, maxsize: int = 1024, clock: Callable[[], float] = time.monotonic
) -> Callable[[Callable[P, R]], TTLCached[P, R]]:
    """Cache results for ``seconds``, keeping at most ``maxsize`` entries (LRU). Thread-safe."""
    if seconds <= 0 or maxsize < 1:
        raise ValueError("seconds must be > 0 and maxsize >= 1")

    def decorator(func: Callable[P, R]) -> TTLCached[P, R]:
        return TTLCached(func, seconds, maxsize, clock)

    return decorator


__all__ = ["TTLCached", "ttl_cache"]
