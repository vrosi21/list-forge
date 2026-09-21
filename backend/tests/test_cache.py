from pathlib import Path

import pytest

from fakes import FakeGenerator, sample_brand, sample_facts
from list_forge.cache import CachedGenerator, cache_key
from list_forge.store import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    opened = Store(tmp_path / "listforge.db")
    yield opened
    opened.close()


def fingerprint_for(brand_id: str = "mindful-souls") -> str:
    generator = FakeGenerator()
    return generator.prompt.fingerprint(sample_brand(id=brand_id), generator.params)


class TestKey:
    def test_the_same_inputs_give_the_same_key(self) -> None:
        first = cache_key(sample_facts(), "mindful-souls", "abc123")
        second = cache_key(sample_facts(), "mindful-souls", "abc123")

        assert first == second

    @pytest.mark.parametrize(
        ("facts", "brand_id", "fingerprint"),
        [
            pytest.param(sample_facts(sku="MS-999"), "mindful-souls", "abc123", id="other-product"),
            pytest.param(sample_facts(pieces="2"), "mindful-souls", "abc123", id="changed-fact"),
            pytest.param(sample_facts(), "beads-and-stones", "abc123", id="other-brand"),
            pytest.param(sample_facts(), "mindful-souls", "def456", id="changed-prompt"),
        ],
    )
    def test_anything_that_changes_the_output_changes_the_key(
        self, facts: object, brand_id: str, fingerprint: str
    ) -> None:
        assert cache_key(facts, brand_id, fingerprint) != cache_key(
            sample_facts(), "mindful-souls", "abc123"
        )


class TestCachedGenerator:
    async def test_the_first_call_reaches_the_model(self, store: Store) -> None:
        inner = FakeGenerator()
        cached = CachedGenerator(inner, store)

        generation = await cached.generate(sample_facts(), sample_brand())

        assert inner.seen == ["MS-AMT-101"]
        assert generation.cached is False

    async def test_the_second_call_is_served_from_the_store(self, store: Store) -> None:
        inner = FakeGenerator()
        cached = CachedGenerator(inner, store)

        await cached.generate(sample_facts(), sample_brand())
        again = await cached.generate(sample_facts(), sample_brand())

        assert inner.seen == ["MS-AMT-101"]
        assert again.cached is True
        assert again.output.title == "Amethyst Point in Deep Purple"

    async def test_a_different_product_is_not_a_hit(self, store: Store) -> None:
        inner = FakeGenerator()
        cached = CachedGenerator(inner, store)

        await cached.generate(sample_facts(), sample_brand())
        await cached.generate(sample_facts(sku="MS-RQZ-102"), sample_brand())

        assert inner.seen == ["MS-AMT-101", "MS-RQZ-102"]

    async def test_editing_the_brand_voice_invalidates_nothing_because_the_key_moves(
        self, store: Store
    ) -> None:
        inner = FakeGenerator()
        cached = CachedGenerator(inner, store)

        await cached.generate(sample_facts(), sample_brand())
        await cached.generate(sample_facts(), sample_brand(voice="Cool and spare. Short lines."))

        assert len(inner.seen) == 2

    async def test_refreshing_ignores_the_stored_answer_but_still_writes(
        self, store: Store
    ) -> None:
        inner = FakeGenerator()
        cached = CachedGenerator(inner, store)
        await cached.generate(sample_facts(), sample_brand())

        await cached.refreshing().generate(sample_facts(), sample_brand())
        after = await cached.generate(sample_facts(), sample_brand())

        assert len(inner.seen) == 2
        assert after.cached is True

    async def test_a_hit_costs_nothing_new(self, store: Store) -> None:
        inner = FakeGenerator()
        cached = CachedGenerator(inner, store)

        first = await cached.generate(sample_facts(), sample_brand())
        second = await cached.generate(sample_facts(), sample_brand())

        assert first.usage.prompt_tokens == 100
        assert second.usage == first.usage
        assert second.cached is True
