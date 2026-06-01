# Metodología: Medición de Adherencia — Payment Confirmation

**Proyecto:** Zendesk Side Conversation Analytics  
**Área:** Care Operations — Ria Money Transfer  
**Última actualización:** Mayo 2026  

---

## 1. Contexto

El proceso de **Payment Confirmation** define qué acción debe tomar un representante cuando un cliente contacta porque su transferencia ya fue pagada. La adherencia mide qué porcentaje de esos tickets recibió la acción correcta según el playbook operativo.

El análisis cubre todos los canales (email, chat/messaging, voz) y todos los delivery methods (Bank Deposit, Office Pick-Up, Mobile Payment, Home Delivery), con excepción de transferencias Xe (fuera de scope actual).

---

## 2. Reglas del Playbook

| Transfer Status | Delivery Method | Acción | Timing |
|---|---|---|---|
| **Paid** (confirmado en FXClient y portal del corresponsal) | Office Pick-Up | Enviar Payment Confirmation | Inmediato |
| **Paid** | Mobile Wallet | Enviar Payment Confirmation | Inmediato |
| **Paid** | Home Delivery | Enviar Payment Confirmation | Inmediato |
| **Paid-Paid** (confirmado en ambos sistemas) | Bank Deposit < 48h | Enviar Payment Confirmation | Inmediato |
| **Paid-Paid** | Bank Deposit > 48h | Iniciar POP | Inmediato |
| **Paid – Unreliable_Paid** | Bank Deposit < 48h | Zendesk envía email con ETA advice automáticamente. Si el cliente no tiene email: pedir email, actualizar perfil y enviar quicktext POP Day 1 | Inmediato |
| **Paid – Unreliable_Paid** | Bank Deposit > 48h | Enviar solicitud al corresponsal para confirmar estatus. Elegir macro aplicable | Inmediato |

> **Nota:** El sub-status "Unreliable_Paid" aplica exclusivamente a Bank Deposit. Office Pick-Up, Mobile Payment y Home Delivery nunca tienen ese sub-status.

---

## 3. Escenarios de Medición (F1–F5)

| Escenario | Condiciones | Acción Esperada |
|---|---|---|
| **F1** | Paid-Paid + <48h + sin SC abierta (Bank Deposit) / Paid + cualquier DM no-bank | Payment Confirmation |
| **F2** | Paid-Paid + <48h + con SC ya abierta | POP vía SC existente |
| **F3** | Paid-Paid + >48h (cualquier DM) | Iniciar POP |
| **F4** | Unreliable_Paid + <48h (Bank Deposit) | ETA email automático / POP Day 1 |
| **F5** | Unreliable_Paid + >48h (Bank Deposit) | SC al corresponsal |

---

## 4. Cómo Medir Adherencia por Canal

La lógica de medición varía según el canal porque voz no siempre deja registro de macro en Zendesk (el rep lee el script y envía la confirmación vía FX Client).

### 4.1 Email y Chat/Messaging

Se requieren **3 condiciones simultáneas**:

| # | Condición | Tag / Indicador en Zendesk |
|---|---|---|
| 1 | Trigger con nota interna disparado | `payment_confirmation_advisory_applied` |
| 2 | Reason for Contact = Payment Confirmation | `order__payment_confirmation` |
| 3 | Macro o quicktext de Payment Confirmation aplicado | `ria_payment_confirmation_reliable_correspondent_sent` |

> Un ticket se cuenta como **adherente** si los 3 tags están presentes.

### 4.2 Voz (Rep humano)

Se requieren **2 condiciones** (la macro no aplica porque el rep envía la confirmación por FX Client):

| # | Condición | Tag / Indicador en Zendesk |
|---|---|---|
| 1 | Trigger con nota interna disparado | `payment_confirmation_advisory_applied` |
| 2 | Reason for Contact = Payment Confirmation | `order__payment_confirmation` |

> Un ticket se cuenta como **adherente** si ambos tags están presentes.

### 4.3 Identificación del Canal de Voz

| Tipo de ticket de voz | Tags identificadores | Incluir en medición |
|---|---|---|
| Llamada atendida solo por VA (sin rep humano) | `inbound_call_-_va_only`, `va_only_solved` | **No** — excluir |
| Llamada transferida de CXI/Sierra al rep | `inbound_call_-_va_to_rep`, `cxi_ch_voice` | **Sí** — regla de 2 condiciones |
| Llamada directa al rep (sin VA) | `inbound_call` (sin `inbound_call_-_va_only`) | **Sí** — regla de 2 condiciones |

---

## 5. Campos de Clasificación en Zendesk

| Campo | Field ID | Uso |
|---|---|---|
| Delivery Method | `20723928879889` | Clasificar Bank Deposit vs otros |
| Order Status | `30676401574161` | Filtrar tickets "Paid" |
| Order Sub-status | `40201614421265` | Distinguir Paid-Paid vs Unreliable_Paid |
| Transaction Date | `11063635162897` | Calcular si < o > 48h |

### Cálculo de las 48h

`horas_desde_orden = (ticket.created_at − transaction_date) / 3600`

- `≤ 48` → escenario de Payment Confirmation (F1 o F4)
- `> 48` → escenario de POP (F3 o F5)

---

## 6. Árbol de Decisión para Clasificar un Ticket

```
¿Order Status = "Paid"?
└─ No → fuera de scope
└─ Sí →
    ¿Sub-status contiene "Unreliable"?
    ├─ No (Paid-Paid o simplemente Paid) →
    │   ¿Delivery Method = Bank Deposit?
    │   ├─ No (Office PU / Mobile / Home) → F1: Payment Confirmation
    │   └─ Sí (Bank Deposit) →
    │       ¿< 48h?
    │       ├─ Sí →
    │       │   ¿Tiene SC abierta?
    │       │   ├─ No  → F1: Payment Confirmation
    │       │   └─ Sí  → F2: POP vía SC existente
    │       └─ No  → F3: Iniciar POP
    └─ Sí (Unreliable_Paid, solo Bank Deposit) →
        ¿< 48h?
        ├─ Sí → F4: ETA email / POP Day 1
        └─ No → F5: SC al corresponsal
```

---

## 7. Criterio de Adherencia Consolidado (F1)

Para un ticket **F1** (el escenario de mayor volumen y menor adherencia):

```
SI canal es voz:
    adherente = (order__payment_confirmation ∈ tags)
                AND (payment_confirmation_advisory_applied ∈ tags)

SI canal es email o chat:
    adherente = (order__payment_confirmation ∈ tags)
                AND (payment_confirmation_advisory_applied ∈ tags)
                AND (ria_payment_confirmation_reliable_correspondent_sent ∈ tags)

SI canal es VA-only (inbound_call_-_va_only):
    excluir del cálculo de adherencia
```

---

## 8. Limitaciones Conocidas

| Limitación | Impacto |
|---|---|
| El tag `payment_confirmation_advisory_applied` (trigger de nota interna) no está presente en todos los grupos/regiones | La condición 1 puede subestimar adherencia en grupos donde el trigger no está configurado |
| La Search API de Zendesk tiene un límite de 1,000 resultados por query | Se usa doble query (con macro / sin macro) para capturar el universo completo |
| Tickets VA-only resueltos automáticamente sin rep | Se excluyen de F1; no hay acción humana que medir |
| El campo Transaction Date se pobla vía webhook; si falla, `hours_from_order` queda vacío | Esos tickets no se pueden clasificar como F1 o F3 y caen fuera del cálculo |

---

## 9. Línea Base Actual (Mayo 2026, últimos 30 días)

| Escenario | Tickets | Adherencia |
|---|---|---|
| F1 — Payment Confirmation | 754 | **2.8%** |
| F2 — POP con SC | 161 | 47.8% |
| F3 — Iniciar POP | 1,477 | 12.9% |
| F4 — ETA / POP Day 1 | 61 | 39.3% |
| F5 — SC al corresponsal | 34 | 8.8% |
| **TOTAL** | **2,487** | **12.7%** |

### F1 por Delivery Method

| Delivery Method | Elegibles | Adherentes | GAP | ADH% |
|---|---|---|---|---|
| Bank Deposit | 351 | 18 | 333 | 5.1% |
| Office Pick-Up | 235 | 1 | 234 | 0.4% |
| Mobile Payment | 161 | 2 | 159 | 1.2% |
| Home Delivery | 7 | 0 | 7 | 0.0% |
| **Total F1** | **754** | **21** | **733** | **2.8%** |

> La adherencia medida actualmente para F1 usa el tag de macro como proxy. La adopción plena del criterio de 3 condiciones (email/chat) y 2 condiciones (voz) requerirá verificar primero que el trigger `payment_confirmation_advisory_applied` esté configurado en todos los grupos.

---

## 10. Para Refrescar los Datos

```bash
# 1. Extraer tickets (todos los delivery methods, últimos 30 días)
python -m scripts.macro_adherence_analysis

# 2. Calcular tabla de adherencia F1-F5
python -m scripts.adherence_full_table

# 3. Regenerar reporte HTML ejecutivo
python -m scripts.build_adherence_report
```

El reporte HTML se guarda en `reports/adherence_report.html` y se publica en:  
**https://georgeorellanasv.github.io/zendesk-sideconv-analytics/**
