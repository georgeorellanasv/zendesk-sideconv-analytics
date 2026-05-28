"""
Construye la tabla completa de adherencia para los 5 escenarios x delivery method.
Lee los tags directamente del CSV (columna 'tags') — sin llamadas extra a la API.

Guarda: reports/adherence_full_table.csv
"""
import csv
from collections import defaultdict

CORRECT_TAGS = {
    "F1": {
        "ria_payment_confirmation_reliable_correspondent_sent",
    },
    "F2": {
        "new_pop_ticket", "pop_side_convo_macro", "pop_side_convo_macro_es",
        "pop_interbank_sc", "ria_pop_day_1_qt", "dandelion_pop_day_1",
        "dandelion_request_pop",
    },
    "F3": {
        "new_pop_ticket", "pop_side_convo_macro", "pop_side_convo_macro_es",
        "pop_interbank_sc", "ria_pop_day_1_qt", "dandelion_pop_day_1",
        "dandelion_request_pop", "ria_pop_success_qt",
    },
    "F4": {
        "payment_confirmation_holding_reply_sent",
        "payment_confirmation_unreliable_advisory_applied",
        "bank_deposit_within_sla_macro", "ria_pop_day_1_qt",
        "dandelion_pop_day_1", "dandelion_bank_deposit_within_sla",
        "partner_reponse_bank_deposit_within_sla",
    },
    "F5": {
        "new_pop_ticket", "pop_side_convo_macro", "pop_side_convo_macro_es",
        "pop_interbank_sc", "dandelion_bank_deposit_sla_breach_macro",
        "unibank_pop_request",
    },
}

LABELS = {
    "F1": "Paid + <48h + sin SC  -> Payment Confirmation",
    "F2": "Paid + <48h + con SC  -> POP (SC abierta)",
    "F3": "Paid + >48h           -> Initiate POP",
    "F4": "Unreliable + <48h     -> ETA email / POP Day 1",
    "F5": "Unreliable + >48h     -> SC al corresponsal",
}

DM_SHORT = {
    "bank_deposit":  "Bank Dep.",
    "office_pick-up": "Office PU",
    "mobile_payment": "Mobile",
    "home_delivery":  "Home Del.",
}


def classify(r: dict) -> str:
    sc_ok  = r["cond_no_sc"] == "True"
    sc_yes = r["cond_no_sc"] == "False"
    ok_48  = r["cond_48h"] == "True"
    ok_sub = r["cond_substatus"] == "True"
    if ok_sub and ok_48 and sc_ok:  return "F1"
    if ok_sub and ok_48 and sc_yes: return "F2"
    if ok_sub and not ok_48:        return "F3"
    if not ok_sub and ok_48:        return "F4"
    if not ok_sub and not ok_48:    return "F5"
    return "FX"


# ── Cargar CSV base ──────────────────────────────────────────────────────────
rows = list(csv.DictReader(open("reports/macro_adherence_report.csv", encoding="utf-8")))
total = len(rows)
print(f"Tickets en CSV: {total}")

has_dm_col  = "delivery_method" in rows[0]
has_tag_col = "tags" in rows[0]
delivery_methods = sorted(set(r.get("delivery_method", "bank_deposit") for r in rows)) if has_dm_col else ["bank_deposit"]
print(f"Delivery methods: {delivery_methods}")

if not has_tag_col:
    raise SystemExit("ERROR: el CSV no tiene columna 'tags'. Re-ejecuta macro_adherence_analysis.py primero.")

# Tags ya estan en el CSV — construir tag_map sin llamadas API
tag_map: dict[str, set[str]] = {
    r["ticket_id"]: set(r["tags"].split("|")) if r["tags"] else set()
    for r in rows
}
print("Tags cargados del CSV (0 llamadas API extra).")

# ── Calcular adherencia por escenario x delivery method ──────────────────────
print("Calculando adherencia...")

# Agrupa: (escenario, delivery_method) → lista de rows
buckets: dict[tuple, list] = defaultdict(list)
for r in rows:
    dm  = r.get("delivery_method", "bank_deposit") if has_dm_col else "bank_deposit"
    esc = classify(r)
    buckets[(esc, dm)].append(r)

summary_rows = []
for esc, label in LABELS.items():
    for dm in delivery_methods:
        bucket = buckets.get((esc, dm), [])
        n = len(bucket)
        if not n:
            continue
        adherent = sum(1 for r in bucket if tag_map.get(r["ticket_id"], set()) & CORRECT_TAGS[esc])
        summary_rows.append({
            "escenario":       esc,
            "delivery_method": dm,
            "descripcion":     label,
            "total_tickets":   n,
            "pct_del_total":   round(n / total * 100, 1),
            "accion_correcta": adherent,
            "sin_accion":      n - adherent,
            "adherencia_pct":  round(adherent / n * 100, 1),
        })

# ── Imprimir tabla global ─────────────────────────────────────────────────────
print(f"\nTABLA DE ADHERENCIA  (n={total}, Paid, 30 dias)")
print("=" * 90)
print(f"{'ESC':<4} {'DM':<10} {'DESCRIPCION':<40} {'N':>5} {'%TOT':>6} {'CORREC':>7} {'GAP':>6} {'ADH%':>6}")
print("-" * 90)

for s in summary_rows:
    dm_lbl = DM_SHORT.get(s["delivery_method"], s["delivery_method"])
    print(f"{s['escenario']:<4} {dm_lbl:<10} {s['descripcion']:<40} {s['total_tickets']:>5} "
          f"{s['pct_del_total']:>5.1f}% {s['accion_correcta']:>7} "
          f"{s['sin_accion']:>6} {s['adherencia_pct']:>5.1f}%")
print("=" * 90)

total_correct = sum(s["accion_correcta"] for s in summary_rows)
total_gap     = sum(s["sin_accion"]      for s in summary_rows)
print(f"{'TOTAL':<4} {'':10} {'':40} {total:>5} {'100%':>6} {total_correct:>7} "
      f"{total_gap:>6} {total_correct/total*100:>5.1f}%")

# ── También imprimir subtotales por delivery method ───────────────────────────
print(f"\nRESUMEN POR DELIVERY METHOD")
print("-" * 60)
for dm in delivery_methods:
    dm_rows = [s for s in summary_rows if s["delivery_method"] == dm]
    n_dm  = sum(s["total_tickets"]   for s in dm_rows)
    cor   = sum(s["accion_correcta"] for s in dm_rows)
    pct   = cor / n_dm * 100 if n_dm else 0
    dm_lbl = DM_SHORT.get(dm, dm)
    print(f"  {dm_lbl:<12} {n_dm:>5} tickets  {cor:>5} correctos  {pct:>5.1f}% adh")

# ── Guardar CSV ───────────────────────────────────────────────────────────────
out = "reports/adherence_full_table.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
    writer.writeheader()
    writer.writerows(summary_rows)
print(f"\nCSV guardado: {out}")
