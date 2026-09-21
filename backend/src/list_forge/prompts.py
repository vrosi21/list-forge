"""Prompt construction and versioning.

Released versions are immutable: to change wording, register a version rather than editing one.
"""

from pydantic import BaseModel, ConfigDict, Field

from list_forge.hashing import stable_hash
from list_forge.models import BrandConfig, GenerationParams, ProductFacts

FINGERPRINT_LENGTH = 12
DEFAULT_PROMPT_VERSION = "copy-v1"

ROLE = "You write product copy for an online store."

FAITHFULNESS_RULES_V1 = """Rules that override every other instruction:
- Use only the facts in the product JSON.
- Never state a number that does not appear in it.
- Never name a stone, colour, material, country or region that does not appear in it.
- When a fact is missing, leave that attribute out instead of guessing.
- Never claim or imply a health, medical, therapeutic or emotional benefit."""

FAITHFULNESS_RULES_V2 = """Rules that override every other instruction:
- Every noun and number in your answer must be traceable to a value in the product JSON.
- Never state a number that does not appear in it, including counts, sizes, weights and prices.
- Never name a stone, colour, material, country or region that does not appear in it.
- An empty or absent field means unknown. Leave that attribute out of the copy entirely.
  Do not write that it is unspecified, unlisted or not stated.
- Never claim or imply a health, medical, therapeutic or emotional benefit, and never imply
  one through a word like healing, calming, grounding, balancing, protective or cleansing.
- A word in the product name does not license a claim. Describe the object, not its effect."""

OUTPUT_CONTRACT = """Return one JSON object and nothing else: no prose, no code fences.
Required keys and limits:
- title: 10 to 70 characters
- short_description: 20 to 160 characters
- description: 200 to 1200 characters
- bullets: 3 to 5 strings, each 3 to 90 characters
- seo_title: 10 to 60 characters
- meta_description: 50 to 155 characters"""

EXAMPLE_V2 = """Worked example.
Product JSON: {"sku":"EX-1","name":"Jade Bead Bracelet","stones":["jade"],"colours":["green"],
"size_mm":6,"pieces":null,"origin":null,"price_eur":null}
Acceptable: "green jade beads, 6 mm across".
Not acceptable: "34 green jade beads" (count invented), "jade from Myanmar" (origin invented),
"calming jade" (benefit implied), "origin not specified" (absence described)."""

REPAIR_INSTRUCTION = "Return only the corrected JSON object."


class PromptVersion(BaseModel):
    """One released prompt, as data. The version label is part of its fingerprint."""

    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    faithfulness_rules: str = Field(min_length=1)
    output_contract: str = Field(min_length=1)
    example: str | None = None

    def system_prompt(self, brand: BrandConfig) -> str:
        """The instruction half of the prompt. Identical for every product of one brand."""
        sections = [ROLE, f"Brand: {brand.name}"]
        if brand.audience:
            sections.append(f"Audience: {brand.audience}")
        sections.append(f"Voice:\n{brand.voice.strip()}")
        if brand.do:
            sections.append("Always:\n" + "\n".join(f"- {rule}" for rule in brand.do))
        if brand.dont:
            sections.append("Never:\n" + "\n".join(f"- {rule}" for rule in brand.dont))
        sections.extend([self.faithfulness_rules, self.output_contract])
        if self.example:
            sections.append(self.example)
        return "\n\n".join(sections)

    def fingerprint(self, brand: BrandConfig, params: GenerationParams) -> str:
        """Identifies everything that shapes the output: version, rendered prompt, parameters."""
        payload = {
            "version": self.version,
            "system": self.system_prompt(brand),
            "params": params.model_dump(mode="json"),
        }
        return stable_hash(payload)[:FINGERPRINT_LENGTH]


class UnknownPromptVersionError(ValueError):
    """Raised when a configured or requested prompt version was never registered."""


PROMPT_VERSIONS: dict[str, PromptVersion] = {
    version.version: version
    for version in (
        PromptVersion(
            version="copy-v1",
            faithfulness_rules=FAITHFULNESS_RULES_V1,
            output_contract=OUTPUT_CONTRACT,
        ),
        PromptVersion(
            version="copy-v2",
            faithfulness_rules=FAITHFULNESS_RULES_V2,
            output_contract=OUTPUT_CONTRACT,
            example=EXAMPLE_V2,
        ),
    )
}


def get_prompt_version(version: str) -> PromptVersion:
    prompt = PROMPT_VERSIONS.get(version)
    if prompt is None:
        known = ", ".join(sorted(PROMPT_VERSIONS))
        raise UnknownPromptVersionError(f"unknown prompt version {version!r}; known: {known}")
    return prompt


def build_messages(system_prompt: str, facts: ProductFacts) -> list[dict[str, str]]:
    """Instructions in the system turn, product data in the user turn, never mixed."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": facts.model_dump_json()},
    ]


def repair_message(detail: str) -> str:
    return f"That response failed validation:\n{detail}\n{REPAIR_INSTRUCTION}"
