from pathlib import Path

import pytest

from conftest import CSV_HEADER, csv_text
from list_forge.catalog import MAX_ROWS, CatalogTooLargeError, load_products, parse_csv

AMETHYST = "MS-AMT-001,Amethyst Point,tower,amethyst,purple,,70,120,1,Brazil,19.90"
ROSE_QUARTZ = "MS-RQZ-022,Rose Quartz Sphere,sphere,rose quartz,pink,,50,180,1,Madagascar,29.50"
NO_SKU = ",Nameless Point,tower,amethyst,purple,,70,120,1,Brazil,19.90"
BAD_PRICE = "MS-BAD-003,Odd Price,tower,amethyst,purple,,70,120,1,Brazil,free"


def test_valid_rows_parse() -> None:
    catalog = parse_csv(csv_text(AMETHYST, ROSE_QUARTZ))

    assert [product.sku for product in catalog.products] == ["MS-AMT-001", "MS-RQZ-022"]
    assert catalog.errors == []


def test_a_bad_row_is_reported_with_its_spreadsheet_row_number() -> None:
    catalog = parse_csv(csv_text(AMETHYST, NO_SKU, ROSE_QUARTZ))

    assert [product.sku for product in catalog.products] == ["MS-AMT-001", "MS-RQZ-022"]
    assert [error.row_number for error in catalog.errors] == [3]
    assert "sku" in catalog.errors[0].message


def test_an_unparseable_number_rejects_only_that_row() -> None:
    catalog = parse_csv(csv_text(AMETHYST, BAD_PRICE))

    assert len(catalog.products) == 1
    assert "price_eur" in catalog.errors[0].message


def test_duplicate_skus_are_rejected() -> None:
    catalog = parse_csv(csv_text(AMETHYST, AMETHYST))

    assert len(catalog.products) == 1
    assert catalog.errors[0].message == "duplicate sku, first seen on row 2"


def test_limit_stops_after_the_requested_number_of_products() -> None:
    catalog = parse_csv(csv_text(AMETHYST, ROSE_QUARTZ), limit=1)

    assert len(catalog.products) == 1
    assert catalog.row_count == 1


def test_oversized_files_are_refused() -> None:
    rows = [AMETHYST.replace("MS-AMT-001", f"MS-{index:05d}") for index in range(MAX_ROWS + 1)]

    with pytest.raises(CatalogTooLargeError):
        parse_csv(csv_text(*rows))


def test_files_saved_by_excel_with_a_byte_order_mark_still_parse(tmp_path: Path) -> None:
    path = tmp_path / "products.csv"
    path.write_text(csv_text(AMETHYST), encoding="utf-8-sig")

    catalog = load_products(path)

    assert [product.sku for product in catalog.products] == ["MS-AMT-001"]


def test_header_only_file_yields_nothing() -> None:
    catalog = parse_csv(CSV_HEADER + "\n")

    assert catalog.row_count == 0
