"""
Fase 0 — Checkpoint 4: Discover Zendesk views and identify "US Care".

Prints all views with their IDs, then shows full conditions for any view
whose title matches "US Care" (case-insensitive).

Usage (from project root):
    python -m scripts.discover_views
"""

import json
import sys

from src.zendesk_client import ZendeskClient


def _summarize_conditions(conditions: dict) -> str:
    """Return a short human-readable summary of view conditions."""
    parts = []
    for rule in conditions.get("all", []):
        parts.append(f"ALL: {rule.get('field')} {rule.get('operator')} {rule.get('value')}")
    for rule in conditions.get("any", []):
        parts.append(f"ANY: {rule.get('field')} {rule.get('operator')} {rule.get('value')}")
    return "; ".join(parts[:3]) + (" ..." if len(parts) > 3 else "")


def main() -> None:
    print("Fetching views from Zendesk...\n")
    try:
        client = ZendeskClient()
        views = client.get_views()
    except Exception as exc:
        print(f"\n  ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Sort by title
    views.sort(key=lambda v: v.get("title", "").lower())

    # Filter to active views or ones matching care/US
    interesting = [
        v for v in views
        if v.get("active") or any(
            kw in v.get("title", "").lower() for kw in ["us care", "care", "us "]
        )
    ]

    print(f"{'ID':<15} {'ACTIVE':<8} TITLE")
    print("-" * 70)
    for view in interesting:
        vid = view.get("id", "")
        title = view.get("title", "")
        active = "yes" if view.get("active") else "no"
        print(f"{str(vid):<15} {active:<8} {title}")

    print(f"\nTotal active/relevant views shown: {len(interesting)} of {len(views)}")

    # Find "US Care" specifically
    us_care_matches = [
        v for v in views
        if "us care" in v.get("title", "").lower()
    ]

    if us_care_matches:
        print("\n" + "=" * 70)
        print("FOUND 'US Care' view(s):")
        print("=" * 70)
        for view in us_care_matches:
            print(f"\n  ID    : {view.get('id')}")
            print(f"  Title : {view.get('title')}")
            print(f"  Active: {view.get('active')}")
            print(f"\n  Full conditions:")
            print(json.dumps(view.get("conditions", {}), indent=4, ensure_ascii=False))
        print(
            "\nNext step: confirm the correct view ID and add it to your .env as VIEW_ID_US_CARE"
        )
    else:
        print(
            "\n  WARNING: No view with 'US Care' in the title was found.\n"
            "  Check the table above and identify the correct view manually.\n"
            "  Look for titles containing 'Care', 'US', or similar."
        )
        print("\nAll view titles for reference:")
        for v in views:
            print(f"  [{v.get('id')}] {v.get('title')} (active={v.get('active')})")


if __name__ == "__main__":
    main()
