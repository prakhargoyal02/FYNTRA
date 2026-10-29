<h1 align="center">
  <a href="https://fyntra-prakhargoyal-0003.streamlit.app">
    <img src="assets/wordmark.svg" alt="FYNTRA" width="330">
  </a>
</h1>

<h3 align="center">Know where your money goes. Decide where it goes next.</h3>

<p align="center">
  A personal-finance workspace for tracking money, understanding spending,<br>
  reviewing bank statements and planning what comes next.<br>
  Built with Python, NumPy, Pandas, SQLite, Streamlit and optional Supabase sync.
</p>

<p align="center">
  <a href="https://fyntra-prakhargoyal-0003.streamlit.app"><img src="https://img.shields.io/badge/live-FYNTRA-B5F3CF?logo=streamlit&logoColor=0B1010" alt="Live FYNTRA"></a>
  <a href="https://github.com/prakhargoyal02/FYNTRA/actions"><img src="https://img.shields.io/github/actions/workflow/status/prakhargoyal02/FYNTRA/tests.yml?branch=main&label=tests" alt="Tests"></a>
  <img src="https://img.shields.io/badge/python-3.12%20%7C%203.13-3776AB?logo=python&logoColor=white" alt="Python 3.12 and 3.13">
  <img src="https://img.shields.io/badge/license-personal%20project-385B49" alt="Personal project">
</p>

<p align="center">
  <a href="#see-your-money-clearly">Overview</a> •
  <a href="#review-bank-statements-before-they-touch-your-ledger">Statements</a> •
  <a href="#install">Install</a> •
  <a href="#how-it-works">How it works</a> •
  <a href="#privacy">Privacy</a> •
  <a href="#build-and-test">Build & test</a>
</p>

---

Most finance apps are good at collecting transactions and bad at explaining what those transactions mean together. FYNTRA keeps the ledger, accounts, budgets, commitments, goals, debt and cash flow connected so the same money is not counted twice and the dashboard stays understandable as the data grows.

## See your money clearly

<p align="center">
  <img src="assets/clarity-desktop.jpg" alt="FYNTRA desktop dashboard" width="78%">
  <img src="assets/clarity-mobile.jpg" alt="FYNTRA mobile dashboard" width="18%">
</p>

FYNTRA gives one place to work with the day-to-day ledger and the bigger financial picture:

- **Accounts and transactions.** Track income, expenses and transfers across bank, cash, savings, cards, wallets and custom accounts.
- **Budgets.** Set monthly category limits, see utilization, remaining room and over-budget pressure.
- **Bills and subscriptions.** Keep recurring commitments visible and record linked payments safely.
- **Goals and debt.** Track savings targets, contributions, debt balances, principal reduction and interest records.
- **Cash flow and insights.** Compare income and expenses, category spending, rolling trends, savings rate and net worth.
- **Calendar.** See upcoming bills, renewals, recurring movements, debt dates and goal milestones in time.
- **Backups.** Export and import structured FYNTRA data with validation and duplicate protection.

The public demo uses fictional data and does not require a login: **[open FYNTRA](https://fyntra-prakhargoyal-0003.streamlit.app)**.

## Review bank statements before they touch your ledger

FYNTRA treats statement ingestion as a review step, not a blind import.

```text
Bank file / screenshot
        │
        ▼
Extract + normalize rows
        │
        ▼
Review dates, amounts, direction and categories
        │
        ├── Keep for statement analysis
        │
        └── Import selected rows into an account
                │
                ▼
        Duplicate-aware ledger transactions
```

Supported inputs include **CSV, XLSX, PDF, TXT, PNG, JPG, JPEG and WEBP**. Imported rows keep source identifiers so statement transactions can be traced and managed later instead of becoming anonymous records.

## The finance rules underneath

The UI is only the surface. A few rules keep the numbers coherent.

### Money is stored in integer paise

```text
₹1,249.50  →  124950 paise  →  SQLite / calculations  →  ₹1,249.50
```

Stored money does not use floating-point values as the source of truth.

### Transfers are neutral

Moving money between your own accounts changes balances, but it does not become new income or new spending.

```text
Savings → Wallet
balances: changed
income:   unchanged
expenses: unchanged
```

### Historical reports have a real cutoff

A report can evaluate the ledger as of a selected historical date instead of always assuming today.

### Linked payments can be reversed

Bills, subscriptions and supported recurring workflows preserve their source relationship when they create ledger entries, allowing supported payment actions to be undone without leaving disconnected records.

## Install

Use Python **3.12 or 3.13**.

### Windows

```powershell
git clone https://github.com/prakhargoyal02/FYNTRA.git
cd FYNTRA
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

### macOS / Linux

```bash
git clone https://github.com/prakhargoyal02/FYNTRA.git
cd FYNTRA
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The fictional local demo works without Supabase credentials. Private cloud mode is optional.

## How it works

<p align="center">
  <img src="assets/architecture.svg" alt="FYNTRA architecture" width="92%">
</p>

The application is split into four main layers:

1. **Streamlit UI** handles navigation, forms, tables and charts.
2. **Finance workflows** validate operations such as transactions, transfers, budgets and linked payments.
3. **Pandas + NumPy analytics** turn ledger data into cash-flow, category, trend and planning views.
4. **SQLite** keeps the local structured ledger; optional **Supabase** adds authenticated private persistence and cloud synchronization.

<details>
<summary><strong>Repository map</strong></summary>

<br>

| Path | Responsibility |
| --- | --- |
| `app.py` | application shell, navigation and session state |
| `premium_views.py` | Overview, Transactions and Budgets views |
| `premium_analytics.py` | cash-flow and insights workspace |
| `views.py` | shared finance forms and workflows |
| `database.py` | schema, validation and atomic finance operations |
| `analytics.py` | Pandas/NumPy reporting and financial summaries |
| `statement_tools.py` | statement extraction and normalization |
| `statement_upload.py` | statement review/import workflow |
| `statement_manage.py` | imported statement management |
| `cloud_sync.py` | optional private cloud synchronization |
| `auth_ui.py` | authentication experience |
| `tests/` | finance, route, statement, workspace and cloud-boundary checks |

</details>

## Built with

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/NumPy-4DABCF?logo=numpy&logoColor=white" alt="NumPy">
  <img src="https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=white" alt="Pandas">
  <img src="https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Supabase-3FCF8E?logo=supabase&logoColor=white" alt="Supabase">
</p>

## Privacy

FYNTRA does **not** process payments and should never be given bank passwords, card PINs, CVVs or OTPs.

| | |
| --- | --- |
| **Public demo** | Uses isolated fictional data and requires no credentials. |
| **Local mode** | Uses a local SQLite ledger. Private database files and uploads are excluded from version control. |
| **Private cloud mode** | Uses Supabase authentication, ownership policies and revision-aware synchronization. |
| **Repository** | Contains application code, tests and fictional demo data only, not personal finance records. |

More detail: [deployment](docs/DEPLOYMENT.md) · [security](docs/SECURITY.md) · [validation](docs/VALIDATION.md)

## Build and test

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The GitHub Actions matrix runs the suite on **Python 3.12 and 3.13**.

```text
42 passed
Python 3.12 ✓
Python 3.13 ✓
```

Tests cover finance behavior, transaction CRUD, historical report dates, statement parsing and imports, statement cleanup, workspace tools, route loading and cloud-sync boundaries.

## Financial conventions

- Currency is stored as **integer paise**.
- INR is the primary display currency.
- Transfers do not count as income or spending.
- Goal contributions earmark existing money rather than creating new assets.
- Credit-card balances are treated as money owed.
- Savings rate is calculated from net cash flow divided by income.
- Zero-income periods do not invent a savings-rate value.
- Projections are arithmetic scenarios based on recorded data, not financial advice.

## Author

**Prakhar Goyal**

[GitHub](https://github.com/prakhargoyal02) · [LinkedIn](https://www.linkedin.com/in/prakhar-goyal-d2002/) · [Live FYNTRA](https://fyntra-prakhargoyal-0003.streamlit.app)

---

<p align="center">
  <a href="https://fyntra-prakhargoyal-0003.streamlit.app">
    <img src="assets/wordmark.svg" alt="FYNTRA" width="260">
  </a>
</p>

<h3 align="center">Know where your money goes. Decide where it goes next.</h3>

<p align="center">
  <a href="https://fyntra-prakhargoyal-0003.streamlit.app">Live App</a> •
  <a href="https://github.com/prakhargoyal02/FYNTRA">Source</a> •
  <a href="https://www.linkedin.com/in/prakhar-goyal-d2002/">LinkedIn</a>
</p>
