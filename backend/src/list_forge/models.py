"""Domain types for the copy generation pipeline."""

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MULTI_VALUE_SEPARATOR = ";"

ReasoningEffort = Literal["low", "medium", "high"]

Title = Annotated[str, Field(min_length=10, max_length=70)]
ShortDescription = Annotated[str, Field(min_length=20, max_length=160)]
Description = Annotated[str, Field(min_length=200, max_length=1200)]
Bullet = Annotated[str, Field(min_length=3, max_length=90)]
SeoTitle = Annotated[str, Field(min_length=10, max_length=60)]
MetaDescription = Annotated[str, Field(min_length=50, max_length=155)]


class Status(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class Severity(StrEnum):
    BLOCK = "block"
    WARN = "warn"


class CheckName(StrEnum):
    NUMBER = "number"
    ENTITY = "entity"
    CLAIM = "claim"


def _split_multi_value(value: object) -> object:
    if not isinstance(value, str):
        return value
    return [part.strip().lower() for part in value.split(MULTI_VALUE_SEPARATOR) if part.strip()]


def _blank_to_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


class ProductFacts(BaseModel):
    """One catalogue row: the only source of truth a generated text may draw on."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, frozen=True)

    sku: str = Field(min_length=1)
    name: str = Field(min_length=1)
    product_type: str | None = None
    stones: list[str] = Field(default_factory=list)
    colours: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    size_mm: Decimal | None = Field(default=None, gt=0)
    weight_g: Decimal | None = Field(default=None, gt=0)
    pieces: int | None = Field(default=None, gt=0)
    origin: str | None = None
    price_eur: Decimal | None = Field(default=None, ge=0)

    @field_validator("stones", "colours", "materials", mode="before")
    @classmethod
    def _split_cells(cls, value: object) -> object:
        return _split_multi_value(value)

    @field_validator(
        "product_type", "size_mm", "weight_g", "pieces", "origin", "price_eur", mode="before"
    )
    @classmethod
    def _empty_cells_are_unknown(cls, value: object) -> object:
        return _blank_to_none(value)

    @property
    def entities(self) -> tuple[str, ...]:
        """Every stone, colour and material this product is allowed to mention."""
        return tuple(dict.fromkeys([*self.stones, *self.colours, *self.materials]))


class ClaimRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    banned: list[str] = Field(default_factory=list)
    allowed_numbers: list[str] = Field(default_factory=list)


class BrandConfig(BaseModel):
    """Voice and compliance rules for one storefront, loaded from a TOML file."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    audience: str | None = None
    source: str | None = None
    do: list[str] = Field(default_factory=list)
    dont: list[str] = Field(default_factory=list)
    claims: ClaimRules = Field(default_factory=ClaimRules)


class BrandSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str


class GeneratedCopy(BaseModel):
    """The model's proposal. Valid shape here says nothing about factual support."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: Title
    short_description: ShortDescription
    description: Description
    bullets: list[Bullet] = Field(min_length=3, max_length=5)
    seo_title: SeoTitle
    meta_description: MetaDescription

    def fields(self) -> dict[str, str]:
        """Copy fields as flat text, keyed by the name a finding refers to."""
        flat: dict[str, str] = {
            "title": self.title,
            "short_description": self.short_description,
            "description": self.description,
            "seo_title": self.seo_title,
            "meta_description": self.meta_description,
        }
        for index, bullet in enumerate(self.bullets):
            flat[f"bullets[{index}]"] = bullet
        return flat


class Finding(BaseModel):
    """One unsupported or forbidden span, located for the reviewer."""

    model_config = ConfigDict(frozen=True)

    check: CheckName
    field: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    text: str
    message: str
    severity: Severity


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt_tokens: int = Field(default=0, ge=0)
    cached_prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)


class GenerationParams(BaseModel):
    """Sampling parameters that change the output and therefore the cache key."""

    model_config = ConfigDict(frozen=True)

    model: str
    temperature: float = Field(ge=0.0, le=2.0)
    reasoning_effort: ReasoningEffort | None = None
    max_completion_tokens: int = Field(gt=0)


class Generation(BaseModel):
    """A validated model response together with what it cost to obtain."""

    model_config = ConfigDict(frozen=True)

    output: GeneratedCopy
    usage: TokenUsage = Field(default_factory=TokenUsage)
    attempts: int = Field(default=1, ge=1)


class Provenance(BaseModel):
    model_config = ConfigDict(frozen=True)

    brand_id: str
    prompt_version: str
    prompt_fingerprint: str
    params: GenerationParams
    usage: TokenUsage = Field(default_factory=TokenUsage)
    attempts: int = Field(default=0, ge=0)
    cost_usd: Decimal = Decimal("0")
    cache_hit: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class Item(BaseModel):
    id: str
    batch_id: str
    row_number: int = Field(ge=1)
    facts: ProductFacts
    status: Status = Status.PENDING
    output: GeneratedCopy | None = None
    findings: list[Finding] = Field(default_factory=list)
    error: str | None = None
    provenance: Provenance | None = None


class Batch(BaseModel):
    id: str
    brand_id: str
    source_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
