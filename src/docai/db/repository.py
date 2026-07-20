"""SQLite persistence — zero-setup for MVP, swap for Postgres later."""
import json
import os
import sqlite3
from datetime import datetime, timezone

from docai.models.schemas import ExtractionResult, Invoice

DB_PATH = os.getenv("DOCAI_DB", "docai.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    filename TEXT,
    model_used TEXT,
    latency_ms INTEGER,
    n_issues INTEGER,
    invoice_json TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_SCHEMA)
    return conn


def save(result: ExtractionResult, filename: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO extractions (created_at, filename, model_used, latency_ms, n_issues, invoice_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                filename,
                result.model_used,
                result.latency_ms,
                len(result.issues),
                result.invoice.model_dump_json(),
            ),
        )
        return cur.lastrowid


def list_invoices(limit: int = 200) -> list[Invoice]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT invoice_json FROM extractions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [Invoice.model_validate(json.loads(r[0])) for r in rows]
