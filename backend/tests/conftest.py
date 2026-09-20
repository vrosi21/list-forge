from pathlib import Path

import pytest

BRAND_TOML = """
id = "{brand_id}"
name = "{name}"
voice = "Calm and concrete."
do = ["Name the stone"]
dont = ["No medical claims"]

[claims]
banned = ['\\bheals?\\b']
"""

CSV_HEADER = (
    "sku,name,product_type,stones,colours,materials,size_mm,weight_g,pieces,origin,price_eur"
)


@pytest.fixture
def brands_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "brands"
    directory.mkdir()
    write_brand(directory, "mindful-souls", "Mindful Souls")
    write_brand(directory, "beads-and-stones", "Beads & Stones")
    return directory


def write_brand(directory: Path, brand_id: str, name: str) -> Path:
    path = directory / f"{brand_id}.toml"
    path.write_text(BRAND_TOML.format(brand_id=brand_id, name=name), encoding="utf-8")
    return path


def csv_text(*rows: str) -> str:
    return "\n".join([CSV_HEADER, *rows]) + "\n"
