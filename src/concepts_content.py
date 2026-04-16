"""
Contenido markdown para la página de Conceptos del dashboard.
Se mantiene en Python como strings para no romper la carga por rutas.
"""

CONCEPTS_ES = """
## Jerarquía de datos

Este análisis trabaja con **tres niveles de información**, cada uno contenido dentro del anterior:

```
🎫 TICKET            ← el expediente del caso
  └── 💬 THREAD      ← una cadena de emails (side conversation)
        └── ✉️ MSG   ← un email individual dentro del thread
```

---

### 🎫 ¿Qué es un TICKET?

Es el **caso principal** registrado en Zendesk. Cada vez que un cliente contacta a Ria (por chat, email, teléfono, etc.), se abre un ticket que contiene toda la información de esa interacción:
- Número de ticket
- Fecha de apertura
- Razón por la que contactó el cliente
- Corresponsal involucrado (banco/partner)
- País, producto, agente asignado, etc.

### 💬 ¿Qué es un THREAD (Side Conversation)?

Es una **cadena paralela de emails** que el agente abre desde un ticket para comunicarse con alguien **fuera** de la conversación principal con el cliente.

**Analogía (como un expediente legal):**
- El **ticket** es el expediente completo del caso
- La **conversación principal** es el diálogo con el cliente
- Los **threads** son los oficios/cartas que se envían a bancos, departamentos internos o el mismo cliente por otro canal — todos ligados al mismo caso

Un ticket puede tener **múltiples threads paralelos**. Por ejemplo:

```
TICKET #22525756 — "Mi transferencia no llegó"
│
├── 📧 Conversación principal: Cliente ↔ Agente Ria
│
├── 💬 Thread #1: Ria → Banorte (corresponsal)
│    "Necesito prueba de pago de US123"
│    └── Banorte responde 20 hrs después
│
├── 💬 Thread #2: Ria → Cliente (otro canal)
│    "Envíanos foto de tu ID"
│    └── Cliente responde
│
└── 💬 Thread #3: Ria → Compliance (interno)
     "Validar operación"
     └── Compliance responde
```

**Características clave:**
- El cliente **no ve** los threads (se mantiene privacidad con corresponsales)
- El agente puede llevar varios diálogos sin ensuciar la conversación principal
- Todo queda ligado al mismo ticket para trazabilidad completa

> ⚠️ **Importante:** un thread **NO** es un ticket merged. Merge es combinar dos tickets duplicados en uno. Un thread es una cadena de emails paralela dentro de un mismo ticket.

### ✉️ ¿Qué es un MSG (Mensaje)?

Es un **email individual dentro de un thread**. Si piensas en Gmail:
- Un email thread = Thread (side conversation)
- Cada email dentro del thread = Msg

El primer mensaje de un thread siempre es de tipo `create` (quien lo inició). Los siguientes son `reply` (respuestas).

---

## Diccionario de columnas

### 🎫 Columnas del TICKET

| Columna | Qué significa |
|---|---|
| **Ticket #** | ID numérico único del ticket en Zendesk |
| **Ticket Opened** | Fecha en que se abrió el ticket |
| **Ticket Status** | Estado del ticket: `open`, `pending`, `hold`, `solved`, `closed` |
| **Ticket Reason** | Razón que el agente seleccionó en el campo custom (ej: `order__cancellation`) |
| **Ticket Correspondent** | Corresponsal principal del caso — el partner/banco que procesa la orden |
| **Ticket Country** | País destino de la transacción |
| **Ticket Subject** | Asunto original del ticket |

### 💬 Columnas del THREAD

| Columna | Qué significa |
|---|---|
| **Thread #** | Número secuencial del thread dentro del ticket (1 = primero, 2 = segundo, etc.) |
| **Thread Subject** | Asunto del thread (puede ser distinto al del ticket) |
| **Thread Started** | Cuándo se inició el thread |
| **Thread Direction** | Hacia dónde va: `ria_to_client`, `ria_to_external`, `external_to_ria`, `internal` |
| **Thread Recipient Type** | Categoría del destinatario: `client`, `correspondent`, `internal`, `unknown` |
| **Thread Classification** | Razón derivada del subject (ej: `proof_of_payment_request`, `refund_request`) |
| **Thread Confidence** | Confianza de la clasificación: `high`, `medium`, `low` |
| **Thread External Reply** | Timestamp en que la contraparte respondió **por primera vez** (primer acuso de recibo) |
| **Thread Response (hrs)** | Horas que tardó la contraparte en dar la primera respuesta |
| **Thread Last Counterparty Reply** | Timestamp del **último mensaje** enviado por la contraparte (el que se acerca a "resolución") |
| **Thread Resolution (hrs)** | Horas desde que Ria abrió el thread hasta el último mensaje de la contraparte |
| **Thread Exchanges** | Número total de mensajes en el thread (indicador de complejidad / ping-pong) |
| **Thread State** | Estado del thread: `open` o `closed` |

### ✉️ Columnas del MSG

| Columna | Qué significa |
|---|---|
| **Msg #** | Número secuencial del mensaje dentro del thread (1 = primer email, 2 = segundo, etc.) |
| **Msg Type** | Tipo: `create` (primer email) o `reply` (respuesta) |
| **Msg Date** | Timestamp en que se envió este mensaje específico |
| **Msg Actor** | Nombre del remitente según aparece en Zendesk. Puede ser una persona (ej: "Adrian Lopez"), un equipo (ej: "AR Supervisors USA"), una empresa externa (ej: "Unitransfer S.A.") o un alias de buzón (ej: "Agtransferenciaslam") |
| **Msg From** | Email del remitente |
| **Msg To** | Emails de los destinatarios |
| **Msg Subject** | Asunto del email específico |
| **Msg Body** | Contenido del mensaje (primeros 2,000 caracteres) |

---

## ⏱️ Métricas de tiempo — cómo se calculan

Cuando Ria abre un thread hacia una contraparte (cliente, banco o depto interno), medimos **tres tiempos complementarios**:

### 1. Thread Response (hrs) — tiempo al **primer** reply
```
#1 create  Ria → banco           2026-04-10 10:00    ← inicio (T0)
#2 reply   banco → Ria           2026-04-11 06:00    ← primera respuesta (20 hrs)
```
**Qué mide:** qué tan rápido la contraparte acusa recibo de tu mensaje inicial.

### 2. Thread Resolution (hrs) — tiempo al **último** reply de la contraparte
```
#1 create  Ria → banco           2026-04-10 10:00    ← T0
#2 reply   banco → Ria           2026-04-11 06:00    (primer reply: 20 hrs)
#3 reply   Ria → banco           2026-04-11 08:00    (Ria follow-up)
#4 reply   banco → Ria           2026-04-12 14:00    (segundo reply banco)
#5 reply   banco → Ria           2026-04-14 10:00    ← último reply del banco (96 hrs) ✅
#6 reply   Ria → banco           2026-04-14 11:00    (Ria cierra — NO cuenta)
```
**Qué mide:** cuánto tardó la conversación con la contraparte hasta que ella dejó de responder (aproximación a "resolución").

### 3. Thread Exchanges — total de mensajes
Número de emails intercambiados en todo el thread. Threads con muchos intercambios suelen indicar:
- Información incompleta inicial
- Múltiples rondas de validación
- Casos complejos

### 🔑 Cómo identificamos "la contraparte"

Usamos el email **específico** del creador del thread, no el dominio:

| Tipo de thread | Creador | Contraparte |
|---|---|---|
| Ria → cliente | `agente@ria...` | Cliente (no-Ria) |
| Ria → banco | `agente@ria...` | Banco (no-Ria) |
| Interno Ria | `agenteA@ria...` | `agenteB@ria...` (mismo dominio pero persona distinta) |

La regla: cualquier email `from_address != creador` es contraparte (excepto bounces como postmaster).

---

## ⚠️ Aclaración importante: "Correspondent"

Hay dos columnas que mencionan "correspondent" y pueden confundir:

| Columna | Nivel | Significa |
|---|---|---|
| **Ticket Correspondent** | Ticket | El corresponsal oficial del caso según Zendesk (ej: "Uniteller") |
| **Thread Recipient Type** | Thread | La **categoría** del destinatario de este thread (`client`, `correspondent`, `internal`) |

Por ejemplo: un ticket con `Ticket Correspondent = Banorte` puede tener un Thread #1 dirigido al **cliente** (`Thread Recipient Type = client`) y un Thread #2 dirigido a **Banorte** (`Thread Recipient Type = correspondent`).

---

## Categorías de clasificación (Thread Classification)

Clasificación que derivamos automáticamente del asunto del thread:

| Categoría | Significado |
|---|---|
| `proof_of_payment_request` | Solicitud de prueba/comprobante de pago |
| `cancellation_request` | Solicitud de cancelación de transferencia |
| `refund_request` | Solicitud de reembolso |
| `recall_request` | Solicitud de recall de fondos |
| `fund_recovery_request` | Solicitud de recuperación de fondos |
| `transaction_status` | Consulta de estado de la transacción |
| `transaction_trace` | Investigación/rastreo de transacción |
| `deposit_delay_notification` | Notificación de depósito bancario demorado |
| `held_transfer_info_request` | Transferencia retenida — solicitud de info al cliente |
| `payout_assistance` | Solicitud de asistencia para payout |
| `modification_request` | Solicitud de modificación de datos |
| `charge_issue` | Problema de cobro o doble cargo |
| `compliance_inquiry` | Consulta de compliance (AML, KYC) |
| `rfi_outbound` / `rfi_inbound` | Request for Information |
| `order_notification` | Notificación genérica de orden al cliente |
| `general_correspondence` | Correspondencia general |
| `internal_collaboration` | Coordinación entre equipos internos de Ria |
| `other` | No matchea ninguna regla |
"""


CONCEPTS_EN = """
## Data Hierarchy

This analysis works with **three levels of information**, each nested within the previous:

```
🎫 TICKET            ← the case file
  └── 💬 THREAD      ← an email chain (side conversation)
        └── ✉️ MSG   ← an individual email within the thread
```

---

### 🎫 What is a TICKET?

The **main case** logged in Zendesk. Every time a customer contacts Ria (via chat, email, phone, etc.), a ticket is opened containing all the information about that interaction:
- Ticket number
- Date opened
- Reason for contact
- Correspondent involved (bank/partner)
- Country, product, assigned agent, etc.

### 💬 What is a THREAD (Side Conversation)?

A **parallel email chain** that the agent opens from a ticket to communicate with someone **outside** the main customer conversation.

**Analogy (like a legal case file):**
- The **ticket** is the complete case file
- The **main conversation** is the dialogue with the customer
- The **threads** are the letters/memos sent to banks, internal departments, or the customer through another channel — all linked to the same case

A ticket can have **multiple parallel threads**. For example:

```
TICKET #22525756 — "My transfer didn't arrive"
│
├── 📧 Main conversation: Customer ↔ Ria agent
│
├── 💬 Thread #1: Ria → Banorte (correspondent)
│    "Need proof of payment for US123"
│    └── Banorte replies 20 hrs later
│
├── 💬 Thread #2: Ria → Customer (other channel)
│    "Please send us a photo of your ID"
│    └── Customer replies
│
└── 💬 Thread #3: Ria → Compliance (internal)
     "Please validate operation"
     └── Compliance replies
```

**Key characteristics:**
- The customer **does NOT see** threads (keeps correspondent communications private)
- The agent can have multiple dialogues without cluttering the main conversation
- Everything stays linked to the same ticket for full traceability

> ⚠️ **Important:** a thread is **NOT** a merged ticket. Merging combines two duplicate tickets into one. A thread is a parallel email chain inside a single ticket.

### ✉️ What is a MSG (Message)?

An **individual email inside a thread**. If you think of Gmail:
- An email thread = Thread (side conversation)
- Each email in the thread = Msg

The first message in a thread is always of type `create` (whoever started it). The following ones are `reply`.

---

## Column Dictionary

### 🎫 TICKET columns

| Column | Meaning |
|---|---|
| **Ticket #** | Unique numeric ID of the ticket in Zendesk |
| **Ticket Opened** | Date the ticket was opened |
| **Ticket Status** | Ticket state: `open`, `pending`, `hold`, `solved`, `closed` |
| **Ticket Reason** | Reason selected by the agent in the custom field (e.g., `order__cancellation`) |
| **Ticket Correspondent** | Main correspondent of the case — the partner/bank processing the order |
| **Ticket Country** | Destination country of the transaction |
| **Ticket Subject** | Original subject of the ticket |

### 💬 THREAD columns

| Column | Meaning |
|---|---|
| **Thread #** | Sequential number of the thread within the ticket (1 = first, 2 = second, etc.) |
| **Thread Subject** | Subject of the thread (may differ from the ticket subject) |
| **Thread Started** | When the thread was started |
| **Thread Direction** | Direction: `ria_to_client`, `ria_to_external`, `external_to_ria`, `internal` |
| **Thread Recipient Type** | Recipient category: `client`, `correspondent`, `internal`, `unknown` |
| **Thread Classification** | Reason derived from the subject (e.g., `proof_of_payment_request`, `refund_request`) |
| **Thread Confidence** | Classification confidence: `high`, `medium`, `low` |
| **Thread External Reply** | Timestamp when the counterparty replied for the **first time** (first acknowledgment) |
| **Thread Response (hrs)** | Hours the counterparty took to provide the first response |
| **Thread Last Counterparty Reply** | Timestamp of the **last message** sent by the counterparty (closest thing to "resolution") |
| **Thread Resolution (hrs)** | Hours from when Ria opened the thread to the last message from the counterparty |
| **Thread Exchanges** | Total number of messages in the thread (indicator of complexity / ping-pong) |
| **Thread State** | Thread state: `open` or `closed` |

### ✉️ MSG columns

| Column | Meaning |
|---|---|
| **Msg #** | Sequential number of the message within the thread (1 = first email, 2 = second, etc.) |
| **Msg Type** | Type: `create` (first email) or `reply` (response) |
| **Msg Date** | Timestamp when this specific message was sent |
| **Msg Actor** | Display name of the sender as shown in Zendesk. Can be a person (e.g., "Adrian Lopez"), a team (e.g., "AR Supervisors USA"), an external entity (e.g., "Unitransfer S.A.") or a mailbox alias (e.g., "Agtransferenciaslam") |
| **Msg From** | Sender's email |
| **Msg To** | Recipients' emails |
| **Msg Subject** | Subject of the specific email |
| **Msg Body** | Message content (first 2,000 characters) |

---

## ⏱️ Time metrics — how they are calculated

When Ria opens a thread to a counterparty (customer, bank, or internal dept), we measure **three complementary times**:

### 1. Thread Response (hrs) — time to **first** reply
```
#1 create  Ria → bank            2026-04-10 10:00    ← start (T0)
#2 reply   bank → Ria            2026-04-11 06:00    ← first response (20 hrs)
```
**What it measures:** how quickly the counterparty acknowledges your initial message.

### 2. Thread Resolution (hrs) — time to **last** counterparty reply
```
#1 create  Ria → bank            2026-04-10 10:00    ← T0
#2 reply   bank → Ria            2026-04-11 06:00    (first reply: 20 hrs)
#3 reply   Ria → bank            2026-04-11 08:00    (Ria follow-up)
#4 reply   bank → Ria            2026-04-12 14:00    (second bank reply)
#5 reply   bank → Ria            2026-04-14 10:00    ← last bank reply (96 hrs) ✅
#6 reply   Ria → bank            2026-04-14 11:00    (Ria closes — NOT counted)
```
**What it measures:** how long the conversation with the counterparty lasted until they stopped replying (proxy for "resolution").

### 3. Thread Exchanges — total messages
Number of emails exchanged across the whole thread. Threads with many exchanges usually indicate:
- Incomplete initial information
- Multiple validation rounds
- Complex cases

### 🔑 How we identify "the counterparty"

We use the **specific email** of the thread creator, not the domain:

| Thread type | Creator | Counterparty |
|---|---|---|
| Ria → customer | `agent@ria...` | Customer (non-Ria) |
| Ria → bank | `agent@ria...` | Bank (non-Ria) |
| Ria internal | `agentA@ria...` | `agentB@ria...` (same domain, different person) |

The rule: any `from_address != creator` is counterparty (except bounces like postmaster).

---

## ⚠️ Important clarification: "Correspondent"

Two columns mention "correspondent" and can be confusing:

| Column | Level | Meaning |
|---|---|---|
| **Ticket Correspondent** | Ticket | The official correspondent of the case in Zendesk (e.g., "Uniteller") |
| **Thread Recipient Type** | Thread | The **category** of this thread's recipient (`client`, `correspondent`, `internal`) |

For example: a ticket with `Ticket Correspondent = Banorte` may have a Thread #1 sent to the **customer** (`Thread Recipient Type = client`) and a Thread #2 sent to **Banorte** (`Thread Recipient Type = correspondent`).

---

## Classification categories (Thread Classification)

Categories we automatically derive from the thread subject:

| Category | Meaning |
|---|---|
| `proof_of_payment_request` | Request for proof of payment / receipt |
| `cancellation_request` | Transfer cancellation request |
| `refund_request` | Refund request |
| `recall_request` | Funds recall request |
| `fund_recovery_request` | Funds recovery request |
| `transaction_status` | Transaction status inquiry |
| `transaction_trace` | Transaction trace/investigation |
| `deposit_delay_notification` | Bank deposit delay notification |
| `held_transfer_info_request` | Held transfer — info request to customer |
| `payout_assistance` | Payout assistance request |
| `modification_request` | Data modification request |
| `charge_issue` | Charge problem or double charge |
| `compliance_inquiry` | Compliance inquiry (AML, KYC) |
| `rfi_outbound` / `rfi_inbound` | Request for Information |
| `order_notification` | Generic order notification to customer |
| `general_correspondence` | General correspondence |
| `internal_collaboration` | Coordination between internal Ria teams |
| `other` | Does not match any rule |
"""
