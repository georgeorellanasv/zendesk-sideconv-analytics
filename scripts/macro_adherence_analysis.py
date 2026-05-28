"""
Macro adherence analysis — Payment Confirmation.

Extrae tickets para todos los delivery methods (bank_deposit, office_pick-up,
mobile_payment, home_delivery) y evalua las 4 condiciones por ticket:
  1. Delivery Method (capturado como columna)
  2. Order Sub-status no contiene "unreliable"
  3. Ticket creado dentro de las 48h desde Transaction Date
  4. Sin side conversations

Adherencia = tag "ria_payment_confirmation_reliable_correspondent_sent" presente.

Usage:
    python -m scripts.macro_adherence_analysis
    python -m scripts.macro_adherence_analysis --days 60
    python -m scripts.macro_adherence_analysis --dm bank_deposit office_pick-up
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.config import REPORTS_DIR
from src.zendesk_client import ZendeskClient

DELIVERY_METHOD_FIELD  = 20723928879889
ORDER_STATUS_FIELD     = 30676401574161
ORDER_SUBSTATUS_FIELD  = 40201614421265
TRANSACTION_DATE_FIELD = 11063635162897
MACRO_TAG = "ria_payment_confirmation_reliable_correspondent_sent"

OUTPUT_CSV = REPORTS_DIR / "macro_adherence_report.csv"


def get_custom_field(ticket: dict, field_id: int) -> str | None:
    for cf in ticket.get("custom_fields", []):
        if cf.get("id") == field_id:
            return cf.get("value")
    return None


def parse_zendesk_datetime(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_date_only(s: str | None) -> datetime | None:
    """YYYY-MM-DD → midnight UTC."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


ALL_DELIVERY_METHODS = [
    "bank_deposit",
    "office_pick-up",
    "mobile_payment",
    "home_delivery",
]


def pull_tickets_for_dm(client: ZendeskClient, dm: str, cutoff: str) -> list[dict]:
    """Dual-query para un delivery method: parte A (con macro) + parte B (sin macro)."""
    base = (
        f"type:ticket "
        f"custom_field_{DELIVERY_METHOD_FIELD}:{dm} "
        f"custom_field_{ORDER_STATUS_FIELD}:paid "
        f"solved>={cutoff}"
    )
    adherent = list(client.search_tickets(f"{base} tags:{MACRO_TAG}"))
    non = [t for t in client.search_tickets(f"{base} status:solved")
           if MACRO_TAG not in t.get("tags", [])]
    seen: set[int] = set()
    combined: list[dict] = []
    for t in adherent + non:
        if t["id"] not in seen:
            seen.add(t["id"])
            combined.append(t)
    return combined


def process_tickets(client: ZendeskClient, tickets: list[dict], dm: str) -> tuple[list[dict], int]:
    rows: list[dict] = []
    sc_errors = 0
    total = len(tickets)
    for i, ticket in enumerate(tickets, 1):
        if i % 100 == 0:
            print(f"    {i}/{total}...")
        tid = ticket["id"]
        tags = ticket.get("tags", [])
        created_at = parse_zendesk_datetime(ticket.get("created_at"))

        sub_status_raw       = get_custom_field(ticket, ORDER_SUBSTATUS_FIELD) or ""
        transaction_date_raw = get_custom_field(ticket, TRANSACTION_DATE_FIELD)
        transaction_date     = parse_date_only(transaction_date_raw)
        order_status_raw     = get_custom_field(ticket, ORDER_STATUS_FIELD) or ""

        macro_applied = MACRO_TAG in tags
        cond_substatus = "unreliable" not in sub_status_raw.lower()

        hours_diff = None
        cond_48h = False
        if created_at and transaction_date:
            hours_diff = (created_at - transaction_date).total_seconds() / 3600
            cond_48h = 0 <= hours_diff <= 48

        cond_no_sc = None
        sc_count = None
        try:
            sc_count = len(client.get_side_conversations(tid))
            cond_no_sc = sc_count == 0
        except Exception:
            sc_errors += 1

        eligible_no_sc    = cond_substatus and cond_48h
        eligible_confirmed = eligible_no_sc and (cond_no_sc is True)
        in_adherence       = eligible_confirmed and macro_applied

        rows.append({
            "ticket_id":          tid,
            "delivery_method":    dm,
            "created_at":         ticket.get("created_at", ""),
            "order_status":       order_status_raw,
            "transaction_date":   transaction_date_raw or "",
            "hours_from_order":   round(hours_diff, 1) if hours_diff is not None else "",
            "sub_status":         sub_status_raw,
            "cond_substatus":     cond_substatus,
            "cond_48h":           cond_48h,
            "sc_count":           sc_count if sc_count is not None else "error",
            "cond_no_sc":         cond_no_sc,
            "eligible_no_sc":     eligible_no_sc,
            "eligible_confirmed": eligible_confirmed,
            "tags":               "|".join(sorted(tags)),
            "macro_applied":      macro_applied,
            "in_adherence":       in_adherence,
        })
    return rows, sc_errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dm", nargs="+", default=ALL_DELIVERY_METHODS,
                        help="Delivery methods a procesar (default: todos)")
    args = parser.parse_args()

    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
    client = ZendeskClient()

    all_rows: list[dict] = []
    total_sc_errors = 0

    for dm in args.dm:
        print(f"\n[{dm}] Extrayendo tickets (solved >= {cutoff})...")
        tickets = pull_tickets_for_dm(client, dm, cutoff)
        print(f"  {len(tickets)} tickets")
        if not tickets:
            continue
        rows, sc_errors = process_tickets(client, tickets, dm)
        all_rows.extend(rows)
        total_sc_errors += sc_errors
        print(f"  SC errors: {sc_errors}")

    total = len(all_rows)
    if not total:
        print("Sin resultados.")
        sys.exit(0)

    # ── Stats globales ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  ADHERENCIA GLOBAL  ({', '.join(args.dm)})")
    print(f"  Periodo: ultimos {args.days} dias  |  Corte: {cutoff}")
    print(f"{'='*60}")
    print(f"  Total tickets:                     {total:>5}")
    print(f"  Errors SC (excluidos de F1):       {total_sc_errors:>5}")

    for dm in args.dm:
        dm_rows = [r for r in all_rows if r["delivery_method"] == dm]
        eligible = [r for r in dm_rows if r["eligible_confirmed"]]
        adherent = [r for r in dm_rows if r["in_adherence"]]
        pct = f"{len(adherent)/len(eligible)*100:.1f}%" if eligible else "N/A"
        print(f"  {dm:<20} {len(dm_rows):>5} tickets | "
              f"{len(eligible):>4} elegibles F1 | {len(adherent):>4} adherentes ({pct})")
    print(f"{'='*60}")

    # ── CSV ────────────────────────────────────────────────────────────────
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"\n  CSV guardado: {OUTPUT_CSV}  ({total} filas)")


if __name__ == "__main__":
    main()
