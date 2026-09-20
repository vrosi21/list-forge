"""Running a batch: generate, check, route. One item at a time, many at once."""

import asyncio
import logging
from collections.abc import Sequence
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
    ) -> None:
        self._generator = generator
        self._vocabulary = vocabulary
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._item_timeout_s = item_timeout_s

    async def run_batch(
        self, products: Sequence[ProductFacts], brand: BrandConfig, batch_id: str | None = None
    ) -> list[Item]:
        """Every product concurrently, results in input order, failures included."""
        batch = batch_id or uuid4().hex
        checks = build_check_suite(brand, self._vocabulary)

        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(self.process_item(product, brand, batch, row_number, checks))
                for row_number, product in enumerate(products, start=1)
            ]
        return [task.result() for task in tasks]

    async def process_item(
        self,
        facts: ProductFacts,
        brand: BrandConfig,
        batch_id: str,
        row_number: int,
        checks: CheckSuite | None = None,
    ) -> Item:
        suite = checks or build_check_suite(brand, self._vocabulary)
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
            status=route(generation.output, findings),
            output=generation.output,
            findings=findings,
            usage=generation.usage,
            attempts=generation.attempts,
        )

    def _item(
        self,
        facts: ProductFacts,
        brand: BrandConfig,
        batch_id: str,
        row_number: int,
        fingerprint: str,
        *,
        status: Status,
        output: GeneratedCopy | None = None,
        findings: Sequence[Finding] = (),
        usage: TokenUsage | None = None,
        attempts: int = 0,
        error: str | None = None,
    ) -> Item:
        counted = usage or TokenUsage()
        params = self._generator.params
        return Item(
            id=uuid4().hex,
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
                cost_usd=estimate_cost_usd(params.model, counted),
                created_at=datetime.now(tz=UTC),
            ),
        )
