from decimal import Decimal

from list_forge.models import TokenUsage
from list_forge.pricing import estimate_cost_usd

MODEL = "openai/gpt-oss-120b"


def test_cost_uses_input_and_output_prices() -> None:
    usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000)

    assert estimate_cost_usd(MODEL, usage) == Decimal("0.750000")


def test_cached_prompt_tokens_are_billed_at_half() -> None:
    usage = TokenUsage(prompt_tokens=1_000_000, cached_prompt_tokens=1_000_000)

    assert estimate_cost_usd(MODEL, usage) == Decimal("0.075000")


def test_a_call_with_no_usage_is_free() -> None:
    assert estimate_cost_usd(MODEL, TokenUsage()) == Decimal("0")


def test_an_unpriced_model_reports_no_estimate() -> None:
    assert estimate_cost_usd("some/other-model", TokenUsage(prompt_tokens=10)) is None
