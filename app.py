"""FYNTRA: Streamlit presentation over a session-isolated SQLite ledger."""
import tempfile
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

import analytics as analytics_module
from database import Store, today as actual_today
from demo_data import seed_demo
from ui import brand, sidebar_status, style
import auth_ui
import statement_tools
import statement_formats
from statement_ocr import ocr_lines
from ledger_scope import scoped_store, statement_imports

statement_formats.install()
statement_tools._ocr_lines = ocr_lines

import statement_workspace
import calendar_view
import views
import premium_views
import data_settings
import about

REPORT_START = date(2002, 12, 2)
LEDGER_LABELS = {"Main ledger": "main", "Merged": "merged", "One statement": "statement"}


def _valid_report_date(value):
    return isinstance(value, date) and REPORT_START <= value <= actual_today()


def _apply_report_date():
    """Copy the date widget value into FYNTRA's report state before the rerun."""
    selected = st.session_state.get("report_date_widget", actual_today())
    if not _valid_report_date(selected):
        selected = actual_today()
        st.session_state.report_date_widget = selected
    st.session_state.report_date = selected
    st.session_state.report_month = selected.strftime("%Y-%m")
    # Keep Calendar centered on the newly selected historical date.
    st.session_state.calendar_timeline_from = selected - timedelta(days=7)
    st.session_state.calendar_timeline_through = selected + timedelta(days=45)


def _apply_ledger_view():
    """Apply the data-view widget selection before the page is rendered."""
    label = st.session_state.get("ledger_view_widget", "Main ledger")
    st.session_state.ledger_view = LEDGER_LABELS.get(label, "main")
    if st.session_state.ledger_view != "statement":
        st.session_state.pop("statement_scope_id", None)
        st.session_state.pop("statement_scope_widget", None)


def _apply_statement_scope():
    """Apply the selected statement before scoped analytics are built."""
    selected = st.session_state.get("statement_scope_widget")
    if selected:
        st.session_state.statement_scope_id = selected


st.set_page_config(
    page_title="FYNTRA · Your money, with clarity",
    page_icon="assets/mark.svg",
    layout="wide",
    initial_sidebar_state="expanded",
)
style()
st.session_state.setdefault("mode", "demo")
if "store" not in st.session_state:
    directory = tempfile.TemporaryDirectory(prefix="fyntra-demo-")
    demo_store = Store(Path(directory.name) / "finance.db")
    seed_demo(demo_store)
    # Publish only a complete store: browser component events can interrupt a rerun.
    st.session_state.demo_directory = directory
    st.session_state.store = demo_store

auth_ui.restore_browser_session()

routes = {
    "Overview": premium_views.overview_page,
    "Transactions": premium_views.transactions_page,
    "Budgets": premium_views.budgets_page,
    "Accounts": views.accounts_page,
    "Bills & subscriptions": views.commitments_page,
    "Goals & debt": views.goals_page,
    "Cash flow & insights": views.analytics_page,
    "Calendar": calendar_view.calendar_page,
    "Data & settings": data_settings.data_page,
}
if st.session_state.mode != "demo":
    routes["Bank statements"] = statement_workspace.statement_page
# Keep project information at the bottom of the workspace navigation.
routes["About FYNTRA"] = about.about_page

with st.sidebar:
    brand()
    st.caption("Know where your money goes. Decide where it goes next.")
    sidebar_status(st.session_state.mode)
    # Keep the stored option values exactly equal to route names. Styling supplies the
    # visual polish without transforming values that tests and callbacks depend on.
    page = st.radio("Workspace", list(routes), label_visibility="collapsed")

    st.divider()
    st.caption("REPORTING WINDOW")
    current_report = st.session_state.get("report_date")
    if not _valid_report_date(current_report):
        current_report = actual_today()
        st.session_state.report_date = current_report
        st.session_state.report_month = current_report.strftime("%Y-%m")
    widget_report = st.session_state.get("report_date_widget")
    if not _valid_report_date(widget_report):
        st.session_state.report_date_widget = current_report
    st.date_input(
        "Report date",
        min_value=REPORT_START,
        max_value=actual_today(),
        key="report_date_widget",
        on_change=_apply_report_date,
        format="DD/MM/YYYY",
        help="Use any date from 2 Dec 2002 through today to inspect your finances as they stood on that day.",
    )
    # First run has no callback, so keep derived state initialized explicitly.
    if "report_month" not in st.session_state:
        _apply_report_date()
    st.caption(f'Viewing through {st.session_state.report_date:%d %b %Y}')

    imported = statement_imports(st.session_state.store) if st.session_state.mode != "demo" else {}
    if imported:
        st.caption("DATA VIEW")
        reverse_labels = {value: label for label, value in LEDGER_LABELS.items()}
        current_mode = st.session_state.get("ledger_view", "main")
        widget_label = st.session_state.get("ledger_view_widget")
        if widget_label not in LEDGER_LABELS:
            st.session_state.ledger_view_widget = reverse_labels.get(current_mode, "Main ledger")
        st.segmented_control(
            "Ledger view",
            list(LEDGER_LABELS),
            key="ledger_view_widget",
            on_change=_apply_ledger_view,
            label_visibility="collapsed",
        )
        if "ledger_view" not in st.session_state:
            _apply_ledger_view()

        if st.session_state.ledger_view == "statement":
            statement_ids = list(imported)
            current_id = st.session_state.get("statement_scope_id")
            if current_id not in imported:
                current_id = statement_ids[0]
                st.session_state.statement_scope_id = current_id
            widget_statement = st.session_state.get("statement_scope_widget")
            if widget_statement not in imported:
                st.session_state.statement_scope_widget = current_id
            st.selectbox(
                "Imported statement",
                statement_ids,
                format_func=lambda value: imported[value],
                key="statement_scope_widget",
                on_change=_apply_statement_scope,
            )
            if st.session_state.get("statement_scope_id") not in imported:
                _apply_statement_scope()
        else:
            st.session_state.pop("statement_scope_id", None)
            st.session_state.pop("statement_scope_widget", None)
    else:
        st.session_state.ledger_view = "main"
        st.session_state.pop("statement_scope_id", None)
        st.session_state.pop("statement_scope_widget", None)
        st.session_state.pop("ledger_view_widget", None)

    st.divider()
    auth_ui.login_panel()
    st.caption("FYNTRA · By Prakhar Goyal")

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

# Existing analytics and views use a shared today() helper. During page rendering,
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
