"""Skipping calls that have already been paid for.

The key covers everything that can change the output, so editing a brand voice or a
sampling parameter simply stops matching old entries. There is no invalidation step.
"""

from list_forge.hashing import stable_hash
from list_forge.llm import CopyGenerator
from list_forge.models import BrandConfig, Generation, GenerationParams, ProductFacts
from list_forge.prompts import PromptVersion
from list_forge.store import Store


def cache_key(facts: ProductFacts, brand_id: str, prompt_fingerprint: str) -> str:
    return stable_hash(
        {
            "facts": facts.model_dump(mode="json"),
            "brand_id": brand_id,
            "prompt_fingerprint": prompt_fingerprint,
        }
    )


class CachedGenerator:
    """A CopyGenerator that answers from the store when it can, and fills it when it cannot."""

    def __init__(self, inner: CopyGenerator, store: Store, *, refresh: bool = False) -> None:
        self._inner = inner
        self._store = store
        self._refresh = refresh

    @property
    def params(self) -> GenerationParams:
        return self._inner.params

    @property
    def prompt(self) -> PromptVersion:
        return self._inner.prompt

    @property
    def inner(self) -> CopyGenerator:
        return self._inner

    def refreshing(self) -> "CachedGenerator":
        """A view that ignores stored answers but still writes what it produces."""
        return CachedGenerator(self._inner, self._store, refresh=True)

    async def generate(self, facts: ProductFacts, brand: BrandConfig) -> Generation:
        fingerprint = self.prompt.fingerprint(brand, self.params)
        key = cache_key(facts, brand.id, fingerprint)

        if not self._refresh:
            stored = self._store.cached_generation(key)
            if stored is not None:
                return stored.model_copy(update={"cached": True})

        generation = await self._inner.generate(facts, brand)
        self._store.store_generation(
            key,
            generation,
            model=self.params.model,
            version=self.prompt.version,
            fingerprint=fingerprint,
        )
        return generation
