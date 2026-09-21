"""Per-recipient daily limits on work that costs tokens, counted in memory."""

from collections.abc import Callable
from datetime import UTC, date, datetime


class DailyBudget:
    """One allowance per label per UTC day."""

    def __init__(
        self, limit: int | None, *, clock: Callable[[], datetime] = lambda: datetime.now(tz=UTC)
    ) -> None:
        self._limit = limit
        self._clock = clock
        self._day: date | None = None
        self._spent: dict[str, int] = {}

    @property
    def limit(self) -> int | None:
        return self._limit

    def remaining(self, label: str) -> int | None:
        """How much of today's allowance is left, or None when nothing is limited."""
        if self._limit is None:
            return None
        self._roll_over()
        return max(self._limit - self._spent.get(label, 0), 0)

    def spend(self, label: str) -> bool:
        """Take one unit from today's allowance, reporting whether there was any left."""
        if self._limit is None:
            return True

        self._roll_over()
        spent = self._spent.get(label, 0)
        if spent >= self._limit:
            return False

        self._spent[label] = spent + 1
        return True

    def _roll_over(self) -> None:
        today = self._clock().date()
        if today != self._day:
            self._day = today
            self._spent.clear()
