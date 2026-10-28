"""FYNTRA: Streamlit presentation over a session-isolated SQLite ledger."""
import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st
from database import Store, today
from demo_data import seed_demo
from ui import brand, style
import auth_ui
import statement_tools
import statement_formats
from statement_ocr import ocr_lines
from ledger_scope import scoped_store, statement_imports
statement_formats.install()
statement_tools._ocr_lines = ocr_lines
import statement_workspace
import views
import data_settings
import about

st.set_page_config(page_title="FYNTRA · Your money, with clarity", page_icon="assets/mark.svg", layout="wide")
style()
st.session_state.setdefault("mode", "demo")
if "store" not in st.session_state:
    directory = tempfile.TemporaryDirectory(prefix="fyntra-demo-")
    demo_store = Store(Path(directory.name)/"finance.db")
    seed_demo(demo_store)
    # Publish only a complete store: browser component events can interrupt a rerun.
    st.session_state.demo_directory = directory
    st.session_state.store = demo_store
auth_ui.restore_browser_session()
routes = {"Overview":views.overview_page, "Transactions":views.transactions_page,
          "Budgets":views.budgets_page, "Accounts":views.accounts_page,
          "Bills & subscriptions":views.commitments_page, "Goals & debt":views.goals_page,
          "Cash flow & insights":views.analytics_page, "Calendar":views.calendar_page,
          "Data & settings":data_settings.data_page}
if st.session_state.mode != "demo":
    routes["Bank statements"] = statement_workspace.statement_page
# Keep project information at the bottom of the workspace navigation.
routes["About FYNTRA"] = about.about_page
with st.sidebar:
    brand()
    st.caption("Know where your money goes. Decide where it goes next.")
    st.caption("FICTIONAL DEMO · YOUR OWN SESSION" if st.session_state.mode=="demo" else "PRIVATE · YOUR ACCOUNT")
    page = st.radio("Workspace", list(routes), label_visibility="collapsed")
    months = pd.period_range(end=today(), periods=24, freq="M").astype(str)[::-1].tolist()
    st.selectbox("Report month", months, key="report_month")

    imported = statement_imports(st.session_state.store) if st.session_state.mode != "demo" else {}
    if imported:
        st.caption("DATA VIEW")
        scope_label = st.segmented_control(
            "Ledger view",
            ["Main ledger", "Merged", "One statement"],
            default="Main ledger",
            key="ledger_view_label",
            label_visibility="collapsed",
        )
        mode_map = {"Main ledger":"main", "Merged":"merged", "One statement":"statement"}
        st.session_state.ledger_view = mode_map.get(scope_label, "main")
        if st.session_state.ledger_view == "statement":
            statement_ids = list(imported)
            current_id = st.session_state.get("statement_scope_id")
            if current_id not in imported:
                current_id = statement_ids[0]
            st.session_state.statement_scope_id = st.selectbox(
                "Imported statement",
                statement_ids,
                index=statement_ids.index(current_id),
                format_func=lambda value: imported[value],
            )
        else:
            st.session_state.pop("statement_scope_id", None)
    else:
        st.session_state.ledger_view = "main"
        st.session_state.pop("statement_scope_id", None)
        st.session_state.pop("ledger_view_label", None)

    auth_ui.login_panel()
    st.caption("FYNTRA v1.0 · By Prakhar Goyal")
if st.session_state.get("sync_error"):
    st.error(st.session_state.sync_error)
if st.session_state.get("notice"):
    st.toast(st.session_state.pop("notice"))

raw_store = st.session_state.store
scope_exempt = {"Data & settings", "Bank statements", "About FYNTRA"}
if page not in scope_exempt and imported:
    st.session_state.store = scoped_store(
        raw_store,
        st.session_state.get("ledger_view", "main"),
        st.session_state.get("statement_scope_id"),
    )
try:
    routes[page]()
finally:
    st.session_state.store = raw_store
st.caption("Based on recorded data. Budgeting education, not investment or lending advice.")
