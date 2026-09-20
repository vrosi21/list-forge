"""List-price cost estimates for model usage."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from list_forge.models import TokenUsage

TOKENS_PER_PRICE_UNIT = Decimal(1_000_000)
CACHED_INPUT_MULTIPLIER = Decimal("0.5")
COST_PRECISION = Decimal("0.000001")


class ModelPrice(BaseModel):
    model_config = ConfigDict(frozen=True)

    input_usd_per_million: Decimal
    output_usd_per_million: Decimal


MODEL_PRICES: dict[str, ModelPrice] = {
    "openai/gpt-oss-20b": ModelPrice(
        input_usd_per_million=Decimal("0.075"), output_usd_per_million=Decimal("0.30")
    ),
    "openai/gpt-oss-120b": ModelPrice(
        input_usd_per_million=Decimal("0.15"), output_usd_per_million=Decimal("0.60")
    ),
}


def estimate_cost_usd(model: str, usage: TokenUsage) -> Decimal | None:
    """List-price cost of one call, or None when the model has no published price here."""
    price = MODEL_PRICES.get(model)
    if price is None:
        return None

    billed_prompt_tokens = max(usage.prompt_tokens - usage.cached_prompt_tokens, 0)
    cost = (
        Decimal(billed_prompt_tokens) * price.input_usd_per_million
        + Decimal(usage.cached_prompt_tokens)
        * price.input_usd_per_million
        * CACHED_INPUT_MULTIPLIER
        + Decimal(usage.completion_tokens) * price.output_usd_per_million
    ) / TOKENS_PER_PRICE_UNIT
    return cost.quantize(COST_PRECISION)
