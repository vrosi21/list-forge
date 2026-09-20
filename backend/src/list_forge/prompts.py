"""Prompt construction and versioning.

Released versions are immutable: to change wording, add a version rather than editing one.
"""

from list_forge.hashing import stable_hash
from list_forge.models import BrandConfig, GenerationParams, ProductFacts

PROMPT_VERSION = "copy-v1"
FINGERPRINT_LENGTH = 12

ROLE = "You write product copy for an online store."

FAITHFULNESS_RULES = """Rules that override every other instruction:
- Use only the facts in the product JSON.
- Never state a number that does not appear in it.
- Never name a stone, colour, material, country or region that does not appear in it.
- When a fact is missing, leave that attribute out instead of guessing.
- Never claim or imply a health, medical, therapeutic or emotional benefit."""

OUTPUT_CONTRACT = """Return one JSON object and nothing else: no prose, no code fences.
Required keys and limits:
- title: 10 to 70 characters
- short_description: 20 to 160 characters
- description: 200 to 1200 characters
- bullets: 3 to 5 strings, each 3 to 90 characters
- seo_title: 10 to 60 characters
- meta_description: 50 to 155 characters"""

REPAIR_INSTRUCTION = "Return only the corrected JSON object."


def build_system_prompt(brand: BrandConfig) -> str:
    """The instruction half of the prompt. Identical for every product of one brand."""
    sections = [ROLE, f"Brand: {brand.name}"]
    if brand.audience:
        sections.append(f"Audience: {brand.audience}")
    sections.append(f"Voice:\n{brand.voice.strip()}")
    if brand.do:
        sections.append("Always:\n" + "\n".join(f"- {rule}" for rule in brand.do))
    if brand.dont:
        sections.append("Never:\n" + "\n".join(f"- {rule}" for rule in brand.dont))
    sections.extend([FAITHFULNESS_RULES, OUTPUT_CONTRACT])
    return "\n\n".join(sections)


def build_messages(system_prompt: str, facts: ProductFacts) -> list[dict[str, str]]:
    """Instructions in the system turn, product data in the user turn, never mixed."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": facts.model_dump_json()},
    ]


def repair_message(detail: str) -> str:
    return f"That response failed validation:\n{detail}\n{REPAIR_INSTRUCTION}"


def prompt_fingerprint(system_prompt: str, params: GenerationParams) -> str:
    """Identifies everything that shapes the output: the rendered prompt and the parameters."""
    payload = {
        "version": PROMPT_VERSION,
        "system": system_prompt,
        "params": params.model_dump(mode="json"),
    }
    return stable_hash(payload)[:FINGERPRINT_LENGTH]
