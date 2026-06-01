"""
Genera reports/adherence_report.html — reporte ejecutivo de adherencia
de Payment Confirmation. Lee reports/adherence_full_table.csv.

Usage:
    python -m scripts.build_adherence_report
"""
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

# ── Leer datos ────────────────────────────────────────────────────────────────
rows = list(csv.DictReader(open("reports/adherence_full_table.csv", encoding="utf-8")))

def to_int(v):   return int(v)   if v else 0
def to_float(v): return float(v) if v else 0.0

# Totales globales
total_tickets   = sum(to_int(r["total_tickets"])   for r in rows)
total_correct   = sum(to_int(r["accion_correcta"]) for r in rows)
total_gap       = sum(to_int(r["sin_accion"])       for r in rows)
global_adh      = round(total_correct / total_tickets * 100, 1) if total_tickets else 0

# Por escenario (sumado sobre delivery methods)
esc_agg: dict[str, dict] = defaultdict(lambda: {"n": 0, "c": 0, "label": "", "desc": ""})
for r in rows:
    e = r["escenario"]
    esc_agg[e]["n"] += to_int(r["total_tickets"])
    esc_agg[e]["c"] += to_int(r["accion_correcta"])
    esc_agg[e]["label"] = r["escenario"]
    esc_agg[e]["desc"]  = r["descripcion"]

# F1 por delivery method
f1_rows = [r for r in rows if r["escenario"] == "F1"]
f1_total = sum(to_int(r["total_tickets"])   for r in f1_rows)
f1_correct= sum(to_int(r["accion_correcta"]) for r in f1_rows)
f1_gap    = f1_total - f1_correct
f1_adh    = round(f1_correct / f1_total * 100, 1) if f1_total else 0

DM_LABEL = {
    "bank_deposit":  "Bank Deposit",
    "office_pick-up": "Office Pick-Up",
    "mobile_payment": "Mobile Payment",
    "home_delivery":  "Home Delivery",
}

# Datos para chart.js — escenarios
esc_order = ["F1", "F2", "F3", "F4", "F5"]
esc_labels    = []
esc_adherent  = []
esc_gap       = []
esc_adh_pct   = []
for e in esc_order:
    if e not in esc_agg: continue
    d = esc_agg[e]
    pct = round(d["c"] / d["n"] * 100, 1) if d["n"] else 0
    esc_labels.append(e)
    esc_adherent.append(d["c"])
    esc_gap.append(d["n"] - d["c"])
    esc_adh_pct.append(pct)

# Datos para chart F1 por DM
dm_order = ["bank_deposit", "office_pick-up", "mobile_payment", "home_delivery"]
f1_dm_labels   = []
f1_dm_adherent = []
f1_dm_gap      = []
f1_dm_pct      = []
for dm in dm_order:
    match = [r for r in f1_rows if r["delivery_method"] == dm]
    if not match: continue
    r = match[0]
    n = to_int(r["total_tickets"])
    c = to_int(r["accion_correcta"])
    f1_dm_labels.append(DM_LABEL.get(dm, dm))
    f1_dm_adherent.append(c)
    f1_dm_gap.append(n - c)
    f1_dm_pct.append(to_float(r["adherencia_pct"]))

TODAY = date.today().strftime("%d %b %Y")

f4_n   = esc_agg.get("F4", {}).get("n", 0)
f4_c   = esc_agg.get("F4", {}).get("c", 0)
f4_pct = round(f4_c / max(f4_n, 1) * 100, 1)
f5_n   = esc_agg.get("F5", {}).get("n", 0)
f5_c   = esc_agg.get("F5", {}).get("c", 0)
f5_pct = round(f5_c / max(f5_n, 1) * 100, 1)

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Adherencia — Payment Confirmation</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --paper: #F5F4EE;
    --ink:   #1F1D1B;
    --clay:  #CC785C;
    --clay-dark: #A1543D;
    --sand:  #EBE5D7;
    --slate: #6A8CAA;
    --slate-dark: #3C4D5E;
    --border: rgba(20,20,19,0.10);
    --green: #5A8A6A;
    --red:   #B84A4A;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Inter, -apple-system, sans-serif;
    background: var(--paper);
    color: var(--ink);
    font-size: 14px;
    line-height: 1.5;
  }}
  /* ── Header ── */
  .header {{
    background: var(--ink);
    color: var(--paper);
    padding: 32px 48px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
  }}
  .header h1 {{ font-size: 22px; font-weight: 600; letter-spacing: -0.3px; }}
  .header .sub {{ font-size: 13px; opacity: 0.6; margin-top: 4px; }}
  .header .meta {{ font-size: 12px; opacity: 0.5; text-align: right; }}
  .lang-btn {{
    background: transparent;
    border: 1px solid rgba(245,244,238,0.3);
    color: var(--paper);
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    margin-top: 8px;
  }}
  /* ── Layout ── */
  .page {{ max-width: 1100px; margin: 0 auto; padding: 32px 24px 64px; }}
  .section {{ margin-bottom: 40px; }}
  .section-title {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--clay);
    margin-bottom: 16px;
  }}
  /* ── KPI Grid ── */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
  .kpi {{
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
  }}
  .kpi .value {{ font-size: 32px; font-weight: 700; line-height: 1; }}
  .kpi .label {{ font-size: 12px; color: #666; margin-top: 6px; }}
  .kpi.alert .value {{ color: var(--red); }}
  .kpi.good  .value {{ color: var(--green); }}
  .kpi.neutral .value {{ color: var(--clay); }}
  /* ── Cards ── */
  .card {{
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 16px;
  }}
  .card h3 {{ font-size: 15px; font-weight: 600; margin-bottom: 4px; }}
  .card .analysis {{
    background: var(--sand);
    border-radius: 6px;
    padding: 14px 16px;
    font-size: 13px;
    margin-top: 16px;
    line-height: 1.6;
  }}
  /* ── Two-col ── */
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  /* ── Table ── */
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{
    text-align: left;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #888;
    border-bottom: 2px solid var(--border);
    padding: 8px 12px;
  }}
  td {{ padding: 10px 12px; border-bottom: 1px solid var(--border); }}
  tr:last-child td {{ border-bottom: none; }}
  .adh-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-weight: 600;
    font-size: 12px;
  }}
  .adh-low  {{ background: #FDE8E8; color: var(--red); }}
  .adh-mid  {{ background: #FFF3E0; color: #B06000; }}
  .adh-high {{ background: #E8F5E9; color: var(--green); }}
  /* ── Progress bar ── */
  .bar-wrap {{ background: var(--sand); border-radius: 4px; height: 8px; margin-top: 4px; }}
  .bar-fill {{ height: 8px; border-radius: 4px; background: var(--clay); }}
  /* ── Bullets ── */
  .bullets {{ list-style: none; padding: 0; }}
  .bullets li {{
    padding: 10px 0 10px 24px;
    border-bottom: 1px solid var(--border);
    position: relative;
    font-size: 13px;
  }}
  .bullets li:last-child {{ border-bottom: none; }}
  .bullets li::before {{
    content: attr(data-num);
    position: absolute;
    left: 0;
    color: var(--clay);
    font-weight: 700;
  }}
  /* ── Canvas ── */
  .chart-wrap {{ position: relative; height: 260px; }}
  /* ── Lang toggle ── */
  [data-en] {{ display: none; }}
  body.en [data-es] {{ display: none; }}
  body.en [data-en] {{ display: unset; }}
  .card.en [data-es] {{ display: none; }}
  .card.en [data-en] {{ display: unset; }}
</style>
</head>
<body>

<!-- HEADER -->
<div class="header">
  <div>
    <div class="sub" data-es>Ria Money Transfer · Zendesk Analytics</div>
    <div class="sub" data-en>Ria Money Transfer · Zendesk Analytics</div>
    <h1 data-es>Adherencia — Payment Confirmation</h1>
    <h1 data-en>Adherence — Payment Confirmation</h1>
    <div class="sub" data-es>Últimos 30 días · {TODAY} · n = {total_tickets:,} tickets</div>
    <div class="sub" data-en>Last 30 days · {TODAY} · n = {total_tickets:,} tickets</div>
  </div>
  <div class="meta">
    <button class="lang-btn" onclick="document.body.classList.toggle('en');this.textContent=document.body.classList.contains('en')?'ES':'EN'">EN</button>
  </div>
</div>

<div style="background:#EBE5D7;padding:11px 24px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center;border-bottom:1px solid rgba(20,20,19,.10)">
  <a href="index.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid #CC785C;background:#CC785C;color:#fff"><span data-es>Reporte F1–F5</span><span data-en>F1–F5 Report</span></a>
  <a href="context.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>Contexto y Metodología</span><span data-en>Context & Methodology</span></a>
  <a href="daily_adherence.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>Dashboard Diario</span><span data-en>Daily Dashboard</span></a>
  <a href="f1_drilldown.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>F1 Detalle</span><span data-en>F1 Detail</span></a>
  <a href="contact_reasons.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>Motivos de Contacto</span><span data-en>Contact Reasons</span></a>
</div>

<div class="page">

<!-- KPIs -->
<div class="section">
  <div class="section-title" data-es>Resumen Ejecutivo</div>
  <div class="section-title" data-en>Executive Summary</div>
  <div class="kpi-grid">
    <div class="kpi neutral">
      <div class="value">{total_tickets:,}</div>
      <div class="label" data-es>Tickets analizados (30 días)</div>
      <div class="label" data-en>Tickets analyzed (30 days)</div>
    </div>
    <div class="kpi alert">
      <div class="value">{global_adh}%</div>
      <div class="label" data-es>Adherencia global</div>
      <div class="label" data-en>Overall adherence</div>
    </div>
    <div class="kpi alert">
      <div class="value">{total_gap:,}</div>
      <div class="label" data-es>Tickets sin acción correcta (GAP)</div>
      <div class="label" data-en>Tickets without correct action (GAP)</div>
    </div>
    <div class="kpi alert">
      <div class="value">{f1_gap:,}</div>
      <div class="label" data-es>GAP crítico — F1 Payment Confirmation</div>
      <div class="label" data-en>Critical GAP — F1 Payment Confirmation</div>
    </div>
  </div>

  <!-- Bullets ejecutivos -->
  <div class="card" style="margin-top:16px;">
    <ul class="bullets">
      <li data-num="→" data-es>De {total_tickets:,} tickets Paid resueltos en 30 días, solo <strong>{total_correct} ({global_adh}%)</strong> recibieron la acción correcta según el playbook operativo.</li>
      <li data-num="→" data-en>Of {total_tickets:,} resolved Paid tickets in 30 days, only <strong>{total_correct} ({global_adh}%)</strong> received the correct action per the operational playbook.</li>
      <li data-num="→" data-es><strong>F1 es el escenario más crítico</strong>: {f1_total:,} tickets elegibles para Payment Confirmation, solo {f1_correct} con la macro aplicada ({f1_adh}%). El GAP es de <strong>{f1_gap:,} tickets</strong>.</li>
      <li data-num="→" data-en><strong>F1 is the most critical scenario</strong>: {f1_total:,} tickets eligible for Payment Confirmation, only {f1_correct} with macro applied ({f1_adh}%). Gap is <strong>{f1_gap:,} tickets</strong>.</li>
      <li data-num="→" data-es>F2 (POP con SC) es el escenario mejor ejecutado — Office Pick-Up alcanza <strong>73%</strong> de adherencia, lo que demuestra que el proceso funciona cuando está claro.</li>
      <li data-num="→" data-en>F2 (POP with SC) is the best-executed scenario — Office Pick-Up reaches <strong>73%</strong> adherence, proving the process works when clearly defined.</li>
      <li data-num="→" data-es>F4 y F5 (tickets Unreliable, exclusivos de Bank Deposit) tienen adherencia moderada ({f4_c}/{f4_n} = {f4_pct}% y {f5_c}/{f5_n} = {f5_pct}%).</li>
      <li data-num="→" data-en>F4 and F5 (Unreliable tickets, Bank Deposit only) show moderate adherence ({f4_c}/{f4_n} = {f4_pct}% and {f5_c}/{f5_n} = {f5_pct}%).</li>
    </ul>
  </div>
</div>

<!-- CHART: ESCENARIOS -->
<div class="section">
  <div class="section-title" data-es>Adherencia por Escenario</div>
  <div class="section-title" data-en>Adherence by Scenario</div>
  <div class="two-col">
    <div class="card">
      <h3 data-es>Tickets por Escenario — Adherente vs GAP</h3>
      <h3 data-en>Tickets by Scenario — Adherent vs GAP</h3>
      <div class="chart-wrap">
        <canvas id="chartEsc"></canvas>
      </div>
    </div>
    <div class="card">
      <h3 data-es>% Adherencia por Escenario</h3>
      <h3 data-en>Adherence % by Scenario</h3>
      <div class="chart-wrap">
        <canvas id="chartEscPct"></canvas>
      </div>
    </div>
  </div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th data-es>Esc.</th><th data-es>Acción Esperada</th><th data-es>Tickets</th><th data-es>Correctos</th><th data-es>GAP</th><th data-es>Adherencia</th>
          <th data-en>Esc.</th><th data-en>Expected Action</th><th data-en>Tickets</th><th data-en>Correct</th><th data-en>GAP</th><th data-en>Adherence</th>
        </tr>
      </thead>
      <tbody>"""

ESC_ACTION_ES = {
    "F1": "Payment Confirmation (macro)",
    "F2": "POP vía SC existente",
    "F3": "Iniciar POP (>48h)",
    "F4": "ETA email / POP Day 1",
    "F5": "SC al corresponsal",
}
ESC_ACTION_EN = {
    "F1": "Payment Confirmation (macro)",
    "F2": "POP via existing SC",
    "F3": "Initiate POP (>48h)",
    "F4": "ETA email / POP Day 1",
    "F5": "SC to correspondent",
}

for e in esc_order:
    if e not in esc_agg: continue
    d = esc_agg[e]
    pct = round(d["c"] / d["n"] * 100, 1) if d["n"] else 0
    badge_cls = "adh-high" if pct >= 40 else ("adh-mid" if pct >= 15 else "adh-low")
    html += f"""
        <tr>
          <td><strong>{e}</strong></td>
          <td data-es>{ESC_ACTION_ES[e]}</td>
          <td data-en>{ESC_ACTION_EN[e]}</td>
          <td>{d['n']:,}</td>
          <td>{d['c']:,}</td>
          <td>{d['n']-d['c']:,}</td>
          <td><span class="adh-badge {badge_cls}">{pct}%</span></td>
        </tr>"""

html += f"""
      </tbody>
    </table>
    <div class="analysis">
      <span data-es><strong>F1 concentra el mayor volumen de GAP ({f1_gap:,} tickets)</strong> — es la oportunidad de mejora más grande. F2 muestra que cuando el proceso está claro (SC ya abierta), los agentes lo siguen con mucha mayor consistencia.</span>
      <span data-en><strong>F1 concentrates the largest GAP volume ({f1_gap:,} tickets)</strong> — it is the biggest improvement opportunity. F2 shows that when the process is clear (SC already open), agents follow it with much greater consistency.</span>
    </div>
  </div>
</div>

<!-- CHART: F1 por DM -->
<div class="section">
  <div class="section-title" data-es>F1 · Payment Confirmation — Detalle por Delivery Method</div>
  <div class="section-title" data-en>F1 · Payment Confirmation — Breakdown by Delivery Method</div>
  <div class="two-col">
    <div class="card">
      <h3 data-es>Tickets Elegibles vs Adherentes</h3>
      <h3 data-en>Eligible vs Adherent Tickets</h3>
      <div class="chart-wrap">
        <canvas id="chartF1"></canvas>
      </div>
    </div>
    <div class="card">
      <h3 data-es>% Adherencia F1 por Delivery Method</h3>
      <h3 data-en>F1 Adherence % by Delivery Method</h3>
      <table style="margin-top:8px;">
        <thead>
          <tr>
            <th data-es>Delivery Method</th><th data-es>Elegibles</th><th data-es>Con macro</th><th data-es>GAP</th><th data-es>ADH%</th>
            <th data-en>Delivery Method</th><th data-en>Eligible</th><th data-en>With macro</th><th data-en>GAP</th><th data-en>ADH%</th>
          </tr>
        </thead>
        <tbody>"""

for r in f1_rows:
    n   = to_int(r["total_tickets"])
    c   = to_int(r["accion_correcta"])
    pct = to_float(r["adherencia_pct"])
    badge_cls = "adh-high" if pct >= 40 else ("adh-mid" if pct >= 15 else "adh-low")
    dm_lbl = DM_LABEL.get(r["delivery_method"], r["delivery_method"])
    html += f"""
          <tr>
            <td>{dm_lbl}</td>
            <td>{n:,}</td>
            <td>{c}</td>
            <td>{n-c:,}</td>
            <td><span class="adh-badge {badge_cls}">{pct}%</span></td>
          </tr>"""

html += f"""
        </tbody>
      </table>
      <div class="bar-wrap" style="margin-top:12px;height:12px;">
        <div class="bar-fill" style="width:{f1_adh}%;background:var(--clay);height:12px;"></div>
      </div>
      <div style="font-size:12px;color:#888;margin-top:4px;" data-es>Adherencia F1 global: <strong>{f1_adh}%</strong> ({f1_correct}/{f1_total})</div>
      <div style="font-size:12px;color:#888;margin-top:4px;" data-en>Overall F1 adherence: <strong>{f1_adh}%</strong> ({f1_correct}/{f1_total})</div>
    </div>
  </div>
  <div class="card">
    <div class="analysis">
      <span data-es><strong>Bank Deposit tiene el mayor volumen absoluto de GAP (333 tickets)</strong>, pero Office Pick-Up tiene la adherencia más baja (0.4% — 1 de 235 tickets). Esto sugiere que la macro de Payment Confirmation no está siendo considerada para tickets de Pick-Up a pesar de aplicar el mismo playbook. Mobile Payment también está en rojo con 1.2%.</span>
      <span data-en><strong>Bank Deposit has the largest absolute GAP (333 tickets)</strong>, but Office Pick-Up has the lowest adherence (0.4% — 1 out of 235 tickets). This suggests the Payment Confirmation macro is not being considered for Pick-Up tickets despite the same playbook applying. Mobile Payment is also critical at 1.2%.</span>
    </div>
  </div>
</div>

<!-- FULL TABLE BY DM -->
<div class="section">
  <div class="section-title" data-es>Tabla Completa — Todos los Escenarios × Delivery Method</div>
  <div class="section-title" data-en>Full Table — All Scenarios × Delivery Method</div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th data-es>Esc.</th><th data-es>Delivery Method</th><th data-es>Tickets</th><th data-es>%Total</th><th data-es>Correctos</th><th data-es>GAP</th><th data-es>Adherencia</th>
          <th data-en>Sce.</th><th data-en>Delivery Method</th><th data-en>Tickets</th><th data-en>%Total</th><th data-en>Correct</th><th data-en>GAP</th><th data-en>Adherence</th>
        </tr>
      </thead>
      <tbody>"""

for r in rows:
    n   = to_int(r["total_tickets"])
    c   = to_int(r["accion_correcta"])
    pct = to_float(r["adherencia_pct"])
    badge_cls = "adh-high" if pct >= 40 else ("adh-mid" if pct >= 15 else "adh-low")
    dm_lbl = DM_LABEL.get(r["delivery_method"], r["delivery_method"])
    html += f"""
        <tr>
          <td><strong>{r['escenario']}</strong></td>
          <td>{dm_lbl}</td>
          <td>{n:,}</td>
          <td>{r['pct_del_total']}%</td>
          <td>{c}</td>
          <td>{n-c:,}</td>
          <td><span class="adh-badge {badge_cls}">{pct}%</span></td>
        </tr>"""

html += f"""
      </tbody>
      <tfoot>
        <tr style="font-weight:600;border-top:2px solid var(--border);">
          <td colspan="2" data-es>TOTAL</td>
          <td colspan="2" data-en>TOTAL</td>
          <td>{total_tickets:,}</td>
          <td>100%</td>
          <td>{total_correct}</td>
          <td>{total_gap:,}</td>
          <td><span class="adh-badge adh-low">{global_adh}%</span></td>
        </tr>
      </tfoot>
    </table>
  </div>
</div>

<!-- RECOMENDACIONES -->
<div class="section">
  <div class="section-title" data-es>Recomendaciones</div>
  <div class="section-title" data-en>Recommendations</div>
  <div class="card">
    <ul class="bullets">
      <li data-num="1" data-es><strong>Entrenamiento urgente en F1 para todos los delivery methods.</strong> El 97.2% de los tickets elegibles para Payment Confirmation no recibe la macro. Priorizar office_pick-up (234 tickets de GAP) y bank_deposit (333 tickets de GAP).</li>
      <li data-num="1" data-en><strong>Urgent F1 training across all delivery methods.</strong> 97.2% of Payment Confirmation-eligible tickets do not receive the macro. Prioritize office_pick-up (234 GAP tickets) and bank_deposit (333 GAP tickets).</li>
      <li data-num="2" data-es><strong>Replicar el modelo de F2 Office Pick-Up (73%) hacia F1.</strong> Los agentes que manejan office_pick-up SÍ aplican POP correctamente cuando hay SC abierta — el problema es la falta de consistencia en la detección del escenario F1.</li>
      <li data-num="2" data-en><strong>Replicate the F2 Office Pick-Up model (73%) into F1.</strong> Agents handling office_pick-up DO apply POP correctly when SC is open — the issue is lack of consistency in detecting the F1 scenario.</li>
      <li data-num="3" data-es><strong>Verificar si la macro de Payment Confirmation está disponible para todos los grupos que atienden office_pick-up y mobile_payment.</strong> La adherencia casi nula en esos delivery methods puede indicar que la macro no aparece en su interfaz.</li>
      <li data-num="3" data-en><strong>Verify whether the Payment Confirmation macro is available to all groups handling office_pick-up and mobile_payment.</strong> Near-zero adherence in those delivery methods may indicate the macro doesn't appear in their interface.</li>
      <li data-num="4" data-es><strong>F5 necesita atención (8.8%).</strong> Cuando la transferencia es Unreliable y tiene más de 48h, el agente debe abrir SC al corresponsal — acción que requiere más pasos y tiene la segunda peor adherencia.</li>
      <li data-num="4" data-en><strong>F5 needs attention (8.8%).</strong> When the transfer is Unreliable and over 48h, the agent must open an SC to the correspondent — an action that requires more steps and has the second-worst adherence.</li>
      <li data-num="5" data-es><strong>Considerar automatización para F1.</strong> Si el sistema puede detectar bank_deposit + Paid + &lt;48h + sin SC, un trigger puede enviar automáticamente la confirmación de pago, eliminando la dependencia del agente.</li>
      <li data-num="5" data-en><strong>Consider automation for F1.</strong> If the system can detect bank_deposit + Paid + &lt;48h + no SC, a trigger can automatically send the payment confirmation, removing agent dependency.</li>
      <li data-num="6" data-es><strong>Establecer meta de adherencia mensual.</strong> Línea base actual: 12.7% global / 2.8% F1. Meta sugerida: 40% global / 25% F1 en 90 días con plan de entrenamiento activo.</li>
      <li data-num="6" data-en><strong>Establish monthly adherence targets.</strong> Current baseline: 12.7% overall / 2.8% F1. Suggested target: 40% overall / 25% F1 in 90 days with active training plan.</li>
    </ul>
  </div>
</div>

</div><!-- /page -->

<script>
const CLAY      = '#CC785C';
const CLAY_DARK = '#A1543D';
const SAND      = '#EBE5D7';
const SLATE     = '#6A8CAA';
const GREEN     = '#5A8A6A';
const RED       = '#B84A4A';
const INK       = '#1F1D1B';

const escLabels   = {json.dumps(esc_labels)};
const escAdherent = {json.dumps(esc_adherent)};
const escGap      = {json.dumps(esc_gap)};
const escAdh      = {json.dumps(esc_adh_pct)};

const f1Labels    = {json.dumps(f1_dm_labels)};
const f1Adherent  = {json.dumps(f1_dm_adherent)};
const f1Gap       = {json.dumps(f1_dm_gap)};
const f1Pct       = {json.dumps(f1_dm_pct)};

const defOpts = {{
  responsive: true,
  maintainAspectRatio: false,
  plugins: {{
    legend: {{ position: 'bottom', labels: {{ font: {{ size: 12 }}, boxWidth: 12 }} }},
    tooltip: {{ cornerRadius: 4 }}
  }}
}};

// Chart 1: Escenarios stacked bar
new Chart(document.getElementById('chartEsc'), {{
  type: 'bar',
  data: {{
    labels: escLabels,
    datasets: [
      {{ label: 'Adherente', data: escAdherent, backgroundColor: GREEN, borderRadius: 3 }},
      {{ label: 'GAP', data: escGap, backgroundColor: '#E8D0C4', borderRadius: 3 }}
    ]
  }},
  options: {{ ...defOpts, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, grid: {{ color: '#eee' }} }} }} }}
}});

// Chart 2: % Adherencia por escenario
new Chart(document.getElementById('chartEscPct'), {{
  type: 'bar',
  data: {{
    labels: escLabels,
    datasets: [{{
      label: '% Adherencia',
      data: escAdh,
      backgroundColor: escAdh.map(v => v >= 40 ? GREEN : v >= 15 ? CLAY : RED),
      borderRadius: 4
    }}]
  }},
  options: {{
    ...defOpts,
    scales: {{
      y: {{ min: 0, max: 100, ticks: {{ callback: v => v + '%' }}, grid: {{ color: '#eee' }} }}
    }},
    plugins: {{
      ...defOpts.plugins,
      legend: {{ display: false }}
    }}
  }}
}});

// Chart 3: F1 por DM stacked bar
new Chart(document.getElementById('chartF1'), {{
  type: 'bar',
  data: {{
    labels: f1Labels,
    datasets: [
      {{ label: 'Adherente', data: f1Adherent, backgroundColor: GREEN, borderRadius: 3 }},
      {{ label: 'GAP', data: f1Gap, backgroundColor: '#E8D0C4', borderRadius: 3 }}
    ]
  }},
  options: {{ ...defOpts, scales: {{ x: {{ stacked: true }}, y: {{ stacked: true, grid: {{ color: '#eee' }} }} }} }}
}});
</script>
</body>
</html>"""

out = Path("reports/adherence_report.html")
out.write_text(html, encoding="utf-8")
size_kb = out.stat().st_size / 1024
print(f"Reporte guardado: {out}  ({size_kb:.0f} KB)")
