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
    # ---- RFI FAMILY (orden importa: específicas primero, catch-all al final) ----
    (
        "rfi_identity_document",
        "high",
        [
            r"copy\s+of\s+(your|the)?\s*id\b",
            r"copia\s+de\s+(tu|su|la)?\s*(id|identificaci[oó]n|c[eé]dula|pasaporte)",
            r"foto\s+de\s+(tu|su|la)?\s*(id|identificaci[oó]n|c[eé]dula|pasaporte)",
            r"send\s+us.*(id|passport|identification)",
            r"env[ií]a(nos|r).*(id|identificaci[oó]n|c[eé]dula|pasaporte)",
            r"proof\s+of\s+identity",
            r"adjuntar\s+(tu|su|la)?\s*(id|identificaci[oó]n|c[eé]dula|pasaporte)",
            r"scan.*(id|passport)",
            r"id\s+del\s+beneficiario",      # ID = documento identidad del beneficiario
            r"id\s+del\s+cliente",
            r"driver'?s?\s+licen[sc]e",
            r"licencia\s+de\s+conducir",
            r"\bpassport\b",
            r"\bpasaporte\b",
        ],
    ),
    (
        "rfi_account_statement",
        "high",
        [
            r"bank\s+statement",
            r"account\s+statement",
            r"estado\s+de\s+cuenta",
            r"statement\s+request",
            r"adjuntar\s+estado\s+(de\s+)?cuenta",
            r"favor\s+enviar\s+estado",
            r"historial\s+(de\s+)?transacciones",
            r"transaction\s+history",
            r"estado\s+bancario",
        ],
    ),
    (
        "rfi_missing_data",
        "high",
        [
            r"please\s+provide\s+(full\s+name|the\s+following|additional|beneficiary)",
            r"favor\s+(enviar|proveer|proporcionar)\s+(los\s+siguientes?|nombre\s+completo|fecha\s+de\s+nacimiento)",
            r"beneficiary\s+(lastname|middlename|firstname|nationality|country|dob)",
            r"full\s+name\s+till",
            r"fecha\s+de\s+nacimiento",
            r"date\s+of\s+birth\b",
            r"\bdob\b",
            r"routing\s+number",
            r"account\s+number",
            r"n[uú]mero\s+de\s+cuenta",
            r"banking\s+details",
            r"datos\s+bancarios",
            r"informaci[oó]n\s+del\s+beneficiario",
            r"beneficiary\s+(details|information|info)",
        ],
    ),
    (
        "rfi_other",
        "medium",
        [
            r"\brfi\b",
            r"request\s+for\s+information",
            r"additional\s+information",
            r"informaci[oó]n\s+adicional",
            r"favor\s+enviar.*comprobante",
            r"requested\s+the\s+following",
            r"please\s+provide",
            r"favor\s+enviar",
            r"por\s+favor\s+env[ií]e",
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
# Automation heuristic — detect if a side conversation was auto-generated
# ---------------------------------------------------------------------------

# Keywords en actor_name que típicamente son buzones/equipos (no personas)
_TEAM_KEYWORDS = (
    "team", "teams", "supervisors", "supervisor", "agentes", "agents",
    "group", "dept", "department", "division", "office", "support",
    "desk", "service", "center", "mailbox",
)

# Emails típicos de buzón automatizado
_MAILBOX_LOCAL_KEYWORDS = (
    "team", "agentes", "agents", "group", "noreply", "no-reply",
    "notifications", "notification", "support", "ar", "receivables",
    "settlement", "settlements",
)


def _looks_like_team_name(name: str) -> bool:
    """Nombre tiene keyword de equipo/buzón."""
    lower = (name or "").strip().lower()
    if not lower:
        return False
    return any(kw in lower for kw in _TEAM_KEYWORDS)


def _has_numeric_prefix(name: str) -> bool:
    """Nombre empieza con dígitos (ej: '421570 - Celeste J Llc')."""
    stripped = (name or "").strip()
    return bool(re.match(r"^\d{3,}\s*[-:]", stripped))


def _is_compact_alias(name: str) -> bool:
    """Una sola palabra larga sin espacios (ej: 'ARCanadateam', 'Agtransferenciaslam')."""
    stripped = (name or "").strip()
    if " " in stripped:
        return False
    # Al menos 8 chars, mezcla de mayúsculas y minúsculas, no es una persona normal
    return len(stripped) >= 8 and any(c.isupper() for c in stripped) and any(c.islower() for c in stripped)


def _is_mailbox_email(email: str) -> bool:
    """Parte local del email coincide con keyword de mailbox."""
    local = (email or "").strip().lower().split("@", 1)[0]
    if not local:
        return False
    return any(kw in local for kw in _MAILBOX_LOCAL_KEYWORDS)


def detect_automation(
    actor_name: str,
    actor_email: str,
    sc_created_at: str | None,
    ticket_created_at: str | None,
) -> tuple[int, str]:
    """
    Heuristically detect if a side conversation was auto-generated.

    Returns (is_automated: int (0/1), signal: str).
    Signal tells which rule triggered — useful for auditing the heuristic.
    """
    # Signal 1: team/mailbox keyword in actor_name
    if _looks_like_team_name(actor_name):
        return 1, "team_keyword_in_name"

    # Signal 2: numeric prefix (like "421570 - Celeste J Llc")
    if _has_numeric_prefix(actor_name):
        return 1, "numeric_prefix_name"

    # Signal 3: compact alias (ARCanadateam, Agtransferenciaslam)
    if _is_compact_alias(actor_name):
        return 1, "compact_alias_name"

    # Signal 4: mailbox-style email
    if _is_mailbox_email(actor_email):
        return 1, "mailbox_email"

    # Signal 5: thread created within 60 seconds of the ticket
    if sc_created_at and ticket_created_at:
        try:
            from datetime import datetime
            dt_sc = datetime.fromisoformat(sc_created_at.replace("Z", "+00:00"))
            dt_tkt = datetime.fromisoformat(ticket_created_at.replace("Z", "+00:00"))
            delta = (dt_sc - dt_tkt).total_seconds()
            if 0 <= delta < 60:
                return 1, "rapid_creation"
        except (ValueError, TypeError):
            pass

    return 0, "manual"


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
                sc.created_at       AS sc_created_at,
                t.created_at        AS ticket_created_at,
                e.from_address,
                e.to_addresses,
                e.message_body,
                e.actor_name,
                e.actor_email
            FROM side_conversations sc
            JOIN tickets t ON t.ticket_id = sc.ticket_id
            LEFT JOIN side_conversation_events e
                ON  e.side_conv_id = sc.side_conv_id
                AND e.event_type   = 'create'
            """
        ).fetchall()

    logger.info("Side conversations a clasificar: %d", len(rows))

    counts: dict[str, int] = {}
    automation_counts: dict[str, int] = {}
    updates: list[tuple[str, str, str, str, int, str, str]] = []

    # Categorías "catch-all" — si el subject matchea estas, también probamos con el body
    GENERIC_LABELS = {"other", "order_notification", "general_correspondence"}

    for row in rows:
        sc_id             = row["side_conv_id"]
        subject           = row["subject"] or ""
        sc_created        = row["sc_created_at"]
        ticket_created    = row["ticket_created_at"]
        from_addr         = row["from_address"] or ""
        to_addr_raw       = row["to_addresses"] or ""
        body              = (row["message_body"] or "")[:500]
        actor_name        = row["actor_name"] or ""
        actor_email       = row["actor_email"] or ""

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
                    downgrade = {"high": "medium", "medium": "low", "low": "low"}
                    reason = body_reason
                    confidence = downgrade.get(body_conf, "low")

        # Automation heuristic
        is_automated, automation_signal = detect_automation(
            actor_name, actor_email, sc_created, ticket_created
        )

        updates.append(
            (direction, recipient_type, reason, confidence,
             is_automated, automation_signal, sc_id)
        )
        key = f"{direction}/{recipient_type}/{reason}"
        counts[key] = counts.get(key, 0) + 1
        automation_counts[automation_signal] = automation_counts.get(automation_signal, 0) + 1

    with get_conn() as conn:
        conn.executemany(
            """
            UPDATE side_conversations
            SET sc_direction             = ?,
                sc_recipient_type        = ?,
                sc_reason_classification = ?,
                sc_reason_confidence     = ?,
                sc_is_automated          = ?,
                sc_automation_signal     = ?
            WHERE side_conv_id = ?
            """,
            updates,
        )

    logger.info("Clasificación completada. Distribución (reason):")
    for key, n in sorted(counts.items(), key=lambda x: -x[1]):
        logger.info("  %-65s %d", key, n)

    logger.info("Distribución de señales de automatización:")
    for key, n in sorted(automation_counts.items(), key=lambda x: -x[1]):
        logger.info("  %-30s %d", key, n)


if __name__ == "__main__":
    run_classification()
