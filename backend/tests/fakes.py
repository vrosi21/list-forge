"""Test doubles for the model provider, so tests never touch the network."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import httpx
from openai import APIConnectionError, AuthenticationError, InternalServerError, RateLimitError

from list_forge.llm import GroqGenerator
from list_forge.models import BrandConfig, GenerationParams, ProductFacts

REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")

VALID_COPY: dict[str, Any] = {
    "title": "Amethyst Point in Deep Purple",
    "short_description": "A single amethyst point, cut and polished for a desk or an altar.",
    "description": "An amethyst point with purple and white banding. " * 6,
    "bullets": ["Amethyst point", "Purple and white banding", "One piece"],
    "seo_title": "Amethyst Point, Purple",
    "meta_description": "An amethyst point with purple and white banding, polished for a desk.",
}


def valid_copy_json(**overrides: Any) -> str:
    return json.dumps(VALID_COPY | overrides)


def sample_facts(**overrides: Any) -> ProductFacts:
    base: dict[str, Any] = {
        "sku": "MS-AMT-101",
        "name": "Amethyst Chevron Crystal Tower",
        "product_type": "tower",
        "stones": "amethyst",
        "colours": "purple;white",
        "pieces": "1",
    }
    return ProductFacts.model_validate(base | overrides)


def sample_brand(**overrides: Any) -> BrandConfig:
    base: dict[str, Any] = {
        "id": "mindful-souls",
        "name": "Mindful Souls",
        "audience": "People who buy crystals for daily ritual.",
        "voice": "Warm, calm and grounded. Short sentences.",
        "do": ["Name the stone"],
        "dont": ["No medical claims"],
        "claims": {"banned": [r"\bheals?\b"]},
    }
    return BrandConfig.model_validate(base | overrides)


def sample_params(**overrides: Any) -> GenerationParams:
    base: dict[str, Any] = {
        "model": "openai/gpt-oss-20b",
        "temperature": 0.7,
        "reasoning_effort": "low",
        "max_completion_tokens": 1500,
    }
    return GenerationParams.model_validate(base | overrides)


@dataclass(frozen=True)
class Reply:
    text: str
    finish_reason: str = "stop"
    prompt_tokens: int = 120
    cached_prompt_tokens: int = 0
    completion_tokens: int = 80


def rate_limit_error(retry_after: str | None = None) -> RateLimitError:
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    response = httpx.Response(429, headers=headers, request=REQUEST)
    return RateLimitError("rate limited", response=response, body=None)


def server_error() -> InternalServerError:
    return InternalServerError("boom", response=httpx.Response(500, request=REQUEST), body=None)


def connection_error() -> APIConnectionError:
    return APIConnectionError(message="connection reset", request=REQUEST)


def auth_error() -> AuthenticationError:
    return AuthenticationError(
        "invalid key", response=httpx.Response(401, request=REQUEST), body=None
    )


class FakeCompletions:
    def __init__(self, script: list[Reply | Exception]) -> None:
        self._script = list(script)
        self.requests: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        if not self._script:
            raise AssertionError("the client was called more times than the script allows")
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item
        return _response(item)


class FakeClient:
    """Mimics only the two calls GroqGenerator makes."""

    def __init__(
        self,
        script: list[Reply | Exception] | None = None,
        *,
        models: Sequence[str] = ("openai/gpt-oss-20b", "openai/gpt-oss-120b"),
        list_error: Exception | None = None,
    ) -> None:
        self.completions = FakeCompletions(script or [])
        self.chat = SimpleNamespace(completions=self.completions)
        self.models = SimpleNamespace(list=self._list)
        self._model_ids = list(models)
        self._list_error = list_error
        self.closed = False

    async def _list(self) -> Any:
        if self._list_error is not None:
            raise self._list_error
        return SimpleNamespace(data=[SimpleNamespace(id=model) for model in self._model_ids])

    async def close(self) -> None:
        self.closed = True


class SleepRecorder:
    """Stands in for asyncio.sleep so retry tests run instantly."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def make_generator(
    script: list[Reply | Exception] | None = None, **overrides: Any
) -> tuple[GroqGenerator, FakeClient, SleepRecorder]:
    client = FakeClient(script)
    sleep = SleepRecorder()
    settings: dict[str, Any] = {
        "max_transport_attempts": 3,
        "max_content_attempts": 3,
        "backoff_base_s": 1.0,
        "backoff_cap_s": 8.0,
    }
    generator = GroqGenerator(client, sample_params(), sleep=sleep, **(settings | overrides))
    return generator, client, sleep


def _response(reply: Reply) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=reply.text), finish_reason=reply.finish_reason
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=reply.prompt_tokens,
            completion_tokens=reply.completion_tokens,
            prompt_tokens_details=SimpleNamespace(cached_tokens=reply.cached_prompt_tokens),
        ),
    )
