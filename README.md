# Zendesk Side Conversations Analytics — Ria CX POC

Local analytics POC for Zendesk side conversations with two core objectives:

1. **Reporting & classification** — Visibility into what types of side conversations exist (RFI, refund, cancellation, proof of payment, trace, compliance, etc.), who generates them, and in what direction (outbound / inbound / internal).
2. **Partner performance** — Response times from external correspondents (BDO, Banorte, Uniteller, BCE-RIA, Mercado Pago, etc.), blocked tickets, and informal SLAs that currently go unmeasured.

## Stack

- Python 3.11+, SQLite, `requests`, `python-dotenv`
- `streamlit` + `pandas` + `plotly` for dashboard
- `pytest` + `ruff` for tests and linting

## Setup (Windows + VS Code)

### 1. Prerequisites

Verify in a PowerShell terminal:

```powershell
python --version   # must be 3.11+
git --version
```

### 2. Open project in VS Code

```powershell
cd "C:\Users\jaguilar\OneDrive - Euronet Worldwide\Desktop\Claude Code\zendesk-sideconv-analytics"
code .
```

### 3. Create virtual environment

```powershell
python -m venv .venv
```

If PowerShell blocks activation:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Activate:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure credentials

Copy `.env.example` to `.env` (use VS Code, NOT Notepad, to avoid BOM encoding issues):

```powershell
Copy-Item .env.example .env
```

Fill in your credentials:
```
ZENDESK_SUBDOMAIN=riamoneyxxx
ZENDESK_EMAIL=george.orellana@riamoneytransfer.com
ZENDESK_TOKEN=<token from Ernesto>
```

## Running the scripts

Always run from the project root with the venv active.

### Fase 0 — Discovery

```powershell
# Validate connection
python -m scripts.test_connection

# List all ticket fields (saves reports/ticket_fields.csv)
python -m scripts.discover_fields

# Find the "US Care" view ID
python -m scripts.discover_views
```

### Fase 3 — Extraction

```powershell
# Dry run (no DB writes)
python -m src.extractor --last-days 2 --dry-run

# Full extraction
python -m src.extractor --last-days 7
```

### Fase 5 — Dashboard

```powershell
streamlit run src/dashboard.py
```

Open browser at http://localhost:8501

## VS Code recommended extensions

- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Ruff** (Astral Software)
- **SQLite Viewer** (Florian Klampfer) — view .db files directly in VS Code
- **Rainbow CSV** — read discovery CSVs with column highlighting

## API Learnings

_Populated as we discover quirks of the Zendesk API._

<!-- Add entries here as we encounter them -->
