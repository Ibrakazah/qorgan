"""SQLite persistence for transfers, trusted-contact alerts and analyst decisions (stdlib only).

Records are stored as JSON documents keyed by id: the MVP needs durability and a reset button, not
relational queries. Path: QORGAN_DB (default .data/qorgan.db).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
TABLES = ("transfers", "alerts", "stoplist", "idempotency")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transfers (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stoplist (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS idempotency (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, doc TEXT NOT NULL);
"""


def db_path() -> Path:
    return Path(os.environ.get("QORGAN_DB", ".data/qorgan.db"))


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """One short-lived connection per operation: commit on success, always close."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(_SCHEMA)
        with conn:
            yield conn
    finally:
        conn.close()


def put(table: str, doc_id: str, created_at: str, doc: dict[str, Any]) -> None:
    assert table in TABLES
    with _LOCK, _connect() as conn:
        conn.execute(
            f"INSERT INTO {table} (id, created_at, doc) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET doc = excluded.doc, created_at = excluded.created_at",
            (doc_id, created_at, json.dumps(doc, ensure_ascii=False)),
        )


def get(table: str, doc_id: str) -> dict[str, Any] | None:
    assert table in TABLES
    with _LOCK, _connect() as conn:
        row = conn.execute(f"SELECT doc FROM {table} WHERE id = ?", (doc_id,)).fetchone()
    return json.loads(row[0]) if row else None


def all_docs(table: str) -> list[dict[str, Any]]:
    assert table in TABLES
    with _LOCK, _connect() as conn:
        rows = conn.execute(f"SELECT doc FROM {table} ORDER BY created_at DESC, id DESC").fetchall()
    return [json.loads(r[0]) for r in rows]


def wipe() -> None:
    with _LOCK, _connect() as conn:
        for table in TABLES:
            conn.execute(f"DELETE FROM {table}")
