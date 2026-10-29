<div align="center">

<img src="assets/readme-banner.svg" alt="FYNTRA — Know where your money goes. Decide where it goes next." width="100%" />

<br />

# FYNTRA

### Know where your money goes. Decide where it goes next.

A full personal-finance workspace for tracking money, understanding spending, reviewing bank statements and making better financial decisions from one place.

<br />

<a href="https://fyntra-prakhargoyal-0003.streamlit.app"><img src="https://img.shields.io/badge/OPEN%20LIVE%20APP-B5F3CF?style=for-the-badge&logo=streamlit&logoColor=0B1010" alt="Open FYNTRA" /></a>
<a href="https://github.com/prakhargoyal02/FYNTRA/actions"><img src="https://img.shields.io/github/actions/workflow/status/prakhargoyal02/FYNTRA/tests.yml?branch=main&style=for-the-badge&label=TESTS" alt="Tests" /></a>
<a href="https://github.com/prakhargoyal02/FYNTRA"><img src="https://img.shields.io/badge/Python-3.12%20%7C%203.13-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" /></a>
<a href="https://streamlit.io"><img src="https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" /></a>

<br />

[**Live Demo**](https://fyntra-prakhargoyal-0003.streamlit.app) · [**GitHub**](https://github.com/prakhargoyal02/FYNTRA) · [**LinkedIn**](https://www.linkedin.com/in/prakhar-goyal-d2002/)

</div>

---

## Why FYNTRA?

Most finance trackers stop at recording expenses. FYNTRA goes further: it keeps a real ledger, connects accounts and transactions, tracks budgets and commitments, analyzes cash flow, supports bank-statement review, and keeps transfers from being miscounted as income or spending.

It is built to feel like one connected product instead of a collection of unrelated finance widgets.

<table>
<tr>
<td width="33%" valign="top">

### 💸 Track
Income, expenses, transfers, accounts, bills, subscriptions, recurring activity and payment history.

</td>
<td width="33%" valign="top">

### 📊 Understand
Monthly cash flow, category spending, budget pressure, savings rate, net worth, trends and financial pulse.

</td>
<td width="33%" valign="top">

### 🧭 Plan
Budgets, goals, debt, upcoming commitments, calendar events and month-end scenarios.

</td>
</tr>
</table>

---

## See it in action

<div align="center">
  <img src="assets/clarity-desktop.jpg" alt="FYNTRA desktop dashboard" width="78%" />
  <img src="assets/clarity-mobile.jpg" alt="FYNTRA mobile dashboard" width="18%" />
</div>

<p align="center"><sub>Desktop and mobile views from the current FYNTRA interface. Demo values are fictional.</sub></p>

> **Try it immediately:** the public demo does not require credentials. Each browser session gets isolated fictional finance data so you can explore the product safely.

---

## What you can do

| | Capability | Details |
| --- | --- | --- |
| 🧭 | **Overview** | Available cash, money in/out, budget position, financial pulse, latest activity, goals, debt and commitments |
| 💳 | **Transactions** | Create, edit, duplicate and delete income, expenses and transfers with advanced filters and search |
| 🏦 | **Accounts** | Bank, cash, savings, card, wallet, investment and custom account types with calculated balances |
| 🎯 | **Budgets** | Monthly category limits, utilization, remaining room, warning states and affordability checks |
| 🧾 | **Bills & subscriptions** | Track recurring commitments and record linked payments without charging real accounts |
| 🌱 | **Goals & debt** | Savings targets, contributions, debt balances, principal reduction and interest records |
| 📈 | **Cash flow & insights** | Monthly movement, category analysis, daily spending, rolling averages, net worth and spending comparisons |
| 🗓️ | **Calendar** | Upcoming bills, renewals, recurring entries, debt dates, planned transactions and goal milestones |
| 📂 | **Bank statements** | Review CSV, XLSX, PDF, TXT and image statements before optionally importing selected rows |
| 📦 | **Data portability** | Export/import structured FYNTRA backups and transaction data with validation and duplicate protection |
| 🔐 | **Private mode** | Optional Supabase authentication, Row Level Security and synchronized cloud state |

---

## Bank statement workflow

FYNTRA treats statement ingestion as a review workflow, not a blind import.

```text
Bank file / screenshot
        │
        ▼
Extract + normalize rows
        │
        ▼
Review dates, amounts, direction and categories
        │
        ├── Save for analysis only
        │
        └── Import selected rows into a FYNTRA account
                │
                ▼
        Duplicate-safe ledger transactions
```

Supported inputs include **CSV, XLSX, PDF, TXT, PNG, JPG, JPEG and WEBP**.

Statement imports keep source identifiers so imported rows can be managed safely later instead of becoming anonymous ledger entries.

---

## Finance engine

The interface is only the surface. FYNTRA's important rules live in the data and analytics layers.

### Integer money storage

Currency is stored as integer paise inside SQLite.

```text
₹1,249.50  →  124950 paise  →  database / calculations  →  ₹1,249.50
```

That avoids letting binary floating-point representation become the source of truth for stored money.

### Transfers are not income

Transfers move value between two accounts but stay neutral in spending and income reports.

```text
Savings → Wallet     account balances change
                     income unchanged
                     expenses unchanged
```

### Historical reports use a cutoff date

Reports can evaluate the ledger as of a selected historical date instead of always assuming today.

### Linked finance actions are reversible

Payments created from bills, subscriptions and supported schedules preserve their source relationship so the app can undo them without leaving disconnected records.

---

## Built with

<div align="center">

<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
<img src="https://img.shields.io/badge/NumPy-4DABCF?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy" />
<img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
<img src="https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
<img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
<img src="https://img.shields.io/badge/Supabase-3FCF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />

</div>

| Layer | Technology | Role |
| --- | --- | --- |
| App logic | **Python** | validation, workflows, domain operations and persistence orchestration |
| Numerical finance | **NumPy** | vectorized rates, projections, rolling calculations and financial summaries |
| Data analysis | **Pandas** | grouping, filtering, joins, transaction analysis and statement normalization |
| Local ledger | **SQLite** | structured relational finance data and atomic operations |
| Interface | **Streamlit + Altair** | responsive app UI, forms, tables and interactive charts |
| Private cloud | **Supabase** | authentication, Row Level Security and optional synchronized state |

---

## Architecture

<div align="center">
  <img src="assets/architecture.svg" alt="FYNTRA architecture" width="92%" />
</div>

```text
                         ┌──────────────────────┐
                         │      Streamlit UI     │
                         │  pages · forms · UX  │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
         ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
         │ Finance logic│   │  Analytics   │   │ Statements   │
         │ validation   │   │ NumPy/Pandas │   │ parse/review │
         └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
                │                  │                  │
                └──────────────────┼──────────────────┘
                                   ▼
                            ┌─────────────┐
                            │   SQLite    │
                            │ local ledger│
                            └──────┬──────┘
                                   │ optional
                                   ▼
                            ┌─────────────┐
                            │  Supabase   │
                            │ private sync│
                            └─────────────┘
```

<details>
<summary><strong>Key modules</strong></summary>

<br />

| File / folder | Responsibility |
| --- | --- |
| `app.py` | application shell, navigation, state and route orchestration |
| `premium_views.py` | Overview, Transactions and Budgets product views |
| `premium_analytics.py` | analytics workspace |
| `views.py` | shared finance workflows and reusable forms |
| `database.py` | schema, validation and finance operations |
| `analytics.py` | Pandas/NumPy financial summaries and reporting |
| `statement_tools.py` | statement extraction and row normalization |
| `statement_upload.py` | upload/review/import workflow |
| `statement_manage.py` | imported statement cleanup and management |
| `cloud_sync.py` | optional private cloud synchronization |
| `auth_ui.py` | authentication experience |
| `tests/` | finance, route, statement, workspace and cloud-boundary regression tests |

</details>

---

## Quick start

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

Then open the local Streamlit address shown in the terminal.

> The fictional demo works without Supabase credentials. Private cloud mode is optional.

---

## Tests

FYNTRA runs the same regression suite on **Python 3.12 and Python 3.13** through GitHub Actions.

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Current suite:

```text
42 passed
Python 3.12 ✓
Python 3.13 ✓
```

The suite covers finance behavior, transaction CRUD, historical report dates, statement parsing/imports, cleanup rules, workspace utilities, route loading and cloud-sync boundaries.

---

## Demo mode vs private mode

<table>
<tr>
<th>Public demo</th>
<th>Private workspace</th>
</tr>
<tr>
<td valign="top">

- No login required
- Fictional deterministic data
- Separate temporary SQLite state per browser session
- Safe for recruiters and visitors to explore
- Nothing in the demo represents real user finances

</td>
<td valign="top">

- Supabase authentication
- Per-user ownership policies
- Private synchronized state
- Statement persistence
- Revision-aware cloud synchronization

</td>
</tr>
</table>

---

## Data and privacy

FYNTRA does **not** process payments and should never be given bank passwords, card PINs, CVVs or OTPs.

No personal finance database is committed to this repository. Local database files, secrets and private uploads are excluded from version control.

For deployment and security details:

- [Deployment guide](docs/DEPLOYMENT.md)
- [Security notes](docs/SECURITY.md)
- [Validation notes](docs/VALIDATION.md)

---

## Project structure

```text
FYNTRA/
├── app.py
├── premium_views.py
├── premium_analytics.py
├── account_workspace.py
├── calendar_view.py
├── data_settings.py
├── views.py
├── database.py
├── analytics.py
├── csv_tools.py
├── statement_tools.py
├── statement_flow.py
├── statement_upload.py
├── statement_manage.py
├── statements.py
├── cloud_sync.py
├── auth_ui.py
├── modern_ui.py
├── assets/
├── docs/
├── supabase/
├── tests/
├── requirements.txt
└── requirements-dev.txt
```

---

## Financial conventions

- Currency is stored as **integer paise**.
- INR is the primary display currency.
- Transfers do not count as income or spending.
- Goal contributions earmark existing money rather than creating new assets.
- Credit-card balances are treated as money owed.
- Savings rate is calculated from net cash flow divided by income.
- Zero-income periods do not invent a savings-rate value.
- Projections are arithmetic scenarios based on recorded data, not financial advice.

---

## Author

<div align="center">

### Prakhar Goyal

Building practical data and software projects with Python.

<a href="https://github.com/prakhargoyal02"><img src="https://img.shields.io/badge/GitHub-prakhargoyal02-181717?style=for-the-badge&logo=github" alt="GitHub" /></a>
<a href="https://www.linkedin.com/in/prakhar-goyal-d2002/"><img src="https://img.shields.io/badge/LinkedIn-Prakhar_Goyal-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white" alt="LinkedIn" /></a>
<a href="https://fyntra-prakhargoyal-0003.streamlit.app"><img src="https://img.shields.io/badge/Live-FYNTRA-B5F3CF?style=for-the-badge&logo=streamlit&logoColor=0B1010" alt="FYNTRA" /></a>

<br /><br />

**If you want to understand the project fastest, open the live demo first and then explore `database.py`, `analytics.py`, and the statement workflow.**

</div>
