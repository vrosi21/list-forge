"""Deterministic checks on generated copy.

Every check is a pure function over (facts, copy). No model, no network, no randomness,
so each rule can be proved by a table of examples.
"""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from list_forge.models import (
    BrandConfig,
    CheckName,
    Finding,
    GeneratedCopy,
    ProductFacts,
    Severity,
)
from list_forge.vocabulary import Match, Vocabulary, normalise

NUMBER_PATTERN = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
ABSENCE_PATTERN = re.compile(
    r"\b(?:"
    r"not\s+(?:specified|stated|listed|given|provided|available|disclosed)"
    r"|unspecified|unstated|undisclosed"
    r"|no\s+(?:listed|stated|specified|known|recorded)\s+\w+"
    r"|no\s+(?:information|details|data)\b"
    r"|(?:does|do|did)\s+not\s+(?:specify|state|list|mention)"
    r"|(?:isn't|aren't|wasn't|weren't)\s+(?:specified|stated|listed|given)"
    r")",
    re.IGNORECASE,
)
THOUSANDS_SEPARATOR = ","
COLOUR_CUE_WINDOW = 14
COLOUR_CUE_BEFORE = re.compile(r"\b(?:in|of|a|an|the|its|their|with|and)\s+$", re.IGNORECASE)
COLOUR_CUE_AFTER = re.compile(
    r"^\s*(?:tone|tones|toned|hue|hues|finish|colou?r|colou?red|shade)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class CheckSuite:
    """The checks for one brand, with every pattern compiled once."""

    vocabulary: Vocabulary
    claim_patterns: tuple[re.Pattern[str], ...]
    allowed_numbers: frozenset[Decimal]

    def run(self, facts: ProductFacts, copy: GeneratedCopy) -> list[Finding]:
        findings: list[Finding] = []
        allowed_numbers = self.allowed_numbers | numbers_in_facts(facts)
        allowed_entities = frozenset(normalise(entity) for entity in facts.entities)
        allowed_origin = normalise(facts.origin) if facts.origin else None

        for field, text in copy.fields().items():
            findings.extend(check_numbers(field, text, allowed_numbers))
            findings.extend(check_entities(field, text, allowed_entities, self.vocabulary))
            findings.extend(check_origin(field, text, allowed_origin, self.vocabulary))
            findings.extend(check_claims(field, text, self.claim_patterns))
            findings.extend(check_absence(field, text))

        return sorted(findings, key=lambda finding: (finding.field, finding.start))


def build_check_suite(brand: BrandConfig, vocabulary: Vocabulary) -> CheckSuite:
    return CheckSuite(
        vocabulary=vocabulary,
        claim_patterns=tuple(re.compile(pattern, re.IGNORECASE) for pattern in brand.claims.banned),
        allowed_numbers=frozenset(parse_numbers(" ".join(brand.claims.allowed_numbers))),
    )


def numbers_in_facts(facts: ProductFacts) -> frozenset[Decimal]:
    """Numbers the copy may use: those in the product name and the numeric fields, never the sku."""
    sources = [
        facts.name,
        str(facts.size_mm or ""),
        str(facts.weight_g or ""),
        str(facts.pieces or ""),
        str(facts.price_eur or ""),
    ]
    return frozenset(parse_numbers(" ".join(sources)))


def parse_numbers(text: str) -> set[Decimal]:
    values: set[Decimal] = set()
    for match in NUMBER_PATTERN.finditer(text):
        value = to_decimal(match.group(0))
        if value is not None:
            values.add(value)
    return values


def to_decimal(literal: str) -> Decimal | None:
    try:
        return Decimal(literal.replace(THOUSANDS_SEPARATOR, ""))
    except InvalidOperation:
        return None


def check_numbers(field: str, text: str, allowed: Iterable[Decimal]) -> list[Finding]:
    """Every number in the copy has to appear in the product data."""
    permitted = set(allowed)
    findings: list[Finding] = []

    for match in NUMBER_PATTERN.finditer(text):
        value = to_decimal(match.group(0))
        if value is None or value in permitted:
            continue
        findings.append(
            _finding(
                CheckName.NUMBER,
                field,
                match.start(),
                match.end(),
                match.group(0),
                f"{match.group(0)} is not in the product data",
            )
        )
    return findings


def check_entities(
    field: str, text: str, allowed: frozenset[str], vocabulary: Vocabulary
) -> list[Finding]:
    """Stones, colours and materials named in the copy have to belong to this product."""
    return [
        _finding(
            CheckName.ENTITY,
            field,
            match.start,
            match.end,
            text[match.start : match.end],
            f"{match.term} is not one of this product's attributes",
        )
        for match in vocabulary.find_entities(text)
        if not _covered(match.term, allowed)
        and not (vocabulary.is_ambiguous(match.term) and not _reads_as_colour(text, match))
    ]


def _reads_as_colour(text: str, match: Match) -> bool:
    """Words like 'clear' and 'gold' only count as a colour claim in colour-shaped phrasing."""
    before = text[max(0, match.start - COLOUR_CUE_WINDOW) : match.start]
    after = text[match.end : match.end + COLOUR_CUE_WINDOW]
    return bool(COLOUR_CUE_BEFORE.search(before) or COLOUR_CUE_AFTER.match(after))


def check_origin(
    field: str, text: str, allowed: str | None, vocabulary: Vocabulary
) -> list[Finding]:
    """A place of origin may only be named when the product data states it."""
    findings: list[Finding] = []
    for match in vocabulary.find_origins(text):
        if allowed is not None and match.term == allowed:
            continue
        reason = (
            f"{match.term} is not the stated origin"
            if allowed
            else f"{match.term} is an origin the product data does not give"
        )
        findings.append(
            _finding(
                CheckName.ORIGIN,
                field,
                match.start,
                match.end,
                text[match.start : match.end],
                reason,
            )
        )
    return findings


def check_claims(field: str, text: str, patterns: Sequence[re.Pattern[str]]) -> list[Finding]:
    """Claims the brand may not make, whatever the product data says."""
    findings: list[Finding] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            findings.append(
                _finding(
                    CheckName.CLAIM,
                    field,
                    match.start(),
                    match.end(),
                    match.group(0),
                    f"{match.group(0)!r} is a claim this brand does not make",
                    severity=Severity.BLOCK,
                )
            )
    return findings


def check_absence(field: str, text: str) -> list[Finding]:
    """Copy should leave a missing attribute out rather than announce that it is missing."""
    return [
        _finding(
            CheckName.ABSENCE,
            field,
            match.start(),
            match.end(),
            match.group(0),
            "copy points at a missing fact instead of leaving it out",
        )
        for match in ABSENCE_PATTERN.finditer(text)
    ]


def _covered(term: str, allowed: frozenset[str]) -> bool:
    """A narrower term is covered by a wider one: 'quartz' passes when the facts say
    'rose quartz'."""
    if term in allowed:
        return True
    words = term.split(" ")
    return any(_contains_words(entity, words) for entity in allowed)


def _contains_words(entity: str, words: Sequence[str]) -> bool:
    entity_words = entity.split(" ")
    return all(word in entity_words for word in words)


def _finding(
    check: CheckName,
    field: str,
    start: int,
    end: int,
    text: str,
    message: str,
    severity: Severity = Severity.WARN,
) -> Finding:
    return Finding(
        check=check,
        field=field,
        start=start,
        end=end,
        text=text,
        message=message,
        severity=severity,
    )
