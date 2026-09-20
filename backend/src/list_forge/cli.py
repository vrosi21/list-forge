"""Command line entry point."""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from openai import APIStatusError, AuthenticationError
from pydantic import ValidationError

from list_forge.brands import BrandConfigError, BrandNotFoundError, list_brands, load_brand
from list_forge.catalog import Catalog, CatalogTooLargeError, load_products
from list_forge.config import ConfigurationError, Settings, get_settings
from list_forge.llm import (
    GenerationError,
    ModelUnavailableError,
    ProviderError,
    build_client,
    build_generator,
)
from list_forge.models import BrandConfig, ProductFacts, TokenUsage
from list_forge.pricing import estimate_cost_usd

PREVIEW_ROWS = 5
EXIT_OK = 0
EXIT_REJECTED = 1
EXIT_UNUSABLE = 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    try:
        settings = get_settings()
    except ValidationError as error:
        print(f"configuration error: {_describe(error)}", file=sys.stderr)
        return EXIT_UNUSABLE

    if args.command == "brands":
        return _run_brands(settings)
    if args.command == "check":
        return asyncio.run(_run_check(settings))
    if args.command == "generate":
        return asyncio.run(_run_generate(settings, args.csv_path, args.brand, args.limit))
    return _run_inspect(settings, args.csv_path, args.brand, args.limit)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="list-forge")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("brands", help="list configured brands")
    commands.add_parser("check", help="verify the model provider is reachable")

    inspect = commands.add_parser("inspect", help="validate a product CSV against a brand")
    _add_catalog_arguments(inspect)

    generate = commands.add_parser("generate", help="generate copy for the first rows of a CSV")
    _add_catalog_arguments(generate)
    return parser


def _add_catalog_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--brand", required=True)
    parser.add_argument("--limit", type=int, default=None)


def _run_brands(settings: Settings) -> int:
    for summary in list_brands(settings.brands_dir):
        print(f"{summary.id:<24} {summary.name}")
    return EXIT_OK


async def _run_check(settings: Settings) -> int:
    print(f"base url: {settings.llm_base_url}")
    print(f"model:    {settings.llm_model}")

    try:
        client = build_client(settings)
    except ConfigurationError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_UNUSABLE

    generator = build_generator(settings, client)
    try:
        model_id = await generator.probe()
    except AuthenticationError:
        print("error: the provider rejected the API key", file=sys.stderr)
        return EXIT_UNUSABLE
    except ModelUnavailableError as error:
        print(f"error: {error}", file=sys.stderr)
        for available in await generator.available_models():
            print(f"  available: {available}", file=sys.stderr)
        return EXIT_UNUSABLE
    except APIStatusError as error:
        print(f"error: provider returned {error.status_code}", file=sys.stderr)
        return EXIT_UNUSABLE
    except (ProviderError, OSError) as error:
        print(f"error: provider unreachable: {error}", file=sys.stderr)
        return EXIT_UNUSABLE
    finally:
        await client.close()

    print(f"provider: reachable, model {model_id} available")
    return EXIT_OK


async def _run_generate(
    settings: Settings, csv_path: Path, brand_id: str, limit: int | None
) -> int:
    loaded = _load(settings, csv_path, brand_id, limit)
    if loaded is None:
        return EXIT_UNUSABLE
    brand, catalog = loaded

    try:
        client = build_client(settings)
    except ConfigurationError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_UNUSABLE

    generator = build_generator(settings, client)
    failures = 0
    total_usage = TokenUsage()

    try:
        for product in catalog.products:
            try:
                generation = await generator.generate(product, brand)
            except AuthenticationError:
                print("error: the provider rejected the API key", file=sys.stderr)
                return EXIT_UNUSABLE
            except (GenerationError, ProviderError) as error:
                failures += 1
                print(f"{product.sku:<14} FAILED  {error}", file=sys.stderr)
                continue

            total_usage = _accumulate(total_usage, generation.usage)
            _print_generation(product, generation.output.title, generation.attempts)
    finally:
        await client.close()

    _print_totals(settings.llm_model, total_usage, failures)
    return EXIT_REJECTED if failures else EXIT_OK


def _run_inspect(settings: Settings, csv_path: Path, brand_id: str, limit: int | None) -> int:
    loaded = _load(settings, csv_path, brand_id, limit)
    if loaded is None:
        return EXIT_UNUSABLE
    brand, catalog = loaded

    print(f"brand:    {brand.name}")
    print(f"rows:     {catalog.row_count}")
    print(f"parsed:   {len(catalog.products)}")
    print(f"rejected: {len(catalog.errors)}")

    for product in catalog.products[:PREVIEW_ROWS]:
        entities = ", ".join(product.entities) or "-"
        print(f"  {product.sku:<16} {product.name:<34} {entities}")

    for row_error in catalog.errors:
        print(f"  row {row_error.row_number}: {row_error.message}", file=sys.stderr)

    return EXIT_REJECTED if catalog.errors else EXIT_OK


def _load(
    settings: Settings, csv_path: Path, brand_id: str, limit: int | None
) -> tuple[BrandConfig, Catalog] | None:
    try:
        brand = load_brand(settings.brands_dir, brand_id)
    except (BrandNotFoundError, BrandConfigError) as error:
        print(f"error: {error}", file=sys.stderr)
        return None

    if not csv_path.is_file():
        print(f"error: no such file: {csv_path}", file=sys.stderr)
        return None

    try:
        catalog = load_products(csv_path, limit=limit)
    except (CatalogTooLargeError, UnicodeDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return None

    return brand, catalog


def _accumulate(total: TokenUsage, usage: TokenUsage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=total.prompt_tokens + usage.prompt_tokens,
        cached_prompt_tokens=total.cached_prompt_tokens + usage.cached_prompt_tokens,
        completion_tokens=total.completion_tokens + usage.completion_tokens,
    )


def _print_generation(product: ProductFacts, title: str, attempts: int) -> None:
    suffix = "" if attempts == 1 else f"  ({attempts} attempts)"
    print(f"{product.sku:<14} {title}{suffix}")


def _print_totals(model: str, usage: TokenUsage, failures: int) -> None:
    cost = estimate_cost_usd(model, usage)
    rendered = "unpriced model" if cost is None else f"${cost:.6f} at list price"
    print(
        f"tokens: {usage.prompt_tokens} in "
        f"({usage.cached_prompt_tokens} cached), {usage.completion_tokens} out"
    )
    print(f"cost:   {rendered}")
    if failures:
        print(f"failed: {failures}")


def _describe(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )


if __name__ == "__main__":
    raise SystemExit(main())
