from pathlib import Path

import pytest

from conftest import write_brand
from list_forge.brands import BrandConfigError, BrandNotFoundError, list_brands, load_brand


def test_a_brand_loads_with_its_rules(brands_dir: Path) -> None:
    brand = load_brand(brands_dir, "mindful-souls")

    assert brand.name == "Mindful Souls"
    assert brand.claims.banned == [r"\bheals?\b"]


def test_an_unknown_brand_is_refused(brands_dir: Path) -> None:
    with pytest.raises(BrandNotFoundError):
        load_brand(brands_dir, "no-such-brand")


@pytest.mark.parametrize("brand_id", ["../secrets", "..\\secrets", "/etc/passwd", "Mindful", ""])
def test_ids_outside_the_whitelist_never_reach_the_filesystem(
    brands_dir: Path, brand_id: str
) -> None:
    with pytest.raises(BrandNotFoundError):
        load_brand(brands_dir, brand_id)


def test_a_file_whose_id_disagrees_with_its_name_is_refused(brands_dir: Path) -> None:
    path = brands_dir / "renamed.toml"
    path.write_text(
        (brands_dir / "mindful-souls.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )

    with pytest.raises(BrandConfigError):
        load_brand(brands_dir, "renamed")


def test_invalid_toml_is_refused(brands_dir: Path) -> None:
    (brands_dir / "broken.toml").write_text("id = ", encoding="utf-8")

    with pytest.raises(BrandConfigError):
        load_brand(brands_dir, "broken")


def test_unknown_fields_are_refused(brands_dir: Path) -> None:
    (brands_dir / "extra.toml").write_text(
        'id = "extra"\nname = "Extra"\nvoice = "Calm."\nmood = "unknown"\n', encoding="utf-8"
    )

    with pytest.raises(BrandConfigError):
        load_brand(brands_dir, "extra")


def test_brands_are_listed_by_name_and_broken_files_are_skipped(brands_dir: Path) -> None:
    (brands_dir / "broken.toml").write_text("id = ", encoding="utf-8")
    write_brand(brands_dir, "aurora", "Aurora Stones")

    assert [summary.id for summary in list_brands(brands_dir)] == [
        "aurora",
        "beads-and-stones",
        "mindful-souls",
    ]
