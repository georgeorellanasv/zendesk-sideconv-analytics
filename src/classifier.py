"""
Fase 4 — Clasificador de side conversations.

Para cada side conversation determina:
  sc_direction             — ria_to_external | ria_to_client | external_to_ria | internal | unknown
  sc_recipient_type        — client | correspondent | internal | unknown
  sc_reason_classification — categoría basada en el subject
  sc_reason_confidence     — high | medium | low

Usa el evento tipo "create" como señal principal (primer mensaje de la conversación).

Usage:
    python -m src.classifier
"""

import json
import logging
import re
import sys

from src.db import get_conn

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dominios internos de Ria / Euronet
# ---------------------------------------------------------------------------

RIA_DOMAINS: frozenset[str] = frozenset(
    {
        "riamoneytransfer.com",
        "riafinancial.com",
        "dandelionpayments.com",
        "euronet.com",
        "euronetsystems.com",
    }
)

# Dominios de correo gratuito / personal → destinatario es un cliente final
FREE_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "yahoo.com",
        "yahoo.es",
        "yahoo.com.mx",
        "yahoo.com.ar",
        "hotmail.com",
        "hotmail.es",
        "hotmail.com.mx",
        "outlook.com",
        "outlook.es",
        "live.com",
        "live.com.mx",
        "icloud.com",
        "me.com",
        "msn.com",
        "aol.com",
        "protonmail.com",
        "proton.me",
    }
)


def _domain(email: str) -> str:
    """Return lowercase domain from an email address, or '' if not parseable."""
    email = (email or "").strip().lower()
    if "@" in email:
        return email.split("@", 1)[1]
    return ""


def _is_ria(email: str) -> bool:
    return _domain(email) in RIA_DOMAINS


def _is_client(email: str) -> bool:
    return _domain(email) in FREE_EMAIL_DOMAINS


def _emails_from_to(to_addresses_json: str) -> list[str]:
    """Parse the to_addresses JSON column into a list of email strings."""
    if not to_addresses_json:
        return []
    try:
        items = json.loads(to_addresses_json)
        if isinstance(items, list):
            emails = []
            for item in items:
                if isinstance(item, dict):
                    emails.append(item.get("email", ""))
                elif isinstance(item, str):
                    emails.append(item)
            return [e for e in emails if e]
        if isinstance(items, str):
            return [items]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


# ---------------------------------------------------------------------------
# Recipient type classifier
# ---------------------------------------------------------------------------

def classify_recipient_type(to_emails: list[str]) -> str:
    """
    Determine the type of recipient(s) in a side conversation.

    Priority: if ANY recipient is a client → client
              elif ANY is external correspondent → correspondent
              elif ALL are Ria → internal
              else → unknown
    """
    if not to_emails:
        return "unknown"

    has_client = any(_is_client(e) for e in to_emails if e)
    has_external = any(not _is_ria(e) and not _is_client(e) for e in to_emails if e)
    all_ria = all(_is_ria(e) for e in to_emails if e)

    if has_client:
        return "client"
    if has_external:
        return "correspondent"
    if all_ria:
        return "internal"
    return "unknown"


# ---------------------------------------------------------------------------
# Direction classifier
# ---------------------------------------------------------------------------

def classify_direction(
    from_address: str, to_addresses_json: str, recipient_type: str
) -> str:
    """
    Determine the direction of a side conversation based on the create event.

    Returns one of:
      ria_to_client    — Ria agent writes to a client (end customer)
      ria_to_external  — Ria agent writes to a correspondent / partner
      internal         — Both sides are Ria domains
      external_to_ria  — External party writes to Ria
      unknown          — Not enough data
    """
    from_addr = (from_address or "").strip()
    to_emails = _emails_from_to(to_addresses_json)

    if not from_addr and not to_emails:
        return "unknown"

    from_is_ria = _is_ria(from_addr)

    if not to_emails:
        return "ria_to_external" if from_is_ria else "external_to_ria"

    all_to_ria = all(_is_ria(e) for e in to_emails if e)

    if from_is_ria:
        if all_to_ria:
            return "internal"
        if recipient_type == "client":
            return "ria_to_client"
        return "ria_to_external"
    else:
        return "external_to_ria"


# ---------------------------------------------------------------------------
# Reason classifier
# ---------------------------------------------------------------------------

# Each entry: (classification_label, confidence, [regex_patterns_on_subject])
# Patterns are checked in order — first match wins.

_RULES: list[tuple[str, str, list[str]]] = [
    (
        "proof_of_payment_request",
        "high",
        [
            r"prueba\s+de\s+pago",
            r"comprobante",
            r"proof\s+of\s+pay",
            r"preuve\s+de\s+paiement",
            r"prueba\s+de\s+dep[oó]sito",
            r"payment\s+proof",
            r"deposit\s+proof",
            r"prueba\s+de\s+deposito",
            r"\bpop\b",                         # abreviación de Proof of Payment
            r"please\s+verify\s+the\s+pay",
        ],
    ),
    (
        "cancellation_request",
        "high",
        [
            r"\bcancel",
            r"solicitud.*cancelaci",
            r"demande\s+de\s+rappel",           # francés: solicitud de recall/cancel
        ],
    ),
    (
        "recall_request",
        "high",
        [
            r"\brecall\b",
        ],
    ),
    (
        "fund_recovery_request",
        "high",
        [
            r"recuperaci[oó]n\s+de\s+fondos",
            r"recuperacion\s+de\s+fondos",
            r"solicitud.*recuperaci",
            r"\brecuperacion\b",
        ],
    ),
    (
        "refund_request",
        "high",
        [
            r"\brefund\b",
            r"reembolso",
            r"reembols",
            r"rembolso",                        # typo frecuente
            r"devoluci[oó]n",
            r"client\s+refund",
            r"verify\s+refund",
            r"proceso\s+de\s+reembolso",
        ],
    ),
    (
        "deposit_delay_notification",
        "high",
        [
            r"bank\s+deposit\s+delayed",
            r"dep[oó]sito\s+bancario\s+pendiente",
            r"dep[oó]sito\s+bancario\s+retrasado",
            r"deposito\s+bancario\s+retrasado",
            r"dep[oó]sito.*demorado",
            r"delayed.*deposit",
        ],
    ),
    (
        "held_transfer_info_request",
        "high",
        [
            r"held\s+transfer",
            r"orden\s+detenida",
            r"orden\s+retenida",
            r"transfer.*hold",
            r"transfer.*held",
            r"transaction.*on\s+hold",
            r"transaction.*is\s+held",
            r"transacci[oó]n.*detenida",
            r"transacci[oó]n\s+se\s+encuentra\s+detenida",
            r"on\s+hold\s+by\s+(the\s+)?(bank|sanctions|correspondent)",
            r"hold\s+by\s+sanctions",
            r"retenida\s+por\s+el\s+banco",
        ],
    ),
    (
        "payout_assistance",
        "high",
        [
            r"payout\s+assist",
            r"payment\s+assist",
            r"asistencia\s+de\s+pago",          # ya estaba en transaction_status — movida aquí primero
        ],
    ),
    (
        "modification_request",
        "high",
        [
            r"\bmodif",                         # modification, modificación, modify
        ],
    ),
    (
        "charge_issue",
        "high",
        [
            r"charge\s+issue",
            r"payment\s+issue",
            r"cargo\s+incorrecto",
            r"doble\s+cargo",
            r"double\s+charge",
        ],
    ),
    (
        "transaction_trace",
        "high",
        [
            r"\btrace\b",
            r"investigaci[oó]n",
            r"investigacion",
        ],
    ),
    (
        "transaction_status",
        "high",
        [
            r"estado\s+de\s+orden",
            r"estado\s+de\s+la\s+orden",
            r"transaction\s+status",
            r"order\s+status",
            r"estado\s+orden",
            r"expa?lanation\s+of\s+status",
            r"status\s+request",
            r"incentive\s+status",
        ],
    ),
    (
        "compliance_inquiry",
        "high",
        [
            r"\bcompliance\b",
            r"\baml\b",
            r"\bkyc\b",
        ],
    ),
    (
        "rfi_outbound",
        "medium",
        [
            r"\brfi\b",
            r"request\s+for\s+information",
            r"statement\s+request",
            r"id\s+del\s+beneficiario",
            r"bank\s+statement",
            r"estado\s+de\s+cuenta",
            r"additional\s+information",
            r"informaci[oó]n\s+adicional",
            r"adjuntar\s+estado",
            r"favor\s+enviar\s+estado",
            r"favor\s+enviar.*comprobante",
            r"requested\s+the\s+following",
        ],
    ),
    (
        "rfi_inbound",
        "medium",
        [
            r"inbound.*rfi",
            r"rfi.*inbound",
        ],
    ),
    (
        "order_notification",
        "medium",
        [
            r"ria\s+money\s+transfer.*[a-z]{2}\d{6,}",   # "Ria Money Transfer US123456"
            r"^order\s+[a-z]{0,2}\d{6,}",               # "Order US513680909"
            r"^[a-z]{2}\d{7,}\s*$",                      # "US1434563678" solo
            r"^[a-z]{2}\d{7,}[^a-z]",                   # "US476257009 ..." al inicio
        ],
    ),
    (
        "general_correspondence",
        "low",
        [
            r"^ria\s+money\s+transfer\s*$",
            r"^ria\s*$",
            r"^greetings\s+from\s+ria",
            r"^form\s*$",
        ],
    ),
]


def classify_reason(subject: str) -> tuple[str, str]:
    """
    Return (classification, confidence) based on subject keyword matching.
    Falls back to ('other', 'low') if no rule matches.
    """
    text = (subject or "").lower()
    for label, confidence, patterns in _RULES:
        for pattern in patterns:
            if re.search(pattern, text):
                return label, confidence
    return "other", "low"


# ---------------------------------------------------------------------------
# Main — update side_conversations table
# ---------------------------------------------------------------------------

def run_classification() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger.info("Iniciando clasificación de side conversations...")

    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                sc.side_conv_id,
                sc.subject,
                e.from_address,
                e.to_addresses,
                e.message_body
            FROM side_conversations sc
            LEFT JOIN side_conversation_events e
                ON  e.side_conv_id = sc.side_conv_id
                AND e.event_type   = 'create'
            """
        ).fetchall()

    logger.info("Side conversations a clasificar: %d", len(rows))

    counts: dict[str, int] = {}
    updates: list[tuple[str, str, str, str, str]] = []

    # Categorías "catch-all" — si el subject matchea estas, también probamos con el body
    GENERIC_LABELS = {"other", "order_notification", "general_correspondence"}

    for row in rows:
        sc_id       = row["side_conv_id"]
        subject     = row["subject"] or ""
        from_addr   = row["from_address"] or ""
        to_addr_raw = row["to_addresses"] or ""
        body        = (row["message_body"] or "")[:500]  # primeros 500 chars

        to_emails      = _emails_from_to(to_addr_raw)
        recipient_type = classify_recipient_type(to_emails)
        direction      = classify_direction(from_addr, to_addr_raw, recipient_type)

        # Override reason for internal convs
        if direction == "internal":
            reason, confidence = "internal_collaboration", "high"
        else:
            reason, confidence = classify_reason(subject)

            # Si el subject es genérico, intentamos reclasificar por el body
            if reason in GENERIC_LABELS and body:
                body_reason, body_conf = classify_reason(body)
                if body_reason not in GENERIC_LABELS:
                    # Degradamos confianza (viene del body, no del subject)
                    downgrade = {"high": "medium", "medium": "low", "low": "low"}
                    reason = body_reason
                    confidence = downgrade.get(body_conf, "low")

        updates.append((direction, recipient_type, reason, confidence, sc_id))
        key = f"{direction}/{recipient_type}/{reason}"
        counts[key] = counts.get(key, 0) + 1

    with get_conn() as conn:
        conn.executemany(
            """
            UPDATE side_conversations
            SET sc_direction             = ?,
                sc_recipient_type        = ?,
                sc_reason_classification = ?,
                sc_reason_confidence     = ?
            WHERE side_conv_id = ?
            """,
            updates,
        )

    logger.info("Clasificación completada. Distribución:")
    for key, n in sorted(counts.items(), key=lambda x: -x[1]):
        logger.info("  %-65s %d", key, n)


if __name__ == "__main__":
    run_classification()
