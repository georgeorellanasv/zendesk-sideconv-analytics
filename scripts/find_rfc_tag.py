"""
Toma tickets F1 donde la macro fue aplicada (ria_payment_confirmation_reliable_correspondent_sent)
y revisa sus audits para encontrar el tag de "reason for contact = payment confirmation".
"""
import csv
from collections import Counter
from src.zendesk_client import ZendeskClient

MACRO_TAG = "ria_payment_confirmation_reliable_correspondent_sent"
TRIGGER_TAG = "payment_confirmation_advisory_applied"

SKIP = {
    "paid", "bank_deposit", "office_pick-up", "mobile_payment", "home_delivery",
    "north_america", "united_states", "south_america", "care_tier_1", "care_tier_2",
    "paid_og", "ticket_updated", "received_by_trg", "no_auto_response",
    "csat_suppressed_tickbox_auto", "consumer", "customer", "digital", "processor",
    "account_data_added", "active", "internet", "inbound_call", "email_ticket_channel",
    "stg_dandelion_automergeapp", "side_conversation_created", "sc_repliedto",
    "side_conversation_replied_to_trigger", "unreliable", "notify_req_public_reply_with_logic",
    "transaction_support", "sla_rfc_mapped", "attachment", "ticket_contains_attachments",
}

def classify(r):
    ok_48  = r["cond_48h"] == "True"
    ok_sub = r["cond_substatus"] == "True"
    sc_ok  = r["cond_no_sc"] == "True"
    sc_yes = r["cond_no_sc"] == "False"
    if ok_sub and ok_48 and sc_ok:  return "F1"
    if ok_sub and ok_48 and sc_yes: return "F2"
    if ok_sub and not ok_48:        return "F3"
    if not ok_sub and ok_48:        return "F4"
    if not ok_sub and not ok_48:    return "F5"
    return "FX"

rows = list(csv.DictReader(open("reports/macro_adherence_report.csv", encoding="utf-8")))
client = ZendeskClient()

# Tickets F1 que tienen la macro aplicada (ya en el CSV via tags column)
f1_with_macro = [
    r for r in rows
    if classify(r) == "F1" and MACRO_TAG in r.get("tags", "").split("|")
]
print(f"F1 con macro aplicada: {len(f1_with_macro)} tickets")
print(f"Revisando audits de los primeros 10...\n")

tag_counter: Counter = Counter()
field_counter: Counter = Counter()

for r in f1_with_macro[:10]:
    tid = int(r["ticket_id"])
    print(f"--- Ticket {tid} (DM: {r.get('delivery_method','?')}) ---")

    # Tags actuales del ticket
    tags = set(r.get("tags","").split("|"))
    action_tags = {t for t in tags if t and t not in SKIP and len(t) > 4}
    print(f"  Tags relevantes: {sorted(action_tags)}")

    # Audits para ver eventos de campo (reason for contact)
    audits = client.get_ticket_audits(tid)
    for audit in audits:
        for event in audit.get("events", []):
            # Cambios de campo custom
            if event.get("type") == "Change":
                field = event.get("field_name", "")
                val   = event.get("value", "")
                prev  = event.get("previous_value", "")
                if val and val != prev and "reason" in field.lower():
                    print(f"  [field change] {field}: '{prev}' -> '{val}'")
                    field_counter[f"{field}={val}"] += 1
                # Tags añadidos
                if field == "tags":
                    pv = event.get("previous_value") or []
                    cv = event.get("value") or []
                    prev_set = set(pv) if isinstance(pv, list) else set(pv.split())
                    curr_set = set(cv) if isinstance(cv, list) else set(cv.split())
                    added = curr_set - prev_set
                    for t in added:
                        if t and t not in SKIP:
                            tag_counter[t] += 1
                            if "reason" in t.lower() or "payment_conf" in t.lower() or "rfc" in t.lower() or "contact" in t.lower():
                                print(f"  [+tag relevante] {t}")
    print()

print("=" * 60)
print("Tags añadidos via audits (sin tags de sistema):")
for t, c in tag_counter.most_common(30):
    marker = " <-- REASON FOR CONTACT?" if ("reason" in t or "rfc" in t or "contact" in t or "payment" in t) else ""
    print(f"  {c:3d}  {t}{marker}")

print("\nCambios de campo 'reason':")
for f, c in field_counter.most_common(20):
    print(f"  {c:3d}  {f}")
