"""About page for FYNTRA."""
import streamlit as st
from ui import hero


def about_page():
    hero(
        "About FYNTRA",
        "Know where your money goes. Decide where it goes next.",
        "FYNTRA / PROJECT 02",
    )
    st.write(
        "FYNTRA is a personal finance workspace for tracking everyday money clearly: "
        "income, expenses, accounts, budgets, bills, subscriptions, goals, debt, cash flow and bank statements."
    )

    st.subheader("What it can do")
    st.markdown(
        """
- Track transactions, transfers and account balances.
- Build monthly budgets and review spending patterns.
- Record bills, subscriptions, savings goals and debt payments.
- Analyze bank statements from CSV, XLSX, PDF, TXT and clear screenshots.
- Keep statements separate, compare only the statements you select, or add reviewed rows to the ledger.
- Export and restore FYNTRA backups.
- Use a fictional demo or a private Supabase-backed workspace.
        """
    )

    st.subheader("Learning guide")
    learning = [
        ("Python · application rules",
         "database.py validates amounts, dates and relationships. Payment functions group related writes into one transaction so partial operations cannot leave inconsistent balances."),
        ("SQLite · one coherent ledger",
         "Related tables store accounts, transactions, budgets, commitments, goals and debts. Money is stored as integer paise, foreign keys protect relationships, and transfers use a source and destination without becoming income or spending."),
        ("Pandas · structured financial data",
         "analytics.py joins account names with merge, filters with loc, parses dates with to_datetime, groups categories with groupby and aggregation, builds monthly pivot tables and sorts results. CSV and statement tools use DataFrames for import, review and cleanup."),
        ("NumPy · numerical reasoning",
         "Vectorized arithmetic supports savings rates, budget utilization, balances, projections, rolling spending and guarded calculations for zero-income or zero-budget cases."),
        ("Streamlit · the product interface",
         "app.py routes screens while views.py and the statement workspace compose forms, charts and responsive containers. Widgets call domain functions instead of embedding the financial rules themselves."),
        ("Supabase · private persistence",
         "Authentication verifies identity. Row Level Security restricts private cloud rows to their owner. Revision checks protect the ledger from silently overwriting a newer cloud copy, while SQLite remains the structured working database."),
    ]
    for title, text in learning:
        with st.container(border=True):
            st.subheader(title)
            st.write(text)

    st.subheader("How the money model stays consistent")
    st.markdown(
        """
- Monetary values are stored internally as **integer paise**.
- Transfers affect account balances but are not counted as income or expenses.
- Bills, subscriptions, debts and recurring schedules create linked ledger entries instead of unrelated duplicates.
- Bank-statement uploads are reviewed first and do not change Transactions unless the user explicitly chooses an import action.
- Saved statements, statement exports and ledger transactions are separate layers so deleting one does not silently erase another.
        """
    )

    st.subheader("What to study in the code")
    st.markdown(
        """
1. Start with `database.py` to understand validation, relationships and atomic money workflows.
2. Read `analytics.py` to see Pandas and NumPy turn ledger rows into summaries and projections.
3. Read `statement_tools.py` to follow statement parsing, normalization, classification and duplicate-safe ledger import.
4. Read `csv_tools.py` for portable FYNTRA backup/import logic.
5. Finish with `app.py`, `views.py` and `statements.py` to see how the interface calls those domain functions.
        """
    )

    st.subheader("Privacy and data boundaries")
    st.write(
        "Source statement files are processed for extraction; reviewed statement rows are saved only when the user chooses to save them. "
        "Private cloud data is ownership-protected, while exported statement snapshots stay separate from saved statements and ledger data."
    )

    st.markdown(
        "Built by [Prakhar Goyal](https://github.com/prakhargoyal02) · "
        "[GitHub source](https://github.com/prakhargoyal02/FYNTRA) · "
        "[LinkedIn](https://www.linkedin.com/in/prakhar-goyal-d2002/)"
    )
    st.caption("FYNTRA v1.0 · Built by Prakhar Goyal")
