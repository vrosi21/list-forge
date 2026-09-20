"""Loading brand configuration from TOML files."""

import logging
import re
import tomllib
from pathlib import Path

from pydantic import ValidationError

from list_forge.models import BrandConfig, BrandSummary

BRAND_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
BRAND_FILE_SUFFIX = ".toml"

logger = logging.getLogger(__name__)


class BrandNotFoundError(LookupError):
    """Raised when no configuration file matches a brand id."""


class BrandConfigError(ValueError):
    """Raised when a brand file exists but does not describe a usable brand."""


def load_brand(brands_dir: Path, brand_id: str) -> BrandConfig:
    """Load one brand. The id is matched against a whitelist before it touches the filesystem."""
    if not BRAND_ID_PATTERN.fullmatch(brand_id):
        raise BrandNotFoundError(f"unknown brand: {brand_id!r}")

    path = brands_dir / f"{brand_id}{BRAND_FILE_SUFFIX}"
    if not path.is_file():
        raise BrandNotFoundError(f"unknown brand: {brand_id!r}")

    brand = _read(path)
    if brand.id != brand_id:
        raise BrandConfigError(f"{path.name} declares id {brand.id!r}")
    return brand


def list_brands(brands_dir: Path) -> list[BrandSummary]:
    """Every readable brand, sorted by name. Unreadable files are logged and skipped."""
    summaries: list[BrandSummary] = []
    for path in sorted(brands_dir.glob(f"*{BRAND_FILE_SUFFIX}")):
        try:
            brand = _read(path)
        except BrandConfigError:
            logger.warning("skipping unreadable brand file: %s", path.name)
            continue
        summaries.append(BrandSummary(id=brand.id, name=brand.name))
    return sorted(summaries, key=lambda summary: summary.name)


def _read(path: Path) -> BrandConfig:
    with path.open("rb") as handle:
        try:
            data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as error:
            raise BrandConfigError(f"{path.name}: {error}") from error

    try:
        return BrandConfig.model_validate(data)
    except ValidationError as error:
        raise BrandConfigError(f"{path.name}: {error.error_count()} invalid field(s)") from error
