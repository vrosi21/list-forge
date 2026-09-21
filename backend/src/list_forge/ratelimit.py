"""A token bucket per caller, so one client cannot monopolise the provider."""

import time
from collections.abc import Callable

MAX_TRACKED_KEYS = 4096


class TokenBucket:
    """Refills continuously, so a burst is allowed but a sustained flood is not."""

    def __init__(
        self,
        capacity: int,
        refill_per_second: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = MAX_TRACKED_KEYS,
    ) -> None:
        if capacity <= 0 or refill_per_second <= 0:
            raise ValueError("a bucket needs a positive capacity and refill rate")

        self._capacity = float(capacity)
        self._refill_per_second = refill_per_second
        self._clock = clock
        self._max_keys = max_keys
        self._tokens: dict[str, tuple[float, float]] = {}

    @property
    def tracked_callers(self) -> int:
        return len(self._tokens)

    def take(self, key: str) -> bool:
        """Spend one token for this caller, reporting whether one was available."""
        now = self._clock()
        tokens, updated_at = self._tokens.get(key, (self._capacity, now))
        tokens = min(self._capacity, tokens + (now - updated_at) * self._refill_per_second)

        if tokens < 1.0:
            self._tokens[key] = (tokens, now)
            return False

        self._evict_if_full(key)
        self._tokens[key] = (tokens - 1.0, now)
        return True

    def _evict_if_full(self, key: str) -> None:
        """Bounded memory: the least recently seen caller makes room for a new one."""
        if key in self._tokens or len(self._tokens) < self._max_keys:
            return
        oldest = min(self._tokens, key=lambda tracked: self._tokens[tracked][1])
        del self._tokens[oldest]
