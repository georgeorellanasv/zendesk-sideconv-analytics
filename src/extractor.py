"""
Fase 3 — Extractor principal.

Recorre los tickets de la vista US Care actualizados en los últimos N días,
extrae sus side conversations y eventos, y los persiste en SQLite.

Usage (desde el root del proyecto, con el venv activo):
    python -m src.extractor --last-days 7
    python -m src.extractor --last-days 2 --dry-run
"""

import argparse
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from src.config import (
    DB_PATH,
    FIELD_ID_CORRESPONDENT,
    FIELD_ID_COUNTRY,
    FIELD_ID_PRODUCT,
    FIELD_ID_REASON_FOR_CONTACT,
    LOG_PATH,
    VIEW_ID_US_CARE,
)
from src.db import (
    get_conn,
    init_db,
    serialize_to_addresses,
    update_extraction_log,
    upsert_event,
    upsert_side_conversation,
    upsert_ticket,
)
from src.zendesk_client import ZendeskClient

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

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
# Helpers — parse Zendesk shapes
# ---------------------------------------------------------------------------

def _get_custom_field(ticket: dict[str, Any], field_id: str) -> str:
    """Return the value of a custom field by its string ID, or empty string."""
    if not field_id:
        return ""
    fid = int(field_id)
    for cf in ticket.get("custom_fields", []):
        if cf.get("id") == fid:
            return cf.get("value") or ""
    return ""


def _parse_ticket(ticket: dict[str, Any], extracted_at: str) -> dict[str, Any]:
    return {
        "ticket_id": ticket["id"],
        "subject": ticket.get("subject", ""),
        "status": ticket.get("status", ""),
        "created_at": ticket.get("created_at", ""),
        "updated_at": ticket.get("updated_at", ""),
        "group_id": ticket.get("group_id"),
        "assignee_id": ticket.get("assignee_id"),
        "reason_raw": _get_custom_field(ticket, FIELD_ID_REASON_FOR_CONTACT),
        "correspondent_raw": _get_custom_field(ticket, FIELD_ID_CORRESPONDENT),
        "country_raw": _get_custom_field(ticket, FIELD_ID_COUNTRY),
        "product_raw": _get_custom_field(ticket, FIELD_ID_PRODUCT),
        "side_conv_count": 0,  # updated later
        "extracted_at": extracted_at,
    }


def _parse_side_conversation(
    sc: dict[str, Any], ticket_id: int, extracted_at: str
) -> dict[str, Any]:
    participants = sc.get("participants", [])
    return {
        "side_conv_id": sc["id"],
        "ticket_id": ticket_id,
        "subject": sc.get("subject", ""),
        "state": sc.get("state", ""),
        "created_at": sc.get("created_at", ""),
        "updated_at": sc.get("updated_at", ""),
        "participant_count": len(participants),
        "sc_direction": None,          # clasificación diferida (Fase 4)
        "sc_reason_classification": None,
        "sc_reason_confidence": None,
        "extracted_at": extracted_at,
    }


def _parse_event(
    event: dict[str, Any],
    side_conv_id: str,
    ticket_id: int,
    extracted_at: str,
) -> dict[str, Any]:
    message = event.get("message") or {}
    actor = event.get("actor") or {}

    # from puede ser str o dict {"email": ..., "name": ...}
    from_raw = message.get("from", "")
    if isinstance(from_raw, dict):
        from_address = from_raw.get("email", "")
    else:
        from_address = str(from_raw)

    return {
        "event_id": event["id"],
        "side_conv_id": side_conv_id,
        "ticket_id": ticket_id,
        "event_type": event.get("type", ""),
        "created_at": event.get("created_at", ""),
        "actor_id": str(actor.get("id", "")),
        "actor_name": actor.get("name", ""),
        "actor_email": actor.get("email", ""),
        "from_address": from_address,
        "to_addresses": serialize_to_addresses(message.get("to")),
        "message_subject": message.get("subject", ""),
        "message_body": (message.get("body") or "")[:2000],  # truncar a 2k chars
        "extracted_at": extracted_at,
    }


# ---------------------------------------------------------------------------
# Cutoff filter
# ---------------------------------------------------------------------------

def _cutoff_dt(last_days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=last_days)


def _ticket_updated_after(ticket: dict[str, Any], cutoff: datetime) -> bool:
    updated_at_str = ticket.get("updated_at", "")
    if not updated_at_str:
        return True
    try:
        dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
        return dt >= cutoff
    except ValueError:
        return True


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def run_extraction(last_days: int, dry_run: bool = False) -> None:
    if not VIEW_ID_US_CARE:
        logger.error("VIEW_ID_US_CARE no está configurado en el .env")
        sys.exit(1)

    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    extracted_at = started_at
    cutoff = _cutoff_dt(last_days)

    logger.info("=" * 60)
    logger.info("Extracción iniciada  run_id=%s", run_id)
    logger.info("  Vista    : US Care (ID %s)", VIEW_ID_US_CARE)
    logger.info("  Filtro   : updated_at >= %s  (last %d days)", cutoff.date(), last_days)
    logger.info("  Dry-run  : %s", dry_run)
    logger.info("  DB       : %s", DB_PATH)
    logger.info("=" * 60)

    if not dry_run:
        init_db()

    client = ZendeskClient()

    # Registrar inicio en log
    if not dry_run:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO extraction_log
                   (run_id, started_at, last_days, status)
                   VALUES (?, ?, ?, 'running')""",
                (run_id, started_at, last_days),
            )

    tickets_processed = 0
    side_convs_found = 0
    events_found = 0
    errors = 0

    try:
        for ticket in client.get_view_tickets(VIEW_ID_US_CARE):
            if not _ticket_updated_after(ticket, cutoff):
                continue

            ticket_id = ticket["id"]
            ticket_row = _parse_ticket(ticket, extracted_at)

            try:
                side_convs = client.get_side_conversations(ticket_id)
            except Exception as exc:
                logger.warning("Error obteniendo side convs del ticket %s: %s", ticket_id, exc)
                errors += 1
                side_convs = []

            ticket_row["side_conv_count"] = len(side_convs)

            if dry_run:
                logger.info(
                    "  [DRY] ticket=%s  status=%s  side_convs=%d  reason=%s",
                    ticket_id,
                    ticket_row["status"],
                    len(side_convs),
                    ticket_row["reason_raw"] or "(vacío)",
                )
            else:
                with get_conn() as conn:
                    upsert_ticket(conn, ticket_row)

            for sc in side_convs:
                sc_id = sc["id"]
                sc_row = _parse_side_conversation(sc, ticket_id, extracted_at)

                try:
                    events = client.get_side_conversation_events(ticket_id, sc_id)
                except Exception as exc:
                    logger.warning(
                        "Error obteniendo events  ticket=%s sc=%s: %s", ticket_id, sc_id, exc
                    )
                    errors += 1
                    events = []

                if dry_run:
                    logger.info(
                        "    [DRY] sc=%s  state=%s  subj=%r  events=%d",
                        sc_id,
                        sc_row["state"],
                        (sc_row["subject"] or "")[:60],
                        len(events),
                    )
                else:
                    with get_conn() as conn:
                        upsert_side_conversation(conn, sc_row)
                        for event in events:
                            event_row = _parse_event(event, sc_id, ticket_id, extracted_at)
                            upsert_event(conn, event_row)

                side_convs_found += 1
                events_found += len(events)

            tickets_processed += 1

    except KeyboardInterrupt:
        logger.warning("Extracción interrumpida por el usuario.")
        if not dry_run:
            with get_conn() as conn:
                update_extraction_log(
                    conn, run_id,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    tickets_processed=tickets_processed,
                    side_convs_found=side_convs_found,
                    events_found=events_found,
                    errors=errors,
                    status="interrupted",
                )
        sys.exit(0)

    except Exception as exc:
        logger.exception("Error fatal durante la extracción: %s", exc)
        errors += 1
        if not dry_run:
            with get_conn() as conn:
                update_extraction_log(
                    conn, run_id,
                    finished_at=datetime.now(timezone.utc).isoformat(),
                    tickets_processed=tickets_processed,
                    side_convs_found=side_convs_found,
                    events_found=events_found,
                    errors=errors,
                    status="failed",
                )
        sys.exit(1)

    finished_at = datetime.now(timezone.utc).isoformat()

    logger.info("-" * 60)
    logger.info("Extracción completada")
    logger.info("  Tickets procesados : %d", tickets_processed)
    logger.info("  Side convs         : %d", side_convs_found)
    logger.info("  Eventos            : %d", events_found)
    logger.info("  Errores            : %d", errors)
    if dry_run:
        logger.info("  (dry-run: nada fue escrito a la DB)")
    logger.info("-" * 60)

    if not dry_run:
        with get_conn() as conn:
            update_extraction_log(
                conn, run_id,
                finished_at=finished_at,
                tickets_processed=tickets_processed,
                side_convs_found=side_convs_found,
                events_found=events_found,
                errors=errors,
                status="success",
            )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrae tickets y side conversations de la vista US Care de Zendesk."
    )
    parser.add_argument(
        "--last-days",
        type=int,
        default=7,
        metavar="N",
        help="Extraer tickets actualizados en los últimos N días (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostrar qué se extraería sin escribir a la base de datos",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_extraction(last_days=args.last_days, dry_run=args.dry_run)
