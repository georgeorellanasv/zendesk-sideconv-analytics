"""
Genera reports/adoption_tracker.html — vista SIMPLE y enfocada:
Bank Deposit + Voice Direct, escenarios donde debia aplicarse Payment
Confirmation (F1), ultimos 15 dias.

Adherencia de voz = 2 condiciones: trigger (nota interna) + RFC Payment Confirmation.
(La macro no aplica en voz: el rep envia la confirmacion por FX Client.)

Usage: python -m scripts.build_adoption_tracker
"""
import csv, json
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path

MACRO   = "ria_payment_confirmation_reliable_correspondent_sent"
RFC     = "order__payment_confirmation"
TRIGGER = "payment_confirmation_advisory_applied"
POP     = {"new_pop_ticket","pop_side_convo_macro","pop_side_convo_macro_es",
           "pop_interbank_sc","ria_pop_day_1_qt","dandelion_pop_day_1",
           "dandelion_request_pop","ria_pop_success_qt"}
VA      = {"inbound_call_-_va_only","va_only_solved"}
WINDOW_DAYS = 15

# Una llamada "llega al agente" si NO la resolvió solo el VA.
# Incluye: directa al agente (inbound_call) Y transferida del VA al rep (va_to_rep / cxi voice).
def reaches_agent(tags):
    if tags & VA: return False
    if tags & {"inbound_call_-_va_to_rep","cxi_ch_voice"}: return True
    if "inbound_call" in tags: return True
    return False

def call_type(tags):
    if tags & {"inbound_call_-_va_to_rep","cxi_ch_voice"}: return "transferida"  # VA -> rep
    return "directa"

def is_f1(r):
    return r["cond_substatus"]=="True" and r["cond_48h"]=="True" and r["cond_no_sc"]=="True"

rows = list(csv.DictReader(open("reports/macro_adherence_report.csv", encoding="utf-8")))
dates = [r["created_at"][:10] for r in rows if r.get("created_at")]
maxd  = max(dates)
cut   = (datetime.strptime(maxd,"%Y-%m-%d") - timedelta(days=WINDOW_DAYS)).strftime("%Y-%m-%d")

elig = []
for r in rows:
    if r.get("delivery_method") != "bank_deposit": continue
    if not is_f1(r): continue
    if r["created_at"][:10] < cut: continue
    tags = set(r.get("tags","").split("|"))
    if not reaches_agent(tags): continue       # solo llamadas que el agente recibe
    elig.append((r, tags))

n      = len(elig)
trig   = sum(1 for _,t in elig if TRIGGER in t)
rfc    = sum(1 for _,t in elig if RFC in t)
adh    = sum(1 for _,t in elig if TRIGGER in t and RFC in t)
pop    = sum(1 for _,t in elig if t & POP)
nada   = sum(1 for _,t in elig if not (t & {TRIGGER,RFC,MACRO} or t & POP))
# de los que recibieron trigger, cuantos respondio el rep con RFC
rep_resp = sum(1 for _,t in elig if TRIGGER in t and RFC in t)
rep_resp_pct = round(rep_resp/trig*100,1) if trig else 0

# Desglose por tipo de llamada: revela DÓNDE falta cobertura del trigger
ct = {"directa":{"n":0,"trig":0}, "transferida":{"n":0,"trig":0}}
for _,t in elig:
    k = call_type(t)
    ct[k]["n"] += 1
    if TRIGGER in t: ct[k]["trig"] += 1
ct_pct = {k: (round(v["trig"]/v["n"]*100) if v["n"] else 0) for k,v in ct.items()}

# diario
byday = defaultdict(lambda:{"n":0,"adh":0,"trig":0,"rfc":0,"pop":0,"nada":0})
for r,t in elig:
    d = r["created_at"][:10]
    byday[d]["n"]+=1
    if TRIGGER in t: byday[d]["trig"]+=1
    if RFC in t: byday[d]["rfc"]+=1
    if TRIGGER in t and RFC in t: byday[d]["adh"]+=1
    if t & POP: byday[d]["pop"]+=1
    if not (t & {TRIGGER,RFC,MACRO} or t & POP): byday[d]["nada"]+=1
days = sorted(byday)
day_n    = [byday[d]["n"]    for d in days]
day_adh  = [byday[d]["adh"]  for d in days]
day_trig = [byday[d]["trig"] for d in days]
day_pct  = [round(byday[d]["adh"]/byday[d]["n"]*100,1) if byday[d]["n"] else 0 for d in days]

# Filas de la tabla de detalle diario (más reciente arriba)
detail_rows = ""
for d in sorted(days, reverse=True):
    b = byday[d]
    p = round(b["adh"]/b["n"]*100) if b["n"] else 0
    badge = "#5A8A6A" if p>=30 else "#C07820" if p>=10 else "#B84A4A"
    detail_rows += (
        f'<tr><td><strong>{d}</strong></td>'
        f'<td>{b["n"]}</td>'
        f'<td>{b["trig"]}</td>'
        f'<td>{b["rfc"]}</td>'
        f'<td>{b["pop"]}</td>'
        f'<td>{b["nada"]}</td>'
        f'<td><strong>{b["adh"]}</strong></td>'
        f'<td><span style="font-weight:700;color:{badge}">{p}%</span></td></tr>'
    )

pct = lambda x: round(x/n*100) if n else 0
TODAY = datetime.now().strftime("%d %b %Y") if False else maxd  # usa fecha de la data

NAV = """
<div style="background:#EBE5D7;padding:11px 24px;display:flex;gap:8px;flex-wrap:wrap;justify-content:center;border-bottom:1px solid rgba(20,20,19,.10)">
  <a href="index.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>Reporte F1–F5</span><span data-en>F1–F5 Report</span></a>
  <a href="context.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>Contexto</span><span data-en>Context</span></a>
  <a href="daily_adherence.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>Dashboard Diario</span><span data-en>Daily Dashboard</span></a>
  <a href="f1_drilldown.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>F1 Detalle</span><span data-en>F1 Detail</span></a>
  <a href="contact_reasons.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid rgba(20,20,19,.12);background:#fff;color:#1F1D1B"><span data-es>Motivos de Contacto</span><span data-en>Contact Reasons</span></a>
  <a href="adoption_tracker.html" style="display:inline-block;padding:7px 15px;border-radius:6px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid #CC785C;background:#CC785C;color:#fff"><span data-es>★ Adopción (BD·Voz)</span><span data-en>★ Adoption (BD·Voice)</span></a>
</div>
"""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Adopción Payment Confirmation — Bank Deposit · Voice Direct</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{--paper:#F5F4EE;--ink:#1F1D1B;--clay:#CC785C;--clay-dk:#A1543D;--sand:#EBE5D7;--slate:#6A8CAA;--border:rgba(20,20,19,.10);--green:#5A8A6A;--red:#B84A4A;--orange:#C07820;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,-apple-system,sans-serif;background:var(--paper);color:var(--ink);font-size:14px;line-height:1.5}}
.header{{background:var(--ink);color:var(--paper);padding:28px 48px;display:flex;justify-content:space-between;align-items:flex-end}}
.header h1{{font-size:20px;font-weight:600}}
.header .sub{{font-size:12px;opacity:.6;margin-top:3px}}
.lang-btn{{background:transparent;border:1px solid rgba(255,255,255,.3);color:var(--paper);padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:8px}}
.page{{max-width:920px;margin:0 auto;padding:28px 24px 80px}}
.sec-title{{font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--clay);margin:32px 0 12px}}
.card{{background:#fff;border:1px solid var(--border);border-radius:8px;padding:24px;margin-bottom:14px}}
.card h3{{font-size:16px;font-weight:600;margin-bottom:4px}}
.card .sub{{font-size:12px;color:#888;margin-bottom:16px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:8px}}
.kpi{{background:#fff;border:1px solid var(--border);border-radius:8px;padding:20px;text-align:center}}
.kpi .val{{font-size:38px;font-weight:700;line-height:1}}
.kpi .lbl{{font-size:12px;color:#777;margin-top:6px}}
.kpi.red .val{{color:var(--red)}}.kpi.clay .val{{color:var(--clay)}}
/* Funnel */
.funnel{{margin:8px 0}}
.fstep{{display:flex;align-items:center;gap:14px;margin-bottom:10px}}
.fbar-wrap{{flex:1;background:var(--sand);border-radius:6px;height:46px;position:relative;overflow:hidden}}
.fbar{{height:46px;border-radius:6px;display:flex;align-items:center;padding-left:14px;color:#fff;font-weight:600;font-size:14px;white-space:nowrap;transition:width .4s}}
.fmeta{{width:230px;font-size:13px}}
.fmeta .ftitle{{font-weight:600}}
.fmeta .fnote{{font-size:11px;color:#888}}
.fnum{{width:90px;text-align:right;font-weight:700;font-size:15px}}
.explain{{background:var(--sand);border-radius:6px;padding:14px 16px;font-size:13px;line-height:1.65;margin-top:16px}}
.explain strong{{color:var(--clay-dk)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.bottleneck{{border-left:4px solid var(--red);background:#FDF2F2;border-radius:6px;padding:16px 18px}}
.bottleneck.b2{{border-left-color:var(--orange);background:#FFF7EC}}
.bottleneck .bt{{font-weight:700;font-size:14px;margin-bottom:6px}}
.bottleneck .bn{{font-size:28px;font-weight:700;color:var(--red)}}
.bottleneck.b2 .bn{{color:var(--orange)}}
.bottleneck .bd{{font-size:12.5px;color:#555;line-height:1.6;margin-top:6px}}
.chart-wrap{{position:relative;height:260px}}
.pill{{display:inline-block;background:#e8e8e0;border-radius:3px;padding:1px 6px;font-size:11px;font-family:monospace;color:#333}}
[data-en]{{display:none}}body.en [data-es]{{display:none}}body.en [data-en]{{display:unset}}
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="sub">Ria Money Transfer · Care Operations</div>
    <h1 data-es>Adopción de Payment Confirmation</h1>
    <h1 data-en>Payment Confirmation Adoption</h1>
    <div class="sub" data-es>Bank Deposit · llamadas atendidas por agente · últimos {WINDOW_DAYS} días (hasta {TODAY})</div>
    <div class="sub" data-en>Bank Deposit · agent-handled calls · last {WINDOW_DAYS} days (through {TODAY})</div>
  </div>
  <div><button class="lang-btn" onclick="document.body.classList.toggle('en');this.textContent=document.body.classList.contains('en')?'ES':'EN'">EN</button></div>
</div>
{NAV}
<div class="page">

<div class="card" style="margin-top:24px">
  <div class="explain" style="margin-top:0">
    <span data-es><strong>Qué mide esta página:</strong> de todas las llamadas de voz que <strong>atendió un agente</strong> (directas + transferidas del asistente virtual) sobre transferencias Bank Deposit ya pagadas y recientes (&lt;48h) — donde la acción correcta era enviar una Payment Confirmation — ¿en cuántas se hizo bien? Solo cuentan las llamadas que el agente recibe; las resueltas solo por el asistente virtual se excluyen. Para voz, "bien hecho" = el sistema avisó al agente (trigger) <strong>y</strong> el agente marcó el motivo correcto. La macro no cuenta aquí porque en voz la confirmación se envía por FX Client, no por Zendesk.</span>
    <span data-en><strong>What this page measures:</strong> of all voice calls <strong>handled by an agent</strong> (direct + transferred from the virtual assistant) about already-paid, recent (&lt;48h) Bank Deposit transfers — where the correct action was to send a Payment Confirmation — in how many was it done right? Only calls the agent receives count; those resolved by the virtual assistant alone are excluded. For voice, "done right" = the system alerted the agent (trigger) <strong>and</strong> the agent selected the correct reason. The macro doesn't count here because in voice the confirmation is sent via FX Client, not Zendesk.</span>
  </div>
</div>

<!-- KPIs -->
<div class="kpi-grid">
  <div class="kpi clay"><div class="val">{n}</div>
    <div class="lbl" data-es>Escenarios donde debía aplicarse PC</div>
    <div class="lbl" data-en>Scenarios where PC should apply</div></div>
  <div class="kpi clay"><div class="val">{adh}</div>
    <div class="lbl" data-es>Hechos correctamente</div>
    <div class="lbl" data-en>Done correctly</div></div>
  <div class="kpi red"><div class="val">{pct(adh)}%</div>
    <div class="lbl" data-es>Adherencia</div>
    <div class="lbl" data-en>Adherence</div></div>
</div>

<!-- FUNNEL -->
<div class="sec-title" data-es>El embudo — dónde se pierde la adherencia</div>
<div class="sec-title" data-en>The funnel — where adherence is lost</div>
<div class="card">
  <div class="funnel">
    <div class="fstep">
      <div class="fmeta"><div class="ftitle" data-es>Escenarios elegibles</div><div class="ftitle" data-en>Eligible scenarios</div>
        <div class="fnote" data-es>Bank Deposit pagado &lt;48h, voz directa</div><div class="fnote" data-en>Paid Bank Deposit &lt;48h, direct voice</div></div>
      <div class="fbar-wrap"><div class="fbar" style="width:100%;background:var(--slate)">{n}</div></div>
      <div class="fnum">100%</div>
    </div>
    <div class="fstep">
      <div class="fmeta"><div class="ftitle" data-es>1· El sistema avisó</div><div class="ftitle" data-en>1· System alerted</div>
        <div class="fnote" data-es>trigger nota interna</div><div class="fnote" data-en>internal-note trigger</div></div>
      <div class="fbar-wrap"><div class="fbar" style="width:{max(pct(trig),6)}%;background:var(--orange)">{trig}</div></div>
      <div class="fnum">{pct(trig)}%</div>
    </div>
    <div class="fstep">
      <div class="fmeta"><div class="ftitle" data-es>2· El agente marcó el motivo</div><div class="ftitle" data-en>2· Agent set the reason</div>
        <div class="fnote" data-es>RFC = Payment Confirmation</div><div class="fnote" data-en>RFC = Payment Confirmation</div></div>
      <div class="fbar-wrap"><div class="fbar" style="width:{max(pct(rfc),5)}%;background:var(--red)">{rfc}</div></div>
      <div class="fnum">{pct(rfc)}%</div>
    </div>
    <div class="fstep">
      <div class="fmeta"><div class="ftitle" data-es>✅ Adherente (1 + 2)</div><div class="ftitle" data-en>✅ Adherent (1 + 2)</div>
        <div class="fnote" data-es>las dos condiciones</div><div class="fnote" data-en>both conditions</div></div>
      <div class="fbar-wrap"><div class="fbar" style="width:{max(pct(adh),5)}%;background:var(--green)">{adh}</div></div>
      <div class="fnum">{pct(adh)}%</div>
    </div>
  </div>
  <div class="explain">
    <span data-es>Cada barra es más corta que la anterior: ahí se pierde la adherencia. De {n} llamadas donde debía mandarse la confirmación, el sistema avisó en {trig} y solo en {adh} el agente además marcó el motivo correcto.</span>
    <span data-en>Each bar is shorter than the one above: that's where adherence is lost. Of {n} calls where the confirmation should have been sent, the system alerted on {trig} and in only {adh} did the agent also set the correct reason.</span>
  </div>
</div>

<!-- COBERTURA DEL TRIGGER POR TIPO DE LLAMADA -->
<div class="sec-title" data-es>Dónde falta el aviso del sistema — por tipo de llamada</div>
<div class="sec-title" data-en>Where the system alert is missing — by call type</div>
<div class="card">
  <div class="sub" data-es>Una llamada llega al agente de dos formas: directa, o transferida por el asistente virtual. El trigger debería avisar en ambas — pero hoy casi no dispara en las transferidas.</div>
  <div class="sub" data-en>A call reaches the agent two ways: direct, or transferred by the virtual assistant. The trigger should alert in both — but today it barely fires on transferred ones.</div>
  <table>
    <thead><tr>
      <th data-es>Tipo de llamada</th><th data-en>Call type</th>
      <th data-es>Llamadas</th><th data-en>Calls</th>
      <th data-es>Con aviso (trigger)</th><th data-en>With alert (trigger)</th>
      <th data-es>Cobertura</th><th data-en>Coverage</th>
    </tr></thead>
    <tbody>
      <tr>
        <td><strong data-es>Directa al agente</strong><strong data-en>Direct to agent</strong></td>
        <td>{ct['directa']['n']}</td><td>{ct['directa']['trig']}</td>
        <td><span style="font-weight:700;color:{'#5A8A6A' if ct_pct['directa']>=30 else '#C07820' if ct_pct['directa']>=10 else '#B84A4A'}">{ct_pct['directa']}%</span></td>
      </tr>
      <tr>
        <td><strong data-es>Transferida del asistente virtual</strong><strong data-en>Transferred from virtual assistant</strong></td>
        <td>{ct['transferida']['n']}</td><td>{ct['transferida']['trig']}</td>
        <td><span style="font-weight:700;color:{'#5A8A6A' if ct_pct['transferida']>=30 else '#C07820' if ct_pct['transferida']>=10 else '#B84A4A'}">{ct_pct['transferida']}%</span></td>
      </tr>
    </tbody>
  </table>
  <div class="explain">
    <span data-es><strong>El scope que hay que atacar:</strong> el trigger funciona razonablemente en las llamadas directas ({ct_pct['directa']}%) pero casi no dispara en las transferidas del asistente virtual ({ct_pct['transferida']}%). Como muchas llamadas llegan al agente por transferencia, ahí se pierde gran parte del sample. <strong>Acción:</strong> extender el trigger para que también avise en el flujo de transferencia (VA → agente).</span>
    <span data-en><strong>The scope to attack:</strong> the trigger works reasonably on direct calls ({ct_pct['directa']}%) but barely fires on calls transferred from the virtual assistant ({ct_pct['transferida']}%). Since many calls reach the agent via transfer, that's where much of the sample is lost. <strong>Action:</strong> extend the trigger to also fire on the transfer flow (VA → agent).</span>
  </div>
</div>

<!-- DOS CUELLOS DE BOTELLA -->
<div class="sec-title" data-es>Las dos cosas que hay que arreglar</div>
<div class="sec-title" data-en>The two things to fix</div>
<div class="two">
  <div class="card">
    <div class="bottleneck">
      <div class="bt" data-es>Cuello 1 — Cobertura del sistema</div>
      <div class="bt" data-en>Bottleneck 1 — System coverage</div>
      <div class="bn">{pct(trig)}%</div>
      <div class="bd" data-es>El trigger solo avisó en {trig} de {n} llamadas. En el resto, el agente nunca recibió la alerta. <strong>Solución:</strong> activar el trigger para todos los grupos (en rollout). El techo de adherencia no puede superar este número.</div>
      <div class="bd" data-en>The trigger only alerted on {trig} of {n} calls. In the rest, the agent never got the alert. <strong>Fix:</strong> activate the trigger for all groups (in rollout). Adherence can't exceed this number.</div>
    </div>
  </div>
  <div class="card">
    <div class="bottleneck b2">
      <div class="bt" data-es>Cuello 2 — Respuesta del agente</div>
      <div class="bt" data-en>Bottleneck 2 — Agent response</div>
      <div class="bn">{rep_resp_pct}%</div>
      <div class="bd" data-es>Aún cuando el sistema SÍ avisó ({trig} llamadas), el agente marcó el motivo correcto solo {rep_resp} veces. <strong>Solución:</strong> entrenamiento — que al ver la nota interna, el agente seleccione el RFC y mande la confirmación.</div>
      <div class="bd" data-en>Even when the system DID alert ({trig} calls), the agent set the correct reason only {rep_resp} times. <strong>Fix:</strong> training — when the internal note appears, the agent should select the RFC and send the confirmation.</div>
    </div>
  </div>
</div>

<!-- TENDENCIA DIARIA -->
<div class="sec-title" data-es>Tendencia diaria — para ver si sube</div>
<div class="sec-title" data-en>Daily trend — to see if it rises</div>
<div class="card">
  <h3 data-es>Escenarios y adherentes por día</h3><h3 data-en>Scenarios and adherent per day</h3>
  <div class="sub" data-es>Verde = hechos correctamente. La línea es el % de adherencia del día.</div>
  <div class="sub" data-en>Green = done correctly. The line is the day's adherence %.</div>
  <div class="chart-wrap"><canvas id="chartDaily"></canvas></div>
  <div class="explain">
    <span data-es>Cuando el entrenamiento empiece y se active el trigger para más grupos, las barras verdes y la línea de % deberían crecer. Hoy es la línea base.</span>
    <span data-en>When training begins and the trigger activates for more groups, the green bars and the % line should grow. Today is the baseline.</span>
  </div>
</div>

<!-- DETALLE DIARIO (TABLA) -->
<div class="sec-title" data-es>Detalle día por día</div>
<div class="sec-title" data-en>Day-by-day detail</div>
<div class="card">
  <div class="sub" data-es>Los números exactos de cada día. Día más reciente arriba.</div>
  <div class="sub" data-en>Exact numbers for each day. Most recent day on top.</div>
  <table>
    <thead><tr>
      <th data-es>Día</th><th data-en>Day</th>
      <th data-es>Escenarios</th><th data-en>Scenarios</th>
      <th data-es>Con aviso</th><th data-en>Alerted</th>
      <th data-es>Con RFC</th><th data-en>With RFC</th>
      <th data-es>Eligió POP</th><th data-en>Chose POP</th>
      <th data-es>Sin acción</th><th data-en>No action</th>
      <th data-es>Adherentes</th><th data-en>Adherent</th>
      <th>%</th>
    </tr></thead>
    <tbody>
      {detail_rows}
    </tbody>
    <tfoot>
      <tr style="font-weight:700;border-top:2px solid var(--border)">
        <td data-es>TOTAL</td><td data-en>TOTAL</td>
        <td>{n}</td><td>{trig}</td><td>{rfc}</td><td>{pop}</td><td>{nada}</td>
        <td>{adh}</td><td>{pct(adh)}%</td>
      </tr>
    </tfoot>
  </table>
  <div class="explain">
    <span data-es><strong>Cómo leer la fila:</strong> "Escenarios" = llamadas donde debía mandarse confirmación · "Con aviso" = el sistema disparó el trigger · "Con RFC" = el agente marcó el motivo · "Adherentes" = cumplió las dos (aviso + RFC). La brecha entre "Escenarios" y "Adherentes" es la oportunidad de cada día.</span>
    <span data-en><strong>How to read a row:</strong> "Scenarios" = calls where confirmation should have been sent · "Alerted" = the system fired the trigger · "With RFC" = the agent set the reason · "Adherent" = met both (alert + RFC). The gap between "Scenarios" and "Adherent" is each day's opportunity.</span>
  </div>
</div>

</div>

<script>
const days={json.dumps(days)};
const dayN={json.dumps(day_n)};
const dayAdh={json.dumps(day_adh)};
const dayTrig={json.dumps(day_trig)};
const dayPct={json.dumps(day_pct)};
const GREEN='#5A8A6A',ORANGE='#C07820',RED='#B84A4A',CLAY='#CC785C';

new Chart(document.getElementById('chartDaily'),{{
  data:{{labels:days,datasets:[
    {{type:'bar',label:'Adherentes ✓',data:dayAdh,backgroundColor:GREEN,borderRadius:3,order:2,yAxisID:'y'}},
    {{type:'bar',label:'No adherentes',data:dayN.map((x,i)=>x-dayAdh[i]),backgroundColor:'#E8C4B4',borderRadius:3,order:2,yAxisID:'y'}},
    {{type:'line',label:'% Adherencia',data:dayPct,borderColor:CLAY,backgroundColor:'rgba(204,120,92,.1)',tension:.3,pointRadius:4,borderWidth:3,order:1,yAxisID:'y1'}}
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,
    plugins:{{legend:{{position:'bottom',labels:{{font:{{size:12}},boxWidth:12,padding:14}}}}}},
    scales:{{
      x:{{stacked:true,ticks:{{font:{{size:11}},maxRotation:45}},grid:{{display:false}}}},
      y:{{stacked:true,position:'left',grid:{{color:'#f0f0f0'}},title:{{display:true,text:'Tickets'}}}},
      y1:{{position:'right',min:0,max:100,grid:{{display:false}},ticks:{{callback:v=>v+'%'}},title:{{display:true,text:'% Adherencia'}}}}
    }}
  }}
}});
</script>
</body>
</html>"""

out = Path("reports/adoption_tracker.html")
out.write_text(html, encoding="utf-8")
print(f"Guardado: {out}  ({out.stat().st_size/1024:.0f} KB)")
print(f"Escenarios={n}  trigger={trig}  rfc={rfc}  adherente={adh}  respuesta_rep={rep_resp_pct}%")
