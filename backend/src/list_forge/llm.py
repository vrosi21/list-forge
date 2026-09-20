"""The model call: one request, its own retry policy, and output that must validate."""

import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)
from pydantic import ValidationError

from list_forge.config import Settings
from list_forge.models import (
    BrandConfig,
    GeneratedCopy,
    Generation,
    GenerationParams,
    ProductFacts,
    TokenUsage,
)
from list_forge.prompts import build_messages, build_system_prompt, repair_message

logger = logging.getLogger(__name__)

Message = dict[str, str]
Sleep = Callable[[float], Awaitable[None]]

RETRYABLE_ERRORS = (APIConnectionError, RateLimitError, InternalServerError)
TRUNCATED_FINISH_REASON = "length"


class ProviderError(RuntimeError):
    """The provider could not be reached, or kept failing, after every transport attempt."""


class GenerationError(RuntimeError):
    """The provider answered, but never with output that satisfied the schema."""


class ModelUnavailableError(RuntimeError):
    """The key works, but the configured model is not one this account can call."""


@dataclass(frozen=True)
class Completion:
    text: str
    usage: TokenUsage
    finish_reason: str | None


class CopyGenerator(Protocol):
    """The seam every caller depends on, so tests never need a network."""

    async def generate(self, facts: ProductFacts, brand: BrandConfig) -> Generation: ...


def build_client(settings: Settings) -> AsyncOpenAI:
    """One client per process: it owns a connection pool and its own timeout policy."""
    return AsyncOpenAI(
        api_key=settings.require_llm_api_key().get_secret_value(),
        base_url=settings.llm_base_url,
        max_retries=0,
        timeout=settings.request_timeout_s,
    )


def backoff_delay(
    attempt: int,
    retry_after_s: float | None,
    base_s: float,
    cap_s: float,
    rand: Callable[[], float] = random.random,
) -> float:
    """Exponential backoff with full jitter, never shorter than the server's own advice."""
    ceiling_s = min(cap_s, base_s * 2 ** (attempt - 1))
    jittered_s = ceiling_s * rand()
    return max(jittered_s, retry_after_s or 0.0)


def retry_after_seconds(error: Exception) -> float | None:
    """The provider's retry-after header, when it sent one."""
    response = getattr(error, "response", None)
    header = getattr(response, "headers", {}).get("retry-after") if response else None
    if header is None:
        return None
    try:
        return float(header)
    except ValueError:
        return None


def extract_json_object(text: str) -> dict[str, Any]:
    """Read one JSON object out of a reply that may carry fences or commentary around it."""
    start = text.find("{")
    if start == -1:
        raise ValueError("response contained no JSON object")
    try:
        data, _ = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as error:
        raise ValueError(f"malformed JSON: {error.msg}") from error
    if not isinstance(data, dict):
        raise ValueError("response was not a JSON object")
    return data


def describe_validation_error(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}" for item in error.errors()
    )


def add_usage(first: TokenUsage, second: TokenUsage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=first.prompt_tokens + second.prompt_tokens,
        cached_prompt_tokens=first.cached_prompt_tokens + second.cached_prompt_tokens,
        completion_tokens=first.completion_tokens + second.completion_tokens,
    )


def read_usage(usage: Any) -> TokenUsage:
    if usage is None:
        return TokenUsage()
    details = getattr(usage, "prompt_tokens_details", None)
    return TokenUsage(
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        cached_prompt_tokens=getattr(details, "cached_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
    )


class GroqGenerator:
    """Turns product facts into validated copy, or into a clear failure."""

    def __init__(
        self,
        client: AsyncOpenAI,
        params: GenerationParams,
        *,
        max_transport_attempts: int,
        max_content_attempts: int,
        backoff_base_s: float,
        backoff_cap_s: float,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._client = client
        self._params = params
        self._max_transport_attempts = max_transport_attempts
        self._max_content_attempts = max_content_attempts
        self._backoff_base_s = backoff_base_s
        self._backoff_cap_s = backoff_cap_s
        self._sleep = sleep

    @property
    def params(self) -> GenerationParams:
        return self._params

    async def available_models(self) -> list[str]:
        """Every model this key may call. Costs no tokens."""
        page = await self._client.models.list()
        return sorted(model.id for model in page.data)

    async def probe(self) -> str:
        """Confirm the key is accepted and the configured model is one it may call."""
        available = await self.available_models()
        if self._params.model not in available:
            raise ModelUnavailableError(
                f"model {self._params.model!r} is not available to this key"
            )
        return self._params.model

    async def generate(self, facts: ProductFacts, brand: BrandConfig) -> Generation:
        messages = build_messages(build_system_prompt(brand), facts)
        usage = TokenUsage()
        last_detail = ""

        for attempt in range(1, self._max_content_attempts + 1):
            completion = await self.complete(messages)
            usage = add_usage(usage, completion.usage)

            try:
                output = self._parse(completion)
            except (ValueError, ValidationError) as error:
                last_detail = (
                    describe_validation_error(error)
                    if isinstance(error, ValidationError)
                    else str(error)
                )
                logger.info("%s: attempt %s rejected (%s)", facts.sku, attempt, last_detail)
                messages = [
                    *messages,
                    {"role": "assistant", "content": completion.text},
                    {"role": "user", "content": repair_message(last_detail)},
                ]
                continue

            return Generation(output=output, usage=usage, attempts=attempt)

        raise GenerationError(
            f"no valid output after {self._max_content_attempts} attempts: {last_detail}"
        )

    async def complete(self, messages: Sequence[Message]) -> Completion:
        last_error: Exception | None = None

        for attempt in range(1, self._max_transport_attempts + 1):
            try:
                response = await self._client.chat.completions.create(**self._request(messages))
            except AuthenticationError:
                raise
            except RETRYABLE_ERRORS as error:
                last_error = error
                delay_s = backoff_delay(
                    attempt,
                    retry_after_seconds(error),
                    self._backoff_base_s,
                    self._backoff_cap_s,
                )
                logger.warning(
                    "%s on attempt %s, retrying in %.1fs", type(error).__name__, attempt, delay_s
                )
                await self._sleep(delay_s)
                continue

            choice = response.choices[0]
            return Completion(
                text=choice.message.content or "",
                usage=read_usage(response.usage),
                finish_reason=choice.finish_reason,
            )

        raise ProviderError(
            f"provider unavailable after {self._max_transport_attempts} attempts"
        ) from last_error

    def _request(self, messages: Sequence[Message]) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self._params.model,
            "messages": list(messages),
            "temperature": self._params.temperature,
            "max_completion_tokens": self._params.max_completion_tokens,
        }
        if self._params.reasoning_effort is not None:
            request["reasoning_effort"] = self._params.reasoning_effort
        return request

    def _parse(self, completion: Completion) -> GeneratedCopy:
        if completion.finish_reason == TRUNCATED_FINISH_REASON:
            raise ValueError("response was cut off by the token limit")
        return GeneratedCopy.model_validate(extract_json_object(completion.text))


def build_generator(settings: Settings, client: AsyncOpenAI) -> GroqGenerator:
    return GroqGenerator(
        client,
        settings.generation_params(),
        max_transport_attempts=settings.max_transport_attempts,
        max_content_attempts=settings.max_content_attempts,
        backoff_base_s=settings.backoff_base_s,
        backoff_cap_s=settings.backoff_cap_s,
    )


__all__ = [
    "APIStatusError",
    "Completion",
    "CopyGenerator",
    "GenerationError",
    "GroqGenerator",
    "ModelUnavailableError",
    "ProviderError",
    "backoff_delay",
    "build_client",
    "build_generator",
    "extract_json_object",
]
