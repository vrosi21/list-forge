"""Measured accuracy of the checks against hand-written copy.

Every case in bad_copy.json carries exactly one planted violation and every case in
good_copy.json is clean, so these two tests report catch rate and false-flag rate.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from fakes import sample_brand, sample_facts
from list_forge.checks import build_check_suite
from list_forge.models import Finding, GeneratedCopy
from list_forge.vocabulary import load_vocabulary

FIXTURES = Path(__file__).parent / "fixtures"
VOCABULARY = load_vocabulary(Path(__file__).parents[1] / "brands" / "vocab.toml")

NEUTRAL_COPY: dict[str, Any] = {
    "title": "A Piece For Your Altar",
    "short_description": "A single piece, cut and polished for a desk or an altar.",
    "description": "",
    "bullets": ["One piece", "Cut and polished", "For a desk or an altar"],
    "seo_title": "A Piece For Your Altar",
    "meta_description": "A single polished piece, ready for a desk, a shelf or an altar at home.",
}
DESCRIPTION_MINIMUM = 200


def load_cases(name: str) -> list[dict[str, Any]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def findings_for(case: dict[str, Any]) -> list[Finding]:
    facts = sample_facts(**case.get("facts", {}))
    copy = GeneratedCopy.model_validate(
        NEUTRAL_COPY | {"description": case["description"].ljust(DESCRIPTION_MINIMUM, ".")}
    )
    return build_check_suite(sample_brand(), VOCABULARY).run(facts, copy)


@pytest.mark.parametrize("case", load_cases("bad_copy.json"), ids=lambda case: case["name"])
def test_every_planted_violation_is_caught(case: dict[str, Any]) -> None:
    findings = findings_for(case)

    assert case["expect"] in {finding.check.value for finding in findings}


@pytest.mark.parametrize("case", load_cases("good_copy.json"), ids=lambda case: case["name"])
def test_clean_copy_is_never_flagged(case: dict[str, Any]) -> None:
    assert findings_for(case) == []


def test_the_fixture_set_stays_worth_running() -> None:
    bad = load_cases("bad_copy.json")
    good = load_cases("good_copy.json")

    assert len(bad) >= 10
    assert len(good) >= 5
    assert {case["expect"] for case in bad} == {"number", "entity", "origin", "claim", "absence"}
