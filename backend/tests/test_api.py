from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import csv_text
from fakes import FakeGenerator
from list_forge.api import create_app
from list_forge.budgets import DailyBudget
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


@pytest.fixture
def guarded_client(tmp_path: Path, generator: FakeGenerator) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,
        GROQ_API_KEY="test-key",
        database_path=tmp_path / "guarded.db",
        demo_codes="a1:alice,b2:bob",
        demo_max_rows=1,
        demo_daily_batches_per_code=2,
    )
    store = Store(settings.database_path)
    vocabulary = load_vocabulary(settings.vocabulary_path)
    cached = CachedGenerator(generator, store)
    services = Services(
        settings=settings,
        store=store,
        vocabulary=vocabulary,
        generator=cached,
        pipeline=Pipeline(cached, vocabulary, max_concurrency=2),
        provider=ProviderStatus(True, settings.llm_model, datetime.now(tz=UTC), "not probed"),
        access=settings.access_policy(),
        daily_budget=DailyBudget(settings.demo_daily_batches_per_code),
        rate_limiter=None,
    )
    with TestClient(create_app(services)) as started:
        yield started
    store.close()


def guarded_upload(client: TestClient, code: str | None, rows: str = AMETHYST):
    headers = {"x-demo-code": code} if code is not None else {}
    return client.post(
        "/batches",
        files={"file": ("products.csv", csv_text(rows).encode("utf-8"), "text/csv")},
        data={"brand_id": "mindful-souls"},
        headers=headers,
    )


class TestAccessCodes:
    def test_a_known_code_is_accepted(self, guarded_client: TestClient) -> None:
        assert guarded_upload(guarded_client, "a1").status_code == 202

    def test_a_missing_code_is_refused(self, guarded_client: TestClient) -> None:
        response = guarded_upload(guarded_client, None)

        assert response.status_code == 401
        assert "access code" in response.json()["detail"]

    def test_an_unknown_code_is_refused(self, guarded_client: TestClient) -> None:
        assert guarded_upload(guarded_client, "nope").status_code == 401

    def test_reading_a_batch_needs_no_code(self, guarded_client: TestClient) -> None:
        batch_id = guarded_upload(guarded_client, "a1").json()["batch_id"]

        assert guarded_client.get(f"/batches/{batch_id}").status_code == 200

    def test_listing_brands_needs_no_code(self, guarded_client: TestClient) -> None:
        assert guarded_client.get("/brands").status_code == 200


class TestDemoLimits:
    def test_a_file_over_the_row_cap_is_refused(self, guarded_client: TestClient) -> None:
        response = guarded_upload(guarded_client, "a1", f"{AMETHYST}\n{ROSE_QUARTZ}")

        assert response.status_code == 413
        assert "at most 1 rows" in response.json()["detail"]

    def test_the_daily_allowance_runs_out(self, guarded_client: TestClient) -> None:
        for _ in range(2):
            assert guarded_upload(guarded_client, "a1").status_code == 202

        response = guarded_upload(guarded_client, "a1")

        assert response.status_code == 429
        assert "runs for today" in response.json()["detail"]

    def test_each_code_has_its_own_allowance(self, guarded_client: TestClient) -> None:
        for _ in range(2):
            guarded_upload(guarded_client, "a1")

        assert guarded_upload(guarded_client, "b2").status_code == 202


class TestAccessStatus:
    def test_an_open_deployment_needs_no_code(self, client: TestClient) -> None:
        body = client.get("/access").json()

        assert body["required"] is False
        assert body["valid"] is True

    def test_a_known_code_reports_its_runs(self, guarded_client: TestClient) -> None:
        body = guarded_client.get("/access", headers={"x-demo-code": "a1"}).json()

        assert body == {
            "required": True,
            "valid": True,
            "runs_remaining": 2,
            "runs_per_day": 2,
            "max_rows": 1,
        }

    def test_checking_a_code_spends_nothing(self, guarded_client: TestClient) -> None:
        for _ in range(5):
            guarded_client.get("/access", headers={"x-demo-code": "a1"})

        assert guarded_upload(guarded_client, "a1").status_code == 202

    def test_a_spent_run_is_reflected(self, guarded_client: TestClient) -> None:
        guarded_upload(guarded_client, "a1")

        body = guarded_client.get("/access", headers={"x-demo-code": "a1"}).json()

        assert body["runs_remaining"] == 1

    @pytest.mark.parametrize("headers", [{}, {"x-demo-code": "nope"}], ids=["missing", "unknown"])
    def test_a_bad_code_is_reported_without_an_error(
        self, guarded_client: TestClient, headers: dict[str, str]
    ) -> None:
        response = guarded_client.get("/access", headers=headers)

        assert response.status_code == 200
        assert response.json()["valid"] is False
        assert response.json()["runs_remaining"] is None


def test_brands_describe_their_voice(client: TestClient) -> None:
    brands = client.get("/brands").json()

    assert all(brand["voice"] for brand in brands)
    assert all("dont" in brand for brand in brands)
