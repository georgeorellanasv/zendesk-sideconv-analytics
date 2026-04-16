"""
Database module — SQLite schema creation and upsert helpers.

Tables:
  tickets                  — one row per Zendesk ticket
  side_conversations       — one row per side conversation
  side_conversation_events — one row per event within a side conversation
  extraction_log           — one row per extraction run
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

from src.config import DB_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id           INTEGER PRIMARY KEY,
    subject             TEXT,
    status              TEXT,
    created_at          TEXT,
    updated_at          TEXT,
    group_id            INTEGER,
    assignee_id         INTEGER,
    reason_raw          TEXT,
    correspondent_raw   TEXT,
    country_raw         TEXT,
    product_raw         TEXT,
    side_conv_count     INTEGER DEFAULT 0,
    extracted_at        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS side_conversations (
    side_conv_id            TEXT PRIMARY KEY,
    ticket_id               INTEGER NOT NULL REFERENCES tickets(ticket_id),
    subject                 TEXT,
    state                   TEXT,
    created_at              TEXT,
    updated_at              TEXT,
    participant_count       INTEGER DEFAULT 0,
    sc_sequence             INTEGER,
    sc_direction            TEXT,
    sc_recipient_type       TEXT,
    sc_reason_classification TEXT,
    sc_reason_confidence    TEXT,
    external_reply_at           TEXT,
    external_response_hrs       REAL,
    last_counterparty_reply_at  TEXT,
    resolution_hrs              REAL,
    total_exchanges             INTEGER,
    extracted_at                TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS side_conversation_events (
    event_id        TEXT PRIMARY KEY,
    side_conv_id    TEXT NOT NULL REFERENCES side_conversations(side_conv_id),
    ticket_id       INTEGER NOT NULL,
    event_sequence  INTEGER,
    event_type      TEXT,
    created_at      TEXT,
    actor_id        TEXT,
    actor_name      TEXT,
    actor_email     TEXT,
    from_address    TEXT,
    to_addresses    TEXT,
    message_subject TEXT,
    message_body    TEXT,
    extracted_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS extraction_log (
    run_id              TEXT PRIMARY KEY,
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    last_days           INTEGER,
    tickets_processed   INTEGER DEFAULT 0,
    side_convs_found    INTEGER DEFAULT 0,
    events_found        INTEGER DEFAULT 0,
    errors              INTEGER DEFAULT 0,
    status              TEXT DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS idx_sc_ticket ON side_conversations(ticket_id);
CREATE INDEX IF NOT EXISTS idx_sce_side_conv ON side_conversation_events(side_conv_id);
CREATE INDEX IF NOT EXISTS idx_sce_ticket ON side_conversation_events(ticket_id);
"""


# ---------------------------------------------------------------------------
# Connection context manager
# ---------------------------------------------------------------------------

@contextmanager
def get_conn(db_path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with WAL mode and foreign keys enabled."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DB_PATH) -> None:
    """Create all tables and indexes if they don't exist."""
    with get_conn(db_path) as conn:
        conn.executescript(_DDL)
    logger.info("Database initialized at %s", db_path)


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------

def upsert_ticket(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO tickets (
            ticket_id, subject, status, created_at, updated_at,
            group_id, assignee_id, reason_raw, correspondent_raw,
            country_raw, product_raw, side_conv_count, extracted_at
        ) VALUES (
            :ticket_id, :subject, :status, :created_at, :updated_at,
            :group_id, :assignee_id, :reason_raw, :correspondent_raw,
            :country_raw, :product_raw, :side_conv_count, :extracted_at
        )
        ON CONFLICT(ticket_id) DO UPDATE SET
            subject           = excluded.subject,
            status            = excluded.status,
            updated_at        = excluded.updated_at,
            group_id          = excluded.group_id,
            assignee_id       = excluded.assignee_id,
            reason_raw        = excluded.reason_raw,
            correspondent_raw = excluded.correspondent_raw,
            country_raw       = excluded.country_raw,
            product_raw       = excluded.product_raw,
            side_conv_count   = excluded.side_conv_count,
            extracted_at      = excluded.extracted_at
        """,
        row,
    )


def upsert_side_conversation(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO side_conversations (
            side_conv_id, ticket_id, subject, state, created_at, updated_at,
            participant_count, sc_direction, sc_recipient_type,
            sc_reason_classification, sc_reason_confidence, extracted_at
        ) VALUES (
            :side_conv_id, :ticket_id, :subject, :state, :created_at, :updated_at,
            :participant_count, :sc_direction, :sc_recipient_type,
            :sc_reason_classification, :sc_reason_confidence, :extracted_at
        )
        ON CONFLICT(side_conv_id) DO UPDATE SET
            state                    = excluded.state,
            updated_at               = excluded.updated_at,
            participant_count        = excluded.participant_count,
            sc_direction             = excluded.sc_direction,
            sc_recipient_type        = excluded.sc_recipient_type,
            sc_reason_classification = excluded.sc_reason_classification,
            sc_reason_confidence     = excluded.sc_reason_confidence,
            extracted_at             = excluded.extracted_at
        """,
        row,
    )


def upsert_event(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    conn.execute(
        """
        INSERT INTO side_conversation_events (
            event_id, side_conv_id, ticket_id, event_type, created_at,
            actor_id, actor_name, actor_email, from_address, to_addresses,
            message_subject, message_body, extracted_at
        ) VALUES (
            :event_id, :side_conv_id, :ticket_id, :event_type, :created_at,
            :actor_id, :actor_name, :actor_email, :from_address, :to_addresses,
            :message_subject, :message_body, :extracted_at
        )
        ON CONFLICT(event_id) DO NOTHING
        """,
        row,
    )


def update_extraction_log(
    conn: sqlite3.Connection,
    run_id: str,
    **kwargs: Any,
) -> None:
    """Update any columns in extraction_log for the given run_id."""
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = :{k}" for k in kwargs)
    conn.execute(
        f"UPDATE extraction_log SET {set_clause} WHERE run_id = :run_id",
        {"run_id": run_id, **kwargs},
    )


def serialize_to_addresses(to_field: Any) -> str:
    """Convert a list/dict of 'to' addresses to a compact JSON string."""
    if not to_field:
        return ""
    if isinstance(to_field, str):
        return to_field
    return json.dumps(to_field, ensure_ascii=False)
