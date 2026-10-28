# FYNTRA Simple Complete Edition

**Know where your money goes. Decide where it goes next.**

This is a beginner-friendly rebuild of FYNTRA.

The project intentionally uses a small number of files so you can understand the full codebase without jumping through dozens of folders.

## Stack

- Python
- NumPy
- Pandas
- SQLite
- Streamlit
- Altair

## Project structure

```text
FYNTRA-Simple-Complete/
├── app.py
├── database.py
├── analytics.py
├── sample_data.py
├── requirements.txt
├── .gitignore
└── README.md
```

## What each file does

### `app.py`
The Streamlit website.

### `database.py`
The SQLite layer for accounts, transactions, budgets, goals, debts, bills, and subscriptions.

### `analytics.py`
The finance calculation layer using Pandas and NumPy.

### `sample_data.py`
Adds fictional demo records for testing.

## Run in VS Code

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Then open **Data & Settings → Load demo data**.

This README is temporary and will be rewritten after the full rebuilt FYNTRA and new UI are complete.
