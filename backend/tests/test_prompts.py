import json

import pytest

from fakes import sample_brand, sample_facts, sample_params
from list_forge.prompts import (
    DEFAULT_PROMPT_VERSION,
    FINGERPRINT_LENGTH,
    PROMPT_VERSIONS,
    UnknownPromptVersionError,
    build_messages,
    get_prompt_version,
    repair_message,
)

V1 = get_prompt_version("copy-v1")
V2 = get_prompt_version("copy-v2")


class TestRegistry:
    def test_the_default_version_is_registered(self) -> None:
        assert DEFAULT_PROMPT_VERSION in PROMPT_VERSIONS

    def test_every_entry_is_keyed_by_its_own_version(self) -> None:
        assert all(key == prompt.version for key, prompt in PROMPT_VERSIONS.items())

    def test_an_unknown_version_names_the_ones_that_exist(self) -> None:
        with pytest.raises(UnknownPromptVersionError, match="copy-v1"):
            get_prompt_version("copy-v99")


class TestSystemPrompt:
    def test_it_carries_the_brand_and_the_rules(self) -> None:
        prompt = V1.system_prompt(sample_brand())

        assert "Mindful Souls" in prompt
        assert "Warm, calm and grounded" in prompt
        assert "Name the stone" in prompt
        assert "No medical claims" in prompt
        assert "Never state a number that does not appear in it." in prompt
        assert "Return one JSON object and nothing else" in prompt

    def test_optional_brand_sections_are_left_out_when_empty(self) -> None:
        prompt = V1.system_prompt(sample_brand(audience=None, do=[], dont=[]))

        assert "Audience:" not in prompt
        assert "Always:" not in prompt
        assert "Never:\n-" not in prompt

    def test_the_second_version_adds_an_example_and_keeps_the_contract(self) -> None:
        prompt = V2.system_prompt(sample_brand())

        assert "Worked example." in prompt
        assert "Return one JSON object and nothing else" in prompt

    def test_the_first_version_carries_no_example(self) -> None:
        assert "Worked example." not in V1.system_prompt(sample_brand())


class TestMessages:
    def test_instructions_and_product_data_stay_in_separate_turns(self) -> None:
        facts = sample_facts()

        messages = build_messages(V1.system_prompt(sample_brand()), facts)

        assert [message["role"] for message in messages] == ["system", "user"]
        assert json.loads(messages[1]["content"])["sku"] == facts.sku
        assert "Mindful Souls" not in messages[1]["content"]


class TestFingerprint:
    def test_it_is_stable_for_the_same_prompt_and_parameters(self) -> None:
        brand = sample_brand()

        first = V1.fingerprint(brand, sample_params())
        second = V1.fingerprint(brand, sample_params())

        assert first == second
        assert len(first) == FINGERPRINT_LENGTH

    def test_editing_the_brand_voice_changes_it(self) -> None:
        original = V1.fingerprint(sample_brand(), sample_params())
        edited = V1.fingerprint(
            sample_brand(voice="Warm, calm and grounded. Short sentences!"), sample_params()
        )

        assert original != edited

    @pytest.mark.parametrize(
        "overrides",
        [
            pytest.param({"temperature": 0.2}, id="temperature"),
            pytest.param({"model": "openai/gpt-oss-120b"}, id="model"),
            pytest.param({"reasoning_effort": "high"}, id="reasoning-effort"),
            pytest.param({"max_completion_tokens": 900}, id="token-cap"),
        ],
    )
    def test_changing_a_sampling_parameter_changes_it(self, overrides: dict) -> None:
        brand = sample_brand()

        assert V1.fingerprint(brand, sample_params()) != V1.fingerprint(
            brand, sample_params(**overrides)
        )

    def test_two_versions_never_share_a_fingerprint(self) -> None:
        brand = sample_brand()

        assert V1.fingerprint(brand, sample_params()) != V2.fingerprint(brand, sample_params())


def test_the_repair_message_quotes_the_validation_failure() -> None:
    message = repair_message("title: String should have at most 70 characters")

    assert "title: String should have at most 70 characters" in message
    assert "corrected JSON object" in message
