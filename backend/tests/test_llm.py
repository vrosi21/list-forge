import pytest
from openai import AuthenticationError

from fakes import (
    FakeClient,
    Reply,
    auth_error,
    connection_error,
    make_generator,
    rate_limit_error,
    sample_brand,
    sample_facts,
    sample_params,
    sample_prompt,
    server_error,
    valid_copy_json,
)
from list_forge.llm import (
    RAW_OUTPUT_LIMIT,
    GenerationError,
    GroqGenerator,
    ModelUnavailableError,
    ProviderError,
    backoff_delay,
    extract_json_object,
    retry_after_seconds,
)

FENCED = 'Here is your copy:\n```json\n{"a": 1}\n```\nHope that helps.'


class TestExtractJsonObject:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            pytest.param('{"a": 1}', {"a": 1}, id="bare-object"),
            pytest.param(FENCED, {"a": 1}, id="fenced-with-commentary"),
            pytest.param('  \n {"a": {"b": [1, 2]}} \n', {"a": {"b": [1, 2]}}, id="nested"),
            pytest.param('{"a": 1} trailing words', {"a": 1}, id="trailing-text"),
        ],
    )
    def test_it_reads_one_object_out_of_a_noisy_reply(
        self, text: str, expected: dict[str, object]
    ) -> None:
        assert extract_json_object(text) == expected

    @pytest.mark.parametrize(
        ("text", "reason"),
        [
            pytest.param("no json here", "no JSON object", id="no-object"),
            pytest.param('{"a": ', "malformed JSON", id="truncated"),
            pytest.param("[1, 2, 3]", "no JSON object", id="array"),
        ],
    )
    def test_it_refuses_anything_else(self, text: str, reason: str) -> None:
        with pytest.raises(ValueError, match=reason):
            extract_json_object(text)


class TestBackoff:
    def test_the_delay_grows_with_each_attempt(self) -> None:
        delays = [backoff_delay(n, None, 1.0, 60.0, rand=lambda: 1.0) for n in (1, 2, 3, 4)]

        assert delays == [1.0, 2.0, 4.0, 8.0]

    def test_the_cap_stops_it_growing_forever(self) -> None:
        assert backoff_delay(10, None, 1.0, 8.0, rand=lambda: 1.0) == 8.0

    def test_jitter_spreads_retries_below_the_ceiling(self) -> None:
        assert backoff_delay(3, None, 1.0, 60.0, rand=lambda: 0.25) == 1.0

    def test_the_servers_retry_after_is_a_floor(self) -> None:
        assert backoff_delay(1, 30.0, 1.0, 60.0, rand=lambda: 0.0) == 30.0

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            pytest.param(rate_limit_error("12"), 12.0, id="header-present"),
            pytest.param(rate_limit_error(), None, id="header-absent"),
            pytest.param(rate_limit_error("soon"), None, id="header-unparseable"),
        ],
    )
    def test_retry_after_is_read_from_the_response(
        self, error: Exception, expected: float | None
    ) -> None:
        assert retry_after_seconds(error) == expected


class TestTransportRetries:
    async def test_a_clean_call_is_not_retried(self) -> None:
        generator, client, sleep = make_generator([Reply(valid_copy_json())])

        await generator.generate(sample_facts(), sample_brand())

        assert len(client.completions.requests) == 1
        assert sleep.delays == []

    async def test_transient_failures_are_retried_after_waiting(self) -> None:
        generator, client, sleep = make_generator(
            [rate_limit_error("2"), server_error(), Reply(valid_copy_json())]
        )

        generation = await generator.generate(sample_facts(), sample_brand())

        assert generation.attempts == 1
        assert len(client.completions.requests) == 3
        assert sleep.delays[0] >= 2.0
        assert len(sleep.delays) == 2

    async def test_a_rejected_key_is_never_retried(self) -> None:
        generator, client, sleep = make_generator([auth_error(), Reply(valid_copy_json())])

        with pytest.raises(AuthenticationError):
            await generator.generate(sample_facts(), sample_brand())

        assert len(client.completions.requests) == 1
        assert sleep.delays == []

    async def test_it_gives_up_after_the_transport_budget(self) -> None:
        generator, client, _ = make_generator(
            [connection_error(), connection_error()], max_transport_attempts=2
        )

        with pytest.raises(ProviderError, match="after 2 attempts"):
            await generator.generate(sample_facts(), sample_brand())

        assert len(client.completions.requests) == 2


class TestContentRetries:
    async def test_valid_output_comes_back_as_a_generation(self) -> None:
        generator, _, _ = make_generator([Reply(valid_copy_json(), cached_prompt_tokens=64)])

        generation = await generator.generate(sample_facts(), sample_brand())

        assert generation.output.title == "Amethyst Point in Deep Purple"
        assert generation.attempts == 1
        assert generation.usage.prompt_tokens == 120
        assert generation.usage.cached_prompt_tokens == 64

    async def test_a_schema_failure_is_re_asked_with_the_reason(self) -> None:
        generator, client, _ = make_generator(
            [Reply(valid_copy_json(title="x")), Reply(valid_copy_json())]
        )

        generation = await generator.generate(sample_facts(), sample_brand())

        assert generation.attempts == 2
        second_request = client.completions.requests[1]["messages"]
        assert second_request[-2]["role"] == "assistant"
        assert "String should have at least 10 characters" in second_request[-1]["content"]

    async def test_unparseable_output_is_re_asked(self) -> None:
        generator, client, _ = make_generator([Reply("I'd rather not."), Reply(valid_copy_json())])

        generation = await generator.generate(sample_facts(), sample_brand())

        assert generation.attempts == 2
        assert "no JSON object" in client.completions.requests[1]["messages"][-1]["content"]

    async def test_a_truncated_reply_counts_as_a_content_failure(self) -> None:
        generator, client, _ = make_generator(
            [Reply(valid_copy_json(), finish_reason="length"), Reply(valid_copy_json())]
        )

        generation = await generator.generate(sample_facts(), sample_brand())

        assert generation.attempts == 2
        assert "cut off" in client.completions.requests[1]["messages"][-1]["content"]

    async def test_tokens_from_every_attempt_are_counted(self) -> None:
        generator, _, _ = make_generator(
            [Reply(valid_copy_json(title="x")), Reply(valid_copy_json())]
        )

        generation = await generator.generate(sample_facts(), sample_brand())

        assert generation.usage.prompt_tokens == 240
        assert generation.usage.completion_tokens == 160

    async def test_it_gives_up_after_the_content_budget(self) -> None:
        generator, client, _ = make_generator(
            [Reply("nope"), Reply("still nope")], max_content_attempts=2
        )

        with pytest.raises(GenerationError, match="no valid output after 2 attempts"):
            await generator.generate(sample_facts(), sample_brand())

        assert len(client.completions.requests) == 2

    async def test_it_carries_the_last_reply_for_the_reviewer(self) -> None:
        generator, _, _ = make_generator(
            [Reply("nope"), Reply("still nope")], max_content_attempts=2
        )

        with pytest.raises(GenerationError) as raised:
            await generator.generate(sample_facts(), sample_brand())

        assert raised.value.raw_output == "still nope"

    async def test_a_long_reply_is_truncated_before_it_is_stored(self) -> None:
        generator, _, _ = make_generator(
            [Reply("x" * (RAW_OUTPUT_LIMIT + 50))], max_content_attempts=1
        )

        with pytest.raises(GenerationError) as raised:
            await generator.generate(sample_facts(), sample_brand())

        assert raised.value.raw_output == "x" * RAW_OUTPUT_LIMIT

    async def test_an_empty_reply_is_stored_as_nothing(self) -> None:
        generator, _, _ = make_generator([Reply("")], max_content_attempts=1)

        with pytest.raises(GenerationError) as raised:
            await generator.generate(sample_facts(), sample_brand())

        assert raised.value.raw_output is None


class TestRequestShape:
    async def test_the_request_carries_the_configured_parameters(self) -> None:
        generator, client, _ = make_generator([Reply(valid_copy_json())])

        await generator.generate(sample_facts(), sample_brand())

        request = client.completions.requests[0]
        assert request["model"] == "openai/gpt-oss-20b"
        assert request["temperature"] == 0.7
        assert request["reasoning_effort"] == "low"
        assert request["max_completion_tokens"] == 1500

    async def test_reasoning_effort_is_omitted_when_unset(self) -> None:
        client = FakeClient([Reply(valid_copy_json())])
        generator = GroqGenerator(
            client,
            sample_params(reasoning_effort=None),
            sample_prompt(),
            max_transport_attempts=1,
            max_content_attempts=1,
            backoff_base_s=1.0,
            backoff_cap_s=2.0,
        )

        await generator.generate(sample_facts(), sample_brand())

        assert "reasoning_effort" not in client.completions.requests[0]


class TestProbe:
    @staticmethod
    def _generator(client: object) -> GroqGenerator:
        return GroqGenerator(
            client,
            sample_params(),
            sample_prompt(),
            max_transport_attempts=1,
            max_content_attempts=1,
            backoff_base_s=1.0,
            backoff_cap_s=2.0,
        )

    async def test_it_returns_the_model_id_when_the_key_works(self) -> None:
        generator, _, _ = make_generator()

        assert await generator.probe() == "openai/gpt-oss-20b"

    async def test_it_lists_every_model_the_key_may_call(self) -> None:
        generator, _, _ = make_generator()

        assert await generator.available_models() == [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ]

    async def test_a_model_the_key_cannot_call_is_reported(self) -> None:
        generator = self._generator(FakeClient(models=["groq/compound"]))

        with pytest.raises(ModelUnavailableError, match="openai/gpt-oss-20b"):
            await generator.probe()

    async def test_it_surfaces_a_rejected_key(self) -> None:
        generator = self._generator(FakeClient(list_error=auth_error()))

        with pytest.raises(AuthenticationError):
            await generator.probe()
