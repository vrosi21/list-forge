from datetime import UTC, datetime, timedelta

from list_forge.budgets import DailyBudget

START = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)


class Clock:
    def __init__(self, now: datetime = START) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **delta: float) -> None:
        self.now += timedelta(**delta)


class TestUnlimited:
    def test_an_absent_limit_never_refuses(self) -> None:
        budget = DailyBudget(None)

        assert all(budget.spend("alice") for _ in range(100))

    def test_an_absent_limit_reports_no_remainder(self) -> None:
        assert DailyBudget(None).remaining("alice") is None


class TestAllowance:
    def test_it_refuses_once_the_allowance_is_gone(self) -> None:
        budget = DailyBudget(2, clock=Clock())

        assert budget.spend("alice") is True
        assert budget.spend("alice") is True
        assert budget.spend("alice") is False

    def test_it_counts_each_recipient_separately(self) -> None:
        budget = DailyBudget(1, clock=Clock())

        assert budget.spend("alice") is True
        assert budget.spend("bob") is True
        assert budget.spend("alice") is False

    def test_it_reports_what_is_left(self) -> None:
        budget = DailyBudget(3, clock=Clock())
        budget.spend("alice")

        assert budget.remaining("alice") == 2
        assert budget.remaining("bob") == 3

    def test_the_remainder_never_goes_negative(self) -> None:
        budget = DailyBudget(1, clock=Clock())
        budget.spend("alice")
        budget.spend("alice")

        assert budget.remaining("alice") == 0


class TestRollOver:
    def test_a_new_day_restores_the_allowance(self) -> None:
        clock = Clock()
        budget = DailyBudget(1, clock=clock)
        budget.spend("alice")

        clock.advance(days=1)

        assert budget.spend("alice") is True

    def test_later_the_same_day_does_not(self) -> None:
        clock = Clock()
        budget = DailyBudget(1, clock=clock)
        budget.spend("alice")

        clock.advance(hours=6)

        assert budget.spend("alice") is False
