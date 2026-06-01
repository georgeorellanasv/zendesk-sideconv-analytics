"""
Genera reports/context.html — página de contexto y metodología del
dashboard de adherencia Payment Confirmation.

Usage: python -m scripts.build_context_page
"""
from datetime import date
from pathlib import Path

TODAY = date.today().strftime("%d %b %Y")

html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Contexto y Metodología — Payment Confirmation Adherencia</title>
<style>
:root{
  --paper:#F5F4EE;--ink:#1F1D1B;--clay:#CC785C;--clay-dk:#A1543D;
  --sand:#EBE5D7;--slate:#6A8CAA;--border:rgba(20,20,19,.10);
  --green:#5A8A6A;--red:#B84A4A;--orange:#C07820;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,-apple-system,sans-serif;background:var(--paper);color:var(--ink);font-size:14px;line-height:1.6}

.header{background:var(--ink);color:var(--paper);padding:28px 48px;display:flex;justify-content:space-between;align-items:flex-end}
.header h1{font-size:20px;font-weight:600}
.header .sub{font-size:12px;opacity:.6;margin-top:3px}
.nav-btn{background:var(--clay);color:#fff;padding:8px 18px;border-radius:5px;text-decoration:none;font-size:13px;font-weight:600}

.page{max-width:860px;margin:0 auto;padding:36px 24px 80px}

/* Secciones */
.sec{margin-bottom:44px}
.sec-num{font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--clay);margin-bottom:6px}
.sec h2{font-size:19px;font-weight:700;margin-bottom:16px;line-height:1.3}
.sec p{font-size:14px;line-height:1.7;margin-bottom:12px;color:#333}
.sec p:last-child{margin-bottom:0}

/* Callout boxes */
.callout{border-radius:8px;padding:16px 20px;margin:16px 0;font-size:13px;line-height:1.7}
.callout.sand{background:var(--sand);border-left:3px solid var(--clay)}
.callout.red{background:#FDE8E8;border-left:3px solid var(--red)}
.callout.green{background:#E8F5E9;border-left:3px solid var(--green)}
.callout.slate{background:#EEF3F7;border-left:3px solid var(--slate)}
.callout strong{display:block;margin-bottom:4px;font-size:13px}

/* Steps */
.steps{counter-reset:step;list-style:none;padding:0;margin:16px 0}
.steps li{counter-increment:step;padding:14px 14px 14px 52px;position:relative;border-bottom:1px solid var(--border);font-size:13px;line-height:1.65}
.steps li:last-child{border-bottom:none}
.steps li::before{content:counter(step);position:absolute;left:14px;top:14px;width:24px;height:24px;background:var(--clay);color:#fff;border-radius:50%;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}
.steps li strong{display:block;margin-bottom:3px;font-size:14px}

/* Tabla de escenarios */
.scenario-table{width:100%;border-collapse:collapse;font-size:13px;margin:16px 0}
.scenario-table th{background:var(--ink);color:var(--paper);padding:10px 12px;text-align:left;font-size:12px;font-weight:600;letter-spacing:.3px}
.scenario-table td{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:top}
.scenario-table tr:last-child td{border-bottom:none}
.scenario-table tr:nth-child(even) td{background:rgba(235,229,215,.3)}
.esc-badge{display:inline-block;background:var(--clay);color:#fff;border-radius:4px;padding:2px 8px;font-weight:700;font-size:12px;min-width:28px;text-align:center}

/* Tabla de tags */
.tag-table{width:100%;border-collapse:collapse;font-size:13px;margin:16px 0}
.tag-table th{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:#888;border-bottom:2px solid var(--border);padding:8px 10px;text-align:left}
.tag-table td{padding:10px 10px;border-bottom:1px solid var(--border);vertical-align:top}
.tag-table tr:last-child td{border-bottom:none}
.pill{display:inline-block;background:#e8e8e0;border-radius:3px;padding:2px 7px;font-size:11px;font-family:monospace;color:#333;white-space:nowrap}
.pill.green{background:#E8F5E9;color:#2E6B42}
.pill.clay{background:#FAE8E0;color:var(--clay-dk)}
.pill.slate{background:#EEF3F7;color:#3C5A7A}

/* Decision tree */
.tree{font-family:monospace;font-size:12.5px;line-height:1.9;background:#fff;border:1px solid var(--border);border-radius:8px;padding:20px 24px;overflow-x:auto;color:#333}

/* FAQ */
.faq{margin:16px 0}
.faq-q{font-weight:700;font-size:14px;color:var(--clay-dk);margin-top:20px;margin-bottom:6px}
.faq-a{font-size:13px;line-height:1.7;color:#333;padding-left:12px;border-left:2px solid var(--sand)}

/* Métricas card */
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0}
.metric-card{background:#fff;border:1px solid var(--border);border-radius:8px;padding:16px}
.metric-card .name{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#888;margin-bottom:6px}
.metric-card .formula{font-family:monospace;font-size:13px;background:var(--sand);border-radius:4px;padding:6px 10px;margin-bottom:8px}
.metric-card .why{font-size:12px;color:#666;line-height:1.6}

/* Nav links */
.nav-links{display:flex;gap:12px;margin-bottom:28px;flex-wrap:wrap}
.nav-link{padding:7px 16px;border-radius:5px;font-size:13px;font-weight:600;text-decoration:none;border:1px solid var(--border);background:#fff;color:var(--ink)}
.nav-link.active{background:var(--clay);color:#fff;border-color:var(--clay)}

/* lang toggle */
[data-en]{display:none}
body.en [data-es]{display:none}
body.en [data-en]{display:unset}
.lang-btn{background:transparent;border:1px solid rgba(255,255,255,.3);color:var(--paper);padding:4px 12px;border-radius:4px;cursor:pointer;font-size:12px;margin-top:8px}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="sub">Ria Money Transfer · Care Operations</div>
    <h1 data-es>Contexto y Metodología</h1>
    <h1 data-en>Context & Methodology</h1>
    <div class="sub" data-es>Por qué medimos esto y cómo lo calculamos</div>
    <div class="sub" data-en>Why we measure this and how we calculate it</div>
  </div>
  <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
    <a href="daily_adherence.html" class="nav-btn" data-es>→ Ver Dashboard</a>
    <a href="daily_adherence.html" class="nav-btn" data-en>→ View Dashboard</a>
    <button class="lang-btn" onclick="document.body.classList.toggle('en');this.textContent=document.body.classList.contains('en')?'ES':'EN'">EN</button>
  </div>
</div>

<div class="page">

<div class="nav-links">
  <a href="index.html" class="nav-link"><span data-es>Reporte F1–F5</span><span data-en>F1–F5 Report</span></a>
  <a href="context.html" class="nav-link active"><span data-es>Contexto y Metodología</span><span data-en>Context & Methodology</span></a>
  <a href="daily_adherence.html" class="nav-link"><span data-es>Dashboard Diario</span><span data-en>Daily Dashboard</span></a>
  <a href="f1_drilldown.html" class="nav-link"><span data-es>F1 Detalle</span><span data-en>F1 Detail</span></a>
  <a href="contact_reasons.html" class="nav-link"><span data-es>Motivos de Contacto</span><span data-en>Contact Reasons</span></a>
</div>

<!-- 1. POR QUÉ -->
<div class="sec">
  <div class="sec-num" data-es>01 — El Problema</div>
  <div class="sec-num" data-en>01 — The Problem</div>
  <h2 data-es>¿Por qué medimos la adherencia del Payment Confirmation?</h2>
  <h2 data-en>Why are we measuring Payment Confirmation adherence?</h2>

  <p data-es>Cuando un cliente llama porque su transferencia ya fue pagada, el representante de Care tiene una acción clara definida en el playbook: enviar una <strong>confirmación de pago (Payment Confirmation)</strong>. Esta confirmación le dice al cliente que el dinero fue enviado correctamente y le da un documento para presentar al banco receptor si los fondos no aparecen.</p>
  <p data-en>When a customer calls because their transfer has been paid, the Care representative has a clear action defined in the playbook: send a <strong>Payment Confirmation</strong>. This confirmation tells the customer the money was sent correctly and gives them a document to present to the receiving bank if funds don't appear.</p>

  <div class="callout red">
    <strong data-es>El problema actual:</strong>
    <strong data-en>The current problem:</strong>
    <span data-es>Basado en datos de los últimos 30 días, solo el <strong>2.8% de los tickets elegibles</strong> para Payment Confirmation recibieron esa acción. El 97.2% restante — más de 730 tickets — no tiene evidencia de que el cliente recibió su confirmación de pago.</span>
    <span data-en>Based on data from the last 30 days, only <strong>2.8% of eligible tickets</strong> for Payment Confirmation received that action. The remaining 97.2% — over 730 tickets — have no evidence that the customer received their payment confirmation.</span>
  </div>

  <p data-es>Este dashboard existe para <strong>monitorear si eso está mejorando</strong>. No es un reporte de errores — es un termómetro de adopción del proceso que nos dice, día a día, si los equipos están incorporando el Payment Confirmation en su flujo de trabajo.</p>
  <p data-en>This dashboard exists to <strong>monitor whether that is improving</strong>. It's not an error report — it's a process adoption thermometer that tells us, day by day, whether teams are incorporating Payment Confirmation into their workflow.</p>
</div>

<!-- 2. EL PROCESO -->
<div class="sec">
  <div class="sec-num" data-es>02 — El Proceso Correcto</div>
  <div class="sec-num" data-en>02 — The Correct Process</div>
  <h2 data-es>¿Qué debería pasar cuando un cliente llama por una transferencia pagada?</h2>
  <h2 data-en>What should happen when a customer calls about a paid transfer?</h2>

  <ol class="steps">
    <li>
      <strong data-es>Zendesk detecta que la transferencia está pagada</strong>
      <strong data-en>Zendesk detects the transfer is paid</strong>
      <span data-es>Un trigger automático revisa el campo Order Status = "Paid" y deja una nota interna en el ticket alertando al agente que debe tomar acción. Esto deja el tag <span class="pill slate">payment_confirmation_advisory_applied</span> en el ticket. <em>(Aún en rollout — no disponible en todos los grupos)</em></span>
      <span data-en>An automatic trigger checks the Order Status = "Paid" field and leaves an internal note alerting the agent to take action. This adds the tag <span class="pill slate">payment_confirmation_advisory_applied</span> to the ticket. <em>(Still in rollout — not available in all groups)</em></span>
    </li>
    <li>
      <strong data-es>El agente identifica el motivo de contacto</strong>
      <strong data-en>The agent identifies the contact reason</strong>
      <span data-es>El agente selecciona <strong>Payment Confirmation</strong> como motivo de contacto (Reason for Contact) en el formulario del ticket. Esto deja el tag <span class="pill clay">order__payment_confirmation</span>. Este paso aplica a <em>todos los canales</em>, incluyendo voz.</span>
      <span data-en>The agent selects <strong>Payment Confirmation</strong> as the contact reason (RFC) in the ticket form. This adds the tag <span class="pill clay">order__payment_confirmation</span>. This step applies to <em>all channels</em>, including voice.</span>
    </li>
    <li>
      <strong data-es>El agente envía la confirmación al cliente</strong>
      <strong data-en>The agent sends the confirmation to the customer</strong>
      <span data-es>
        <strong>Email / Chat:</strong> aplica el quicktext o macro "Payment Confirmation" en Zendesk → deja el tag <span class="pill green">ria_payment_confirmation_reliable_correspondent_sent</span>.<br>
        <strong>Voz:</strong> el agente lee el script y envía la confirmación vía FX Client (no Zendesk) → no hay tag de macro, pero el RFC correcto es suficiente evidencia.
      </span>
      <span data-en>
        <strong>Email / Chat:</strong> applies the "Payment Confirmation" quicktext or macro in Zendesk → adds the tag <span class="pill green">ria_payment_confirmation_reliable_correspondent_sent</span>.<br>
        <strong>Voice:</strong> the agent reads the script and sends the confirmation via FX Client (not Zendesk) → no macro tag, but the correct RFC is sufficient evidence.
      </span>
    </li>
  </ol>

  <div class="callout slate">
    <strong data-es>¿Por qué el proceso varía por canal?</strong>
    <strong data-en>Why does the process vary by channel?</strong>
    <span data-es>En voz, el agente no puede aplicar una macro de Zendesk mientras está en la llamada — la confirmación se envía directamente desde FX Client (el sistema de transferencias). Por eso, para voz medimos el RFC (motivo de contacto) como evidencia de que el agente identificó correctamente el caso. Para email y chat, la macro de Zendesk ES el canal de envío, por lo que su uso queda registrado directamente.</span>
    <span data-en>In voice calls, the agent can't apply a Zendesk macro while on the call — the confirmation is sent directly from FX Client (the transfer system). That's why for voice we measure the RFC (contact reason) as evidence that the agent correctly identified the case. For email and chat, the Zendesk macro IS the sending channel, so its use is directly recorded.</span>
  </div>
</div>

<!-- 3. LOS ESCENARIOS -->
<div class="sec">
  <div class="sec-num" data-es>03 — Los 5 Escenarios</div>
  <div class="sec-num" data-en>03 — The 5 Scenarios</div>
  <h2 data-es>¿Por qué no todos los tickets pagados son iguales?</h2>
  <h2 data-en>Why aren't all paid tickets the same?</h2>

  <p data-es>El playbook define 5 escenarios distintos (F1–F5) dependiendo del tipo de pago, el método de entrega, y el tiempo transcurrido desde que se procesó. Cada escenario tiene una acción diferente.</p>
  <p data-en>The playbook defines 5 different scenarios (F1–F5) depending on the payment type, delivery method, and time elapsed since it was processed. Each scenario requires a different action.</p>

  <table class="scenario-table">
    <thead>
      <tr>
        <th>Esc.</th>
        <th data-es>Condición</th><th data-en>Condition</th>
        <th data-es>Acción requerida</th><th data-en>Required action</th>
        <th data-es>% del volumen</th><th data-en>% of volume</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><span class="esc-badge">F1</span></td>
        <td data-es>Paid + menos de 48h + sin Side Conversation abierta</td>
        <td data-en>Paid + less than 48h + no open Side Conversation</td>
        <td data-es><strong>Enviar Payment Confirmation</strong> — el cliente necesita confirmación inmediata</td>
        <td data-en><strong>Send Payment Confirmation</strong> — the customer needs immediate confirmation</td>
        <td>30.3%</td>
      </tr>
      <tr>
        <td><span class="esc-badge">F2</span></td>
        <td data-es>Paid + menos de 48h + ya hay Side Conversation abierta</td>
        <td data-en>Paid + less than 48h + Side Conversation already open</td>
        <td data-es><strong>POP vía SC existente</strong> — usar la investigación ya iniciada</td>
        <td data-en><strong>POP via existing SC</strong> — use the already-initiated investigation</td>
        <td>6.5%</td>
      </tr>
      <tr>
        <td><span class="esc-badge">F3</span></td>
        <td data-es>Paid + más de 48h (cualquier DM)</td>
        <td data-en>Paid + more than 48h (any DM)</td>
        <td data-es><strong>Iniciar POP</strong> — si lleva más de 48h sin aparecer, hay que investigar</td>
        <td data-en><strong>Initiate POP</strong> — if funds haven't appeared after 48h, investigation is needed</td>
        <td>59.4%</td>
      </tr>
      <tr>
        <td><span class="esc-badge">F4</span></td>
        <td data-es>Unreliable_Paid + menos de 48h (solo Bank Deposit)</td>
        <td data-en>Unreliable_Paid + less than 48h (Bank Deposit only)</td>
        <td data-es><strong>ETA email / POP Day 1</strong> — advertir que puede tardar más de lo normal</td>
        <td data-en><strong>ETA email / POP Day 1</strong> — warn that it may take longer than normal</td>
        <td>2.5%</td>
      </tr>
      <tr>
        <td><span class="esc-badge">F5</span></td>
        <td data-es>Unreliable_Paid + más de 48h (solo Bank Deposit)</td>
        <td data-en>Unreliable_Paid + more than 48h (Bank Deposit only)</td>
        <td data-es><strong>SC al corresponsal</strong> — escalar al banco para confirmar estado</td>
        <td data-en><strong>SC to correspondent</strong> — escalate to bank to confirm status</td>
        <td>1.4%</td>
      </tr>
    </tbody>
  </table>

  <div class="callout sand">
    <strong data-es>¿Por qué F4 y F5 solo aplican a Bank Deposit?</strong>
    <strong data-en>Why do F4 and F5 only apply to Bank Deposit?</strong>
    <span data-es>El sub-status "Unreliable_Paid" ocurre cuando el sistema confirma el pago pero el corresponsal bancario no ha actualizado su portal todavía. Esto solo sucede con transferencias bancarias (Bank Deposit). Office Pick-Up, Mobile Payment y Home Delivery tienen flujos de confirmación distintos que no generan ese estado.</span>
    <span data-en>"Unreliable_Paid" status occurs when the system confirms payment but the bank correspondent hasn't updated their portal yet. This only happens with bank transfers (Bank Deposit). Office Pick-Up, Mobile Payment, and Home Delivery have different confirmation flows that don't generate that status.</span>
  </div>
</div>

<!-- 4. CÓMO SE MIDE -->
<div class="sec">
  <div class="sec-num" data-es>04 — Cómo se Calcula la Adherencia</div>
  <div class="sec-num" data-en>04 — How Adherence Is Calculated</div>
  <h2 data-es>¿Por qué usamos tags de Zendesk como indicadores?</h2>
  <h2 data-en>Why do we use Zendesk tags as indicators?</h2>

  <p data-es>No existe un campo único en Zendesk que registre "el agente envió el Payment Confirmation". En su lugar, cada acción del agente deja un rastro de tags en el ticket. Medimos esos tags como evidencia indirecta de que la acción fue tomada.</p>
  <p data-en>There is no single field in Zendesk that records "the agent sent the Payment Confirmation." Instead, each agent action leaves a trail of tags on the ticket. We measure those tags as indirect evidence that the action was taken.</p>

  <table class="tag-table">
    <thead>
      <tr>
        <th data-es>Tag</th><th data-en>Tag</th>
        <th data-es>Lo deja</th><th data-en>Added by</th>
        <th data-es>Qué indica</th><th data-en>What it indicates</th>
        <th data-es>Canal</th><th data-en>Channel</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><span class="pill green">ria_payment_confirmation_reliable_correspondent_sent</span></td>
        <td data-es>Macro o quicktext de Zendesk</td>
        <td data-en>Zendesk macro or quicktext</td>
        <td data-es>El agente envió la confirmación de pago usando el shortcut de Zendesk</td>
        <td data-en>The agent sent the payment confirmation using the Zendesk shortcut</td>
        <td>Email, Chat</td>
      </tr>
      <tr>
        <td><span class="pill clay">order__payment_confirmation</span></td>
        <td data-es>Formulario del ticket (Reason for Contact)</td>
        <td data-en>Ticket form (Reason for Contact)</td>
        <td data-es>El agente identificó correctamente que el caso es un Payment Confirmation</td>
        <td data-en>The agent correctly identified the case as a Payment Confirmation</td>
        <td data-es>Todos los canales (voz, email, chat)</td><td data-en>All channels (voice, email, chat)</td>
      </tr>
      <tr>
        <td><span class="pill slate">payment_confirmation_advisory_applied</span></td>
        <td data-es>Trigger automático de Zendesk</td>
        <td data-en>Zendesk automatic trigger</td>
        <td data-es>El sistema detectó las condiciones y alertó al agente. <em>Aún en rollout</em></td>
        <td data-en>The system detected the conditions and alerted the agent. <em>Still in rollout</em></td>
        <td data-es>Automático</td><td data-en>Automatic</td>
      </tr>
    </tbody>
  </table>

  <div class="metric-grid">
    <div class="metric-card">
      <div class="name" data-es>Definición de "Adherente"</div>
      <div class="name" data-en>Definition of "Adherent"</div>
      <div class="formula">tiene macro_tag OR tiene rfc_tag</div>
      <div class="why" data-es>Un ticket es adherente si tiene <em>al menos uno</em> de los dos tags de acción. Esto cubre tanto los casos de email/chat (macro) como los de voz (solo RFC, ya que la macro no aplica).</div>
      <div class="why" data-en>A ticket is adherent if it has <em>at least one</em> of the two action tags. This covers both email/chat cases (macro) and voice cases (only RFC, since macro doesn't apply).</div>
    </div>
    <div class="metric-card">
      <div class="name" data-es>Tickets excluidos</div>
      <div class="name" data-en>Excluded tickets</div>
      <div class="formula">inbound_call_-_va_only OR va_only_solved</div>
      <div class="why" data-es>Los tickets resueltos solo por el agente virtual (sin rep humano) se excluyen. No hay acción humana que medir — el VA resuelve sin intervención del agente.</div>
      <div class="why" data-en>Tickets resolved only by the virtual agent (without a human rep) are excluded. There is no human action to measure — the VA resolves without agent intervention.</div>
    </div>
    <div class="metric-card">
      <div class="name" data-es>% Adherencia</div>
      <div class="name" data-en>Adherence %</div>
      <div class="formula">adherentes / (total - va_only) × 100</div>
      <div class="why" data-es>Del total de tickets F1 con rep humano, qué porcentaje tiene evidencia de que se envió la confirmación de pago.</div>
      <div class="why" data-en>Of all F1 tickets handled by a human rep, what percentage has evidence that the payment confirmation was sent.</div>
    </div>
    <div class="metric-card">
      <div class="name">GAP</div>
      <div class="formula">total_elegibles - adherentes</div>
      <div class="why" data-es>Número de clientes que deberían haber recibido confirmación de pago y no la recibieron. Cada ticket de GAP es una conversación donde el cliente se fue sin la información que necesitaba.</div>
      <div class="why" data-en>Number of customers who should have received a payment confirmation and didn't. Each GAP ticket is a conversation where the customer left without the information they needed.</div>
    </div>
  </div>
</div>

<!-- 5. ÁRBOL -->
<div class="sec">
  <div class="sec-num" data-es>05 — Árbol de Decisión</div>
  <div class="sec-num" data-en>05 — Decision Tree</div>
  <h2 data-es>¿Cómo se clasifica cada ticket en un escenario?</h2>
  <h2 data-en>How is each ticket classified into a scenario?</h2>

  <div class="tree">¿Order Status = "Paid"?
└─ No → fuera de scope (no es un caso de transferencia pagada)
└─ Sí →
    ¿Sub-status contiene "Unreliable"?
    │
    ├─ No (Paid confirmado en ambos sistemas) →
    │   ¿Delivery Method = Bank Deposit?
    │   ├─ No (Office Pick-Up / Mobile / Home Delivery)
    │   │   └─ <span style="color:#5A8A6A;font-weight:700">F1: Enviar Payment Confirmation</span>
    │   └─ Sí (Bank Deposit) →
    │       ¿Menos de 48h desde la fecha de la orden?
    │       ├─ Sí →
    │       │   ¿Tiene Side Conversation abierta?
    │       │   ├─ No  → <span style="color:#5A8A6A;font-weight:700">F1: Enviar Payment Confirmation</span>
    │       │   └─ Sí  → <span style="color:#6A8CAA;font-weight:700">F2: POP vía SC existente</span>
    │       └─ No  → <span style="color:#C07820;font-weight:700">F3: Iniciar POP</span>
    │
    └─ Sí (Unreliable_Paid — solo Bank Deposit) →
        ¿Menos de 48h?
        ├─ Sí → <span style="color:#C07820;font-weight:700">F4: ETA email / POP Day 1</span>
        └─ No → <span style="color:#B84A4A;font-weight:700">F5: SC al corresponsal</span></div>

  <div class="callout sand" style="margin-top:16px">
    <strong data-es>¿Cómo se calcula las "48h"?</strong>
    <strong data-en>How are "48h" calculated?</strong>
    <span data-es>Se toma la fecha del campo "Transaction Date" (el momento en que el corresponsal procesó el pago) y se compara con la fecha de creación del ticket. Si la diferencia es menor o igual a 48 horas, el ticket cae en el escenario de Payment Confirmation o F4. Si es mayor, cae en POP (F3) o F5.</span>
    <span data-en>The "Transaction Date" field (when the correspondent processed the payment) is taken and compared with the ticket creation date. If the difference is 48 hours or less, the ticket falls into the Payment Confirmation or F4 scenario. If greater, it falls into POP (F3) or F5.</span>
  </div>
</div>

<!-- 6. FAQ -->
<div class="sec">
  <div class="sec-num">06 — FAQ</div>
  <h2 data-es>Preguntas frecuentes</h2>
  <h2 data-en>Frequently asked questions</h2>

  <div class="faq">
    <div class="faq-q" data-es>¿Por qué la adherencia está en 2.8% y no en un número más alto?</div>
    <div class="faq-q" data-en>Why is adherence at 2.8% and not higher?</div>
    <div class="faq-a" data-es>Dos razones principales: (1) el trigger de alerta al agente está en rollout — muchos agentes aún no reciben la nota interna automática. (2) Seleccionar el RFC correcto y aplicar la macro son pasos manuales adicionales que el agente debe hacer conscientemente. El 2.8% representa los agentes que ya están siguiendo el proceso completo. El objetivo es escalar ese número.</div>
    <div class="faq-a" data-en>Two main reasons: (1) the agent alert trigger is in rollout — many agents don't yet receive the automatic internal note. (2) Selecting the correct RFC and applying the macro are additional manual steps the agent must consciously perform. The 2.8% represents agents already following the complete process. The goal is to scale that number.</div>

    <div class="faq-q" data-es>¿Un ticket sin el tag de adherencia significa que el cliente NO recibió su confirmación?</div>
    <div class="faq-q" data-en>Does a ticket without the adherence tag mean the customer did NOT receive their confirmation?</div>
    <div class="faq-a" data-es>No necesariamente. Puede que el agente haya enviado la confirmación de otra forma (por ejemplo, por email personal o copiando el texto manualmente) sin usar la macro de Zendesk. Sin embargo, si no hay registro en el sistema, no tenemos forma de saberlo — y el proceso operativo requiere que quede registrado. El tag es la evidencia auditable.</div>
    <div class="faq-a" data-en>Not necessarily. The agent may have sent the confirmation another way (e.g., personal email or copying the text manually) without using the Zendesk macro. However, if there's no record in the system, we have no way to know — and the operational process requires it to be recorded. The tag is the auditable evidence.</div>

    <div class="faq-q" data-es>¿Por qué el trigger automático solo aparece en algunos tickets de voz?</div>
    <div class="faq-q" data-en>Why does the automatic trigger only appear on some voice tickets?</div>
    <div class="faq-a" data-es>El trigger <span class="pill slate">payment_confirmation_advisory_applied</span> está siendo activado gradualmente por grupos. En la semana del análisis solo estaba activo para algunos grupos de US Care y EMEA. La próxima semana debería estar disponible para más grupos.</div>
    <div class="faq-a" data-en>The <span class="pill slate">payment_confirmation_advisory_applied</span> trigger is being gradually activated by group. During the analysis week, it was only active for some US Care and EMEA groups. It should be available to more groups next week.</div>

    <div class="faq-q" data-es>¿Qué pasa con los tickets de transferencias Xe?</div>
    <div class="faq-q" data-en>What about Xe transfer tickets?</div>
    <div class="faq-a" data-es>Las transferencias Xe están fuera del scope actual de este análisis. Tienen sus propios flujos y se agregarán al dashboard en una fase posterior.</div>
    <div class="faq-a" data-en>Xe transfers are currently out of scope for this analysis. They have their own flows and will be added to the dashboard in a later phase.</div>

    <div class="faq-q" data-es>¿Cómo sé si la mejora en adherencia se debe al entrenamiento o a otra cosa?</div>
    <div class="faq-q" data-en>How do I know if adherence improvement is due to training or something else?</div>
    <div class="faq-a" data-es>El dashboard muestra el desglose por <strong>señal</strong> (macro vs RFC vs trigger). Si la mejora viene del trigger (automático), significa que el sistema está haciendo más trabajo. Si viene del RFC o la macro, son los agentes adoptando el proceso. Esa distinción es clave para saber si el entrenamiento está funcionando.</div>
    <div class="faq-a" data-en>The dashboard shows the breakdown by <strong>signal</strong> (macro vs RFC vs trigger). If improvement comes from the trigger (automatic), the system is doing more work. If it comes from the RFC or macro, agents are adopting the process. That distinction is key to knowing whether training is working.</div>
  </div>
</div>

<!-- 7. METAS -->
<div class="sec">
  <div class="sec-num" data-es>07 — Metas y Próximos Pasos</div>
  <div class="sec-num" data-en>07 — Goals & Next Steps</div>
  <h2 data-es>¿Qué es el éxito y cuándo lo alcanzamos?</h2>
  <h2 data-en>What does success look like and when do we reach it?</h2>

  <div class="callout green">
    <strong data-es>Línea base actual (Mayo 2026):</strong>
    <strong data-en>Current baseline (May 2026):</strong>
    <span data-es>2.8% adherencia F1 global · 0.5% US Care · 754 tickets elegibles en 30 días</span>
    <span data-en>2.8% global F1 adherence · 0.5% US Care · 754 eligible tickets in 30 days</span>
  </div>

  <table class="tag-table" style="margin-top:16px">
    <thead>
      <tr>
        <th data-es>Hito</th><th data-en>Milestone</th>
        <th data-es>Meta sugerida</th><th data-en>Suggested target</th>
        <th data-es>Señal en el dashboard</th><th data-en>Signal in dashboard</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td data-es>Trigger activo en todos los grupos US Care</td>
        <td data-en>Trigger active in all US Care groups</td>
        <td data-es>Semana 1 de junio</td><td data-en>Week 1 of June</td>
        <td data-es>↑ <span class="pill slate">payment_confirmation_advisory_applied</span> en chart de señales</td>
        <td data-en>↑ <span class="pill slate">payment_confirmation_advisory_applied</span> in signals chart</td>
      </tr>
      <tr>
        <td data-es>Reps US Care seleccionan RFC correcto</td>
        <td data-en>US Care reps select correct RFC</td>
        <td data-es>20% adherencia en 30 días</td><td data-en>20% adherence in 30 days</td>
        <td data-es>↑ <span class="pill clay">order__payment_confirmation</span> en chart de señales</td>
        <td data-en>↑ <span class="pill clay">order__payment_confirmation</span> in signals chart</td>
      </tr>
      <tr>
        <td data-es>Email/Chat con macro consistente</td>
        <td data-en>Email/Chat with consistent macro use</td>
        <td data-es>40% adherencia email</td><td data-en>40% email adherence</td>
        <td data-es>↑ <span class="pill green">ria_payment_confirmation_...</span></td>
        <td data-en>↑ <span class="pill green">ria_payment_confirmation_...</span></td>
      </tr>
      <tr>
        <td data-es>Proceso completo adoptado (90 días)</td>
        <td data-en>Full process adopted (90 days)</td>
        <td data-es>40% adherencia global F1</td><td data-en>40% global F1 adherence</td>
        <td data-es>Línea de tendencia sostenida arriba de 40%</td>
        <td data-en>Sustained trend line above 40%</td>
      </tr>
    </tbody>
  </table>
</div>

<div style="text-align:center;margin-top:48px;padding-top:24px;border-top:1px solid var(--border);font-size:12px;color:#aaa" data-es>
  Generado automáticamente a partir de datos de Zendesk · """ + TODAY + """ · Ria Money Transfer Care Analytics
</div>
<div style="text-align:center;margin-top:48px;padding-top:24px;border-top:1px solid var(--border);font-size:12px;color:#aaa" data-en>
  Automatically generated from Zendesk data · """ + TODAY + """ · Ria Money Transfer Care Analytics
</div>

</div>
</body>
</html>"""

out = Path("reports/context.html")
out.write_text(html, encoding="utf-8")
print(f"Guardado: {out}  ({out.stat().st_size/1024:.0f} KB)")
