"""
Genera reports/daily_adherence.html — dashboard de adherencia diaria F1
con filtros interactivos y explicaciones en cada gráfico.

Usage: python -m scripts.build_daily_adherence
"""
import csv, json
from collections import defaultdict
from datetime import date
from pathlib import Path

MACRO_TAG   = "ria_payment_confirmation_reliable_correspondent_sent"
RFC_TAG     = "order__payment_confirmation"
VA_ONLY     = {"inbound_call_-_va_only", "va_only_solved"}
US_WFM      = {"ria_wfm_us_phone", "cxi_ria_wfm_nam_care_phone"}
EMEA_WFM    = {"ria_wfm_europe_es_uk_phone", "cxi_ria_wfm_emea_care_phone"}

# Tags de POP — el "atajo caro". En F1 (<48h, pagado) es el error que
# queremos ver bajar mientras Payment Confirmation sube.
POP_TAGS = {
    "new_pop_ticket", "pop_side_convo_macro", "pop_side_convo_macro_es",
    "pop_interbank_sc", "ria_pop_day_1_qt", "dandelion_pop_day_1",
    "dandelion_request_pop", "ria_pop_success_qt",
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

def get_channel(tags):
    if tags & VA_ONLY:                                      return "va_only"
    if tags & {"inbound_call_-_va_to_rep","cxi_ch_voice"}: return "voice_rep"
    if "inbound_call" in tags:                              return "voice_direct"
    if tags & {"native_messaging","live_chat_-_message"}:   return "messaging"
    if "email_ticket_channel" in tags:                      return "email"
    return "other"

def get_group(tags):
    if tags & US_WFM:   return "us_care"
    if tags & EMEA_WFM: return "emea_care"
    return "other"

rows = list(csv.DictReader(open("reports/macro_adherence_report.csv", encoding="utf-8")))
# F1 = foco principal del dashboard. F2 se incluye SOLO para el gráfico de
# sustitución: juntos forman el "territorio Payment Confirmation" (pagado+<48h),
# donde el atajo POP es visible (un POP abre una SC, lo que reclasifica F1->F2).
terr_all = [r for r in rows if classify(r) in ("F1", "F2")]

# ── Construir lista de tickets para JS ────────────────────────────────────────
tickets_js = []
for r in terr_all:
    tags    = set(r.get("tags","").split("|"))
    ch      = get_channel(tags)
    grp     = get_group(tags)
    adh     = None if ch == "va_only" else bool(tags & {MACRO_TAG, RFC_TAG})
    dm      = r.get("delivery_method", "bank_deposit")
    dt      = r.get("created_at","")[:10]
    tickets_js.append({
        "date": dt, "channel": ch, "group": grp,
        "dm": dm, "adherent": adh, "scen": classify(r),
        "has_macro":   MACRO_TAG in tags,
        "has_rfc":     RFC_TAG in tags,
        "has_trigger": "payment_confirmation_advisory_applied" in tags,
        "has_pop":     bool(tags & POP_TAGS),
    })

TODAY = date.today().strftime("%d %b %Y")
TICKETS_JSON = json.dumps(tickets_js)

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Payment Confirmation — Adherencia Diaria</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root{{
  --paper:#F5F4EE;--ink:#1F1D1B;--clay:#CC785C;--clay-dk:#A1543D;
  --sand:#EBE5D7;--slate:#6A8CAA;--border:rgba(20,20,19,.10);
  --green:#5A8A6A;--red:#B84A4A;--orange:#C07820;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Inter,-apple-system,sans-serif;background:var(--paper);color:var(--ink);font-size:14px;line-height:1.5}}

.header{{background:var(--ink);color:var(--paper);padding:28px 48px;display:flex;justify-content:space-between;align-items:flex-end}}
.header h1{{font-size:20px;font-weight:600}}
.header .sub{{font-size:12px;opacity:.6;margin-top:3px}}
.lang-btn{{background:transparent;border:1px solid rgba(255,255,255,.3);color:var(--paper);padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:8px}}

.page{{max-width:1140px;margin:0 auto;padding:28px 24px 80px}}
.sec-title{{font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--clay);margin-bottom:12px;margin-top:32px}}

/* ── Filtros ── */
.filters{{background:#fff;border:1px solid var(--border);border-radius:8px;padding:16px 20px;display:flex;flex-wrap:wrap;gap:20px;align-items:flex-end;margin-bottom:20px}}
.filter-group label{{display:block;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:#888;margin-bottom:5px}}
.filter-group select{{border:1px solid var(--border);border-radius:5px;padding:6px 10px;font-size:13px;background:#fff;color:var(--ink);cursor:pointer;min-width:160px}}
.filter-group select:focus{{outline:2px solid var(--clay);outline-offset:1px}}
.filter-note{{font-size:12px;color:#999;align-self:flex-end;padding-bottom:2px}}

/* ── KPIs ── */
.kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.kpi{{background:#fff;border:1px solid var(--border);border-radius:8px;padding:18px 20px}}
.kpi .val{{font-size:30px;font-weight:700;line-height:1}}
.kpi .lbl{{font-size:12px;color:#777;margin-top:5px}}
.kpi .sublbl{{font-size:11px;color:#aaa;margin-top:2px}}
.kpi.red .val{{color:var(--red)}}
.kpi.clay .val{{color:var(--clay)}}
.kpi.green .val{{color:var(--green)}}

/* ── Cards ── */
.card{{background:#fff;border:1px solid var(--border);border-radius:8px;padding:22px;margin-bottom:14px}}
.card-header{{margin-bottom:4px}}
.card-header h3{{font-size:15px;font-weight:600}}
.card-header .card-sub{{font-size:12px;color:#888;margin-top:3px;margin-bottom:14px}}
.chart-wrap{{position:relative;height:250px}}
.chart-wrap.tall{{height:300px}}

.explain{{background:var(--sand);border-radius:6px;padding:13px 16px;font-size:13px;margin-top:16px;line-height:1.65}}
.explain strong{{color:var(--clay-dk)}}
.explain .tip{{display:block;margin-top:6px;font-size:12px;color:#666}}

/* ── Dos columnas ── */
.two{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}

/* ── Tabla ── */
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:#888;border-bottom:2px solid var(--border);padding:8px 10px;text-align:left}}
td{{padding:9px 10px;border-bottom:1px solid var(--border)}}
tr:last-child td{{border-bottom:none}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-weight:600;font-size:12px}}
.b-red{{background:#FDE8E8;color:var(--red)}}
.b-mid{{background:#FFF3E0;color:var(--orange)}}
.b-grn{{background:#E8F5E9;color:var(--green)}}
.pill{{display:inline-block;background:#eee;border-radius:3px;padding:1px 6px;font-size:11px;font-family:monospace;color:#333}}

/* ── Lang ── */
[data-en]{{display:none}}
body.en [data-es]{{display:none}}
body.en [data-en]{{display:unset}}

/* ── No data msg ── */
.no-data{{text-align:center;padding:40px;color:#aaa;font-size:13px}}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="sub">Ria Money Transfer · Care Operations</div>
    <h1 data-es>Adherencia Diaria — Payment Confirmation (F1)</h1>
    <h1 data-en>Daily Adherence — Payment Confirmation (F1)</h1>
    <div class="sub" data-es>Últimos 30 días · Actualizado {TODAY}</div>
    <div class="sub" data-en>Last 30 days · Updated {TODAY}</div>
  </div>
  <div>
    <button class="lang-btn" onclick="document.body.classList.toggle('en');this.textContent=document.body.classList.contains('en')?'ES':'EN'">EN</button>
  </div>
</div>

<div class="page">

<!-- FILTROS -->
<div class="sec-title" data-es>Filtros</div>
<div class="sec-title" data-en>Filters</div>
<div class="filters">
  <div class="filter-group">
    <label data-es>Grupo de agentes</label>
    <label data-en>Agent group</label>
    <select id="fGroup" onchange="refresh()">
      <option value="all" data-es>Todos los grupos</option>
      <option value="all" data-en>All groups</option>
      <option value="us_care">US Care</option>
      <option value="emea_care">EMEA Care</option>
      <option value="other" data-es>Otros grupos</option>
      <option value="other" data-en>Other groups</option>
    </select>
  </div>
  <div class="filter-group">
    <label data-es>Canal de contacto</label>
    <label data-en>Contact channel</label>
    <select id="fChannel" onchange="refresh()">
      <option value="all" data-es>Todos los canales</option>
      <option value="all" data-en>All channels</option>
      <option value="voice_direct" data-es>Voz directa (rep)</option>
      <option value="voice_direct" data-en>Direct voice (rep)</option>
      <option value="voice_rep" data-es>Voz vía CXI/Sierra</option>
      <option value="voice_rep" data-en>Voice via CXI/Sierra</option>
      <option value="email">Email</option>
      <option value="messaging">Messaging / Chat</option>
    </select>
  </div>
  <div class="filter-group">
    <label data-es>Delivery Method</label>
    <label data-en>Delivery Method</label>
    <select id="fDM" onchange="refresh()">
      <option value="all" data-es>Todos</option>
      <option value="all" data-en>All</option>
      <option value="bank_deposit">Bank Deposit</option>
      <option value="office_pick-up">Office Pick-Up</option>
      <option value="mobile_payment">Mobile Payment</option>
      <option value="home_delivery">Home Delivery</option>
    </select>
  </div>
  <div class="filter-group">
    <label data-es>Período</label>
    <label data-en>Period</label>
    <select id="fDays" onchange="refresh()">
      <option value="30" data-es>Últimos 30 días</option>
      <option value="30" data-en>Last 30 days</option>
      <option value="14" data-es>Últimos 14 días</option>
      <option value="14" data-en>Last 14 days</option>
      <option value="7" data-es>Últimos 7 días</option>
      <option value="7" data-en>Last 7 days</option>
    </select>
  </div>
  <div class="filter-note" data-es>* Tickets VA-only excluidos siempre (sin rep humano)</div>
  <div class="filter-note" data-en>* VA-only tickets always excluded (no human rep)</div>
</div>

<!-- KPIs -->
<div class="sec-title" data-es>Resumen del período seleccionado</div>
<div class="sec-title" data-en>Summary for selected period</div>
<div class="kpi-grid">
  <div class="kpi clay">
    <div class="val" id="kpiTotal">—</div>
    <div class="lbl" data-es>Tickets F1 elegibles</div>
    <div class="lbl" data-en>Eligible F1 tickets</div>
    <div class="sublbl" data-es>Con rep humano, excluyendo VA-only</div>
    <div class="sublbl" data-en>With human rep, excluding VA-only</div>
  </div>
  <div class="kpi red">
    <div class="val" id="kpiAdh">—</div>
    <div class="lbl" data-es>Adherencia</div>
    <div class="lbl" data-en>Adherence</div>
    <div class="sublbl" data-es>Tickets con acción correcta / total</div>
    <div class="sublbl" data-en>Tickets with correct action / total</div>
  </div>
  <div class="kpi red">
    <div class="val" id="kpiGap">—</div>
    <div class="lbl" data-es>Tickets sin acción (GAP)</div>
    <div class="lbl" data-en>Tickets without action (GAP)</div>
    <div class="sublbl" data-es>Oportunidad de mejora</div>
    <div class="sublbl" data-en>Improvement opportunity</div>
  </div>
  <div class="kpi clay">
    <div class="val" id="kpiTrend">—</div>
    <div class="lbl" data-es>Tendencia (últimos 7 vs anteriores 7 días)</div>
    <div class="lbl" data-en>Trend (last 7 vs previous 7 days)</div>
    <div class="sublbl" data-es>↑ mejora · ↓ baja · = sin cambio</div>
    <div class="sublbl" data-en>↑ improving · ↓ declining · = no change</div>
  </div>
</div>

<!-- HERO: Sustitución POP → Payment Confirmation -->
<div class="sec-title" data-es>★ La métrica clave — ¿Estamos sustituyendo POP por Payment Confirmation?</div>
<div class="sec-title" data-en>★ The key metric — Are we substituting POP with Payment Confirmation?</div>
<div class="card" style="border:2px solid var(--clay)">
  <div class="card-header">
    <h3 data-es>Payment Confirmation (↑ correcto) vs POP (↓ atajo caro) — territorio pagado &lt;48h</h3>
    <h3 data-en>Payment Confirmation (↑ correct) vs POP (↓ expensive shortcut) — paid &lt;48h territory</h3>
    <div class="card-sub" data-es>El éxito no es una sola línea subiendo — son dos líneas en sentidos opuestos. Mide sobre todo el territorio donde la acción correcta es confirmar (pagado + &lt;48h, F1+F2 juntos). Se combinan porque abrir un POP crea una Side Conversation, lo que mueve el ticket de F1 a F2 — el atajo solo es visible al juntar ambos.</div>
    <div class="card-sub" data-en>Success isn't one line rising — it's two lines moving in opposite directions. Measured over the full territory where the correct action is to confirm (paid + &lt;48h, F1+F2 combined). They're combined because opening a POP creates a Side Conversation, which moves the ticket from F1 to F2 — the shortcut is only visible when both are joined.</div>
  </div>
  <div class="chart-wrap tall"><canvas id="chartSubst"></canvas></div>
  <div class="explain">
    <span data-es>
      <strong>Cómo leerlo:</strong> la línea <span style="color:#5A8A6A;font-weight:700">verde (Payment Confirmation)</span> debe subir; la línea <span style="color:#B84A4A;font-weight:700">roja (POP)</span> debe bajar. Cuando se cruzan, significa que el equipo dejó de usar el POP como reflejo y está resolviendo al primer contacto.
      <span class="tip">💡 Importante: el POP NO es un error en todos los casos — en F3 (&gt;48h) es la acción correcta. Aquí medimos solo F1, donde el POP es un atajo evitable. La sustitución es más visible en Bank Deposit (usa el filtro de Delivery Method).</span>
    </span>
    <span data-en>
      <strong>How to read it:</strong> the <span style="color:#5A8A6A;font-weight:700">green line (Payment Confirmation)</span> should rise; the <span style="color:#B84A4A;font-weight:700">red line (POP)</span> should fall. When they cross, it means the team stopped using POP as a reflex and is resolving at first contact.
      <span class="tip">💡 Important: POP is NOT an error in every case — in F3 (&gt;48h) it's the correct action. Here we measure only F1, where POP is an avoidable shortcut. Substitution is most visible in Bank Deposit (use the Delivery Method filter).</span>
    </span>
  </div>
</div>

<!-- CHART 1: Tendencia % diario -->
<div class="sec-title" data-es>¿Está mejorando la adherencia?</div>
<div class="sec-title" data-en>Is adherence improving?</div>
<div class="card">
  <div class="card-header">
    <h3 data-es>% de Adherencia por Día</h3>
    <h3 data-en>Daily Adherence %</h3>
    <div class="card-sub" data-es>Cada punto = un día. Muestra si los agentes están aplicando Payment Confirmation con más frecuencia con el paso del tiempo.</div>
    <div class="card-sub" data-en>Each point = one day. Shows whether agents are applying Payment Confirmation more frequently over time.</div>
  </div>
  <div class="chart-wrap tall"><canvas id="chartPct"></canvas></div>
  <div class="explain">
    <span data-es>
      <strong>Qué buscar:</strong> una tendencia ascendente en esta línea indica que el entrenamiento o la activación de triggers está funcionando.
      Si la línea permanece cerca de 0%, los agentes aún no están aplicando la macro ni seleccionando el motivo de contacto correcto.
      <span class="tip">💡 Un pico aislado en un día no indica mejora — busca una tendencia sostenida de al menos 3-5 días consecutivos subiendo.</span>
    </span>
    <span data-en>
      <strong>What to look for:</strong> an upward trend in this line indicates training or trigger activation is working.
      If the line stays near 0%, agents are still not applying the macro or selecting the correct contact reason.
      <span class="tip">💡 An isolated spike on one day doesn't indicate improvement — look for a sustained trend of at least 3-5 consecutive days rising.</span>
    </span>
  </div>
</div>

<!-- CHART 2+3: Volumen por día -->
<div class="sec-title" data-es>¿Cuántos tickets hay y cuántos reciben la acción correcta?</div>
<div class="sec-title" data-en>How many tickets exist and how many receive the correct action?</div>
<div class="two">
  <div class="card">
    <div class="card-header">
      <h3 data-es>Tickets por Día — Adherentes vs GAP</h3>
      <h3 data-en>Tickets per Day — Adherent vs GAP</h3>
      <div class="card-sub" data-es>Verde = recibió Payment Confirmation. Salmón = no la recibió (oportunidad perdida).</div>
      <div class="card-sub" data-en>Green = received Payment Confirmation. Salmon = did not receive it (missed opportunity).</div>
    </div>
    <div class="chart-wrap"><canvas id="chartVol"></canvas></div>
    <div class="explain">
      <span data-es>
        <strong>GAP (salmón)</strong> = clientes que deberían haber recibido confirmación de pago pero no la recibieron.
        Cada barra salmón representa una oportunidad donde el agente no siguió el proceso correcto.
        <span class="tip">💡 El volumen alto de salmón no es una falla del sistema — es la brecha de proceso que este dashboard está midiendo.</span>
      </span>
      <span data-en>
        <strong>GAP (salmon)</strong> = customers who should have received a payment confirmation but didn't.
        Each salmon bar represents an opportunity where the agent didn't follow the correct process.
        <span class="tip">💡 High salmon volume isn't a system failure — it's the process gap this dashboard is measuring.</span>
      </span>
    </div>
  </div>

  <div class="card">
    <div class="card-header">
      <h3 data-es>Desglose por Señal de Adherencia</h3>
      <h3 data-en>Breakdown by Adherence Signal</h3>
      <div class="card-sub" data-es>Qué tipo de evidencia indica que el agente tomó la acción correcta.</div>
      <div class="card-sub" data-en>What type of evidence indicates the agent took the correct action.</div>
    </div>
    <div class="chart-wrap"><canvas id="chartSignal"></canvas></div>
    <div class="explain">
      <span data-es>
        <strong>Macro/Quicktext</strong> (<span class="pill">ria_payment_confirmation_reliable_correspondent_sent</span>): el agente usó el shortcut en Zendesk — aplica a email y chat.<br>
        <strong>RFC correcto</strong> (<span class="pill">order__payment_confirmation</span>): el agente seleccionó "Payment Confirmation" como motivo de contacto — aplica a todos los canales incluyendo voz.<br>
        <strong>Trigger automático</strong> (<span class="pill">payment_confirmation_advisory_applied</span>): Zendesk envió la nota interna alertando al agente — aún en rollout.
        <span class="tip">💡 Un ticket puede tener una o varias señales. Las tres juntas = proceso completo.</span>
      </span>
      <span data-en>
        <strong>Macro/Quicktext</strong> (<span class="pill">ria_payment_confirmation_reliable_correspondent_sent</span>): agent used the Zendesk shortcut — applies to email and chat.<br>
        <strong>Correct RFC</strong> (<span class="pill">order__payment_confirmation</span>): agent selected "Payment Confirmation" as contact reason — applies to all channels including voice.<br>
        <strong>Auto trigger</strong> (<span class="pill">payment_confirmation_advisory_applied</span>): Zendesk sent the internal note alerting the agent — still in rollout.
        <span class="tip">💡 A ticket can have one or more signals. All three together = complete process.</span>
      </span>
    </div>
  </div>
</div>

<!-- CHART 4: Por canal -->
<div class="sec-title" data-es>¿En qué canal están fallando más?</div>
<div class="sec-title" data-en>Which channel is underperforming?</div>
<div class="card">
  <div class="card-header">
    <h3 data-es>Adherencia por Canal de Contacto</h3>
    <h3 data-en>Adherence by Contact Channel</h3>
    <div class="card-sub" data-es>Comparación de adherencia entre canales. Cada canal tiene una regla diferente: voz no requiere macro, solo RFC correcto.</div>
    <div class="card-sub" data-en>Adherence comparison across channels. Each channel has a different rule: voice doesn't require macro, only correct RFC.</div>
  </div>
  <div class="chart-wrap"><canvas id="chartCh"></canvas></div>
  <div class="explain">
    <span data-es>
      <strong>Voz directa</strong>: el rep lee el script y envía confirmación vía FX Client (no Zendesk). Adherente si seleccionó RFC = Payment Confirmation.<br>
      <strong>Voz vía CXI/Sierra</strong>: llamada transferida del agente de IA al rep humano. Misma regla que voz directa.<br>
      <strong>Email</strong>: requiere aplicar la macro o quicktext de Payment Confirmation.<br>
      <strong>Messaging/Chat</strong>: requiere usar el shortcut de messaging equivalente.
      <span class="tip">💡 Si voz está en 0% pero email tiene algo de adherencia, el problema es principalmente de entrenamiento en voz — el RFC no se está seleccionando.</span>
    </span>
    <span data-en>
      <strong>Direct voice</strong>: rep reads script and sends confirmation via FX Client (not Zendesk). Adherent if RFC = Payment Confirmation was selected.<br>
      <strong>Voice via CXI/Sierra</strong>: call transferred from AI agent to human rep. Same rule as direct voice.<br>
      <strong>Email</strong>: requires applying the Payment Confirmation macro or quicktext.<br>
      <strong>Messaging/Chat</strong>: requires using the equivalent messaging shortcut.
      <span class="tip">💡 If voice is at 0% but email has some adherence, the problem is mainly voice training — RFC is not being selected.</span>
    </span>
  </div>
</div>

<!-- TABLA DETALLE -->
<div class="sec-title" data-es>Detalle por Delivery Method y Canal</div>
<div class="sec-title" data-en>Detail by Delivery Method and Channel</div>
<div class="card">
  <div class="card-header">
    <div class="card-sub" data-es>Combinación de cada delivery method con cada canal. Permite identificar exactamente dónde está el mayor GAP.</div>
    <div class="card-sub" data-en>Combination of each delivery method with each channel. Helps identify exactly where the largest gap is.</div>
  </div>
  <table id="detailTable">
    <thead>
      <tr>
        <th data-es>Delivery Method</th><th data-en>Delivery Method</th>
        <th data-es>Canal</th><th data-en>Channel</th>
        <th data-es>Total</th><th data-en>Total</th>
        <th data-es>Adherentes</th><th data-en>Adherent</th>
        <th data-es>GAP</th><th data-en>GAP</th>
        <th data-es>Adherencia</th><th data-en>Adherence</th>
      </tr>
    </thead>
    <tbody id="detailBody"></tbody>
  </table>
</div>

</div><!-- /page -->

<script>
const ALL_TICKETS = {TICKETS_JSON};

const DM_LABEL = {{
  'bank_deposit':'Bank Deposit','office_pick-up':'Office Pick-Up',
  'mobile_payment':'Mobile Payment','home_delivery':'Home Delivery'
}};
const CH_LABEL_ES = {{
  'voice_direct':'Voz directa','voice_rep':'Voz CXI/Sierra',
  'email':'Email','messaging':'Messaging','other':'Otro'
}};
const CH_LABEL_EN = {{
  'voice_direct':'Direct voice','voice_rep':'Voice CXI/Sierra',
  'email':'Email','messaging':'Messaging','other':'Other'
}};

let charts = {{}};

function getFilters() {{
  return {{
    group:   document.getElementById('fGroup').value,
    channel: document.getElementById('fChannel').value,
    dm:      document.getElementById('fDM').value,
    days:    parseInt(document.getElementById('fDays').value)
  }};
}}

function filterTickets(f, scens) {{
  scens = scens || ['F1'];   // default: solo F1 (foco del dashboard)
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - f.days);
  const cutStr = cutoff.toISOString().slice(0,10);
  return ALL_TICKETS.filter(t => {{
    if (!scens.includes(t.scen)) return false;
    if (t.adherent === null) return false; // va_only
    if (t.date < cutStr) return false;
    if (f.group   !== 'all' && t.group   !== f.group)   return false;
    if (f.channel !== 'all' && t.channel !== f.channel) return false;
    if (f.dm      !== 'all' && t.dm      !== f.dm)      return false;
    return true;
  }});
}}

function dailyAgg(tickets) {{
  const m = {{}};
  tickets.forEach(t => {{
    if (!m[t.date]) m[t.date] = {{n:0,adh:0}};
    m[t.date].n++;
    if (t.adherent) m[t.date].adh++;
  }});
  const days = Object.keys(m).sort();
  return {{
    days,
    n:   days.map(d=>m[d].n),
    adh: days.map(d=>m[d].adh),
    pct: days.map(d=>m[d].n ? +(m[d].adh/m[d].n*100).toFixed(1) : 0)
  }};
}}

function destroyChart(id) {{
  if (charts[id]) {{ charts[id].destroy(); delete charts[id]; }}
}}

function makeChart(id, cfg) {{
  destroyChart(id);
  charts[id] = new Chart(document.getElementById(id), cfg);
}}

const BASE = {{
  responsive:true, maintainAspectRatio:false,
  plugins:{{
    legend:{{position:'bottom',labels:{{font:{{size:12}},boxWidth:12,padding:16}}}},
    tooltip:{{cornerRadius:4,callbacks:{{label:ctx=>` ${{ctx.dataset.label}}: ${{ctx.parsed.y ?? ctx.parsed}}`}}}}
  }},
  scales:{{
    x:{{ticks:{{font:{{size:11}},maxRotation:45}},grid:{{display:false}}}},
    y:{{grid:{{color:'#f0f0f0'}}}}
  }}
}};

function refresh() {{
  const f = getFilters();
  const tickets = filterTickets(f);
  const {{days, n, adh, pct}} = dailyAgg(tickets);

  const total = tickets.length;
  const adhN  = tickets.filter(t=>t.adherent).length;
  const gap   = total - adhN;
  const adhPct = total ? (adhN/total*100).toFixed(1) : '0.0';

  // Trend: últimos 7 vs anteriores 7
  const sorted = [...days].sort();
  const last7 = sorted.slice(-7);
  const prev7 = sorted.slice(-14,-7);
  const pctLast = last7.length ? (tickets.filter(t=>last7.includes(t.date)&&t.adherent).length /
    Math.max(1,tickets.filter(t=>last7.includes(t.date)).length)*100).toFixed(1) : null;
  const pctPrev = prev7.length ? (tickets.filter(t=>prev7.includes(t.date)&&t.adherent).length /
    Math.max(1,tickets.filter(t=>prev7.includes(t.date)).length)*100).toFixed(1) : null;
  let trendTxt = '—';
  if (pctLast !== null && pctPrev !== null) {{
    const diff = (parseFloat(pctLast)-parseFloat(pctPrev)).toFixed(1);
    trendTxt = diff > 0 ? `↑ +${{diff}}pp` : diff < 0 ? `↓ ${{diff}}pp` : `= 0pp`;
  }}

  document.getElementById('kpiTotal').textContent = total.toLocaleString();
  document.getElementById('kpiAdh').textContent   = adhPct + '%';
  document.getElementById('kpiGap').textContent   = gap.toLocaleString();
  document.getElementById('kpiTrend').textContent = trendTxt;

  // Colores del trend en KPI
  const trendEl = document.getElementById('kpiTrend').parentElement;
  trendEl.className = 'kpi ' + (trendTxt.startsWith('↑') ? 'green' : trendTxt.startsWith('↓') ? 'red' : 'clay');

  const adhEl = document.getElementById('kpiAdh').parentElement;
  adhEl.className = 'kpi ' + (parseFloat(adhPct)>=30?'green':parseFloat(adhPct)>=10?'':'red');

  // Chart HERO: Sustitución POP -> Payment Confirmation
  // Mide sobre el TERRITORIO Payment Confirmation = F1+F2 (pagado + <48h).
  // Se combinan porque abrir un POP crea una SC, lo que mueve el ticket de F1 a F2:
  // el atajo solo es visible al juntar ambos.
  // PC%  = % con macro o RFC (acción correcta de confirmación)
  // POP% = % con tag de POP (el atajo caro que crea backlog)
  const territory = filterTickets(f, ['F1','F2']);
  const substDays = [...new Set(territory.map(t=>t.date))].sort();
  const popByDay = {{}};
  territory.forEach(t => {{
    if (!popByDay[t.date]) popByDay[t.date] = {{pc:0, pop:0, n:0}};
    popByDay[t.date].n++;
    if (t.has_macro || t.has_rfc) popByDay[t.date].pc++;
    if (t.has_pop)                popByDay[t.date].pop++;
  }});
  const pcPct  = substDays.map(d => popByDay[d].n ? +(popByDay[d].pc /popByDay[d].n*100).toFixed(1) : 0);
  const popPct = substDays.map(d => popByDay[d].n ? +(popByDay[d].pop/popByDay[d].n*100).toFixed(1) : 0);
  const pcAbs  = substDays.map(d => popByDay[d].pc);
  const popAbs = substDays.map(d => popByDay[d].pop);

  makeChart('chartSubst', {{
    type:'line',
    data:{{labels:substDays, datasets:[
      {{label:'Payment Confirmation % (correcto ↑)', data:pcPct,
        borderColor:'#5A8A6A', backgroundColor:'rgba(90,138,106,.10)',
        pointRadius:4, pointHoverRadius:6, tension:.3, fill:true, borderWidth:3}},
      {{label:'POP % (atajo evitable ↓)', data:popPct,
        borderColor:'#B84A4A', backgroundColor:'rgba(184,74,74,.08)',
        pointRadius:4, pointHoverRadius:6, tension:.3, fill:true, borderWidth:3,
        borderDash:[5,3]}}
    ]}},
    options:{{...BASE,
      plugins:{{...BASE.plugins,
        tooltip:{{callbacks:{{label:ctx=>{{
          const i=ctx.dataIndex;
          const nn=popByDay[substDays[i]]?popByDay[substDays[i]].n:0;
          if(ctx.datasetIndex===0) return ` Payment Confirmation: ${{pcPct[i]}}% (${{pcAbs[i]}} de ${{nn}})`;
          return ` POP: ${{popPct[i]}}% (${{popAbs[i]}} de ${{nn}})`;
        }}}}}}
      }},
      scales:{{...BASE.scales, y:{{...BASE.scales.y,min:0,
        max:Math.max(50,Math.max(...pcPct,...popPct)+10),
        ticks:{{callback:v=>v+'%'}}}}}}
    }}
  }});

  // Chart 1: % diario
  makeChart('chartPct', {{
    type:'line',
    data:{{labels:days, datasets:[{{
      label:'% Adherencia',
      data:pct,
      borderColor:'#CC785C',
      backgroundColor:'rgba(204,120,92,.12)',
      pointRadius:5, pointHoverRadius:7,
      tension:.3, fill:true,
      pointBackgroundColor: pct.map(v=>v>0?'#5A8A6A':'#CC785C')
    }}]}},
    options:{{...BASE,
      plugins:{{...BASE.plugins,
        annotation:{{annotations:{{line1:{{type:'line',yMin:0,yMax:0,borderColor:'#ddd',borderWidth:1}}}}}},
        tooltip:{{callbacks:{{label:ctx=>`Adherencia: ${{ctx.parsed.y}}% (${{adh[ctx.dataIndex]}} de ${{n[ctx.dataIndex]}} tickets)` }}}}
      }},
      scales:{{...BASE.scales, y:{{...BASE.scales.y,min:0,max:Math.max(100,Math.max(...pct)+10),
        ticks:{{callback:v=>v+'%'}}}}}}
    }}
  }});

  // Chart 2: Volumen stacked
  makeChart('chartVol', {{
    type:'bar',
    data:{{labels:days, datasets:[
      {{label:'Adherentes ✓', data:adh, backgroundColor:'#5A8A6A', borderRadius:3}},
      {{label:'GAP (sin acción)', data:n.map((x,i)=>x-adh[i]), backgroundColor:'#E8C4B4', borderRadius:3}}
    ]}},
    options:{{...BASE,
      scales:{{x:{{...BASE.scales.x,stacked:true}},y:{{...BASE.scales.y,stacked:true,
        ticks:{{callback:v=>v+' tix'}}}}}}
    }}
  }});

  // Chart 3: Señales
  const nMacro   = tickets.filter(t=>t.has_macro).length;
  const nRfc     = tickets.filter(t=>t.has_rfc).length;
  const nTrigger = tickets.filter(t=>t.has_trigger).length;
  const nNone    = tickets.filter(t=>!t.has_macro&&!t.has_rfc&&!t.has_trigger).length;
  makeChart('chartSignal', {{
    type:'doughnut',
    data:{{
      labels:['Macro/Quicktext','RFC correcto','Trigger automático','Sin señal (GAP)'],
      datasets:[{{
        data:[nMacro,nRfc,nTrigger,nNone],
        backgroundColor:['#5A8A6A','#6A8CAA','#C07820','#E8C4B4'],
        borderWidth:2, borderColor:'#fff'
      }}]
    }},
    options:{{responsive:true,maintainAspectRatio:false,
      plugins:{{
        legend:{{position:'right',labels:{{font:{{size:12}},boxWidth:14,padding:14}}}},
        tooltip:{{callbacks:{{label:ctx=>` ${{ctx.label}}: ${{ctx.parsed}} tickets (${{total?+(ctx.parsed/total*100).toFixed(1):0}}%)`}}}}
      }}
    }}
  }});

  // Chart 4: Por canal
  const channels = ['voice_direct','voice_rep','email','messaging','other'];
  const isEN = document.body.classList.contains('en');
  const chLabels = channels.map(c=>(isEN?CH_LABEL_EN:CH_LABEL_ES)[c]||c);
  const chTotals = channels.map(c=>tickets.filter(t=>t.channel===c).length);
  const chAdh    = channels.map(c=>tickets.filter(t=>t.channel===c&&t.adherent).length);
  const chPct    = chTotals.map((n,i)=>n?+(chAdh[i]/n*100).toFixed(1):0);
  makeChart('chartCh', {{
    type:'bar',
    data:{{labels:chLabels, datasets:[
      {{label:'Adherentes ✓', data:chAdh, backgroundColor:'#5A8A6A',borderRadius:3}},
      {{label:'GAP', data:chTotals.map((n,i)=>n-chAdh[i]), backgroundColor:'#E8C4B4',borderRadius:3}}
    ]}},
    options:{{...BASE,
      scales:{{
        x:{{...BASE.scales.x,stacked:true,ticks:{{font:{{size:12}},maxRotation:0}}}},
        y:{{...BASE.scales.y,stacked:true}}
      }},
      plugins:{{...BASE.plugins,
        tooltip:{{callbacks:{{
          afterBody: ctx=>{{
            const i=ctx[0].dataIndex;
            return [`Adherencia: ${{chPct[i]}}% (${{chAdh[i]}}/${{chTotals[i]}})`];
          }}
        }}}}
      }}
    }}
  }});

  // Tabla detalle
  const dms = ['bank_deposit','office_pick-up','mobile_payment','home_delivery'];
  const chs = ['voice_direct','voice_rep','email','messaging','other'];
  const rows = [];
  dms.forEach(dm=>chs.forEach(ch=>{{
    const bucket = tickets.filter(t=>t.dm===dm&&t.channel===ch);
    if (!bucket.length) return;
    const a = bucket.filter(t=>t.adherent).length;
    const p = +(a/bucket.length*100).toFixed(1);
    rows.push({{dm,ch,n:bucket.length,a,p}});
  }}));
  rows.sort((a,b)=>b.n-a.n);

  const tbody = document.getElementById('detailBody');
  tbody.innerHTML = rows.map(r=>{{
    const bc = r.p>=30?'b-grn':r.p>=10?'b-mid':'b-red';
    const dmLbl = DM_LABEL[r.dm]||r.dm;
    const chLbl = (isEN?CH_LABEL_EN:CH_LABEL_ES)[r.ch]||r.ch;
    return `<tr>
      <td><strong>${{dmLbl}}</strong></td>
      <td>${{chLbl}}</td>
      <td>${{r.n}}</td>
      <td>${{r.a}}</td>
      <td>${{r.n-r.a}}</td>
      <td><span class="badge ${{bc}}">${{r.p}}%</span></td>
    </tr>`;
  }}).join('') || '<tr><td colspan="6" class="no-data">Sin datos para los filtros seleccionados</td></tr>';
}}

// Init
refresh();
</script>
</body>
</html>"""

out = Path("reports/daily_adherence.html")
out.write_text(html, encoding="utf-8")
print(f"Guardado: {out}  ({out.stat().st_size/1024:.0f} KB)")
