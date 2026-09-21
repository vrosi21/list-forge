"""The HTTP surface: a thin adapter over the same pipeline the CLI uses."""

import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import AuthenticationError
from pydantic import BaseModel

from list_forge.brands import BrandConfigError, BrandNotFoundError, list_brands, load_brand
from list_forge.catalog import Catalog, CatalogTooLargeError, parse_csv
from list_forge.config import get_settings
from list_forge.models import Batch, BrandConfig, BrandSummary, Item, Status, TokenUsage
from list_forge.pricing import estimate_cost_usd
from list_forge.services import Services, build_services

logger = logging.getLogger(__name__)

CSV_ENCODING = "utf-8-sig"
ACCESS_HEADER = "x-demo-code"
FORWARDED_FOR_HEADER = "x-forwarded-for"
UNKNOWN_CLIENT = "unknown"
ACCEPTED = 202
UNAUTHORIZED = 401
PAYLOAD_TOO_LARGE = 413
UNPROCESSABLE = 422
TOO_MANY_REQUESTS = 429
BAD_GATEWAY = 502


class HealthResponse(BaseModel):
    status: str
    provider_reachable: bool
    model: str
    checked_at: datetime
    detail: str | None = None


class BatchCreated(BaseModel):
    batch_id: str


class AccessStatus(BaseModel):
    required: bool
    valid: bool
    runs_remaining: int | None = None
    runs_per_day: int | None = None
    max_rows: int | None = None


class BatchTotals(BaseModel):
    prompt_tokens: int = 0
    cached_prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: Decimal | None = None
    saved_usd: Decimal | None = None
    cache_hits: int = 0


class BatchResponse(BaseModel):
    batch: Batch
    counts: dict[str, int]
    totals: BatchTotals
    items: list[Item]


def get_services(request: Request) -> Services:
    return request.app.state.services


ServicesDep = Annotated[Services, Depends(get_services)]


def client_address(request: Request, *, trust_proxy: bool) -> str:
    """The caller's address, read from the proxy header only where a proxy is expected."""
    if trust_proxy:
        forwarded = request.headers.get(FORWARDED_FOR_HEADER, "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else UNKNOWN_CLIENT


def enforce_rate_limit(request: Request, services: ServicesDep) -> None:
    limiter = services.rate_limiter
    if limiter is None:
        return
    address = client_address(request, trust_proxy=services.settings.trust_proxy_headers)
    if not limiter.take(address):
        raise HTTPException(TOO_MANY_REQUESTS, "too many requests, try again shortly")


def guard_spend(request: Request, services: ServicesDep) -> str:
    """Everything that protects the provider key, in the order that costs least to reject."""
    enforce_rate_limit(request, services)

    label = services.access.label_for(request.headers.get(ACCESS_HEADER))
    if label is None:
        raise HTTPException(UNAUTHORIZED, "this demo needs an access code")

    if not services.daily_budget.spend(label):
        raise HTTPException(
            TOO_MANY_REQUESTS,
            f"this access code has used its {services.daily_budget.limit} runs for today",
        )
    return label


SpendDep = Annotated[str, Depends(guard_spend)]


def create_app(services: Services | None = None) -> FastAPI:
    """Pass services in for tests; leave them out and the lifespan builds the real ones."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if services is not None:
            app.state.services = services
            yield
            return
        async with build_services(get_settings()) as built:
            app.state.services = built
            yield

    app = FastAPI(title="ListForge", lifespan=lifespan)
    origin = (services.settings if services else get_settings()).frontend_origin
    app.add_middleware(
        CORSMiddleware, allow_origins=[origin], allow_methods=["*"], allow_headers=["*"]
    )
    _register_routes(app)
    return app


def _register_routes(app: FastAPI) -> None:
    @app.get("/health")
    def health(services: ServicesDep) -> HealthResponse:
        return HealthResponse(
            status="ok",
            provider_reachable=services.provider.reachable,
            model=services.provider.model,
            checked_at=services.provider.checked_at,
            detail=services.provider.detail,
        )

    @app.get("/brands")
    def brands(services: ServicesDep) -> list[BrandSummary]:
        return list_brands(services.settings.brands_dir)

    @app.get("/access", dependencies=[Depends(enforce_rate_limit)])
    def access(request: Request, services: ServicesDep) -> AccessStatus:
        """Whether a code would be accepted, without spending any of its runs."""
        label = services.access.label_for(request.headers.get(ACCESS_HEADER))
        budget = services.daily_budget
        return AccessStatus(
            required=services.access.required,
            valid=label is not None,
            runs_remaining=budget.remaining(label) if label is not None else None,
            runs_per_day=budget.limit,
            max_rows=services.settings.demo_max_rows,
        )

    @app.post("/batches", status_code=ACCEPTED)
    async def create_batch(
        file: UploadFile,
        brand_id: Annotated[str, Form()],
        background: BackgroundTasks,
        services: ServicesDep,
        label: SpendDep,
    ) -> BatchCreated:
        brand = _brand(services, brand_id)
        catalog = _catalog(services, await _read(file, services.settings.max_upload_bytes))
        if not catalog.products:
            raise HTTPException(UNPROCESSABLE, "no usable rows in the file")

        allowed_rows = services.settings.demo_max_rows
        if allowed_rows is not None and catalog.row_count > allowed_rows:
            raise HTTPException(
                PAYLOAD_TOO_LARGE, f"this demo accepts at most {allowed_rows} rows per file"
            )

        batch, items = services.store.start_batch(
            brand.id, file.filename or "upload.csv", catalog.products
        )
        logger.info("batch %s started by %s", batch.id, label)
        background.add_task(_process_batch, services, batch, brand, items)
        return BatchCreated(batch_id=batch.id)

    @app.get("/batches/{batch_id}")
    def read_batch(batch_id: str, services: ServicesDep) -> BatchResponse:
        batch = services.store.get_batch(batch_id)
        if batch is None:
            raise HTTPException(404, "no such batch")

        items = services.store.list_items(batch_id)
        return BatchResponse(
            batch=batch, counts=_counts(items), totals=_totals(services, items), items=items
        )

    @app.post("/items/{item_id}/regenerate")
    async def regenerate(item_id: str, services: ServicesDep, label: SpendDep) -> Item:
        logger.info("item %s regenerated by %s", item_id, label)
        item = services.store.get_item(item_id)
        if item is None:
            raise HTTPException(404, "no such item")

        brand = _brand(services, item.provenance.brand_id if item.provenance else "")
        try:
            refreshed = await services.refreshing_pipeline().process_item(
                item.facts, brand, item.batch_id, item.row_number, None, item.id
            )
        except AuthenticationError as error:
            raise HTTPException(BAD_GATEWAY, "the provider rejected the API key") from error

        services.store.save_item(refreshed)
        return refreshed


async def _read(file: UploadFile, limit: int) -> bytes:
    payload = await file.read(limit + 1)
    if len(payload) > limit:
        raise HTTPException(PAYLOAD_TOO_LARGE, f"file is larger than {limit} bytes")
    return payload


def _brand(services: Services, brand_id: str) -> BrandConfig:
    try:
        return load_brand(services.settings.brands_dir, brand_id)
    except BrandNotFoundError as error:
        raise HTTPException(UNPROCESSABLE, f"unknown brand: {brand_id!r}") from error
    except BrandConfigError as error:
        raise HTTPException(UNPROCESSABLE, str(error)) from error


def _catalog(services: Services, payload: bytes) -> Catalog:
    try:
        text = payload.decode(CSV_ENCODING)
    except UnicodeDecodeError as error:
        raise HTTPException(UNPROCESSABLE, "file is not UTF-8 text") from error

    try:
        return parse_csv(text)
    except CatalogTooLargeError as error:
        raise HTTPException(PAYLOAD_TOO_LARGE, str(error)) from error


async def _process_batch(
    services: Services, batch: Batch, brand: BrandConfig, items: Sequence[Item]
) -> None:
    """Runs after the response is sent. Anything it cannot finish is recorded as failed."""
    try:
        await services.pipeline.run_batch(
            [item.facts for item in items],
            brand,
            batch.id,
            on_item=services.store.save_item,
            item_ids=[item.id for item in items],
        )
    except BaseExceptionGroup as group:
        reason = str(group.exceptions[0])
        logger.error("batch %s aborted: %s", batch.id, reason)
        _fail_unfinished(services, batch.id, f"batch aborted: {reason}")


def _fail_unfinished(services: Services, batch_id: str, reason: str) -> None:
    for item in services.store.list_items(batch_id):
        if item.status in {Status.PENDING, Status.PROCESSING}:
            services.store.save_item(
                item.model_copy(update={"status": Status.FAILED, "error": reason})
            )


def _counts(items: Sequence[Item]) -> dict[str, int]:
    counts = {status.value: 0 for status in Status}
    for item in items:
        counts[item.status.value] += 1
    return counts


def _totals(services: Services, items: Sequence[Item]) -> BatchTotals:
    """Work paid for on this run is separated from work a cache hit gave away."""
    spent = TokenUsage()
    saved = TokenUsage()
    cache_hits = 0

    for item in items:
        if item.provenance is None:
            continue
        if item.provenance.cache_hit:
            saved = _add(saved, item.provenance.usage)
            cache_hits += 1
        else:
            spent = _add(spent, item.provenance.usage)

    total = _add(spent, saved)
    model = services.settings.llm_model
    return BatchTotals(
        prompt_tokens=total.prompt_tokens,
        cached_prompt_tokens=total.cached_prompt_tokens,
        completion_tokens=total.completion_tokens,
        cost_usd=estimate_cost_usd(model, spent),
        saved_usd=estimate_cost_usd(model, saved),
        cache_hits=cache_hits,
    )


def _add(total: TokenUsage, usage: TokenUsage) -> TokenUsage:
    return TokenUsage(
        prompt_tokens=total.prompt_tokens + usage.prompt_tokens,
        cached_prompt_tokens=total.cached_prompt_tokens + usage.cached_prompt_tokens,
        completion_tokens=total.completion_tokens + usage.completion_tokens,
    )


app = create_app()
