"""
Build F1 drill-down HTML report from macro_adherence_report.csv.

Usage:
    python -m scripts.build_f1_drilldown
"""
from __future__ import annotations

import csv
import json
import pathlib
from collections import defaultdict
from datetime import datetime, timezone

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = pathlib.Path(__file__).parent.parent
CSV_PATH = ROOT / "reports" / "macro_adherence_report.csv"
OUT_PATH = ROOT / "reports" / "f1_drilldown.html"


# ── Signal helpers ────────────────────────────────────────────────────────────
def _has_macro(row: dict) -> bool:
    """True if the ticket used the payment-confirmation macro."""
    return row.get("macro_applied", "").strip().lower() in ("true", "1", "yes")


def _has_rfc(row: dict) -> bool:
    """True if the reliable-correspondent tag is present in tags."""
    tags = row.get("tags", "")
    return "ria_payment_confirmation_reliable_correspondent_sent" in tags


def _has_trigger(row: dict) -> bool:
    """True if the payment_confirmation_macro tag is present (trigger fired)."""
    tags = row.get("tags", "")
    return "payment_confirmation_macro" in tags


def _channel(row: dict) -> str:
    tags = row.get("tags", "")
    if "inbound_call_-_va_to_rep" in tags or "cxi_ch_voice" in tags:
        return "voice_rep"
    if "inbound_call" in tags and "inbound_call_-_va_to_rep" not in tags:
        return "voice_direct"
    if "email_ticket_channel" in tags:
        return "email"
    return "other"


def _group(row: dict) -> str:
    tags = row.get("tags", "")
    if "ria_wfm_us_phone" in tags or "cxi_ria_wfm_nam_care_phone" in tags:
        return "us_care"
    if "ria_wfm_europe_es_uk_phone" in tags or "user_region_emea" in tags:
        return "emea_care"
    return "other"


# ── Core compute ─────────────────────────────────────────────────────────────
def compute_stats(csv_path: pathlib.Path) -> dict:
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            rows.append(r)

    # Only measurable = eligible_confirmed == True (the F1 population)
    measurable = [r for r in rows if r.get("eligible_confirmed", "").strip().lower() == "true"]
    # in_adherence == True
    adherent_rows = [r for r in measurable if r.get("in_adherence", "").strip().lower() == "true"]

    total_f1 = len(rows)
    total_measurable = len(measurable)
    total_adherent = len(adherent_rows)
    global_pct = round(total_adherent / total_measurable * 100, 2) if total_measurable else 0

    # ── by_dm ──────────────────────────────────────────────────────────────
    dm_n: dict[str, int] = defaultdict(int)
    dm_adh: dict[str, int] = defaultdict(int)
    for r in measurable:
        dm = r.get("delivery_method", "unknown").strip()
        dm_n[dm] += 1
    for r in adherent_rows:
        dm = r.get("delivery_method", "unknown").strip()
        dm_adh[dm] += 1

    by_dm = {}
    for dm in dm_n:
        n = dm_n[dm]
        a = dm_adh.get(dm, 0)
        by_dm[dm] = {"n": n, "adherent": a, "pct": round(a / n * 100, 2) if n else 0}

    # ── by_channel ────────────────────────────────────────────────────────
    ch_n: dict[str, int] = defaultdict(int)
    ch_adh: dict[str, int] = defaultdict(int)
    for r in measurable:
        ch = _channel(r)
        ch_n[ch] += 1
    for r in adherent_rows:
        ch = _channel(r)
        ch_adh[ch] += 1

    by_channel = {}
    for ch in ch_n:
        n = ch_n[ch]
        a = ch_adh.get(ch, 0)
        by_channel[ch] = {"n": n, "adherent": a, "pct": round(a / n * 100, 2) if n else 0}

    # ── by_group ──────────────────────────────────────────────────────────
    grp_n: dict[str, int] = defaultdict(int)
    grp_adh: dict[str, int] = defaultdict(int)
    for r in measurable:
        g = _group(r)
        grp_n[g] += 1
    for r in adherent_rows:
        g = _group(r)
        grp_adh[g] += 1

    by_group = {}
    for g in grp_n:
        n = grp_n[g]
        a = grp_adh.get(g, 0)
        by_group[g] = {"n": n, "adherent": a, "pct": round(a / n * 100, 2) if n else 0}

    # ── dm_x_channel ──────────────────────────────────────────────────────
    cross_n: dict[tuple, int] = defaultdict(int)
    cross_adh: dict[tuple, int] = defaultdict(int)
    for r in measurable:
        key = (r.get("delivery_method", "").strip(), _channel(r))
        cross_n[key] += 1
    for r in adherent_rows:
        key = (r.get("delivery_method", "").strip(), _channel(r))
        cross_adh[key] += 1

    dm_x_channel = []
    for (dm, ch), n in sorted(cross_n.items(), key=lambda x: -x[1]):
        a = cross_adh.get((dm, ch), 0)
        dm_x_channel.append({
            "dm": dm, "channel": ch, "n": n,
            "adherent": a,
            "pct": round(a / n * 100, 2) if n else 0
        })

    # ── by_signal ─────────────────────────────────────────────────────────
    n_macro = sum(1 for r in measurable if _has_macro(r))
    n_rfc = sum(1 for r in measurable if _has_rfc(r))
    n_trigger = sum(1 for r in measurable if _has_trigger(r))
    n_both = sum(1 for r in measurable if _has_macro(r) and _has_rfc(r))
    n_only_macro = sum(1 for r in measurable if _has_macro(r) and not _has_rfc(r))
    n_only_rfc = sum(1 for r in measurable if _has_rfc(r) and not _has_macro(r))
    n_none = sum(1 for r in measurable if not _has_macro(r) and not _has_rfc(r) and not _has_trigger(r))

    by_signal = {
        "n_macro": n_macro, "n_rfc": n_rfc, "n_trigger": n_trigger,
        "n_both_macro_rfc": n_both,
        "n_only_macro": n_only_macro, "n_only_rfc": n_only_rfc,
        "n_none": n_none,
    }

    # ── by_dm_by_signal ───────────────────────────────────────────────────
    by_dm_by_signal = {}
    for dm in dm_n:
        dm_rows = [r for r in measurable if r.get("delivery_method", "").strip() == dm]
        by_dm_by_signal[dm] = {
            "n_macro": sum(1 for r in dm_rows if _has_macro(r)),
            "n_rfc": sum(1 for r in dm_rows if _has_rfc(r)),
            "n_trigger": sum(1 for r in dm_rows if _has_trigger(r)),
            "n_none": sum(1 for r in dm_rows if not _has_macro(r) and not _has_rfc(r) and not _has_trigger(r)),
        }

    # ── top_gap_segments ──────────────────────────────────────────────────
    top_gap = sorted(
        [{"dm": e["dm"], "channel": e["channel"], "n": e["n"],
          "adherent": e["adherent"], "gap": e["n"] - e["adherent"], "pct": e["pct"]}
         for e in dm_x_channel],
        key=lambda x: -x["gap"]
    )[:5]

    # ── daily_by_group ────────────────────────────────────────────────────
    daily_global_n: dict[str, int] = defaultdict(int)
    daily_global_adh: dict[str, int] = defaultdict(int)
    daily_us_n: dict[str, int] = defaultdict(int)
    daily_us_adh: dict[str, int] = defaultdict(int)

    for r in measurable:
        date_str = r.get("created_at", "")[:10]
        daily_global_n[date_str] += 1
        if r.get("in_adherence", "").strip().lower() == "true":
            daily_global_adh[date_str] += 1
        if _group(r) == "us_care":
            daily_us_n[date_str] += 1
            if r.get("in_adherence", "").strip().lower() == "true":
                daily_us_adh[date_str] += 1

    def _daily_series(n_map, adh_map):
        return [
            {"date": d, "n": n_map[d], "adherent": adh_map.get(d, 0)}
            for d in sorted(n_map)
        ]

    daily_by_group = {
        "us_care": _daily_series(daily_us_n, daily_us_adh),
        "global": _daily_series(daily_global_n, daily_global_adh),
    }

    # ── best_segment (n >= 10, highest pct) ───────────────────────────────
    best = max(
        (e for e in dm_x_channel if e["n"] >= 10),
        key=lambda x: x["pct"],
        default=None
    )
    best_segment = f"{best['dm']} × {best['channel']} ({best['pct']}%)" if best else "—"

    return {
        "total_f1": total_f1,
        "total_measurable": total_measurable,
        "total_adherent": total_adherent,
        "global_pct": global_pct,
        "best_segment": best_segment,
        "by_dm": by_dm,
        "by_channel": by_channel,
        "by_group": by_group,
        "dm_x_channel": dm_x_channel,
        "by_signal": by_signal,
        "by_dm_by_signal": by_dm_by_signal,
        "top_gap_segments": top_gap,
        "daily_by_group": daily_by_group,
    }


# ── HTML builder ──────────────────────────────────────────────────────────────
_DM_LABELS = {
    "bank_deposit": "Bank Deposit",
    "office_pick-up": "Office Pick-Up",
    "mobile_payment": "Mobile Payment",
    "home_delivery": "Home Delivery",
}
_CH_LABELS = {
    "voice_rep": "Voice (Rep)",
    "voice_direct": "Voice (Direct)",
    "email": "Email",
    "other": "Other",
}
_GRP_LABELS = {
    "us_care": "US Care",
    "emea_care": "EMEA Care",
    "other": "Other Teams",
}


def _cell_color(pct: float) -> str:
    if pct == 0:
        return "#f5e6e6"   # very light red
    if pct < 10:
        return "#f2c4c4"   # red
    if pct < 30:
        return "#f7ddb0"   # orange
    return "#c9e6c9"       # green


def build_html(stats: dict) -> str:
    s = stats
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")

    # Build DM×Channel matrix
    dm_order = ["bank_deposit", "office_pick-up", "mobile_payment", "home_delivery"]
    ch_order = ["voice_rep", "voice_direct", "email", "other"]
    matrix: dict[tuple, dict] = {}
    for e in s["dm_x_channel"]:
        matrix[(e["dm"], e["channel"])] = e

    matrix_rows_html = ""
    for dm in dm_order:
        matrix_rows_html += f"<tr><td class='matrix-label'>{_DM_LABELS.get(dm, dm)}</td>"
        for ch in ch_order:
            cell = matrix.get((dm, ch))
            if cell and cell["n"] > 0:
                color = _cell_color(cell["pct"])
                matrix_rows_html += (
                    f"<td style='background:{color};text-align:center;padding:8px 6px'>"
                    f"<strong>{cell['pct']}%</strong><br><small>n={cell['n']}</small></td>"
                )
            else:
                matrix_rows_html += "<td style='background:#f0f0ec;color:#aaa;text-align:center'>—</td>"
        matrix_rows_html += "</tr>\n"

    # Top gap recommendations
    gap_recs = {
        ("bank_deposit", "email"): "Activate email auto-macro trigger for Bank Deposit confirmed tickets",
        ("bank_deposit", "voice_direct"): "Add macro to Voice Direct SOP — agent script must include macro step",
        ("office_pick-up", "voice_direct"): "Office Pick-Up voice script missing macro; add to handle-time checklist",
        ("office_pick-up", "email"): "Email template for Office Pick-Up lacks payment confirmation macro",
        ("bank_deposit", "voice_rep"): "VA-to-Rep handoff not preserving macro trigger — update transfer flow",
    }
    gap_rows_html = ""
    for i, seg in enumerate(s["top_gap_segments"], 1):
        key = (seg["dm"], seg["channel"])
        rec = gap_recs.get(key, "Review agent workflow for this segment")
        dm_lbl = _DM_LABELS.get(seg["dm"], seg["dm"])
        ch_lbl = _CH_LABELS.get(seg["channel"], seg["channel"])
        bar_pct = min(seg["pct"], 100)
        pct_bar = (
            f"<div style='height:6px;background:#e8e4dc;border-radius:3px;margin-top:4px'>"
            f"<div style='width:{bar_pct}%;height:100%;background:var(--clay);border-radius:3px'></div></div>"
        )
        gap_rows_html += f"""
        <tr>
          <td style='padding:12px 8px;font-weight:600'>{i}</td>
          <td style='padding:12px 8px'>{dm_lbl}</td>
          <td style='padding:12px 8px'>{ch_lbl}</td>
          <td style='padding:12px 8px;text-align:center'>{seg['n']}</td>
          <td style='padding:12px 8px;text-align:center'>{seg['adherent']}</td>
          <td style='padding:12px 8px;text-align:center;color:var(--red);font-weight:600'>{seg['gap']}</td>
          <td style='padding:12px 8px'>{pct_bar}{seg['pct']}%</td>
          <td style='padding:12px 8px;font-size:13px;color:#555'>{rec}</td>
        </tr>"""

    # DM table rows
    dm_table_rows = ""
    for dm, v in s["by_dm"].items():
        gap = v["n"] - v["adherent"]
        dm_table_rows += f"""
        <tr>
          <td style='padding:10px 8px'>{_DM_LABELS.get(dm, dm)}</td>
          <td style='padding:10px 8px;text-align:center'>{v['n']}</td>
          <td style='padding:10px 8px;text-align:center;color:var(--green)'>{v['adherent']}</td>
          <td style='padding:10px 8px;text-align:center;color:var(--red)'>{gap}</td>
          <td style='padding:10px 8px;text-align:center'>{v['pct']}%</td>
        </tr>"""

    # Channel table rows
    ch_table_rows = ""
    for ch, v in s["by_channel"].items():
        gap = v["n"] - v["adherent"]
        ch_table_rows += f"""
        <tr>
          <td style='padding:10px 8px'>{_CH_LABELS.get(ch, ch)}</td>
          <td style='padding:10px 8px;text-align:center'>{v['n']}</td>
          <td style='padding:10px 8px;text-align:center;color:var(--green)'>{v['adherent']}</td>
          <td style='padding:10px 8px;text-align:center;color:var(--red)'>{gap}</td>
          <td style='padding:10px 8px;text-align:center'>{v['pct']}%</td>
        </tr>"""

    # JS data payloads
    by_dm_json = json.dumps(s["by_dm"])
    by_channel_json = json.dumps(s["by_channel"])
    dm_x_channel_json = json.dumps(s["dm_x_channel"])
    by_signal_json = json.dumps(s["by_signal"])
    by_dm_by_signal_json = json.dumps(s["by_dm_by_signal"])
    daily_json = json.dumps(s["daily_by_group"])

    dm_labels_js = json.dumps({k: _DM_LABELS.get(k, k) for k in dm_order})
    ch_labels_js = json.dumps({k: _CH_LABELS.get(k, k) for k in ch_order})

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>F1 — Payment Confirmation · Análisis Detallado</title>
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
  .header {{
    background: var(--ink);
    color: var(--paper);
    padding: 32px 48px;
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 16px;
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
    display: block;
  }}
  .nav-bar {{
    background: var(--sand);
    border-bottom: 1px solid var(--border);
    padding: 10px 48px;
    display: flex;
    gap: 24px;
    font-size: 13px;
    flex-wrap: wrap;
  }}
  .nav-bar a {{
    color: var(--ink);
    text-decoration: none;
    opacity: 0.7;
    font-weight: 500;
  }}
  .nav-bar a:hover {{ opacity: 1; color: var(--clay); }}
  .nav-bar a.active {{ color: var(--clay); opacity: 1; border-bottom: 2px solid var(--clay); padding-bottom: 2px; }}
  .page {{ max-width: 1100px; margin: 0 auto; padding: 32px 24px 80px; }}
  .section {{ margin-bottom: 48px; }}
  .section-title {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--clay);
    margin-bottom: 8px;
  }}
  .section-desc {{
    font-size: 13px;
    color: #555;
    margin-bottom: 20px;
    max-width: 760px;
  }}
  .insight {{
    background: var(--sand);
    border-left: 3px solid var(--clay);
    padding: 14px 18px;
    border-radius: 0 6px 6px 0;
    margin-top: 18px;
    font-size: 13px;
    line-height: 1.6;
  }}
  .insight strong {{ color: var(--clay-dark); }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }}
  .kpi-card {{
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 24px;
  }}
  .kpi-label {{ font-size: 11px; font-weight: 600; letter-spacing: 0.8px; text-transform: uppercase; color: #888; margin-bottom: 8px; }}
  .kpi-value {{ font-size: 28px; font-weight: 700; color: var(--ink); line-height: 1; }}
  .kpi-sub {{ font-size: 12px; color: #888; margin-top: 4px; }}
  .kpi-card.highlight {{ border-left: 4px solid var(--clay); }}
  .kpi-card.warn {{ border-left: 4px solid var(--red); }}
  .kpi-card.good {{ border-left: 4px solid var(--green); }}
  .chart-wrap {{
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 20px;
  }}
  .chart-wrap canvas {{ max-height: 340px; }}
  table.data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    background: #fff;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }}
  table.data-table th {{
    background: var(--sand);
    font-weight: 600;
    padding: 10px 8px;
    text-align: left;
    font-size: 11px;
    letter-spacing: 0.6px;
    text-transform: uppercase;
    border-bottom: 1px solid var(--border);
  }}
  table.data-table tr:not(:last-child) td {{
    border-bottom: 1px solid rgba(20,20,19,0.05);
  }}
  table.data-table tr:hover td {{ background: #faf9f4; }}
  .matrix-label {{
    font-weight: 600;
    font-size: 12px;
    padding: 10px 12px;
    background: var(--sand);
    border-right: 1px solid var(--border);
    white-space: nowrap;
  }}
  .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
  @media (max-width: 720px) {{ .two-col {{ grid-template-columns: 1fr; }} }}

  /* EN/ES toggle */
  body.en [data-es] {{ display: none; }}
  body:not(.en) [data-en] {{ display: none; }}
</style>
</head>
<body>

<!-- ── HEADER ── -->
<div class="header">
  <div>
    <h1>F1 — Payment Confirmation &middot; <span data-es>Análisis Detallado</span><span data-en>Detailed Analysis</span></h1>
    <div class="sub">
      <span data-es>Desglose de adherencia por Delivery Method, Canal y Señales</span>
      <span data-en>Adherence breakdown by Delivery Method, Channel and Signals</span>
    </div>
  </div>
  <div class="meta">
    <div data-es>Generado: {today}</div>
    <div data-en>Generated: {today}</div>
    <button class="lang-btn" onclick="toggleLang()" id="langBtn">Switch to English</button>
  </div>
</div>

<!-- ── NAV ── -->
<nav class="nav-bar">
  <a href="context.html">
    <span data-es>Contexto</span><span data-en>Context</span>
  </a>
  <a href="daily_adherence.html">
    <span data-es>Tendencia Diaria</span><span data-en>Daily Trend</span>
  </a>
  <a href="adherence_report.html">
    <span data-es>Reporte Principal</span><span data-en>Main Report</span>
  </a>
  <a href="f1_drilldown.html" class="active">
    <span data-es>F1 Drill-Down</span><span data-en>F1 Drill-Down</span>
  </a>
</nav>

<div class="page">

<!-- ── A) KPI CARDS ── -->
<div class="section">
  <div class="section-title" data-es>Resumen Ejecutivo — F1 Payment Confirmation</div>
  <div class="section-title" data-en>Executive Summary — F1 Payment Confirmation</div>
  <div class="kpi-grid">
    <div class="kpi-card highlight">
      <div class="kpi-label"><span data-es>Tickets Elegibles</span><span data-en>Eligible Tickets</span></div>
      <div class="kpi-value">{s['total_measurable']:,}</div>
      <div class="kpi-sub">
        <span data-es>de {s['total_f1']:,} totales en F1</span>
        <span data-en>of {s['total_f1']:,} total F1 tickets</span>
      </div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label"><span data-es>Adherencia Global</span><span data-en>Global Adherence</span></div>
      <div class="kpi-value">{s['global_pct']}%</div>
      <div class="kpi-sub">
        <span data-es>{s['total_adherent']} tickets adherentes</span>
        <span data-en>{s['total_adherent']} adherent tickets</span>
      </div>
    </div>
    <div class="kpi-card warn">
      <div class="kpi-label"><span data-es>GAP Total</span><span data-en>Total GAP</span></div>
      <div class="kpi-value" style="color:var(--red)">{s['total_measurable'] - s['total_adherent']:,}</div>
      <div class="kpi-sub">
        <span data-es>tickets sin adherencia</span>
        <span data-en>non-adherent tickets</span>
      </div>
    </div>
    <div class="kpi-card good">
      <div class="kpi-label"><span data-es>Mejor Segmento (n≥10)</span><span data-en>Best Segment (n≥10)</span></div>
      <div class="kpi-value" style="font-size:16px;line-height:1.3;margin-top:4px">{s['best_segment']}</div>
      <div class="kpi-sub">
        <span data-es>mayor % de adherencia</span>
        <span data-en>highest adherence %</span>
      </div>
    </div>
  </div>
</div>

<!-- ── D) MAYOR GAP ABSOLUTO ── -->
<div class="section">
  <div class="section-title" data-es>¿Dónde está el mayor GAP?</div>
  <div class="section-title" data-en>Where Is the Biggest GAP?</div>
  <div class="section-desc">
    <span data-es>GAP absoluto (tickets no adherentes) por Delivery Method. El tamaño de la barra indica cuántos tickets quedan sin cumplir, no el porcentaje.</span>
    <span data-en>Absolute GAP (non-adherent tickets) by Delivery Method. Bar size shows raw ticket count, not percentage.</span>
  </div>
  <div class="chart-wrap">
    <canvas id="chartGap"></canvas>
  </div>
  <div class="insight">
    <strong data-es>Interpretación:</strong><strong data-en>Insight:</strong>
    <span data-es> Bank Deposit concentra el mayor GAP absoluto por volumen. Office Pick-Up tiene la adherencia porcentual más baja (&lt;1%), lo que indica una brecha sistemática de proceso, no solo de volumen. Priorizar Bank Deposit por impacto; Office Pick-Up por cobertura de proceso.</span>
    <span data-en> Bank Deposit has the largest absolute GAP due to volume. Office Pick-Up has the lowest percentage adherence (&lt;1%), indicating a systematic process gap, not just a volume issue. Prioritize Bank Deposit for impact; Office Pick-Up for process coverage.</span>
  </div>
</div>

<!-- ── E) ADHERENCIA POR DELIVERY METHOD ── -->
<div class="section">
  <div class="section-title" data-es>Adherencia por Delivery Method</div>
  <div class="section-title" data-en>Adherence by Delivery Method</div>
  <div class="section-desc">
    <span data-es>Barras agrupadas: tickets adherentes vs. GAP por método de entrega. Las etiquetas muestran el % de adherencia sobre cada par.</span>
    <span data-en>Grouped bars: adherent tickets vs. GAP by delivery method. Labels show adherence % on each pair.</span>
  </div>
  <div class="two-col">
    <div class="chart-wrap">
      <canvas id="chartDM"></canvas>
    </div>
    <div>
      <table class="data-table">
        <thead>
          <tr>
            <th><span data-es>Método</span><span data-en>Method</span></th>
            <th>n</th>
            <th><span data-es>Adh.</span><span data-en>Adh.</span></th>
            <th>GAP</th>
            <th>%</th>
          </tr>
        </thead>
        <tbody>{dm_table_rows}</tbody>
      </table>
      <div class="insight" style="margin-top:16px">
        <strong data-es>Bank Deposit lidera en volumen y adherencia relativa (5.49%).</strong>
        <strong data-en>Bank Deposit leads in volume and relative adherence (5.49%).</strong>
        <span data-es> Home Delivery tiene 0% — posiblemente el flujo de confirmación aún no está configurado para este método.</span>
        <span data-en> Home Delivery has 0% — the confirmation flow may not yet be configured for this method.</span>
      </div>
    </div>
  </div>
</div>

<!-- ── F) ADHERENCIA POR CANAL ── -->
<div class="section">
  <div class="section-title" data-es>Adherencia por Canal</div>
  <div class="section-title" data-en>Adherence by Channel</div>
  <div class="section-desc">
    <span data-es>Los canales de voz (Voice Rep y Voice Direct) muestran mejor adherencia que email. La regla de adherencia difiere por canal: voz requiere macro durante la llamada; email requiere respuesta con macro en <48h.</span>
    <span data-en>Voice channels (Voice Rep and Voice Direct) show higher adherence than email. The adherence rule differs by channel: voice requires macro during the call; email requires a macro response within 48h.</span>
  </div>
  <div class="two-col">
    <div class="chart-wrap">
      <canvas id="chartCH"></canvas>
    </div>
    <div>
      <table class="data-table">
        <thead>
          <tr>
            <th><span data-es>Canal</span><span data-en>Channel</span></th>
            <th>n</th>
            <th><span data-es>Adh.</span><span data-en>Adh.</span></th>
            <th>GAP</th>
            <th>%</th>
          </tr>
        </thead>
        <tbody>{ch_table_rows}</tbody>
      </table>
      <div class="insight" style="margin-top:16px">
        <strong data-es>Voice Rep (4.96%) supera a Email (2.44%).</strong>
        <strong data-en>Voice Rep (4.96%) outperforms Email (2.44%).</strong>
        <span data-es> "Other" (0.79%) agrupa canales sin clasificación — posibles tickets de chat o web que no tienen macro trigger habilitado.</span>
        <span data-en> "Other" (0.79%) groups unclassified channels — likely chat or web tickets without macro trigger enabled.</span>
      </div>
    </div>
  </div>
</div>

<!-- ── G) MATRIZ DM × CANAL ── -->
<div class="section">
  <div class="section-title" data-es>Matriz Delivery Method × Canal</div>
  <div class="section-title" data-en>Delivery Method × Channel Matrix</div>
  <div class="section-desc">
    <span data-es>Cada celda muestra % adherencia y volumen (n). Color: rojo &lt;10%, naranja 10-30%, verde &gt;30%.</span>
    <span data-en>Each cell shows adherence % and volume (n). Color: red &lt;10%, orange 10-30%, green &gt;30%.</span>
  </div>
  <div style="overflow-x:auto">
    <table class="data-table" style="min-width:600px">
      <thead>
        <tr>
          <th style="background:var(--sand)"></th>
          <th style="text-align:center;background:var(--sand)">Voice (Rep)</th>
          <th style="text-align:center;background:var(--sand)">Voice (Direct)</th>
          <th style="text-align:center;background:var(--sand)">Email</th>
          <th style="text-align:center;background:var(--sand)">Other</th>
        </tr>
      </thead>
      <tbody>
        {matrix_rows_html}
      </tbody>
    </table>
  </div>
  <div class="insight">
    <strong data-es>Hotspot de oportunidad:</strong><strong data-en>Opportunity hotspot:</strong>
    <span data-es> Bank Deposit × Voice Direct (8.18%) es el segmento de mayor adherencia relativa con volumen significativo (n=110). Office Pick-Up en todos los canales está en 0-2.7% — requiere intervención inmediata de proceso.</span>
    <span data-en> Bank Deposit × Voice Direct (8.18%) is the highest-adherence segment with significant volume (n=110). Office Pick-Up across all channels is 0-2.7% — requires immediate process intervention.</span>
  </div>
</div>

<!-- ── H) SEÑALES DE ADHERENCIA ── -->
<div class="section">
  <div class="section-title" data-es>¿Cómo llegaron los agentes a la adherencia?</div>
  <div class="section-title" data-en>How Are Agents Reaching Adherence?</div>
  <div class="section-desc">
    <span data-es>Distribución de señales en los tickets elegibles. <strong>Macro</strong>: agente aplicó el macro manualmente. <strong>RFC</strong>: tag de corresponsal confiable presente. <strong>Trigger</strong>: disparo automático detectado. <strong>Ninguna</strong>: sin señal.</span>
    <span data-en>Signal distribution across eligible tickets. <strong>Macro</strong>: agent applied macro manually. <strong>RFC</strong>: reliable correspondent tag present. <strong>Trigger</strong>: automatic trigger detected. <strong>None</strong>: no signal found.</span>
  </div>
  <div class="two-col">
    <div class="chart-wrap" style="display:flex;align-items:center;justify-content:center">
      <canvas id="chartDonut" style="max-height:280px"></canvas>
    </div>
    <div>
      <div style="padding:16px 0">
        <div style="display:flex;flex-direction:column;gap:10px;font-size:13px">
          <div><span style="display:inline-block;width:12px;height:12px;background:#CC785C;border-radius:2px;margin-right:8px"></span>
            <span data-es><strong>Solo Macro:</strong> agente aplicó macro sin RFC</span>
            <span data-en><strong>Macro only:</strong> agent applied macro without RFC</span>
          </div>
          <div><span style="display:inline-block;width:12px;height:12px;background:#6A8CAA;border-radius:2px;margin-right:8px"></span>
            <span data-es><strong>Solo RFC:</strong> tag de corresponsal confiable, sin macro</span>
            <span data-en><strong>RFC only:</strong> reliable correspondent tag, no macro</span>
          </div>
          <div><span style="display:inline-block;width:12px;height:12px;background:#5A8A6A;border-radius:2px;margin-right:8px"></span>
            <span data-es><strong>Macro + RFC:</strong> ambas señales presentes</span>
            <span data-en><strong>Macro + RFC:</strong> both signals present</span>
          </div>
          <div><span style="display:inline-block;width:12px;height:12px;background:#C9A27E;border-radius:2px;margin-right:8px"></span>
            <span data-es><strong>Trigger (automático):</strong> disparo de sistema detectado</span>
            <span data-en><strong>Trigger (auto):</strong> system trigger detected</span>
          </div>
          <div><span style="display:inline-block;width:12px;height:12px;background:#D1D7DE;border-radius:2px;margin-right:8px"></span>
            <span data-es><strong>Sin señal:</strong> no se detectó ninguna acción</span>
            <span data-en><strong>No signal:</strong> no action detected</span>
          </div>
        </div>
      </div>
      <div class="insight">
        <strong data-es>El 96.7% de tickets elegibles no tiene señal.</strong>
        <strong data-en>96.7% of eligible tickets have no signal.</strong>
        <span data-es> Los triggers automáticos (n=34) superan los RFC manuales (n=6) — el sistema puede escalar sin depender del agente.</span>
        <span data-en> Automatic triggers (n=34) outnumber manual RFC tags (n=6) — the system can scale without agent dependency.</span>
      </div>
    </div>
  </div>
</div>

<!-- ── I) SEÑALES POR DELIVERY METHOD ── -->
<div class="section">
  <div class="section-title" data-es>Señales por Delivery Method</div>
  <div class="section-title" data-en>Signals by Delivery Method</div>
  <div class="section-desc">
    <span data-es>Para cada DM: cuántos tickets tienen macro / RFC / trigger / ninguna señal.</span>
    <span data-en>For each DM: how many tickets have macro / RFC / trigger / no signal.</span>
  </div>
  <div class="chart-wrap">
    <canvas id="chartSignalDM"></canvas>
  </div>
  <div class="insight">
    <strong data-es>Bank Deposit concentra todos los triggers automáticos (n=34).</strong>
    <strong data-en>Bank Deposit concentrates all automatic triggers (n=34).</strong>
    <span data-es> Office Pick-Up, Mobile Payment y Home Delivery tienen 0 triggers — expandir la lógica de trigger a estos DMs es la palanca de mayor impacto.</span>
    <span data-en> Office Pick-Up, Mobile Payment and Home Delivery have 0 triggers — expanding trigger logic to these DMs is the highest-leverage lever.</span>
  </div>
</div>

<!-- ── J) TOP SEGMENTOS ── -->
<div class="section">
  <div class="section-title" data-es>Top 5 Segmentos con Mayor Oportunidad</div>
  <div class="section-title" data-en>Top 5 Highest-Opportunity Segments</div>
  <div class="section-desc">
    <span data-es>Combinaciones DM × Canal ordenadas por GAP absoluto, con recomendación accionable por segmento.</span>
    <span data-en>DM × Channel combinations sorted by absolute GAP, with an actionable recommendation per segment.</span>
  </div>
  <div style="overflow-x:auto">
    <table class="data-table" style="min-width:700px">
      <thead>
        <tr>
          <th>#</th>
          <th><span data-es>Método</span><span data-en>Method</span></th>
          <th><span data-es>Canal</span><span data-en>Channel</span></th>
          <th>n</th>
          <th><span data-es>Adh.</span><span data-en>Adh.</span></th>
          <th>GAP</th>
          <th>%</th>
          <th><span data-es>Recomendación</span><span data-en>Recommendation</span></th>
        </tr>
      </thead>
      <tbody>{gap_rows_html}</tbody>
    </table>
  </div>
  <div class="insight">
    <strong data-es>Cerrar estos 5 segmentos representaría 421 tickets adicionales adherentes</strong><strong data-en>Closing these 5 segments would add 421 adherent tickets</strong>
    <span data-es> — subiendo la tasa global de 3.25% a ~62.7% si se alcanzan. La prioridad debe ser Bank Deposit × Email y Bank Deposit × Voice Direct por volumen + factibilidad.</span>
    <span data-en> — raising the global rate from 3.25% to ~62.7% if achieved. Priority: Bank Deposit × Email and Bank Deposit × Voice Direct for volume + feasibility.</span>
  </div>
</div>

<!-- ── K) TENDENCIA DIARIA ── -->
<div class="section">
  <div class="section-title" data-es>Tendencia Diaria: US Care vs Global</div>
  <div class="section-title" data-en>Daily Trend: US Care vs Global</div>
  <div class="section-desc">
    <span data-es>% adherencia diario. Global incluye todos los grupos; US Care muestra el grupo norteamericano de forma aislada.</span>
    <span data-en>Daily adherence %. Global includes all groups; US Care shows the North American group in isolation.</span>
  </div>
  <div class="chart-wrap">
    <canvas id="chartDaily"></canvas>
  </div>
  <div class="insight">
    <strong data-es>El volumen se concentra a finales de mayo (2026-05-25 a 28).</strong>
    <strong data-en>Volume concentrates in late May (2026-05-25 to 28).</strong>
    <span data-es> La adherencia global cae a medida que sube el volumen — señal de que los procesos de adherencia no escalan linealmente. US Care tuvo adherencia 0% hasta el 28 de mayo.</span>
    <span data-en> Global adherence drops as volume increases — signal that adherence processes do not scale linearly. US Care had 0% adherence until May 28.</span>
  </div>
</div>

</div><!-- end .page -->

<script>
// ── Data ─────────────────────────────────────────────────────────────────────
const byDM         = {by_dm_json};
const byChannel    = {by_channel_json};
const dmXChannel   = {dm_x_channel_json};
const bySignal     = {by_signal_json};
const byDMSignal   = {by_dm_by_signal_json};
const dailyData    = {daily_json};
const DM_LABELS    = {dm_labels_js};
const CH_LABELS    = {ch_labels_js};

const DM_ORDER = ["bank_deposit","office_pick-up","mobile_payment","home_delivery"];
const CH_ORDER = ["voice_rep","voice_direct","email","other"];

const C = {{
  clay: "#CC785C", clayDark: "#A1543D",
  slate: "#6A8CAA", slateDark: "#3C4D5E",
  green: "#5A8A6A", red: "#B84A4A",
  sand: "#EBE5D7", ink: "#1F1D1B",
  tan: "#C9A27E", grey: "#D1D7DE",
}};

const baseOpts = {{
  responsive: true,
  plugins: {{ legend: {{ labels: {{ font: {{ family: "Inter" }} }} }} }},
  scales: {{
    x: {{ grid: {{ display: false }}, ticks: {{ font: {{ family: "Inter", size: 12 }} }} }},
    y: {{ grid: {{ color: "rgba(0,0,0,0.05)" }}, ticks: {{ font: {{ family: "Inter", size: 12 }} }} }},
  }}
}};

// ── D) Gap absolute by DM ─────────────────────────────────────────────────
(function() {{
  const gaps = DM_ORDER.map(dm => (byDM[dm] ? byDM[dm].n - byDM[dm].adherent : 0));
  const pcts = DM_ORDER.map(dm => (byDM[dm] ? byDM[dm].pct : 0));
  const ctx = document.getElementById("chartGap").getContext("2d");
  new Chart(ctx, {{
    type: "bar",
    data: {{
      labels: DM_ORDER.map(d => DM_LABELS[d]),
      datasets: [{{
        label: "GAP (tickets no adherentes)",
        data: gaps,
        backgroundColor: [C.red, "#D4766A", "#D88A6A", "#DBA07A"],
        borderRadius: 4,
      }}]
    }},
    options: {{
      ...baseOpts,
      indexAxis: "y",
      plugins: {{
        ...baseOpts.plugins,
        tooltip: {{
          callbacks: {{
            afterLabel: (ctx) => {{
              const dm = DM_ORDER[ctx.dataIndex];
              return `Adherencia: ${{byDM[dm]?.pct ?? 0}}%`;
            }}
          }}
        }}
      }}
    }}
  }});
}})();

// ── E) DM grouped bars ────────────────────────────────────────────────────
(function() {{
  const ctx = document.getElementById("chartDM").getContext("2d");
  new Chart(ctx, {{
    type: "bar",
    data: {{
      labels: DM_ORDER.map(d => DM_LABELS[d]),
      datasets: [
        {{
          label: "Adherente",
          data: DM_ORDER.map(dm => byDM[dm]?.adherent ?? 0),
          backgroundColor: C.green,
          borderRadius: 3,
        }},
        {{
          label: "GAP",
          data: DM_ORDER.map(dm => (byDM[dm] ? byDM[dm].n - byDM[dm].adherent : 0)),
          backgroundColor: C.red,
          borderRadius: 3,
        }}
      ]
    }},
    options: {{
      ...baseOpts,
      plugins: {{
        ...baseOpts.plugins,
        tooltip: {{
          callbacks: {{
            afterBody: (items) => {{
              const dm = DM_ORDER[items[0].dataIndex];
              return [`Adherencia: ${{byDM[dm]?.pct ?? 0}}%`];
            }}
          }}
        }}
      }}
    }}
  }});
}})();

// ── F) Channel grouped bars ───────────────────────────────────────────────
(function() {{
  const ctx = document.getElementById("chartCH").getContext("2d");
  new Chart(ctx, {{
    type: "bar",
    data: {{
      labels: CH_ORDER.map(c => CH_LABELS[c]),
      datasets: [
        {{
          label: "Adherente",
          data: CH_ORDER.map(ch => byChannel[ch]?.adherent ?? 0),
          backgroundColor: C.slate,
          borderRadius: 3,
        }},
        {{
          label: "GAP",
          data: CH_ORDER.map(ch => (byChannel[ch] ? byChannel[ch].n - byChannel[ch].adherent : 0)),
          backgroundColor: "#D1BFA7",
          borderRadius: 3,
        }}
      ]
    }},
    options: baseOpts,
  }});
}})();

// ── H) Donut signal ───────────────────────────────────────────────────────
(function() {{
  const ctx = document.getElementById("chartDonut").getContext("2d");
  new Chart(ctx, {{
    type: "doughnut",
    data: {{
      labels: ["Solo Macro","Solo RFC","Macro + RFC","Trigger (auto)","Sin señal"],
      datasets: [{{
        data: [
          bySignal.n_only_macro,
          bySignal.n_only_rfc,
          bySignal.n_both_macro_rfc,
          bySignal.n_trigger,
          bySignal.n_none
        ],
        backgroundColor: [C.clay, C.slate, C.green, C.tan, C.grey],
        borderWidth: 2,
        borderColor: "#F5F4EE",
      }}]
    }},
    options: {{
      responsive: true,
      cutout: "60%",
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: (ctx) => ` ${{ctx.label}}: ${{ctx.parsed}}`,
          }}
        }}
      }}
    }}
  }});
}})();

// ── I) Signal stacked by DM ───────────────────────────────────────────────
(function() {{
  const ctx = document.getElementById("chartSignalDM").getContext("2d");
  new Chart(ctx, {{
    type: "bar",
    data: {{
      labels: DM_ORDER.map(d => DM_LABELS[d]),
      datasets: [
        {{
          label: "Macro",
          data: DM_ORDER.map(dm => byDMSignal[dm]?.n_macro ?? 0),
          backgroundColor: C.clay,
          stack: "s",
          borderRadius: 0,
        }},
        {{
          label: "RFC",
          data: DM_ORDER.map(dm => byDMSignal[dm]?.n_rfc ?? 0),
          backgroundColor: C.slate,
          stack: "s",
        }},
        {{
          label: "Trigger (auto)",
          data: DM_ORDER.map(dm => byDMSignal[dm]?.n_trigger ?? 0),
          backgroundColor: C.tan,
          stack: "s",
        }},
        {{
          label: "Sin señal",
          data: DM_ORDER.map(dm => byDMSignal[dm]?.n_none ?? 0),
          backgroundColor: C.grey,
          stack: "s",
        }},
      ]
    }},
    options: {{
      ...baseOpts,
      scales: {{
        x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ font: {{ family: "Inter" }} }} }},
        y: {{ stacked: true, grid: {{ color: "rgba(0,0,0,0.05)" }}, ticks: {{ font: {{ family: "Inter" }} }} }},
      }},
    }}
  }});
}})();

// ── K) Daily trend ────────────────────────────────────────────────────────
(function() {{
  const global = dailyData.global ?? [];
  const usCare = dailyData.us_care ?? [];

  const allDates = [...new Set([
    ...global.map(d => d.date),
    ...usCare.map(d => d.date),
  ])].sort();

  function lookup(series, date) {{
    const found = series.find(d => d.date === date);
    if (!found || found.n === 0) return null;
    return Math.round(found.adherent / found.n * 10000) / 100;
  }}

  const ctx = document.getElementById("chartDaily").getContext("2d");
  new Chart(ctx, {{
    type: "line",
    data: {{
      labels: allDates,
      datasets: [
        {{
          label: "Global",
          data: allDates.map(d => lookup(global, d)),
          borderColor: C.clay,
          backgroundColor: "rgba(204,120,92,0.1)",
          tension: 0.3,
          pointRadius: 4,
          spanGaps: true,
          fill: true,
        }},
        {{
          label: "US Care",
          data: allDates.map(d => lookup(usCare, d)),
          borderColor: C.slate,
          backgroundColor: "rgba(106,140,170,0.1)",
          tension: 0.3,
          pointRadius: 4,
          spanGaps: true,
          fill: true,
          borderDash: [5,3],
        }},
      ]
    }},
    options: {{
      ...baseOpts,
      plugins: {{
        ...baseOpts.plugins,
        tooltip: {{
          callbacks: {{
            label: (ctx) => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y !== null ? ctx.parsed.y + "%" : "—"}}`,
          }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ display: false }}, ticks: {{ font: {{ family: "Inter", size: 11 }}, maxRotation: 45 }} }},
        y: {{
          grid: {{ color: "rgba(0,0,0,0.05)" }},
          ticks: {{ font: {{ family: "Inter" }}, callback: v => v + "%" }},
          min: 0,
        }},
      }},
    }}
  }});
}})();

// ── Lang toggle ───────────────────────────────────────────────────────────
function toggleLang() {{
  const isEN = document.body.classList.toggle("en");
  document.getElementById("langBtn").textContent = isEN ? "Ver en Español" : "Switch to English";
}}
</script>
</body>
</html>"""
    return html


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    print(f"Reading {CSV_PATH} ...")
    stats = compute_stats(CSV_PATH)

    print(f"  total_f1={stats['total_f1']}  measurable={stats['total_measurable']}"
          f"  adherent={stats['total_adherent']}  pct={stats['global_pct']}%")
    print(f"  best_segment: {stats['best_segment']}")

    html = build_html(stats)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_PATH}  ({len(html):,} chars)")


if __name__ == "__main__":
    main()
