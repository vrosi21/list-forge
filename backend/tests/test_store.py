from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fakes import VALID_COPY, sample_facts, sample_params
from list_forge.models import Batch, GeneratedCopy, Generation, RunKind, Status, TokenUsage
from list_forge.store import INTERRUPTED, Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    opened = Store(tmp_path / "listforge.db")
    yield opened
    opened.close()


def generation() -> Generation:
    return Generation(
        output=GeneratedCopy.model_validate(VALID_COPY),
        usage=TokenUsage(prompt_tokens=120, completion_tokens=80),
    )


class TestBatches:
    def test_a_started_batch_has_one_pending_item_per_product(self, store: Store) -> None:
        batch, items = store.start_batch("mindful-souls", "products.csv", [sample_facts()] * 3)

        assert isinstance(batch, Batch)
        assert [item.status for item in store.list_items(batch.id)] == [Status.PENDING] * 3
        assert [item.row_number for item in items] == [1, 2, 3]

    def test_items_come_back_in_row_order(self, store: Store) -> None:
        batch, _ = store.start_batch(
            "mindful-souls", "products.csv", [sample_facts(sku=f"MS-{n}") for n in range(5)]
        )

        assert [item.facts.sku for item in store.list_items(batch.id)] == [
            f"MS-{n}" for n in range(5)
        ]

    def test_saving_an_item_replaces_the_stored_one(self, store: Store) -> None:
        batch, items = store.start_batch("mindful-souls", "products.csv", [sample_facts()])
        done = items[0].model_copy(update={"status": Status.APPROVED})

        store.save_item(done)

        assert store.get_item(items[0].id).status is Status.APPROVED
        assert len(store.list_items(batch.id)) == 1

    def test_an_item_survives_the_round_trip_with_its_types(self, store: Store) -> None:
        _, items = store.start_batch("mindful-souls", "products.csv", [sample_facts(pieces="7")])

        stored = store.get_item(items[0].id)

        assert stored is not None
        assert stored.facts.pieces == 7
        assert stored.status is Status.PENDING

    def test_unknown_ids_read_as_missing(self, store: Store) -> None:
        assert store.get_batch("nope") is None
        assert store.get_item("nope") is None
        assert store.list_items("nope") == []


class TestRestartRecovery:
    def test_work_left_in_flight_is_failed_at_startup(self, store: Store) -> None:
        batch, _ = store.start_batch("mindful-souls", "products.csv", [sample_facts()] * 2)

        assert store.mark_interrupted() == 2
        items = store.list_items(batch.id)
        assert [item.status for item in items] == [Status.FAILED] * 2
        assert items[0].error == INTERRUPTED

    def test_finished_work_is_left_alone(self, store: Store) -> None:
        batch, items = store.start_batch("mindful-souls", "products.csv", [sample_facts()])
        store.save_item(items[0].model_copy(update={"status": Status.APPROVED}))

        assert store.mark_interrupted() == 0
        assert store.list_items(batch.id)[0].status is Status.APPROVED


class TestGenerations:
    def test_a_stored_generation_comes_back_whole(self, store: Store) -> None:
        store.store_generation(
            "key-1", generation(), model="m", version="copy-v1", fingerprint="abc123"
        )

        stored = store.cached_generation("key-1")

        assert stored is not None
        assert stored.output.title == VALID_COPY["title"]
        assert stored.usage.prompt_tokens == 120

    def test_an_unknown_key_is_a_miss(self, store: Store) -> None:
        assert store.cached_generation("key-2") is None

    def test_storing_the_same_key_twice_keeps_the_newer_answer(self, store: Store) -> None:
        store.store_generation(
            "key-3", generation(), model="m", version="copy-v1", fingerprint="abc123"
        )
        replacement = generation().model_copy(update={"attempts": 3})

        store.store_generation(
            "key-3", replacement, model="m", version="copy-v1", fingerprint="abc123"
        )

        assert store.cached_generation("key-3").attempts == 3


def test_a_second_store_reads_what_the_first_one_wrote(tmp_path: Path) -> None:
    path = tmp_path / "listforge.db"
    first = Store(path)
    batch, _ = first.start_batch("mindful-souls", "products.csv", [sample_facts()])
    first.store_generation(
        "key", generation(), model=sample_params().model, version="copy-v1", fingerprint="abc123"
    )
    first.close()

    second = Store(path)
    try:
        assert second.get_batch(batch.id) is not None
        assert second.cached_generation("key") is not None
    finally:
        second.close()


NOW = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


class TestRunLog:
    def test_nothing_recorded_means_no_usage(self, store: Store) -> None:
        assert store.usage_by_label() == []

    def test_runs_are_counted_per_code_and_kind(self, store: Store) -> None:
        store.record_run("alice", RunKind.BATCH, "b1", 5, at=NOW)
        store.record_run("alice", RunKind.BATCH, "b2", 3, at=NOW + timedelta(minutes=1))
        store.record_run("alice", RunKind.REGENERATE, "i1", 1, at=NOW + timedelta(minutes=2))
        store.record_run("bob", RunKind.BATCH, "b3", 2, at=NOW)

        usage = {summary.label: summary for summary in store.usage_by_label()}

        assert (usage["alice"].batches, usage["alice"].regenerations) == (2, 1)
        assert usage["alice"].products == 9
        assert usage["alice"].last_run_at == NOW + timedelta(minutes=2)
        assert (usage["bob"].batches, usage["bob"].regenerations, usage["bob"].products) == (
            1,
            0,
            2,
        )

    def test_the_most_recently_active_code_comes_first(self, store: Store) -> None:
        store.record_run("alice", RunKind.BATCH, "b1", 1, at=NOW)
        store.record_run("bob", RunKind.BATCH, "b2", 1, at=NOW + timedelta(hours=1))

        assert [summary.label for summary in store.usage_by_label()] == ["bob", "alice"]

    @pytest.mark.parametrize(
        ("since", "expected"),
        [
            (None, 2),
            (NOW - timedelta(days=1), 1),
            (NOW + timedelta(days=1), 0),
        ],
    )
    def test_a_start_date_leaves_older_runs_out(
        self, store: Store, since: datetime | None, expected: int
    ) -> None:
        store.record_run("alice", RunKind.BATCH, "old", 1, at=NOW - timedelta(days=30))
        store.record_run("alice", RunKind.BATCH, "new", 1, at=NOW)

        batches = sum(summary.batches for summary in store.usage_by_label(since))

        assert batches == expected

    def test_the_log_survives_a_restart(self, tmp_path: Path) -> None:
        path = tmp_path / "runs.db"
        first = Store(path)
        first.record_run("alice", RunKind.BATCH, "b1", 1, at=NOW)
        first.close()

        second = Store(path)
        try:
            assert [summary.label for summary in second.usage_by_label()] == ["alice"]
        finally:
            second.close()
