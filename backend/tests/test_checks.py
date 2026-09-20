from decimal import Decimal

import pytest

from fakes import VALID_COPY, sample_brand, sample_facts
from list_forge.checks import build_check_suite, check_absence, check_numbers, numbers_in_facts
from list_forge.models import CheckName, GeneratedCopy, Severity
from list_forge.vocabulary import build_vocabulary

VOCABULARY = build_vocabulary(
    entities=[
        "amethyst",
        "quartz",
        "rose quartz",
        "clear quartz",
        "tiger's eye",
        "labradorite",
        "sterling silver",
        "elastic cord",
        "purple",
        "white",
        "pink",
        "gold",
    ],
    origins=["brazil", "morocco", "india"],
)


def copy_with(**overrides: str | list[str]) -> GeneratedCopy:
    return GeneratedCopy.model_validate(VALID_COPY | overrides)


def findings_for(text: str, *, facts_overrides: dict[str, object] | None = None) -> list:
    facts = sample_facts(**(facts_overrides or {}))
    suite = build_check_suite(sample_brand(), VOCABULARY)
    description = text.ljust(200, ".")
    return [
        finding
        for finding in suite.run(facts, copy_with(description=description))
        if finding.field == "description"
    ]


class TestNumbers:
    @pytest.mark.parametrize(
        ("text", "allowed", "flagged"),
        [
            pytest.param("Set of 7 stones", {"7"}, [], id="supported"),
            pytest.param("Only 19.90 euro", {"19.9"}, [], id="trailing-zero-is-the-same-number"),
            pytest.param("1,000 facets", {"1000"}, [], id="thousands-separator"),
            pytest.param("8 mm beads, 19 per strand", {"8"}, ["19"], id="one-invented"),
            pytest.param("Weighs 120 g", set(), ["120"], id="nothing-allowed"),
        ],
    )
    def test_only_numbers_from_the_facts_survive(
        self, text: str, allowed: set[str], flagged: list[str]
    ) -> None:
        allowed_decimals = {Decimal(value) for value in allowed}

        results = check_numbers("description", text, allowed_decimals)

        assert [finding.text for finding in results] == flagged

    def test_a_flagged_number_carries_its_position(self) -> None:
        text = "Stands 80 mm tall"

        finding = check_numbers("description", text, set())[0]

        assert text[finding.start : finding.end] == "80"
        assert finding.check is CheckName.NUMBER
        assert finding.severity is Severity.WARN

    def test_numbers_in_the_product_name_are_allowed(self) -> None:
        facts = sample_facts(name="7 Chakra Tumbled Stone Set", pieces="7")

        assert Decimal("7") in numbers_in_facts(facts)

    def test_numbers_inside_the_sku_are_not_allowed(self) -> None:
        facts = sample_facts(sku="MS-AMT-101", name="Amethyst Tower", pieces=None)

        assert Decimal("101") not in numbers_in_facts(facts)


class TestEntities:
    def test_a_stone_the_product_has_is_fine(self) -> None:
        assert findings_for("A polished amethyst tower in purple and white") == []

    def test_a_stone_the_product_does_not_have_is_flagged(self) -> None:
        findings = findings_for("Amethyst with flecks of labradorite")

        assert [finding.text for finding in findings] == ["labradorite"]
        assert findings[0].check is CheckName.ENTITY

    def test_an_invented_material_is_flagged(self) -> None:
        findings = findings_for("Finished with a sterling silver clasp")

        assert [finding.text for finding in findings] == ["sterling silver"]

    def test_a_wider_term_covers_a_narrower_mention(self) -> None:
        findings = findings_for(
            "Cut from quartz", facts_overrides={"stones": "rose quartz", "colours": "pink"}
        )

        assert findings == []

    def test_a_different_variety_is_still_flagged(self) -> None:
        findings = findings_for(
            "Made of clear quartz", facts_overrides={"stones": "rose quartz", "colours": "pink"}
        )

        assert [finding.text for finding in findings] == ["clear quartz"]


class TestOrigin:
    def test_an_origin_the_facts_do_not_give_is_flagged(self) -> None:
        findings = findings_for("Mined in Brazil and polished by hand")

        assert [finding.check for finding in findings] == [CheckName.ORIGIN]
        assert findings[0].text == "Brazil"

    def test_the_stated_origin_may_be_named(self) -> None:
        findings = findings_for("Mined in Morocco", facts_overrides={"origin": "Morocco"})

        assert findings == []

    def test_a_different_origin_is_flagged_even_when_one_is_stated(self) -> None:
        findings = findings_for("Mined in India", facts_overrides={"origin": "Morocco"})

        assert [finding.text for finding in findings] == ["India"]


class TestClaims:
    @pytest.mark.parametrize(
        "text",
        ["It heals the wearer", "A healing stone", "HEALS anxiety", "Use it to heal"],
    )
    def test_banned_claims_are_blocked(self, text: str) -> None:
        findings = findings_for(text)

        assert findings[0].check is CheckName.CLAIM
        assert findings[0].severity is Severity.BLOCK

    def test_the_product_name_does_not_license_a_claim(self) -> None:
        findings = findings_for(
            "A healing tool for your altar",
            facts_overrides={"name": "Selenite Crystal Wand Cleansing Healing Tool"},
        )

        assert [finding.check for finding in findings] == [CheckName.CLAIM]


class TestAbsence:
    @pytest.mark.parametrize(
        "text",
        [
            "Its weight is not specified, but it feels substantial",
            "The origin is not stated",
            "Dimensions unspecified",
        ],
    )
    def test_pointing_at_a_missing_fact_is_flagged(self, text: str) -> None:
        findings = check_absence("description", text)

        assert [finding.check for finding in findings] == [CheckName.ABSENCE]

    def test_ordinary_copy_is_left_alone(self) -> None:
        assert check_absence("description", "A single amethyst point for your altar") == []


class TestSuite:
    def test_every_copy_field_is_checked_including_bullets(self) -> None:
        suite = build_check_suite(sample_brand(), VOCABULARY)
        copy = copy_with(bullets=["Contains labradorite", "Amethyst point", "One piece"])

        findings = suite.run(sample_facts(), copy)

        assert [finding.field for finding in findings] == ["bullets[0]"]

    def test_clean_copy_produces_no_findings(self) -> None:
        suite = build_check_suite(sample_brand(), VOCABULARY)

        assert suite.run(sample_facts(), copy_with()) == []

    def test_findings_are_ordered_by_field_and_position(self) -> None:
        suite = build_check_suite(sample_brand(), VOCABULARY)
        copy = copy_with(description="Weighs 120 g and contains labradorite. ".ljust(200, "."))

        findings = suite.run(sample_facts(), copy)

        assert [finding.text for finding in findings] == ["120", "labradorite"]
