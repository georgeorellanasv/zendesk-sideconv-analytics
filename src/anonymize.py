"""
Anonimiza la DB real para uso en demo público (ej. GitHub / Streamlit Cloud).

Qué enmascara:
  - Nombres de personas (actor_name)          → "Customer N" / "Ria Agent N" / "Partner Contact N"
  - Parte local de emails (antes del @)        → mantiene dominio, reemplaza usuario
  - Emails en to_addresses (JSON)               → idem

Qué preserva:
  - Dominios de emails corresponsales           → para analítica de partners
  - Order IDs y subjects                        → se mantienen (no son PII sensible)
  - Message bodies                              → se mantienen (ya truncados a 2000 chars)
  - Timestamps, métricas, clasificaciones       → intactos

Uso:
    python -m src.anonymize

Genera: data/sideconv_demo.db
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import sys
from pathlib import Path

from src.config import DB_PATH

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clasificación de dominios
# ---------------------------------------------------------------------------

RIA_DOMAINS: frozenset[str] = frozenset({
    "riamoneytransfer.com",
    "riafinancial.com",
    "dandelionpayments.com",
    "euronet.com",
    "euronetsystems.com",
})

FREE_EMAIL_DOMAINS: frozenset[str] = frozenset({
    "gmail.com", "yahoo.com", "yahoo.es", "yahoo.com.mx", "yahoo.com.ar",
    "hotmail.com", "hotmail.es", "hotmail.com.mx",
    "outlook.com", "outlook.es",
    "live.com", "live.com.mx",
    "icloud.com", "me.com", "msn.com", "aol.com",
    "protonmail.com", "proton.me",
})


def _domain(email: str) -> str:
    email = (email or "").strip().lower()
    return email.split("@", 1)[1] if "@" in email else ""


def _classify_email(email: str) -> str:
    """Return 'ria', 'client' or 'partner' based on the domain."""
    d = _domain(email)
    if d in RIA_DOMAINS:
        return "ria"
    if d in FREE_EMAIL_DOMAINS:
        return "client"
    return "partner"


# ---------------------------------------------------------------------------
# Build email + name mappings
# ---------------------------------------------------------------------------

def _build_email_mapping(conn: sqlite3.Connection) -> dict[str, str]:
    """Return a dict {original_email_lower: anonymized_email}."""
    emails: set[str] = set()

    # from_address
    for row in conn.execute("SELECT DISTINCT from_address FROM side_conversation_events WHERE from_address != ''"):
        if row[0]:
            emails.add(row[0].strip().lower())

    # actor_email
    for row in conn.execute("SELECT DISTINCT actor_email FROM side_conversation_events WHERE actor_email != ''"):
        if row[0]:
            emails.add(row[0].strip().lower())

    # to_addresses (JSON)
    for row in conn.execute("SELECT to_addresses FROM side_conversation_events WHERE to_addresses != ''"):
        try:
            items = json.loads(row[0] or "[]")
            for it in items or []:
                if isinstance(it, dict):
                    e = (it.get("email") or "").strip().lower()
                    if e:
                        emails.add(e)
        except (json.JSONDecodeError, TypeError):
            pass

    # Asignar IDs estables (ordenados alfabéticamente → determinista)
    mapping: dict[str, str] = {}
    counter = {"ria": 0, "client": 0, "partner": 0}

    for email in sorted(emails):
        if not email or "@" not in email:
            continue
        cls = _classify_email(email)
        dom = _domain(email)
        counter[cls] += 1
        n = counter[cls]

        if cls == "ria":
            # Mantener dominio Ria para que analítica "internal" siga funcionando
            mapping[email] = f"ria_agent_{n}@{dom}"
        elif cls == "client":
            # Dominio free → genérico example.com
            mapping[email] = f"customer_{n}@example.com"
        else:
            # Mantener dominio del partner (crítico para Partner Scorecard)
            mapping[email] = f"contact_{n}@{dom}"

    return mapping


def _build_name_mapping(conn: sqlite3.Connection, email_map: dict[str, str]) -> dict[str, str]:
    """
    Return a dict {original_name_lower: anonymized_name}.

    We derive the "type" (ria/client/partner) by cross-referencing with the
    actor_email when available. If unknown, default to "Partner Contact N".
    """
    name_type_map: dict[str, str] = {}  # name_lower -> "ria" / "client" / "partner"

    for row in conn.execute(
        "SELECT DISTINCT actor_name, actor_email FROM side_conversation_events "
        "WHERE actor_name IS NOT NULL AND actor_name != ''"
    ):
        name = (row[0] or "").strip()
        email = (row[1] or "").strip().lower()
        if not name:
            continue
        cls = _classify_email(email) if email else "partner"
        name_lower = name.lower()
        # Si ya existe y los clasificamos distinto, preferimos el no-partner (más específico)
        existing = name_type_map.get(name_lower)
        if existing is None or (existing == "partner" and cls != "partner"):
            name_type_map[name_lower] = cls

    # Asignar IDs estables por tipo
    mapping: dict[str, str] = {}
    counter = {"ria": 0, "client": 0, "partner": 0}
    labels = {"ria": "Ria Agent", "client": "Customer", "partner": "Partner Contact"}

    for name_lower in sorted(name_type_map.keys()):
        cls = name_type_map[name_lower]
        counter[cls] += 1
        mapping[name_lower] = f"{labels[cls]} {counter[cls]}"

    return mapping


def _anonymize_to_addresses(to_json: str, email_map: dict[str, str]) -> str:
    """Replace emails inside the JSON to_addresses field while preserving structure."""
    if not to_json:
        return ""
    try:
        items = json.loads(to_json)
    except (json.JSONDecodeError, TypeError):
        return to_json
    if not isinstance(items, list):
        return to_json

    new_items = []
    for it in items:
        if isinstance(it, dict):
            orig = (it.get("email") or "").strip().lower()
            masked_email = email_map.get(orig) or it.get("email") or ""
            new_item = {**it, "email": masked_email}
            # Nombre también si viene
            if "name" in new_item and new_item["name"]:
                new_item["name"] = masked_email.split("@")[0] if masked_email else ""
            new_items.append(new_item)
        else:
            new_items.append(it)
    return json.dumps(new_items, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    src_path: Path = DB_PATH
    dst_path: Path = src_path.parent / "sideconv_demo.db"

    if not src_path.exists():
        logger.error("DB fuente no existe: %s", src_path)
        sys.exit(1)

    logger.info("Copiando DB real -> demo: %s -> %s", src_path.name, dst_path.name)
    shutil.copy2(src_path, dst_path)

    conn = sqlite3.connect(dst_path)
    conn.row_factory = sqlite3.Row

    logger.info("Construyendo mappings...")
    email_map = _build_email_mapping(conn)
    name_map = _build_name_mapping(conn, email_map)
    logger.info("  emails a enmascarar: %d", len(email_map))
    logger.info("  nombres a enmascarar: %d", len(name_map))

    # ---- Aplicar email mapping ----
    logger.info("Aplicando mapping de emails...")
    for orig, masked in email_map.items():
        conn.execute(
            "UPDATE side_conversation_events SET from_address = ? WHERE LOWER(from_address) = ?",
            (masked, orig),
        )
        conn.execute(
            "UPDATE side_conversation_events SET actor_email = ? WHERE LOWER(actor_email) = ?",
            (masked, orig),
        )

    # ---- Aplicar name mapping ----
    logger.info("Aplicando mapping de nombres...")
    for orig, masked in name_map.items():
        conn.execute(
            "UPDATE side_conversation_events SET actor_name = ? WHERE LOWER(actor_name) = ?",
            (masked, orig),
        )

    # ---- Anonymize to_addresses (JSON) ----
    logger.info("Anonimizando to_addresses (JSON)...")
    rows = conn.execute("SELECT event_id, to_addresses FROM side_conversation_events WHERE to_addresses != ''").fetchall()
    for row in rows:
        new_to = _anonymize_to_addresses(row["to_addresses"], email_map)
        if new_to != row["to_addresses"]:
            conn.execute(
                "UPDATE side_conversation_events SET to_addresses = ? WHERE event_id = ?",
                (new_to, row["event_id"]),
            )

    conn.commit()

    # ---- Validation: sanity check ----
    sample = conn.execute(
        "SELECT actor_name, actor_email, from_address FROM side_conversation_events LIMIT 5"
    ).fetchall()
    logger.info("Muestra post-anonymización:")
    for r in sample:
        logger.info("  name=%r  email=%r  from=%r", r["actor_name"], r["actor_email"], r["from_address"])

    conn.close()
    logger.info("OK - DB anonimizada generada en: %s", dst_path)
    logger.info("  Tamaño: %.1f KB", dst_path.stat().st_size / 1024)


if __name__ == "__main__":
    main()
