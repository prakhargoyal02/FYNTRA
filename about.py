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
- Keep uploaded statements separate, compare selected statements, or import reviewed rows into the ledger.
- Export and restore FYNTRA backups.
- Use a fictional demo or a private Supabase-backed workspace.
        """
    )

    st.subheader("How it is built")
    st.markdown(
        """
- **Python** handles application rules, validation and workflows.
- **SQLite** stores the structured local/session ledger.
- **Pandas** prepares transaction tables, filters, groups and summaries.
- **NumPy** supports financial calculations and rolling/statistical values.
- **Streamlit** provides the interface.
- **Supabase** provides optional private authentication and cloud persistence.
        """
    )

    st.subheader("Data principles")
    st.write(
        "Money is stored internally as integer paise. Transfers are not counted as income or spending. "
        "Statement uploads do not change the ledger unless the user explicitly imports reviewed rows. "
        "Private cloud rows are protected by user ownership rules."
    )

    st.caption("FYNTRA v1.0 · Built by Prakhar Goyal")
