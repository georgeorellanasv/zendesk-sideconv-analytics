"""
Fase 0 — Checkpoint 2: Validate Zendesk API credentials.

Usage (from project root):
    python -m scripts.test_connection
"""

import sys

from src.zendesk_client import ZendeskClient


def main() -> None:
    print("Testing Zendesk connection...")
    try:
        client = ZendeskClient()
        data = client.get_current_user()
        user = data.get("user", {})
        print(f"\n  OK — Authenticated as:")
        print(f"       Name  : {user.get('name')}")
        print(f"       Email : {user.get('email')}")
        print(f"       Role  : {user.get('role')}")
        print(f"       ID    : {user.get('id')}")
        print("\nConnection successful. You can proceed to discover_fields.py\n")
    except EnvironmentError as exc:
        print(f"\n  ERROR (config): {exc}", file=sys.stderr)
        sys.exit(1)
    except ConnectionError as exc:
        print(f"\n  ERROR (network): {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n  ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
