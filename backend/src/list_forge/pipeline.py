"""Running a batch: generate, check, route. One item at a time, many at once."""

import asyncio
import logging
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from uuid import uuid4

from openai import AuthenticationError

from list_forge.checks import CheckSuite, build_check_suite
from list_forge.llm import CopyGenerator, GenerationError, ProviderError
from list_forge.models import (
    BrandConfig,
    Finding,
    GeneratedCopy,
    Item,
    ProductFacts,
    Provenance,
    Status,
    TokenUsage,
)
from list_forge.pricing import estimate_cost_usd
from list_forge.prompts import PROMPT_VERSION, build_system_prompt, prompt_fingerprint
from list_forge.routing import route
from list_forge.vocabulary import Vocabulary

logger = logging.getLogger(__name__)

DEFAULT_ITEM_TIMEOUT_S = 120.0


class Pipeline:
    """One product in, one routed item out. A single bad row never raises."""

    def __init__(
        self,
        generator: CopyGenerator,
        vocabulary: Vocabulary,
        *,
        max_concurrency: int,
        item_timeout_s: float = DEFAULT_ITEM_TIMEOUT_S,
        semaphore: asyncio.Semaphore | None = None,
    ) -> None:
        self._generator = generator
        self._vocabulary = vocabulary
        self._semaphore = semaphore or asyncio.Semaphore(max_concurrency)
        self._item_timeout_s = item_timeout_s

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Shared so that a second pipeline cannot double the calls in flight."""
        return self._semaphore

    async def run_batch(
        self,
        products: Sequence[ProductFacts],
        brand: BrandConfig,
        batch_id: str | None = None,
        on_item: Callable[[Item], None] | None = None,
        item_ids: Sequence[str] | None = None,
    ) -> list[Item]:
        """Every product concurrently, results in input order, failures included."""
        batch = batch_id or uuid4().hex
        checks = build_check_suite(brand, self._vocabulary)
        ids = list(item_ids) if item_ids else [uuid4().hex for _ in products]
        if len(ids) != len(products):
            raise ValueError("item_ids must match the number of products")

        async def process(product: ProductFacts, row_number: int, item_id: str) -> Item:
            item = await self.process_item(product, brand, batch, row_number, checks, item_id)
            if on_item is not None:
                on_item(item)
            return item

        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(process(product, row_number, item_id))
                for row_number, (product, item_id) in enumerate(
                    zip(products, ids, strict=True), start=1
                )
            ]
        return [task.result() for task in tasks]

    async def process_item(
        self,
        facts: ProductFacts,
        brand: BrandConfig,
        batch_id: str,
        row_number: int,
        checks: CheckSuite | None = None,
        item_id: str | None = None,
    ) -> Item:
        suite = checks or build_check_suite(brand, self._vocabulary)
        identifier = item_id or uuid4().hex
        fingerprint = prompt_fingerprint(build_system_prompt(brand), self._generator.params)

        try:
            async with self._semaphore:
                async with asyncio.timeout(self._item_timeout_s):
                    generation = await self._generator.generate(facts, brand)
        except AuthenticationError:
            raise
        except (GenerationError, ProviderError, TimeoutError) as error:
            logger.warning("%s failed: %s", facts.sku, error)
            return self._item(
                facts,
                brand,
                batch_id,
                row_number,
                fingerprint,
                identifier,
                status=Status.FAILED,
                error=str(error),
            )

        findings = suite.run(facts, generation.output)
        return self._item(
            facts,
            brand,
            batch_id,
            row_number,
            fingerprint,
            identifier,
            status=route(generation.output, findings),
            output=generation.output,
            findings=findings,
            usage=generation.usage,
            attempts=generation.attempts,
            cache_hit=generation.cached,
        )

    def _item(
        self,
        facts: ProductFacts,
        brand: BrandConfig,
        batch_id: str,
        row_number: int,
        fingerprint: str,
        identifier: str,
        *,
        status: Status,
        output: GeneratedCopy | None = None,
        findings: Sequence[Finding] = (),
        usage: TokenUsage | None = None,
        attempts: int = 0,
        cache_hit: bool = False,
        error: str | None = None,
    ) -> Item:
        counted = usage or TokenUsage()
        params = self._generator.params
        return Item(
            id=identifier,
            batch_id=batch_id,
            row_number=row_number,
            facts=facts,
            status=status,
            output=output,
            findings=list(findings),
            error=error,
            provenance=Provenance(
                brand_id=brand.id,
                prompt_version=PROMPT_VERSION,
                prompt_fingerprint=fingerprint,
                params=params,
                usage=counted,
                attempts=attempts,
                cache_hit=cache_hit,
                cost_usd=estimate_cost_usd(params.model, counted),
                created_at=datetime.now(tz=UTC),
            ),
        )
