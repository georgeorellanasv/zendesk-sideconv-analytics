# Zendesk Side Conversations Analytics — Ria CX POC

Local analytics POC for Zendesk side conversations with two core objectives:

1. **Reporting & classification** — Visibility into what types of side conversations exist (proof of payment, cancellation, refund, held transfer, etc.), who generates them, and toward whom (client / correspondent / internal).
2. **Partner performance** — Response times from external correspondents (Uniteller, Banorte, BDO, Banreservas, Transnetwork, etc.), blocked tickets, and informal SLAs that currently go unmeasured.

## What's inside

- **Extractor** — pulls tickets from a Zendesk view, their side conversations and events, into a local SQLite DB
- **Classifier** — derives for each thread: direction, recipient type, reason category, response times, resolution time, total exchanges
- **Dashboard (Streamlit)** with 6 pages:
  - **Summary** — hierarchical KPIs (Ticket → Thread → Message), reasons at each level, correspondents overview, statistical distributions
  - **Operational Health** — SLA compliance, P90 response, one-and-done rate, ghost rate, aging buckets, heatmap day×hour
  - **Partner Scorecard** — leaderboard per correspondent (volume, median, P90, SLA %, exchanges, ghosted %, blocked hours), Partner × Classification heatmap, box-plot distributions
  - **Customer Journey** — % tickets with client contact, client response rate, silent clients, multi-contact tickets, top reasons for client contact
  - **Database** — complete flat view (Ticket + Thread + Message), filterable, searchable, exportable to Excel
  - **Concepts** — bilingual data dictionary and concept explanations
- **Bilingual** English / Spanish (toggle in sidebar)

## Stack

- Python 3.11+, SQLite, `requests`, `python-dotenv`
- `streamlit` + `pandas` + `plotly` for dashboard
- `openpyxl` for Excel exports
- `pytest` + `ruff` for tests and linting

## Setup (Windows + VS Code)

### 1. Prerequisites

```powershell
python --version   # must be 3.11+
git --version
```

### 2. Clone and open in VS Code

```powershell
git clone <repo-url>
cd zendesk-sideconv-analytics
code .
```

### 3. Create virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure credentials

Copy `.env.example` to `.env` and fill in your credentials:

```
ZENDESK_SUBDOMAIN=<your-subdomain>
ZENDESK_EMAIL=<your-email>
ZENDESK_TOKEN=<your-api-token>

# For corporate networks with SSL inspection (e.g., Euronet), set to false
SSL_VERIFY=false

# Populated after running discovery scripts
FIELD_ID_REASON_FOR_CONTACT=
FIELD_ID_CORRESPONDENT=
FIELD_ID_COUNTRY=
FIELD_ID_PRODUCT=
VIEW_ID_US_CARE=
```

## Running the pipeline

Always run from the project root with the venv active.

### Phase 0 — Discovery (one-time)

```powershell
# Validate connection
python -m scripts.test_connection

# List all ticket fields -> reports/ticket_fields.csv
python -m scripts.discover_fields

# Find the view ID for US Care
python -m scripts.discover_views
```

After running these, update `.env` with the field IDs and view ID discovered.

### Phase 3 — Extraction

```powershell
# Dry run (no DB writes)
python -m src.extractor --last-days 2 --dry-run

# Full extraction
python -m src.extractor --last-days 7
```

### Phase 4 — Classification

```powershell
# Derive direction, recipient type, classification, response times, etc.
python -m src.classifier
```

### Phase 5 — Dashboard

```powershell
streamlit run src/dashboard.py
```

Open browser at http://localhost:8501

## Project structure

```
src/
├── config.py                 # .env loader and constants
├── zendesk_client.py         # HTTP client for Zendesk API
├── db.py                     # SQLite schema and upsert helpers
├── extractor.py              # Main extraction pipeline
├── classifier.py             # Direction / recipient / reason classifier
├── dashboard.py              # Streamlit dashboard (6 pages)
├── i18n.py                   # Bilingual labels and tooltips
└── concepts_content.py       # Markdown content for Concepts page

scripts/
├── test_connection.py
├── discover_fields.py
└── discover_views.py

docs/
├── data_dictionary.md
├── classification_rules.md
└── api_learnings.md
```

## Data model

```
🎫 TICKET            ← the case file
  └── 💬 THREAD      ← an email chain (side conversation)
        └── ✉️ MSG   ← an individual email within the thread
```

See the **Concepts** page in the dashboard for full explanations of each entity and column.

## Security notes

- `.env` with credentials is **excluded** from git via `.gitignore`
- The SQLite database (`data/*.db`) contains real customer data and is **excluded** from git
- Logs (`logs/`) and discovery reports (`reports/`) are also **excluded**
- For corporate networks with SSL inspection, set `SSL_VERIFY=false` in `.env`

## VS Code recommended extensions

- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Ruff** (Astral Software)
- **SQLite Viewer** (Florian Klampfer)
- **Rainbow CSV**
