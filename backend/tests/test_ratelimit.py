import pytest

from list_forge.ratelimit import TokenBucket


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestConstruction:
    @pytest.mark.parametrize(
        ("capacity", "refill"),
        [
            pytest.param(0, 1.0, id="no-capacity"),
            pytest.param(-1, 1.0, id="negative-capacity"),
            pytest.param(1, 0.0, id="no-refill"),
        ],
    )
    def test_it_refuses_a_bucket_that_can_never_allow_anything(
        self, capacity: int, refill: float
    ) -> None:
        with pytest.raises(ValueError, match="positive"):
            TokenBucket(capacity, refill)


class TestTaking:
    def test_a_burst_up_to_capacity_is_allowed(self) -> None:
        bucket = TokenBucket(3, 1.0, clock=Clock())

        assert [bucket.take("1.2.3.4") for _ in range(4)] == [True, True, True, False]

    def test_callers_are_counted_separately(self) -> None:
        bucket = TokenBucket(1, 1.0, clock=Clock())

        assert bucket.take("1.2.3.4") is True
        assert bucket.take("5.6.7.8") is True
        assert bucket.take("1.2.3.4") is False

    def test_waiting_refills_the_bucket(self) -> None:
        clock = Clock()
        bucket = TokenBucket(1, 1.0, clock=clock)
        bucket.take("1.2.3.4")

        clock.advance(1.0)

        assert bucket.take("1.2.3.4") is True

    def test_a_partial_wait_is_not_enough(self) -> None:
        clock = Clock()
        bucket = TokenBucket(1, 1.0, clock=clock)
        bucket.take("1.2.3.4")

        clock.advance(0.5)

        assert bucket.take("1.2.3.4") is False

    def test_it_never_refills_past_capacity(self) -> None:
        clock = Clock()
        bucket = TokenBucket(2, 1.0, clock=clock)

        clock.advance(600.0)

        assert [bucket.take("1.2.3.4") for _ in range(3)] == [True, True, False]


class TestMemory:
    def test_tracked_callers_stay_bounded(self) -> None:
        clock = Clock()
        bucket = TokenBucket(1, 1.0, clock=clock, max_keys=2)

        for index in range(5):
            bucket.take(f"10.0.0.{index}")
            clock.advance(1.0)

        assert bucket.tracked_callers <= 2
