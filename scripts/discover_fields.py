"""
Fase 0 — Checkpoint 3: Discover all ticket fields (system + custom).

Prints a sorted table and saves a CSV to reports/ticket_fields.csv.
After running, identify the IDs for:
    - Reason for Contact
    - Correspondent
    - Correspondent Number (if exists)
    - Country
    - Product

Usage (from project root):
    python -m scripts.discover_fields
"""

import csv
import sys
from pathlib import Path

from src.config import REPORTS_DIR
from src.zendesk_client import ZendeskClient

OUTPUT_CSV = REPORTS_DIR / "ticket_fields.csv"


def main() -> None:
    print("Fetching ticket fields from Zendesk...")
    try:
        client = ZendeskClient()
        fields = client.get_ticket_fields()
    except Exception as exc:
        print(f"\n  ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Sort alphabetically by title
    fields.sort(key=lambda f: f.get("title", "").lower())

    # Print table header
    print(f"\n{'ID':<15} {'TYPE':<20} {'ACTIVE':<8} TITLE")
    print("-" * 80)

    rows_for_csv: list[dict] = []

    for field in fields:
        fid = field.get("id", "")
        title = field.get("title", "")
        ftype = field.get("type", "")
        active = "yes" if field.get("active") else "no"

        print(f"{str(fid):<15} {ftype:<20} {active:<8} {title}")

        # If field has options, print first 5
        options = field.get("custom_field_options", []) or field.get("system_field_options", [])
        if options:
            preview = options[:5]
            for opt in preview:
                print(f"  {'':>15}   -> {opt.get('name', opt.get('value', ''))}")
            if len(options) > 5:
                print(f"  {'':>15}   ... ({len(options) - 5} more options)")

        rows_for_csv.append(
            {
                "id": fid,
                "title": title,
                "type": ftype,
                "active": active,
                "options_count": len(options),
                "first_5_options": " | ".join(
                    opt.get("name", opt.get("value", "")) for opt in options[:5]
                ),
            }
        )

    # Save CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "type", "active", "options_count", "first_5_options"])
        writer.writeheader()
        writer.writerows(rows_for_csv)

    print(f"\nTotal fields: {len(fields)}")
    print(f"CSV saved to: {OUTPUT_CSV}")
    print(
        "\nNext step: identify the IDs for Reason for Contact, Correspondent, "
        "Country, Product and add them to your .env file."
    )


if __name__ == "__main__":
    main()
