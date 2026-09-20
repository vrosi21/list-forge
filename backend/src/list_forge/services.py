"""Everything long-lived, built once and shared by the CLI and the API."""

import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from openai import APIStatusError, AuthenticationError

from list_forge.cache import CachedGenerator
from list_forge.config import ConfigurationError, Settings
from list_forge.llm import (
    CopyGenerator,
    GroqGenerator,
    ModelUnavailableError,
    ProviderError,
    build_client,
    build_generator,
)
from list_forge.pipeline import Pipeline
from list_forge.store import Store
from list_forge.vocabulary import Vocabulary, load_vocabulary

logger = logging.getLogger(__name__)

NOT_PROBED = "provider was not probed"


@dataclass(frozen=True)
class ProviderStatus:
    reachable: bool
    model: str
    checked_at: datetime
    detail: str | None = None


@dataclass(frozen=True)
class Services:
    settings: Settings
    store: Store
    vocabulary: Vocabulary
    generator: CachedGenerator
    pipeline: Pipeline
    provider: ProviderStatus

    def refreshing_pipeline(self) -> Pipeline:
        """Ignores stored answers, shares the semaphore so calls in flight stay capped."""
        return Pipeline(
            self.generator.refreshing(),
            self.vocabulary,
            max_concurrency=self.settings.max_concurrency,
            semaphore=self.pipeline.semaphore,
        )


@asynccontextmanager
async def build_services(
    settings: Settings, *, generator: CopyGenerator | None = None
) -> AsyncIterator[Services]:
    """Opens the store and the provider client, and closes both however the caller leaves."""
    async with AsyncExitStack() as stack:
        store = Store(settings.database_path)
        stack.callback(store.close)

        interrupted = store.mark_interrupted()
        if interrupted:
            logger.warning("failed %s item(s) left in flight by an earlier run", interrupted)

        vocabulary = load_vocabulary(settings.vocabulary_path)

        if generator is None:
            client = build_client(settings)
            stack.push_async_callback(client.close)
            base: CopyGenerator = build_generator(settings, client)
            provider = await probe_provider(base, settings)
        else:
            base = generator
            provider = ProviderStatus(
                reachable=True,
                model=base.params.model,
                checked_at=datetime.now(tz=UTC),
                detail=NOT_PROBED,
            )

        cached = CachedGenerator(base, store)
        yield Services(
            settings=settings,
            store=store,
            vocabulary=vocabulary,
            generator=cached,
            pipeline=Pipeline(cached, vocabulary, max_concurrency=settings.max_concurrency),
            provider=provider,
        )


async def probe_provider(generator: CopyGenerator, settings: Settings) -> ProviderStatus:
    """A rejected key stops the process; an unreachable provider only starts it degraded."""
    checked_at = datetime.now(tz=UTC)
    if not isinstance(generator, GroqGenerator):
        return ProviderStatus(True, settings.llm_model, checked_at, NOT_PROBED)

    try:
        model = await generator.probe()
    except AuthenticationError as error:
        raise ConfigurationError("the provider rejected the API key") from error
    except ModelUnavailableError as error:
        raise ConfigurationError(str(error)) from error
    except (APIStatusError, ProviderError, OSError) as error:
        logger.warning("provider unreachable at startup: %s", error)
        return ProviderStatus(False, settings.llm_model, checked_at, str(error))

    return ProviderStatus(True, model, checked_at)
