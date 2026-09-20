import json

from fakes import sample_brand, sample_facts, sample_params
from list_forge.prompts import (
    FINGERPRINT_LENGTH,
    build_messages,
    build_system_prompt,
    prompt_fingerprint,
    repair_message,
)


def test_the_system_prompt_carries_the_brand_and_the_rules() -> None:
    prompt = build_system_prompt(sample_brand())

    assert "Mindful Souls" in prompt
    assert "Warm, calm and grounded" in prompt
    assert "Name the stone" in prompt
    assert "No medical claims" in prompt
    assert "Never state a number that does not appear in it." in prompt
    assert "Return one JSON object and nothing else" in prompt


def test_optional_brand_sections_are_left_out_when_empty() -> None:
    prompt = build_system_prompt(sample_brand(audience=None, do=[], dont=[]))

    assert "Audience:" not in prompt
    assert "Always:" not in prompt
    assert "Never:\n-" not in prompt


def test_instructions_and_product_data_stay_in_separate_turns() -> None:
    facts = sample_facts()

    messages = build_messages(build_system_prompt(sample_brand()), facts)

    assert [message["role"] for message in messages] == ["system", "user"]
    assert json.loads(messages[1]["content"])["sku"] == facts.sku
    assert "Mindful Souls" not in messages[1]["content"]


def test_the_fingerprint_is_stable_for_the_same_prompt_and_parameters() -> None:
    prompt = build_system_prompt(sample_brand())

    first = prompt_fingerprint(prompt, sample_params())
    second = prompt_fingerprint(prompt, sample_params())

    assert first == second
    assert len(first) == FINGERPRINT_LENGTH


def test_editing_the_brand_voice_changes_the_fingerprint() -> None:
    original = prompt_fingerprint(build_system_prompt(sample_brand()), sample_params())
    edited = prompt_fingerprint(
        build_system_prompt(sample_brand(voice="Warm, calm and grounded. Short sentences!")),
        sample_params(),
    )

    assert original != edited


def test_changing_a_sampling_parameter_changes_the_fingerprint() -> None:
    prompt = build_system_prompt(sample_brand())

    assert prompt_fingerprint(prompt, sample_params()) != prompt_fingerprint(
        prompt, sample_params(temperature=0.2)
    )
    assert prompt_fingerprint(prompt, sample_params()) != prompt_fingerprint(
        prompt, sample_params(model="openai/gpt-oss-120b")
    )


def test_the_repair_message_quotes_the_validation_failure() -> None:
    message = repair_message("title: String should have at most 70 characters")

    assert "title: String should have at most 70 characters" in message
    assert "corrected JSON object" in message
