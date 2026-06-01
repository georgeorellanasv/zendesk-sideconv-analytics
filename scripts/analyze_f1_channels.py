"""
Analiza los tickets F1 del CSV para entender:
1. Distribución por canal (voice vs email/chat vs messaging)
2. Tags de grupo/WFM presentes (para identificar US Care)
3. Co-ocurrencia de los tags de adherencia candidatos
"""
import csv
from collections import Counter

MACRO_TAG   = "ria_payment_confirmation_reliable_correspondent_sent"
RFC_TAG     = "order__payment_confirmation"
TRIGGER_TAG = "payment_confirmation_advisory_applied"

VOICE_VA_ONLY = {"inbound_call_-_va_only", "va_only_solved"}
VOICE_REP     = {"inbound_call_-_va_to_rep", "cxi_ch_voice", "voice_english", "voice_spanish"}
VOICE_ANY     = {"inbound_call"} | VOICE_VA_ONLY | VOICE_REP

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
f1 = [r for r in rows if classify(r) == "F1"]
print(f"F1 tickets: {len(f1)}\n")

# ── Clasificar por canal ──────────────────────────────────────────────────────
ch_counts = Counter()
wfm_tags  = Counter()
group_tags = Counter()

for r in f1:
    tags = set(r.get("tags","").split("|"))

    # Canal
    if tags & VOICE_VA_ONLY:
        ch = "va_only"
    elif tags & {"inbound_call_-_va_to_rep", "cxi_ch_voice"}:
        ch = "voice_rep"
    elif "inbound_call" in tags:
        ch = "voice_direct"
    elif tags & {"native_messaging", "live_chat_-_message", "chat_-_va_to_rep"}:
        ch = "messaging"
    elif "email_ticket_channel" in tags:
        ch = "email"
    else:
        ch = "other/unknown"
    ch_counts[ch] += 1
    r["_channel"] = ch

    # WFM / grupo tags
    for t in tags:
        if t.startswith("ria_wfm_") or t.startswith("cxi_ria_wfm_"):
            wfm_tags[t] += 1
        if "care" in t and "tier" not in t and "user" not in t:
            group_tags[t] += 1

print("=== CANAL ===")
for ch, c in ch_counts.most_common():
    print(f"  {c:4d}  {ch}")

print("\n=== WFM tags (grupo de trabajo) ===")
for t, c in wfm_tags.most_common(20):
    print(f"  {c:4d}  {t}")

print("\n=== Tags de grupo Care ===")
for t, c in group_tags.most_common(20):
    print(f"  {c:4d}  {t}")

# ── Co-ocurrencia de tags de adherencia por canal ─────────────────────────────
print("\n=== CO-OCURRENCIA DE TAGS DE ADHERENCIA ===")
header = f"{'canal':<16} {'n':>5}  {'macro':>5}  {'rfc':>5}  {'trigger':>7}  {'macro%':>6}  {'rfc%':>5}  {'tri%':>5}"
print(header)
print("-" * len(header))

for ch in ["voice_rep", "voice_direct", "va_only", "messaging", "email", "other/unknown"]:
    bucket = [r for r in f1 if r.get("_channel") == ch]
    if not bucket: continue
    n = len(bucket)
    macro   = sum(1 for r in bucket if MACRO_TAG   in r.get("tags","").split("|"))
    rfc     = sum(1 for r in bucket if RFC_TAG     in r.get("tags","").split("|"))
    trigger = sum(1 for r in bucket if TRIGGER_TAG in r.get("tags","").split("|"))
    print(f"  {ch:<14} {n:>5}  {macro:>5}  {rfc:>5}  {trigger:>7}  "
          f"{macro/n*100:>5.1f}%  {rfc/n*100:>4.1f}%  {trigger/n*100:>4.1f}%")

# ── US Care: filtrar por wfm tag ──────────────────────────────────────────────
US_WFM = {"ria_wfm_us_phone", "cxi_ria_wfm_nam_care_phone", "ria_wfm_nam_care_phone"}
us_care = [r for r in f1 if US_WFM & set(r.get("tags","").split("|"))]
print(f"\n=== US Care (tags: {US_WFM}) ===")
print(f"  F1 tickets US Care: {len(us_care)} de {len(f1)}")
if us_care:
    macro_us = sum(1 for r in us_care if MACRO_TAG in r.get("tags","").split("|"))
    rfc_us   = sum(1 for r in us_care if RFC_TAG   in r.get("tags","").split("|"))
    print(f"  Con macro:   {macro_us}/{len(us_care)} = {macro_us/len(us_care)*100:.1f}%")
    print(f"  Con RFC tag: {rfc_us}/{len(us_care)}  = {rfc_us/len(us_care)*100:.1f}%")
