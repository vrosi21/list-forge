from decimal import Decimal

import pytest
from pydantic import ValidationError

from list_forge.models import GeneratedCopy, ProductFacts

VALID_COPY = {
    "title": "Amethyst Point in Deep Purple",
    "short_description": "A single amethyst point, cut and polished for a desk or an altar.",
    "description": "A" * 250,
    "bullets": ["Amethyst point", "70 mm tall", "Weighs 120 g"],
    "seo_title": "Amethyst Point, 70 mm",
    "meta_description": "An amethyst point of 70 mm, polished and ready for a desk or altar shelf.",
}


def facts(**overrides: object) -> ProductFacts:
    base: dict[str, object] = {"sku": "MS-1", "name": "Amethyst Point"}
    return ProductFacts.model_validate(base | overrides)


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("amethyst", ["amethyst"]),
        ("Amethyst; Rose Quartz", ["amethyst", "rose quartz"]),
        ("amethyst;;  citrine  ", ["amethyst", "citrine"]),
        ("", []),
    ],
)
def test_multi_value_cells_split_into_normalised_lists(cell: str, expected: list[str]) -> None:
    assert facts(stones=cell).stones == expected


@pytest.mark.parametrize("field", ["product_type", "origin", "size_mm", "pieces", "price_eur"])
def test_blank_cells_become_unknown(field: str) -> None:
    assert getattr(facts(**{field: "   "}), field) is None


def test_numeric_cells_keep_decimal_precision() -> None:
    assert facts(price_eur="24.90").price_eur == Decimal("24.90")


def test_entities_are_deduplicated_in_order() -> None:
    product = facts(stones="rose quartz;clear quartz", colours="pink", materials="rose quartz")
    assert product.entities == ("rose quartz", "clear quartz", "pink")


def test_facts_reject_a_missing_sku() -> None:
    with pytest.raises(ValidationError):
        ProductFacts.model_validate({"name": "Amethyst Point"})


def test_copy_rejects_an_over_long_title() -> None:
    with pytest.raises(ValidationError):
        GeneratedCopy.model_validate(VALID_COPY | {"title": "A" * 71})


def test_copy_rejects_unexpected_fields() -> None:
    with pytest.raises(ValidationError):
        GeneratedCopy.model_validate(VALID_COPY | {"tags": ["amethyst"]})


def test_copy_rejects_too_few_bullets() -> None:
    with pytest.raises(ValidationError):
        GeneratedCopy.model_validate(VALID_COPY | {"bullets": ["One", "Two"]})


def test_copy_fields_are_addressable_for_findings() -> None:
    fields = GeneratedCopy.model_validate(VALID_COPY).fields()
    assert fields["title"] == VALID_COPY["title"]
    assert fields["bullets[2]"] == "Weighs 120 g"
