# Pipeline Architecture — Ria CX Side Conversations Analytics

Documentación técnica completa del pipeline: cómo se extrae la información, cómo fluye, qué hace cada componente, y cómo se deploya.

---

## 🎯 Objetivo

Extraer y analizar las **side conversations** (hilos paralelos de email) que los agentes de Ria abren dentro de tickets de Zendesk, para generar:

1. **Reporting** — qué tipos de solicitudes existen y hacia quién van
2. **Métricas de desempeño** — cuánto tardan los corresponsales en responder, cuánto ping-pong hay

Todo corre **localmente** (PC + SQLite). La DB anonimizada se comparte en GitHub para demo público.

---

## 📐 Stack tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| **Source** | Zendesk REST API v2 | Es donde viven los tickets/threads |
| **Auth** | HTTP Basic con API Token | Zendesk lo soporta nativamente; simple y seguro |
| **Extracción** | Python 3.12 + `requests` | Librerías maduras, fácil paginar y retry |
| **Storage** | SQLite (archivo `.db`) | Local, sin servidor, suficiente para <1M registros |
| **Procesamiento** | Python + regex | Clasificación basada en patrones del subject + body |
| **Visualización** | Streamlit + Pandas + Plotly | Dashboard interactivo sin HTML/JS |
| **Config** | `.env` + `python-dotenv` | Credenciales fuera del código |
| **Deploy** | GitHub + Streamlit Cloud | Gratis y simple |

---

## 🏗️ Jerarquía de datos

Tres niveles, cada uno contenido en el anterior:

```
🎫 TICKET            ← el expediente del caso (1 por consulta de cliente)
  └── 💬 THREAD      ← una cadena de emails (side conversation)
        └── ✉️ MSG   ← un email individual dentro del thread
```

**Analogía:** Un ticket es como un expediente legal. Los threads son como los oficios/cartas que se mandan a bancos, departamentos internos o clientes. Los mensajes son los emails individuales dentro de cada oficio.

Un ticket puede tener múltiples threads paralelos. Un thread puede tener múltiples mensajes.

---

## 🔄 Pipeline completo — fase por fase

### **Fase 0 — Discovery (una sola vez)**

**Objetivo:** descubrir IDs de campos custom y vistas de Zendesk.

**Cómo funciona:**

1. `scripts/test_connection.py` → hace `GET /api/v2/users/me.json` autenticándose con el token. Si responde con el usuario, la conexión funciona.
2. `scripts/discover_fields.py` → hace `GET /api/v2/ticket_fields.json` (paginado). Zendesk devuelve los ~431 campos definidos en la instancia. Guarda en `reports/ticket_fields.csv`.
3. `scripts/discover_views.py` → hace `GET /api/v2/views.json`. Busca la vista "US Care" por nombre y devuelve su ID.

**Resultado:** IDs como:
- `FIELD_ID_REASON_FOR_CONTACT = 42979471558801` (campo custom "Ria - Reason for Contact")
- `VIEW_ID_US_CARE = 10439252513809`

Estos IDs se agregan al `.env`.

---

### **Fase 1 — Schema de la base de datos**

**Archivo:** `src/db.py`

**Diseño jerárquico de 4 tablas:**

```
tickets (1 por caso)
  ↓ 1:N
side_conversations (1 por thread)
  ↓ 1:N
side_conversation_events (1 por mensaje)

extraction_log (metadata de cada corrida del extractor)
```

**Columnas clave:**

| Tabla | Campos importantes |
|---|---|
| `tickets` | ID, status, fechas, campos custom (reason, correspondent, country, product) |
| `side_conversations` | ID (UUID), ticket_id, subject, state, **secuencia dentro del ticket**, **clasificación derivada**, **tiempos de respuesta calculados** |
| `side_conversation_events` | event_id, side_conv_id, **secuencia dentro del thread**, type (create/reply), actor, from/to addresses, body |

**Upsert pattern:** Usa `ON CONFLICT DO UPDATE` para que re-extraer el mismo ticket no duplique.

---

### **Fase 2/3 — Extractor principal**

**Archivo:** `src/extractor.py`
**Comando:** `python -m src.extractor --last-days 7`

**Paso 1 — Autenticación:**

```python
# src/zendesk_client.py
auth = HTTPBasicAuth(f"{email}/token", api_token)
```

Zendesk requiere el formato `email/token` como username, y el token como password. Basic Auth cifrada por HTTPS.

**Paso 2 — Traer tickets de la vista US Care:**

```
GET /api/v2/views/{VIEW_ID_US_CARE}/tickets.json?per_page=100
```

Devuelve los tickets filtrados según los criterios de esa vista (status != solved, group=US Care, etc.). Paginado — cada página trae 100 tickets. El extractor sigue los `next_page` URLs hasta que no hay más.

**Paso 3 — Filtrar por fecha:**

En el cliente, filtramos los tickets cuyo `updated_at >= now - last_days`. Esto es filtrado **del lado nuestro** (Zendesk no permite filtrar views por fecha).

**Paso 4 — Extraer campos custom:**

Para cada ticket, buscamos los IDs custom en su array `custom_fields`:

```python
def _get_custom_field(ticket, field_id):
    for cf in ticket["custom_fields"]:
        if cf["id"] == int(field_id):
            return cf["value"]
    return ""
```

**Paso 5 — Side conversations de cada ticket:**

```
GET /api/v2/tickets/{ticket_id}/side_conversations.json
```

Retorna todos los threads abiertos desde ese ticket (subject, state, participants).

**Paso 6 — Eventos de cada side conversation:**

```
GET /api/v2/tickets/{ticket_id}/side_conversations/{sc_id}/events.json
```

Retorna todos los mensajes: create + replies + updates. Cada uno tiene `actor`, `from_address`, `to_addresses`, `message.body`, `created_at`.

> ⚠️ **Bug real encontrado:** la API retorna la clave `"events"` pero inicialmente el cliente buscaba `"side_conversation_events"`. Por eso la primera extracción dio 0 eventos. Fix: `data.get("events", [])`.

**Paso 7 — Persistir en SQLite:**

Cada objeto se convierte a dict con nombres de columna limpios y se hace upsert con `INSERT ... ON CONFLICT DO UPDATE`. El body se trunca a 2,000 caracteres.

**Paso 8 — Rate limiting:**

Si Zendesk responde `HTTP 429 Too Many Requests`, el cliente lee el header `Retry-After` y duerme ese tiempo antes de reintentar.

**Paso 9 — Logging:**

Todo se escribe a `logs/extractor.log` + `extraction_log` en la DB (run_id, tickets_procesados, errores, duración).

**Resultado típico de una corrida (7 días):** 427 tickets, 510 threads, 1,938 eventos en ~6 minutos.

---

### **Fase 4 — Clasificador**

**Archivo:** `src/classifier.py`
**Comando:** `python -m src.classifier`

**No extrae data nueva** — lee lo que ya está en SQLite y deriva columnas nuevas.

**A) Direction (hacia dónde va el thread):**

```
create_from = evento "create".from_address

- Si from es Ria domain y todos los to son Ria → internal
- Si from es Ria y algún to es free email (gmail, yahoo) → ria_to_client
- Si from es Ria y to es dominio externo → ria_to_external
- Si from es externo → external_to_ria
```

**B) Recipient type (tipo de destinatario):**

```
- Free email domains (gmail, yahoo, hotmail...) → client
- Dominios Ria (riamoneytransfer.com, riafinancial.com...) → internal
- Resto de dominios (bdo.com.ph, uniteller.com...) → correspondent
```

**C) Classification (categoría de la razón):**

Lista ordenada de ~18 reglas regex contra el subject, y si no matchea, contra el body. Ejemplos:

```python
("proof_of_payment_request", ["prueba de pago", "comprobante", "proof of pay", ...])
("cancellation_request", ["cancel", "solicitud.*cancelaci", ...])
```

Para subjects genéricos como "US1234567890", el clasificador busca también en el body (_"Favor enviar estado de cuenta"_ → `rfi_outbound`).

**D) Métricas de tiempo:**

| Métrica | Qué mide |
|---|---|
| `external_response_hrs` | Horas entre create y primer reply cuyo `from_address != creador` |
| `last_counterparty_reply_at` | Timestamp del último reply de la contraparte |
| `resolution_hrs` | Horas desde create hasta ese último reply |
| `total_exchanges` | Conteo total de mensajes en el thread |

**E) Secuencia:**

- `sc_sequence` = ROW_NUMBER() por ticket ordenado por `created_at`
- `event_sequence` = ROW_NUMBER() por thread ordenado por `created_at`

Todo se persiste con `UPDATE side_conversations SET ...` bulk.

---

### **Fase 5 — Dashboard (Streamlit)**

**Archivo:** `src/dashboard.py`
**Comando:** `streamlit run src/dashboard.py`

**Cómo funciona:**

- Streamlit ejecuta el script de Python y convierte cada `st.metric()`, `st.plotly_chart()`, etc. en componentes web renderizados en el browser
- `@st.cache_data` memoiza las queries de SQLite para no releer el archivo cada interacción
- El sidebar tiene filtros globales (dirección, recipient type, clasificación, idioma)
- 6 páginas independientes navegables por radio button

**Páginas:**

1. **Summary** — KPIs jerárquicos (Ticket → Thread → Msg), razones por nivel, top corresponsales, distribuciones
2. **Operational Health** — SLA 24h%, median/P90, one-and-done rate, ghost rate, aging buckets, heatmap día×hora
3. **Partner Scorecard** — leaderboard por corresponsal, heatmap Partner × Classification, box plots
4. **Customer Journey** — % tickets con cliente contactado, client response rate, top razones
5. **Database** — flat view filtrable exportable a Excel
6. **Concepts** — diccionario bilingüe de cada columna y jerarquía

**Internacionalización:** `src/i18n.py` — dict de traducciones EN/ES. Todos los labels pasan por `t("key", lang)`.

---

### **Fase 6 — Anonimización (para GitHub)**

**Archivo:** `src/anonymize.py`
**Comando:** `python -m src.anonymize`

**Por qué:** la DB real tiene PII (nombres, emails de clientes). Para compartir en GitHub público, necesitamos una versión anonimizada.

**Cómo funciona:**

1. Copia `data/sideconv.db` → `data/sideconv_demo.db`
2. Construye un mapping `email_real → email_falso`:
   - `riamoneytransfer.com` → `ria_agent_N@riamoneytransfer.com` (mantiene dominio)
   - `gmail.com / yahoo.com / ...` → `customer_N@example.com`
   - Dominios corresponsales (bdo.com.ph, uniteller.com) → `contact_N@bdo.com.ph` (mantiene dominio para analítica)
3. Construye mapping `nombre → "Customer N" / "Ria Agent N" / "Partner Contact N"` según el tipo de email
4. UPDATEs masivos en la DB demo reemplazando:
   - `from_address`, `actor_email`
   - `actor_name`
   - `to_addresses` (JSON — parsea, reemplaza, re-serializa)
5. Preserva: Order IDs, subjects, bodies, timestamps, métricas

**Resultado:** DB demo de ~5.7 MB con la misma estructura y métricas pero sin PII. Se incluye en el repo de GitHub; la original `sideconv.db` está en `.gitignore`.

---

### **Fase 7 — Deploy**

**GitHub:**

- El PC tiene el repo local con todo el código + `sideconv_demo.db`
- `.gitignore` excluye `.env`, `sideconv.db` (real), `logs/`, `reports/`, `.venv/`
- `git push` → sube al repo `georgeorellanasv/zendesk-sideconv-analytics`
- GitHub solo guarda archivos, no ejecuta nada

**Streamlit Cloud:**

- Lee el código de GitHub
- Levanta un servidor con Python + `pip install -r requirements.txt`
- Ejecuta `streamlit run src/dashboard.py`
- Expone una URL pública `ria-sideconv-analytics.streamlit.app`
- Usuarios visitan la URL y ven el dashboard funcional con la DB demo
- Cada `git push` a `main` re-deploya automáticamente

---

## 🌊 Flujo de datos completo

```
     Zendesk API                      PC local                     GitHub                     Streamlit Cloud
     (cloud)                          (tú)                         (cloud)                    (cloud)
       │                               │                            │                           │
       │◄────── GET tickets ──────────│                             │                           │
       │──── JSON (100 tickets) ──────►│                            │                           │
       │                               │──► SQLite INSERT           │                           │
       │                               │                            │                           │
       │                               │── src.classifier ──►       │                           │
       │                               │── src.anonymize ──►        │                           │
       │                               │   sideconv_demo.db         │                           │
       │                               │                            │                           │
       │                               │──── git push ─────────────►│                           │
       │                               │                            │───── auto-deploy ────────►│
       │                               │                            │                           │
       │                               │                            │                           │──► URL pública
       │                               │                            │                           │    Dashboard
       │                               │                            │                           │    interactivo
```

---

## 🔐 Separación de credenciales y código

```
.env (NUNCA en git)           src/config.py (en git)
----------------------        ---------------------
ZENDESK_SUBDOMAIN=mts-eeft    lee .env
ZENDESK_TOKEN=yno1J...        expone constantes
SSL_VERIFY=false
FIELD_ID_...=1234
```

Cuando cambias de máquina o compartes código:

- El código de GitHub **no tiene credenciales**
- Cada persona crea su propio `.env` con su token
- Streamlit Cloud no necesita credenciales porque solo lee la DB demo (no llama a Zendesk)

---

## 📊 Análisis de API calls

### Fórmula

```
Total = Pagination calls  +  Side convs calls  +  Event calls
      = ⌈N_tickets_view / 100⌉  +  N_tickets_filtrados  +  N_side_convs
```

### Números reales (última corrida, 7 días)

| Etapa | Cálculo | Calls |
|---|---|---|
| Paginación de tickets (view US Care) | ~427 tickets en batches de 100 | ~5 |
| Side conversations por ticket | 1 call por ticket filtrado | 427 |
| Events por side conversation | 1 call por side conv | 510 |
| **TOTAL** | | **~942 calls** |

### Distribución en el tiempo

La corrida completa tomó ~6 minutos:

```
942 calls / 6 min = ~157 calls/min
```

### Rate limits de Zendesk

| Plan | Límite |
|---|---|
| Standard | 200 req/min |
| Professional | 400 req/min |
| Enterprise | 700 req/min |

Estamos bien dentro del límite. Si se excediera, el cliente tiene auto-retry con `Retry-After`.

### Cómo escala

| Last days | Tickets filtrados (estimado) | Side convs (estimado) | Total calls | Tiempo |
|---|---|---|---|---|
| 2 | ~150 | ~180 | ~335 | ~2 min |
| 7 | 427 | 510 | ~942 | ~6 min |
| 14 | ~850 | ~1,000 | ~1,860 | ~12 min |
| 30 | ~1,800 | ~2,100 | ~3,910 | ~25 min |

Todo lineal.

### Por qué tantos calls

Zendesk API **no tiene un endpoint que traiga todo junto**. Hay que ir "en cascada":

```
GET view/tickets             →  lista tickets         (1 call por 100 tickets)
  └─ GET ticket/side_convs   →  threads de un ticket  (1 call por ticket)
      └─ GET events          →  mensajes del thread   (1 call por thread)
```

Cada nivel requiere el ID del anterior, así que no puedes paralelizarlo todo.

---

## 📝 Archivos clave del proyecto

| Archivo | Función |
|---|---|
| `src/config.py` | Carga `.env`, expone constantes |
| `src/zendesk_client.py` | Wrapper HTTP de Zendesk API |
| `src/db.py` | Schema SQLite + upsert helpers |
| `src/extractor.py` | Pipeline principal de extracción |
| `src/classifier.py` | Deriva direction, recipient, clasificación, tiempos |
| `src/anonymize.py` | Genera DB demo sin PII |
| `src/dashboard.py` | 6 páginas Streamlit |
| `src/i18n.py` | Traducciones EN/ES |
| `src/concepts_content.py` | Markdown de la página de conceptos |
| `scripts/discover_*.py` | Discovery de fields y views |

---

## 🛠️ Comandos de referencia

```powershell
# Activar entorno
cd "C:\Users\...\zendesk-sideconv-analytics"
.\.venv\Scripts\Activate.ps1

# Extraer data fresca
python -m src.extractor --last-days 7

# Reclasificar (después de extraer)
python -m src.classifier

# Regenerar DB demo (antes de push a GitHub)
python -m src.anonymize

# Correr dashboard local
streamlit run src/dashboard.py

# Subir cambios a GitHub (auto-deploya Streamlit Cloud)
git add .
git commit -m "mensaje"
git push
```

---

## 💡 Optimizaciones posibles (backlog)

1. **Incremental extraction** — solo traer tickets con `updated_at > last_extraction`. Ya existe `extraction_log` con timestamps, podría implementarse.
2. **Paralelismo controlado** — sacar side_convs de múltiples tickets simultáneamente con `concurrent.futures`, respetando rate limit.
3. **Filtrado server-side** — Zendesk permite búsqueda incremental con la Search API (`GET /api/v2/search.json?query=...`) que podría reducir calls al 1er nivel.
4. **Clasificador con LLM** — reemplazar regex por llamadas a Claude para casos ambiguos (mejor accuracy, mayor costo).
5. **Alertas automáticas** — cron job que detecte threads ghosted (>72h sin reply) y envíe notificación.

Para el volumen actual (cientos de tickets/semana), lo implementado es suficiente.

---

## 🔒 Seguridad y compliance

- ✅ Código **read-only** contra Zendesk (solo GET requests, nunca POST/PUT/DELETE)
- ✅ Credenciales fuera del repo (`.env` en `.gitignore`)
- ✅ DB real con PII **no** se sube a GitHub
- ✅ DB demo con data anonimizada para compartir públicamente
- ✅ SSL verification deshabilitado solo para redes corporativas con interceptación (Euronet)
- ✅ Auth por API token (revocable en cualquier momento desde Zendesk Admin)

---

## 🤖 Uso de MCP

**No se usó MCP (Model Context Protocol)** para construir este proyecto. Todo es código Python tradicional. Razones:

- Pipeline debe ser **independiente** (corre sin Claude)
- **Reproducible** y **auditable** (código versionado en Git)
- **Deployable** (Streamlit Cloud no tiene acceso a MCP)
- **Portable** (cualquiera con el repo y su propio token puede correrlo)

MCP sería útil para tareas ad-hoc exploratorias, pero no para un pipeline productivo.
