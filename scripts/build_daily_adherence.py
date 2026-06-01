"""
Genera reports/daily_adherence.html — dashboard de adherencia diaria F1
enfocado en US Care. Muestra tendencia día a día para monitorear adopción.

Usage:
    python -m scripts.build_daily_adherence
"""
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

# ── Tags ─────────────────────────────────────────────────────────────────────
MACRO_TAG   = "ria_payment_confirmation_reliable_correspondent_sent"
RFC_TAG     = "order__payment_confirmation"
VA_ONLY     = {"inbound_call_-_va_only", "va_only_solved"}
US_WFM      = {"ria_wfm_us_phone", "cxi_ria_wfm_nam_care_phone", "ria_wfm_nam_care_phone"}

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

def get_channel(tags):
    if tags & VA_ONLY:                              return "va_only"
    if tags & {"inbound_call_-_va_to_rep","cxi_ch_voice"}: return "voice_rep"
    if "inbound_call" in tags:                      return "voice_direct"
    if tags & {"native_messaging","live_chat_-_message"}: return "messaging"
    if "email_ticket_channel" in tags:              return "email"
    return "other"

def is_adherent(tags, channel):
    if channel == "va_only": return None  # excluir
    return bool(tags & {MACRO_TAG, RFC_TAG})

# ── Leer datos ────────────────────────────────────────────────────────────────
rows = list(csv.DictReader(open("reports/macro_adherence_report.csv", encoding="utf-8")))
f1_all = [r for r in rows if classify(r) == "F1"]

# ── Parsear fecha y canal ─────────────────────────────────────────────────────
for r in f1_all:
    tags = set(r.get("tags","").split("|"))
    r["_tags"]    = tags
    r["_channel"] = get_channel(tags)
    r["_us_care"] = bool(tags & US_WFM)
    r["_adherent"]= is_adherent(tags, r["_channel"])
    try:
        r["_date"] = r["created_at"][:10]  # YYYY-MM-DD
    except Exception:
        r["_date"] = None

# ── Conjuntos ─────────────────────────────────────────────────────────────────
f1_measurable = [r for r in f1_all if r["_adherent"] is not None]
f1_us         = [r for r in f1_measurable if r["_us_care"]]
f1_global     = f1_measurable

# ── Agregado diario ───────────────────────────────────────────────────────────
def daily_agg(bucket):
    by_day = defaultdict(lambda: {"n": 0, "adh": 0})
    for r in bucket:
        d = r["_date"]
        if not d: continue
        by_day[d]["n"]   += 1
        by_day[d]["adh"] += int(bool(r["_adherent"]))
    days = sorted(by_day.keys())
    return days, [by_day[d]["n"] for d in days], [by_day[d]["adh"] for d in days], \
           [round(by_day[d]["adh"]/by_day[d]["n"]*100,1) if by_day[d]["n"] else 0 for d in days]

days_us,    n_us,    adh_us,    pct_us    = daily_agg(f1_us)
days_gl,    n_gl,    adh_gl,    pct_gl    = daily_agg(f1_global)

# ── Canal breakdown ───────────────────────────────────────────────────────────
ch_data = defaultdict(lambda: {"n":0,"adh":0})
for r in f1_measurable:
    ch_data[r["_channel"]]["n"]   += 1
    ch_data[r["_channel"]]["adh"] += int(bool(r["_adherent"]))

# ── KPIs ──────────────────────────────────────────────────────────────────────
tot_us   = len(f1_us)
adh_us_n = sum(1 for r in f1_us if r["_adherent"])
pct_us_kpi = round(adh_us_n/tot_us*100,1) if tot_us else 0

tot_gl   = len(f1_global)
adh_gl_n = sum(1 for r in f1_global if r["_adherent"])
pct_gl_kpi = round(adh_gl_n/tot_gl*100,1) if tot_gl else 0

TODAY = date.today().strftime("%d %b %Y")

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Payment Confirmation — Adherencia Diaria</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{
  --paper:#F5F4EE;--ink:#1F1D1B;--clay:#CC785C;--clay-dark:#A1543D;
  --sand:#EBE5D7;--slate:#6A8CAA;--border:rgba(20,20,19,0.10);
  --green:#5A8A6A;--red:#B84A4A;--orange:#C07820;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,-apple-system,sans-serif;background:var(--paper);color:var(--ink);font-size:14px;line-height:1.5}}
.header{{background:var(--ink);color:var(--paper);padding:28px 48px;display:flex;justify-content:space-between;align-items:flex-end}}
.header h1{{font-size:20px;font-weight:600}}
.header .sub{{font-size:12px;opacity:.6;margin-top:4px}}
.lang-btn{{background:transparent;border:1px solid rgba(245,244,238,.3);color:var(--paper);padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px}}
.page{{max-width:1100px;margin:0 auto;padding:28px 24px 60px}}
.sec-title{{font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--clay);margin-bottom:14px}}
.section{{margin-bottom:36px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.kpi{{background:#fff;border:1px solid var(--border);border-radius:8px;padding:18px}}
.kpi .val{{font-size:30px;font-weight:700;line-height:1}}
.kpi .lbl{{font-size:12px;color:#777;margin-top:5px}}
.kpi.red .val{{color:var(--red)}}
.kpi.clay .val{{color:var(--clay)}}
.kpi.green .val{{color:var(--green)}}
.card{{background:#fff;border:1px solid var(--border);border-radius:8px;padding:22px;margin-bottom:14px}}
.card h3{{font-size:14px;font-weight:600;margin-bottom:14px}}
.note{{background:var(--sand);border-radius:6px;padding:12px 14px;font-size:13px;margin-top:14px;line-height:1.6}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.chart-wrap{{position:relative;height:240px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:#888;border-bottom:2px solid var(--border);padding:7px 10px;text-align:left}}
td{{padding:9px 10px;border-bottom:1px solid var(--border)}}
tr:last-child td{{border-bottom:none}}
.badge{{display:inline-block;padding:2px 7px;border-radius:10px;font-weight:600;font-size:12px}}
.b-red{{background:#FDE8E8;color:var(--red)}}
.b-mid{{background:#FFF3E0;color:var(--orange)}}
.b-green{{background:#E8F5E9;color:var(--green)}}
.pill{{display:inline-block;background:var(--sand);border-radius:4px;padding:2px 8px;font-size:11px;font-family:monospace}}
/* lang */
[data-en]{{display:none}}
body.en [data-es]{{display:none}}
body.en [data-en]{{display:unset}}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="sub">Ria Money Transfer · Care Operations</div>
    <h1 data-es>Adherencia Diaria — Payment Confirmation (F1)</h1>
    <h1 data-en>Daily Adherence — Payment Confirmation (F1)</h1>
    <div class="sub" data-es>Últimos 30 días · {TODAY} · Enfoque: US Care</div>
    <div class="sub" data-en>Last 30 days · {TODAY} · Focus: US Care</div>
  </div>
  <div><button class="lang-btn" onclick="document.body.classList.toggle('en');this.textContent=document.body.classList.contains('en')?'ES':'EN'">EN</button></div>
</div>

<div class="page">

<!-- KPIs -->
<div class="section">
  <div class="sec-title" data-es>Resumen — Últimos 30 días</div>
  <div class="sec-title" data-en>Summary — Last 30 days</div>
  <div class="kpi-grid">
    <div class="kpi clay">
      <div class="val">{tot_us}</div>
      <div class="lbl" data-es>Tickets F1 US Care</div>
      <div class="lbl" data-en>F1 Tickets US Care</div>
    </div>
    <div class="kpi red">
      <div class="val">{pct_us_kpi}%</div>
      <div class="lbl" data-es>Adherencia US Care</div>
      <div class="lbl" data-en>US Care Adherence</div>
    </div>
    <div class="kpi clay">
      <div class="val">{tot_gl}</div>
      <div class="lbl" data-es>Tickets F1 Global (sin VA-only)</div>
      <div class="lbl" data-en>F1 Tickets Global (excl. VA-only)</div>
    </div>
    <div class="kpi red">
      <div class="val">{pct_gl_kpi}%</div>
      <div class="lbl" data-es>Adherencia Global</div>
      <div class="lbl" data-en>Global Adherence</div>
    </div>
  </div>

  <div class="card" style="margin-top:14px">
    <div class="note">
      <span data-es><strong>Definición de adherencia:</strong> un ticket F1 es adherente si tiene el tag
        <span class="pill">ria_payment_confirmation_reliable_correspondent_sent</span> (macro/quicktext aplicado)
        <strong>o</strong> <span class="pill">order__payment_confirmation</span> (reason for contact correcto).
        Los tickets VA-only (<span class="pill">inbound_call_-_va_only</span>) se excluyen del cálculo.
      </span>
      <span data-en><strong>Adherence definition:</strong> an F1 ticket is adherent if it has the tag
        <span class="pill">ria_payment_confirmation_reliable_correspondent_sent</span> (macro/quicktext applied)
        <strong>or</strong> <span class="pill">order__payment_confirmation</span> (correct reason for contact).
        VA-only tickets (<span class="pill">inbound_call_-_va_only</span>) are excluded.
      </span>
    </div>
  </div>
</div>

<!-- TENDENCIA DIARIA -->
<div class="section">
  <div class="sec-title" data-es>Tendencia Diaria — US Care vs Global</div>
  <div class="sec-title" data-en>Daily Trend — US Care vs Global</div>
  <div class="card">
    <h3 data-es>% Adherencia por día (F1)</h3>
    <h3 data-en>Daily Adherence % (F1)</h3>
    <div class="chart-wrap" style="height:280px">
      <canvas id="chartDaily"></canvas>
    </div>
    <div class="note">
      <span data-es>La línea base está cerca de 0% — el objetivo del dashboard es capturar el momento en que la adopción empiece a subir conforme se entrena a los equipos y se activan los triggers. Cada punto = un día.</span>
      <span data-en>The baseline is near 0% — the dashboard's purpose is to capture the moment adoption starts rising as teams are trained and triggers are activated. Each point = one day.</span>
    </div>
  </div>

  <div class="two">
    <div class="card">
      <h3 data-es>Tickets F1 por día — US Care</h3>
      <h3 data-en>F1 Tickets per Day — US Care</h3>
      <div class="chart-wrap">
        <canvas id="chartVolUS"></canvas>
      </div>
    </div>
    <div class="card">
      <h3 data-es>Tickets F1 por día — Global</h3>
      <h3 data-en>F1 Tickets per Day — Global</h3>
      <div class="chart-wrap">
        <canvas id="chartVolGL"></canvas>
      </div>
    </div>
  </div>
</div>

<!-- CANAL BREAKDOWN -->
<div class="section">
  <div class="sec-title" data-es>Detalle por Canal (Global F1)</div>
  <div class="sec-title" data-en>Breakdown by Channel (Global F1)</div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th data-es>Canal</th><th data-es>Tickets</th><th data-es>Adherentes</th><th data-es>GAP</th><th data-es>ADH%</th><th data-es>Nota</th>
          <th data-en>Channel</th><th data-en>Tickets</th><th data-en>Adherent</th><th data-en>GAP</th><th data-en>ADH%</th><th data-en>Note</th>
        </tr>
      </thead>
      <tbody>"""

CH_LABEL = {
    "voice_direct": "Voz directa",
    "voice_rep":    "Voz (VA→Rep)",
    "email":        "Email",
    "messaging":    "Messaging/Chat",
    "other":        "Otro/Desconocido",
}
CH_NOTE_ES = {
    "voice_direct": "Rep lee script, envía por FX Client",
    "voice_rep":    "VA transfiere al rep",
    "email":        "Macro o quicktext vía Zendesk",
    "messaging":    "Shortcut de messaging",
    "other":        "Canal no identificado",
}
CH_NOTE_EN = {
    "voice_direct": "Rep reads script, sends via FX Client",
    "voice_rep":    "VA transfers to rep",
    "email":        "Macro or quicktext via Zendesk",
    "messaging":    "Messaging shortcut",
    "other":        "Unidentified channel",
}

for ch, d in sorted(ch_data.items(), key=lambda x: -x[1]["n"]):
    n   = d["n"]
    a   = d["adh"]
    g   = n - a
    pct = round(a/n*100,1) if n else 0
    bc  = "b-green" if pct>=30 else ("b-mid" if pct>=10 else "b-red")
    lbl = CH_LABEL.get(ch, ch)
    html += f"""
        <tr>
          <td><strong>{lbl}</strong></td>
          <td>{n}</td><td>{a}</td><td>{g}</td>
          <td><span class="badge {bc}">{pct}%</span></td>
          <td style="color:#888;font-size:12px">
            <span data-es>{CH_NOTE_ES.get(ch,'')}</span>
            <span data-en>{CH_NOTE_EN.get(ch,'')}</span>
          </td>
        </tr>"""

va_n = sum(1 for r in f1_all if r["_channel"]=="va_only")
html += f"""
        <tr style="opacity:.5">
          <td>VA-only (excluido)</td>
          <td>{va_n}</td><td>—</td><td>—</td><td>—</td>
          <td style="color:#888;font-size:12px" data-es>Sin rep humano — no medible</td>
          <td style="color:#888;font-size:12px" data-en>No human rep — not measurable</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<!-- PRÓXIMOS PASOS -->
<div class="section">
  <div class="sec-title" data-es>Qué Monitorear</div>
  <div class="sec-title" data-en>What to Monitor</div>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th data-es>Hito</th><th data-es>Señal en Zendesk</th><th data-es>Impacto esperado</th>
          <th data-en>Milestone</th><th data-en>Signal in Zendesk</th><th data-en>Expected impact</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td data-es>Trigger activo en US Care</td>
          <td data-en>Trigger active in US Care</td>
          <td><span class="pill">payment_confirmation_advisory_applied</span></td>
          <td data-es>↑ adherencia voice_direct</td>
          <td data-en>↑ voice_direct adherence</td>
        </tr>
        <tr>
          <td data-es>Reps seleccionan RFC correcto</td>
          <td data-en>Reps select correct RFC</td>
          <td><span class="pill">order__payment_confirmation</span></td>
          <td data-es>↑ adherencia voz y email</td>
          <td data-en>↑ voice & email adherence</td>
        </tr>
        <tr>
          <td data-es>Macro/quicktext usado en email</td>
          <td data-en>Macro/quicktext used in email</td>
          <td><span class="pill">ria_payment_confirmation_reliable_correspondent_sent</span></td>
          <td data-es>↑ adherencia email (mayor volumen)</td>
          <td data-en>↑ email adherence (highest volume)</td>
        </tr>
        <tr>
          <td data-es>Trigger activo en todos los grupos</td>
          <td data-en>Trigger active in all groups</td>
          <td data-es>Sin cambio de tag — ver % global</td>
          <td data-en>No tag change — see global %</td>
          <td data-es>↑ adherencia global</td>
          <td data-en>↑ global adherence</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

</div>

<script>
const CLAY='#CC785C', GREEN='#5A8A6A', SLATE='#6A8CAA', SAND='#EBE5D7';

const daysUS  = {json.dumps(days_us)};
const nUS     = {json.dumps(n_us)};
const adhUS   = {json.dumps(adh_us)};
const pctUS   = {json.dumps(pct_us)};

const daysGL  = {json.dumps(days_gl)};
const nGL     = {json.dumps(n_gl)};
const adhGL   = {json.dumps(adh_gl)};
const pctGL   = {json.dumps(pct_gl)};

const baseOpts = {{
  responsive:true, maintainAspectRatio:false,
  plugins:{{legend:{{position:'bottom',labels:{{font:{{size:12}},boxWidth:12}}}},
            tooltip:{{cornerRadius:4}}}},
  scales:{{x:{{ticks:{{font:{{size:11}},maxRotation:45}},grid:{{display:false}}}},
           y:{{grid:{{color:'#eee'}}}}}}
}};

// Chart 1: % diario US Care vs Global
new Chart(document.getElementById('chartDaily'),{{
  type:'line',
  data:{{
    labels: daysGL,
    datasets:[
      {{label:'US Care %', data:pctUS.length?pctUS:Array(daysGL.length).fill(null),
        borderColor:CLAY, backgroundColor:'rgba(204,120,92,.1)',
        pointRadius:4, pointHoverRadius:6, tension:.3, fill:true}},
      {{label:'Global %', data:pctGL,
        borderColor:SLATE, backgroundColor:'rgba(106,140,170,.08)',
        pointRadius:3, pointHoverRadius:5, tension:.3, fill:true,
        borderDash:[4,3]}}
    ]
  }},
  options:{{...baseOpts,
    scales:{{...baseOpts.scales,
      y:{{...baseOpts.scales.y, min:0, max:100,
         ticks:{{callback:v=>v+'%'}}}}}}}}
}});

// Chart 2: Volumen diario US Care
new Chart(document.getElementById('chartVolUS'),{{
  type:'bar',
  data:{{
    labels:daysUS,
    datasets:[
      {{label:'Adherentes',data:adhUS,backgroundColor:GREEN,borderRadius:3}},
      {{label:'GAP',data:nUS.map((n,i)=>n-adhUS[i]),backgroundColor:'#E8D0C4',borderRadius:3}}
    ]
  }},
  options:{{...baseOpts,scales:{{x:{{...baseOpts.scales.x,stacked:true}},y:{{...baseOpts.scales.y,stacked:true}}}}}}
}});

// Chart 3: Volumen diario Global
new Chart(document.getElementById('chartVolGL'),{{
  type:'bar',
  data:{{
    labels:daysGL,
    datasets:[
      {{label:'Adherentes',data:adhGL,backgroundColor:GREEN,borderRadius:3}},
      {{label:'GAP',data:nGL.map((n,i)=>n-adhGL[i]),backgroundColor:'#E8D0C4',borderRadius:3}}
    ]
  }},
  options:{{...baseOpts,scales:{{x:{{...baseOpts.scales.x,stacked:true}},y:{{...baseOpts.scales.y,stacked:true}}}}}}
}});
</script>
</body>
</html>"""

out = Path("reports/daily_adherence.html")
out.write_text(html, encoding="utf-8")
print(f"Guardado: {out}  ({out.stat().st_size/1024:.0f} KB)")
