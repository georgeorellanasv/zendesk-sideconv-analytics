"""
Fase 3.5 — Enricher via ticket audits.

Para cada ticket en la DB, trae sus audits de Zendesk y reconstruye el
historial del campo "Reason for Contact". Escribe:

  tickets.reason_initial        — primer valor que tuvo el campo
  tickets.reason_last           — valor actual / más reciente
  tickets.reason_changes_count  — cuántas veces cambió
  tickets.reason_history        — JSON array completo del timeline

Consumo de API: 1 call por ticket (+ pagination si hay >100 audits).
El rate limiter en ZendeskClient mantiene ≤180 req/min.

Usage:
    python -m src.enricher                     # todos los tickets
    python -m src.enricher --last-days 7       # solo tickets actualizados en 7 días
    python -m src.enricher --ticket-id 12345   # solo un ticket específico
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import FIELD_ID_REASON_FOR_CONTACT, LOG_PATH
from src.db import get_conn
from src.zendesk_client import ZendeskClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Audit parsing
# ---------------------------------------------------------------------------

def _extract_reason_changes(audits: list[dict[str, Any]], field_id: str) -> list[dict[str, Any]]:
    """
    Parse audit events and return reason field changes in chronological order.

    Each returned item: {"at": iso_timestamp, "from": old_value, "to": new_value}

    Audit event shape (change):
        {
            "type": "Change",
            "field_name": "custom_fields_XXXXXXX",
            "previous_value": "...",
            "value": "..."
        }

    Audit event shape (create — ticket created with initial value):
        {
            "type": "Create",
            "field_name": "custom_fields_XXXXXXX",
            "value": "..."
        }
    """
    target_field = f"custom_fields_{field_id}"
    changes: list[dict[str, Any]] = []

    for audit in audits:
        audit_at = audit.get("created_at")
        for event in audit.get("events", []):
            evt_type = event.get("type", "").lower()
            field_name = event.get("field_name", "")

            if field_name != target_field:
                continue

            if evt_type == "create":
                changes.append({
                    "at": audit_at,
                    "from": None,
                    "to": event.get("value"),
                })
            elif evt_type == "change":
                changes.append({
                    "at": audit_at,
                    "from": event.get("previous_value"),
                    "to": event.get("value"),
                })

    # Sort chronologically just in case
    changes.sort(key=lambda c: c.get("at") or "")
    return changes


def _summarize_changes(changes: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Given the full timeline, derive:
      reason_initial        — first 'to' value
      reason_last           — last 'to' value
      reason_changes_count  — number of change events (excluding initial set)
      reason_history        — JSON string of the timeline
    """
    if not changes:
        return {
            "reason_initial": None,
            "reason_last": None,
            "reason_changes_count": 0,
            "reason_history": json.dumps([], ensure_ascii=False),
        }

    initial = changes[0].get("to")
    last = changes[-1].get("to")
    # Don't count the initial "from None -> X" as a change
    change_count = sum(1 for c in changes if c.get("from") is not None)

    return {
        "reason_initial": initial,
        "reason_last": last,
        "reason_changes_count": change_count,
        "reason_history": json.dumps(changes, ensure_ascii=False),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_enrichment(last_days: int | None = None, ticket_id: int | None = None) -> None:
    if not FIELD_ID_REASON_FOR_CONTACT:
        logger.error("FIELD_ID_REASON_FOR_CONTACT no está configurado en el .env")
        sys.exit(1)

    # Select which tickets to enrich
    with get_conn() as conn:
        if ticket_id is not None:
            rows = conn.execute(
                "SELECT ticket_id FROM tickets WHERE ticket_id = ?", (ticket_id,)
            ).fetchall()
        elif last_days is not None:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=last_days)).isoformat()
            rows = conn.execute(
                "SELECT ticket_id FROM tickets WHERE updated_at >= ? ORDER BY ticket_id",
                (cutoff,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT ticket_id FROM tickets ORDER BY ticket_id").fetchall()

    ticket_ids = [r["ticket_id"] for r in rows]

    logger.info("=" * 60)
    logger.info("Enrichment iniciado (reason history via audits)")
    logger.info("  Tickets a procesar : %d", len(ticket_ids))
    logger.info("  Field ID           : %s", FIELD_ID_REASON_FOR_CONTACT)
    logger.info("=" * 60)

    client = ZendeskClient()
    processed = 0
    errors = 0

    for tid in ticket_ids:
        try:
            audits = client.get_ticket_audits(tid)
        except Exception as exc:
            logger.warning("Error obteniendo audits del ticket %s: %s", tid, exc)
            errors += 1
            continue

        changes = _extract_reason_changes(audits, FIELD_ID_REASON_FOR_CONTACT)
        summary = _summarize_changes(changes)

        with get_conn() as conn:
            conn.execute(
                """
                UPDATE tickets
                SET reason_initial        = :reason_initial,
                    reason_last           = :reason_last,
                    reason_changes_count  = :reason_changes_count,
                    reason_history        = :reason_history
                WHERE ticket_id = :ticket_id
                """,
                {**summary, "ticket_id": tid},
            )

        processed += 1
        if processed % 50 == 0:
            logger.info("  ... %d/%d procesados", processed, len(ticket_ids))

    logger.info("-" * 60)
    logger.info("Enrichment completado")
    logger.info("  Procesados : %d", processed)
    logger.info("  Errores    : %d", errors)

    # Stats
    with get_conn() as conn:
        stats = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN reason_changes_count > 0 THEN 1 ELSE 0 END) AS with_changes,
                MAX(reason_changes_count) AS max_changes,
                AVG(reason_changes_count) AS avg_changes
            FROM tickets
            """
        ).fetchone()
    logger.info("  Tickets con reason cambiada: %d de %d", stats["with_changes"], stats["total"])
    logger.info("  Cambios max/avg: %d / %.2f", stats["max_changes"] or 0, stats["avg_changes"] or 0)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrich tickets with reason-change history via Zendesk audits."
    )
    parser.add_argument(
        "--last-days", type=int, default=None,
        help="Solo procesar tickets actualizados en los últimos N días (default: todos)",
    )
    parser.add_argument(
        "--ticket-id", type=int, default=None,
        help="Procesar solo un ticket específico (override de --last-days)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_enrichment(last_days=args.last_days, ticket_id=args.ticket_id)
