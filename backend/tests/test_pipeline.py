import pytest

from fakes import VALID_COPY, FakeGenerator, auth_error, sample_brand, sample_facts
from list_forge.llm import GenerationError, ProviderError
from list_forge.models import GeneratedCopy, Status
from list_forge.pipeline import Pipeline
from list_forge.prompts import PROMPT_VERSION
from list_forge.vocabulary import build_vocabulary

VOCABULARY = build_vocabulary(
    entities=["amethyst", "labradorite", "purple", "white"], origins=["brazil"]
)

CLEAN = GeneratedCopy.model_validate(VALID_COPY)
WITH_INVENTED_STONE = GeneratedCopy.model_validate(
    VALID_COPY | {"description": "Amethyst with flecks of labradorite. ".ljust(220, ".")}
)


def products(count: int) -> list:
    return [sample_facts(sku=f"MS-{index:03d}") for index in range(count)]


def pipeline(generator: FakeGenerator, *, max_concurrency: int = 4) -> Pipeline:
    return Pipeline(generator, VOCABULARY, max_concurrency=max_concurrency)


class TestRouting:
    async def test_clean_copy_is_approved(self) -> None:
        items = await pipeline(FakeGenerator()).run_batch([sample_facts()], sample_brand())

        assert items[0].status is Status.APPROVED
        assert items[0].findings == []

    async def test_copy_with_an_unsupported_claim_goes_to_review(self) -> None:
        generator = FakeGenerator(default=WITH_INVENTED_STONE)

        items = await pipeline(generator).run_batch([sample_facts()], sample_brand())

        assert items[0].status is Status.NEEDS_REVIEW
        assert [finding.text for finding in items[0].findings] == ["labradorite"]

    async def test_a_generation_failure_becomes_a_failed_item(self) -> None:
        generator = FakeGenerator(default=GenerationError("no valid output after 3 attempts"))

        items = await pipeline(generator).run_batch([sample_facts()], sample_brand())

        assert items[0].status is Status.FAILED
        assert items[0].output is None
        assert "no valid output" in (items[0].error or "")

    async def test_a_failed_item_keeps_the_last_raw_reply(self) -> None:
        generator = FakeGenerator(default=GenerationError("no valid output", "{ not json"))

        items = await pipeline(generator).run_batch([sample_facts()], sample_brand())

        assert items[0].raw_output == "{ not json"

    async def test_a_provider_failure_has_no_raw_reply(self) -> None:
        generator = FakeGenerator(default=ProviderError("provider unavailable"))

        items = await pipeline(generator).run_batch([sample_facts()], sample_brand())

        assert items[0].status is Status.FAILED
        assert items[0].raw_output is None


class TestBatch:
    async def test_one_bad_row_does_not_sink_the_batch(self) -> None:
        generator = FakeGenerator(replies={"MS-001": ProviderError("provider unavailable")})

        items = await pipeline(generator).run_batch(products(4), sample_brand())

        assert [item.status for item in items] == [
            Status.APPROVED,
            Status.FAILED,
            Status.APPROVED,
            Status.APPROVED,
        ]

    async def test_results_keep_the_input_order(self) -> None:
        items = await pipeline(FakeGenerator()).run_batch(products(5), sample_brand())

        assert [item.facts.sku for item in items] == [f"MS-{index:03d}" for index in range(5)]
        assert [item.row_number for item in items] == [1, 2, 3, 4, 5]

    async def test_every_item_shares_one_batch_id(self) -> None:
        items = await pipeline(FakeGenerator()).run_batch(products(3), sample_brand())

        assert len({item.batch_id for item in items}) == 1

    async def test_a_rejected_key_stops_the_whole_batch(self) -> None:
        generator = FakeGenerator(replies={"MS-002": auth_error()})

        with pytest.raises(BaseExceptionGroup):
            await pipeline(generator).run_batch(products(6), sample_brand())


class TestConcurrency:
    async def test_the_semaphore_caps_calls_in_flight(self) -> None:
        generator = FakeGenerator()

        await pipeline(generator, max_concurrency=2).run_batch(products(8), sample_brand())

        assert generator.peak_in_flight <= 2
        assert len(generator.seen) == 8

    async def test_waiting_for_a_free_slot_does_not_count_against_the_item_deadline(self) -> None:
        generator = FakeGenerator(delay_s=0.02)
        queued = Pipeline(generator, VOCABULARY, max_concurrency=1, item_timeout_s=0.05)

        items = await queued.run_batch(products(5), sample_brand())

        assert [item.status for item in items] == [Status.APPROVED] * 5

    async def test_a_call_that_runs_past_the_deadline_still_fails(self) -> None:
        generator = FakeGenerator(delay_s=0.2)
        slow = Pipeline(generator, VOCABULARY, max_concurrency=2, item_timeout_s=0.02)

        items = await slow.run_batch(products(2), sample_brand())

        assert [item.status for item in items] == [Status.FAILED, Status.FAILED]

    async def test_a_higher_limit_lets_more_run_at_once(self) -> None:
        generator = FakeGenerator()

        await pipeline(generator, max_concurrency=5).run_batch(products(8), sample_brand())

        assert generator.peak_in_flight > 2


class TestProvenance:
    async def test_every_item_records_how_it_was_made(self) -> None:
        items = await pipeline(FakeGenerator()).run_batch([sample_facts()], sample_brand())

        provenance = items[0].provenance
        assert provenance is not None
        assert provenance.prompt_version == PROMPT_VERSION
        assert len(provenance.prompt_fingerprint) == 12
        assert provenance.brand_id == "mindful-souls"
        assert provenance.params.model == "openai/gpt-oss-20b"
        assert provenance.usage.prompt_tokens == 100
        assert provenance.usage.cached_prompt_tokens == 10
        assert provenance.cost_usd is not None

    async def test_a_failed_item_still_records_its_provenance(self) -> None:
        generator = FakeGenerator(default=GenerationError("gave up"))

        items = await pipeline(generator).run_batch([sample_facts()], sample_brand())

        assert items[0].provenance is not None
        assert items[0].provenance.usage.prompt_tokens == 0
