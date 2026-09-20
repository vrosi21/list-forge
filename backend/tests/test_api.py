from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import csv_text
from fakes import FakeGenerator
from list_forge.api import create_app
from list_forge.cache import CachedGenerator
from list_forge.config import Settings
from list_forge.pipeline import Pipeline
from list_forge.services import ProviderStatus, Services
from list_forge.store import Store
from list_forge.vocabulary import load_vocabulary

AMETHYST = "MS-AMT-101,Amethyst Chevron Crystal Tower,tower,amethyst,purple;white,,,,1,,"
ROSE_QUARTZ = "MS-RQZ-102,Rose Quartz Sphere,sphere,rose quartz,pink,,35,,1,,"


@pytest.fixture
def generator() -> FakeGenerator:
    return FakeGenerator()


@pytest.fixture
def services(tmp_path: Path, generator: FakeGenerator) -> Iterator[Services]:
    settings = Settings(
        _env_file=None,
        GROQ_API_KEY="test-key",
        database_path=tmp_path / "listforge.db",
        max_upload_bytes=2_000,
    )
    store = Store(settings.database_path)
    vocabulary = load_vocabulary(settings.vocabulary_path)
    cached = CachedGenerator(generator, store)
    yield Services(
        settings=settings,
        store=store,
        vocabulary=vocabulary,
        generator=cached,
        pipeline=Pipeline(cached, vocabulary, max_concurrency=2),
        provider=ProviderStatus(True, settings.llm_model, datetime.now(tz=UTC), "not probed"),
    )
    store.close()


@pytest.fixture
def client(services: Services) -> Iterator[TestClient]:
    with TestClient(create_app(services)) as started:
        yield started


def upload(client: TestClient, rows: str = AMETHYST, brand_id: str = "mindful-souls") -> str:
    response = client.post(
        "/batches",
        files={"file": ("products.csv", csv_text(rows).encode("utf-8"), "text/csv")},
        data={"brand_id": brand_id},
    )
    assert response.status_code == 202, response.text
    return response.json()["batch_id"]


class TestHealth:
    def test_it_reports_the_provider(self, client: TestClient) -> None:
        body = client.get("/health").json()

        assert body["status"] == "ok"
        assert body["provider_reachable"] is True
        assert body["model"] == "openai/gpt-oss-20b"


class TestBrands:
    def test_it_lists_the_configured_brands(self, client: TestClient) -> None:
        ids = {brand["id"] for brand in client.get("/brands").json()}

        assert {"mindful-souls", "beads-and-stones"} <= ids


class TestCreateBatch:
    def test_an_upload_is_accepted_and_processed(self, client: TestClient) -> None:
        batch_id = upload(client)

        body = client.get(f"/batches/{batch_id}").json()

        assert body["batch"]["brand_id"] == "mindful-souls"
        assert body["counts"]["approved"] == 1
        assert body["counts"]["pending"] == 0
        assert body["items"][0]["facts"]["sku"] == "MS-AMT-101"

    def test_rows_keep_their_order_and_identity(self, client: TestClient) -> None:
        batch_id = upload(client, f"{AMETHYST}\n{ROSE_QUARTZ}")

        items = client.get(f"/batches/{batch_id}").json()["items"]

        assert [item["row_number"] for item in items] == [1, 2]
        assert len({item["id"] for item in items}) == 2

    def test_an_unknown_brand_is_refused(self, client: TestClient) -> None:
        response = client.post(
            "/batches",
            files={"file": ("products.csv", csv_text(AMETHYST).encode("utf-8"), "text/csv")},
            data={"brand_id": "no-such-brand"},
        )

        assert response.status_code == 422

    def test_a_file_with_no_usable_rows_is_refused(self, client: TestClient) -> None:
        response = client.post(
            "/batches",
            files={"file": ("products.csv", csv_text().encode("utf-8"), "text/csv")},
            data={"brand_id": "mindful-souls"},
        )

        assert response.status_code == 422

    def test_an_oversized_upload_is_refused(self, client: TestClient) -> None:
        rows = "\n".join([AMETHYST] * 60)

        response = client.post(
            "/batches",
            files={"file": ("products.csv", csv_text(rows).encode("utf-8"), "text/csv")},
            data={"brand_id": "mindful-souls"},
        )

        assert response.status_code == 413


class TestReadBatch:
    def test_an_unknown_batch_is_missing(self, client: TestClient) -> None:
        assert client.get("/batches/nope").status_code == 404

    def test_totals_add_up_the_usage(self, client: TestClient) -> None:
        batch_id = upload(client, f"{AMETHYST}\n{ROSE_QUARTZ}")

        totals = client.get(f"/batches/{batch_id}").json()["totals"]

        assert totals["prompt_tokens"] == 200
        assert totals["completion_tokens"] == 100
        assert totals["cache_hits"] == 0


class TestCaching:
    def test_the_same_file_twice_is_served_from_the_cache(
        self, client: TestClient, generator: FakeGenerator
    ) -> None:
        upload(client)
        second = upload(client)

        body = client.get(f"/batches/{second}").json()

        assert len(generator.seen) == 1
        assert body["totals"]["cache_hits"] == 1
        assert body["items"][0]["provenance"]["cache_hit"] is True

    def test_a_cached_run_reports_no_new_spend(
        self, client: TestClient, generator: FakeGenerator
    ) -> None:
        upload(client)
        second = upload(client)

        totals = client.get(f"/batches/{second}").json()["totals"]

        assert Decimal(totals["cost_usd"]) == 0
        assert Decimal(totals["saved_usd"]) > 0


class TestRegenerate:
    def test_it_asks_the_model_again_and_stores_the_answer(
        self, client: TestClient, generator: FakeGenerator
    ) -> None:
        batch_id = upload(client)
        item_id = client.get(f"/batches/{batch_id}").json()["items"][0]["id"]

        response = client.post(f"/items/{item_id}/regenerate")

        assert response.status_code == 200
        assert response.json()["id"] == item_id
        assert len(generator.seen) == 2

    def test_an_unknown_item_is_missing(self, client: TestClient) -> None:
        assert client.post("/items/nope/regenerate").status_code == 404
