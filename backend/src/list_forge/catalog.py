"""Reading product rows from CSV into validated facts."""

import csv
from collections.abc import Iterable, Mapping
from io import StringIO
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from list_forge.models import ProductFacts

CSV_ENCODING = "utf-8-sig"
FIRST_DATA_ROW_NUMBER = 2
MAX_ROWS = 500


class CatalogTooLargeError(ValueError):
    """Raised when a file carries more rows than the pipeline accepts."""


class RowError(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_number: int = Field(ge=1)
    message: str


class Catalog(BaseModel):
    """Rows that parsed, and the reason each rejected row did not."""

    model_config = ConfigDict(frozen=True)

    products: list[ProductFacts] = Field(default_factory=list)
    errors: list[RowError] = Field(default_factory=list)

    @property
    def row_count(self) -> int:
        return len(self.products) + len(self.errors)


def parse_rows(rows: Iterable[Mapping[str, str | None]], *, limit: int | None = None) -> Catalog:
    """Validate raw CSV rows, keeping one error per rejected row instead of failing the file."""
    products: list[ProductFacts] = []
    errors: list[RowError] = []
    seen_skus: dict[str, int] = {}

    for row_number, row in enumerate(rows, start=FIRST_DATA_ROW_NUMBER):
        if limit is not None and len(products) >= limit:
            break
        if row_number - FIRST_DATA_ROW_NUMBER >= MAX_ROWS:
            raise CatalogTooLargeError(f"more than {MAX_ROWS} rows")

        try:
            facts = ProductFacts.model_validate(_clean(row))
        except ValidationError as error:
            errors.append(RowError(row_number=row_number, message=_describe(error)))
            continue

        first_seen = seen_skus.get(facts.sku)
        if first_seen is not None:
            errors.append(
                RowError(
                    row_number=row_number, message=f"duplicate sku, first seen on row {first_seen}"
                )
            )
            continue

        seen_skus[facts.sku] = row_number
        products.append(facts)

    return Catalog(products=products, errors=errors)


def parse_csv(text: str, *, limit: int | None = None) -> Catalog:
    return parse_rows(csv.DictReader(StringIO(text)), limit=limit)


def load_products(path: Path, *, limit: int | None = None) -> Catalog:
    with path.open(encoding=CSV_ENCODING, newline="") as handle:
        return parse_rows(csv.DictReader(handle), limit=limit)


def _clean(row: Mapping[str, str | None]) -> dict[str, str]:
    return {key: (value or "") for key, value in row.items() if key}


def _describe(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )
