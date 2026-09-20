"""SQLite persistence for batches, items and cached generations.

Queryable facts live in columns; the validated object itself is stored as JSON and
re-validated on the way out, so the database is treated as another untrusted boundary.
"""

import sqlite3
import threading
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from list_forge.models import Batch, Generation, Item, ProductFacts, Status

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id           TEXT PRIMARY KEY,
    brand_id     TEXT NOT NULL,
    source_name  TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS items (
    id          TEXT PRIMARY KEY,
    batch_id    TEXT NOT NULL REFERENCES batches(id),
    row_number  INTEGER NOT NULL,
    sku         TEXT NOT NULL,
    status      TEXT NOT NULL,
    document    TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS items_by_batch ON items (batch_id, row_number);

CREATE TABLE IF NOT EXISTS generations (
    key                TEXT PRIMARY KEY,
    document           TEXT NOT NULL,
    model              TEXT NOT NULL,
    prompt_version     TEXT NOT NULL,
    prompt_fingerprint TEXT NOT NULL,
    created_at         TEXT NOT NULL
);
"""

INTERRUPTED = "interrupted by a restart"


class Store:
    """Every call here is a short synchronous query: microseconds, not milliseconds."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._write() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.executescript(SCHEMA)

    def close(self) -> None:
        self._connection.close()

    def create_batch(self, batch: Batch, items: Sequence[Item]) -> None:
        with self._write() as connection:
            connection.execute(
                "INSERT INTO batches (id, brand_id, source_name, created_at) VALUES (?, ?, ?, ?)",
                (batch.id, batch.brand_id, batch.source_name, batch.created_at.isoformat()),
            )
            connection.executemany(
                "INSERT INTO items (id, batch_id, row_number, sku, status, document, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [self._item_row(item) for item in items],
            )

    def start_batch(
        self, brand_id: str, source_name: str, products: Sequence[ProductFacts]
    ) -> tuple[Batch, list[Item]]:
        """Records a batch and one pending item per product, so progress is visible at once."""
        batch = Batch(id=uuid4().hex, brand_id=brand_id, source_name=source_name)
        items = [
            Item(
                id=uuid4().hex,
                batch_id=batch.id,
                row_number=row_number,
                facts=facts,
                status=Status.PENDING,
            )
            for row_number, facts in enumerate(products, start=1)
        ]
        self.create_batch(batch, items)
        return batch, items

    def save_item(self, item: Item) -> None:
        with self._write() as connection:
            connection.execute(
                "INSERT INTO items (id, batch_id, row_number, sku, status, document, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET status = excluded.status,"
                " document = excluded.document, updated_at = excluded.updated_at",
                self._item_row(item),
            )

    def get_batch(self, batch_id: str) -> Batch | None:
        row = self._connection.execute(
            "SELECT id, brand_id, source_name, created_at FROM batches WHERE id = ?", (batch_id,)
        ).fetchone()
        return Batch.model_validate(dict(row)) if row else None

    def list_items(self, batch_id: str) -> list[Item]:
        rows = self._connection.execute(
            "SELECT document FROM items WHERE batch_id = ? ORDER BY row_number", (batch_id,)
        ).fetchall()
        return [Item.model_validate_json(row["document"]) for row in rows]

    def get_item(self, item_id: str) -> Item | None:
        row = self._connection.execute(
            "SELECT document FROM items WHERE id = ?", (item_id,)
        ).fetchone()
        return Item.model_validate_json(row["document"]) if row else None

    def mark_interrupted(self) -> int:
        """Work in flight does not survive a restart, so stale rows are failed at startup."""
        items = [
            Item.model_validate_json(row["document"])
            for row in self._connection.execute(
                "SELECT document FROM items WHERE status IN (?, ?)",
                (Status.PENDING.value, Status.PROCESSING.value),
            ).fetchall()
        ]
        for item in items:
            self.save_item(item.model_copy(update={"status": Status.FAILED, "error": INTERRUPTED}))
        return len(items)

    def cached_generation(self, key: str) -> Generation | None:
        row = self._connection.execute(
            "SELECT document FROM generations WHERE key = ?", (key,)
        ).fetchone()
        return Generation.model_validate_json(row["document"]) if row else None

    def store_generation(
        self, key: str, generation: Generation, *, model: str, version: str, fingerprint: str
    ) -> None:
        with self._write() as connection:
            connection.execute(
                "INSERT INTO generations"
                " (key, document, model, prompt_version, prompt_fingerprint, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET document = excluded.document,"
                " created_at = excluded.created_at",
                (
                    key,
                    generation.model_dump_json(),
                    model,
                    version,
                    fingerprint,
                    datetime.now(tz=UTC).isoformat(),
                ),
            )

    def _item_row(self, item: Item) -> tuple[str, str, int, str, str, str, str]:
        return (
            item.id,
            item.batch_id,
            item.row_number,
            item.facts.sku,
            item.status.value,
            item.model_dump_json(),
            datetime.now(tz=UTC).isoformat(),
        )

    def _write(self) -> "_Transaction":
        return _Transaction(self._connection, self._lock)


class _Transaction:
    """One writer at a time, committed on the way out, rolled back on an error."""

    def __init__(self, connection: sqlite3.Connection, lock: threading.Lock) -> None:
        self._connection = connection
        self._lock = lock

    def __enter__(self) -> sqlite3.Connection:
        self._lock.acquire()
        return self._connection

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        try:
            if exc_type is None:
                self._connection.commit()
            else:
                self._connection.rollback()
        finally:
            self._lock.release()
