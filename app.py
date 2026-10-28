"""FYNTRA: Streamlit presentation over a session-isolated SQLite ledger."""
import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

import analytics as analytics_module
from database import Store, today as actual_today
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

REPORT_START = date(2002, 12, 2)

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

routes = {
    "Overview": views.overview_page,
    "Transactions": views.transactions_page,
    "Budgets": views.budgets_page,
    "Accounts": views.accounts_page,
    "Bills & subscriptions": views.commitments_page,
    "Goals & debt": views.goals_page,
    "Cash flow & insights": views.analytics_page,
    "Calendar": views.calendar_page,
    "Data & settings": data_settings.data_page,
}
if st.session_state.mode != "demo":
    routes["Bank statements"] = statement_workspace.statement_page
# Keep project information at the bottom of the workspace navigation.
routes["About FYNTRA"] = about.about_page

with st.sidebar:
    brand()
    st.caption("Know where your money goes. Decide where it goes next.")
    st.caption("FICTIONAL DEMO · YOUR OWN SESSION" if st.session_state.mode == "demo" else "PRIVATE · YOUR ACCOUNT")
    page = st.radio("Workspace", list(routes), label_visibility="collapsed")

    current_report = st.session_state.get("report_date")
    if not isinstance(current_report, date) or current_report < REPORT_START or current_report > actual_today():
        st.session_state.report_date = actual_today()
    st.date_input(
        "Report date",
        min_value=REPORT_START,
        max_value=actual_today(),
        key="report_date",
        format="DD/MM/YYYY",
        help="Use any date from 2 Dec 2002 through today to inspect your finances as they stood on that day.",
    )
    st.session_state.report_month = st.session_state.report_date.strftime("%Y-%m")
    st.caption(f'Viewing records through {st.session_state.report_date:%d %b %Y}')

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
        mode_map = {"Main ledger": "main", "Merged": "merged", "One statement": "statement"}
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

# Existing analytics and views use a shared `today()` helper. During page rendering,
# point those read calculations at the selected report date so historical views are
# consistent across balances, charts, timelines and monthly summaries.
report_cutoff = st.session_state.report_date
original_analytics_today = analytics_module.today
original_views_today = views.today
analytics_module.today = lambda: report_cutoff
views.today = lambda: report_cutoff
try:
    routes[page]()
finally:
    analytics_module.today = original_analytics_today
    views.today = original_views_today
    st.session_state.store = raw_store

st.caption("Based on recorded data. Budgeting education, not investment or lending advice.")
