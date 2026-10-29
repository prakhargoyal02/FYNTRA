"""FYNTRA: Streamlit presentation over a session-isolated SQLite ledger."""
import tempfile
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

import analytics as analytics_module
from database import Store, today as actual_today
from demo_data import seed_demo
from ui import style
from taste_theme import apply_taste_layer
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
import premium_analytics
import data_settings
import about
import web_shell

REPORT_START = date(2002, 12, 2)
LEDGER_LABELS = {"Main ledger": "main", "Merged": "merged", "One statement": "statement"}


def _valid_report_date(value):
    return isinstance(value, date) and REPORT_START <= value <= actual_today()


def _apply_report_date():
    selected = st.session_state.get("report_date_widget", actual_today())
    if not _valid_report_date(selected):
        selected = actual_today()
        st.session_state.report_date_widget = selected
    st.session_state.report_date = selected
    st.session_state.report_month = selected.strftime("%Y-%m")
    st.session_state.calendar_timeline_from = selected - timedelta(days=7)
    st.session_state.calendar_timeline_through = selected + timedelta(days=45)


def _apply_top_report_date():
    st.session_state.report_date_widget = st.session_state.get("top_report_date", actual_today())
    _apply_report_date()


def _apply_ledger_view():
    label = st.session_state.get("ledger_view_widget", "Main ledger")
    st.session_state.ledger_view = LEDGER_LABELS.get(label, "main")
    if st.session_state.ledger_view != "statement":
        st.session_state.pop("statement_scope_id", None)
        st.session_state.pop("statement_scope_widget", None)
        st.session_state.pop("top_statement_scope", None)


def _apply_top_ledger_view():
    st.session_state.ledger_view_widget = st.session_state.get("top_ledger_view", "Main ledger")
    _apply_ledger_view()


def _apply_statement_scope():
    selected = st.session_state.get("statement_scope_widget")
    if selected:
        st.session_state.statement_scope_id = selected


def _apply_top_statement_scope():
    selected = st.session_state.get("top_statement_scope")
    if selected:
        st.session_state.statement_scope_widget = selected
        _apply_statement_scope()


st.set_page_config(
    page_title="FYNTRA · Your money, with clarity",
    page_icon="assets/mark.svg",
    layout="wide",
    initial_sidebar_state="collapsed",
)
style()
apply_taste_layer()
st.session_state.setdefault("mode", "demo")
if "store" not in st.session_state:
    directory = tempfile.TemporaryDirectory(prefix="fyntra-demo-")
    demo_store = Store(Path(directory.name) / "finance.db")
    seed_demo(demo_store)
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
    "Cash flow & insights": premium_analytics.analytics_page,
    "Calendar": calendar_view.calendar_page,
    "Data & settings": data_settings.data_page,
}
if st.session_state.mode != "demo":
    routes["Bank statements"] = statement_workspace.statement_page
routes["About FYNTRA"] = about.about_page

if st.session_state.get("page_nav") not in routes:
    st.session_state.page_nav = "Overview"

# Compatibility controls stay in Streamlit's sidebar so existing state callbacks and
# regression tests continue to operate. The CSS theme hides the rail from users.
with st.sidebar:
    page = st.radio("Workspace", list(routes), key="page_nav", label_visibility="collapsed")

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
    )
    if "report_month" not in st.session_state:
        _apply_report_date()

    imported = statement_imports(st.session_state.store) if st.session_state.mode != "demo" else {}
    if imported:
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
            if st.session_state.get("statement_scope_widget") not in imported:
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

# Keep the visible top-shell controls synchronized with the compatibility controls.
st.session_state.top_report_date = st.session_state.report_date
if imported:
    reverse_labels = {value: label for label, value in LEDGER_LABELS.items()}
    st.session_state.top_ledger_view = reverse_labels.get(st.session_state.get("ledger_view", "main"), "Main ledger")
    if st.session_state.get("ledger_view") == "statement":
        current_id = st.session_state.get("statement_scope_id")
        if current_id in imported:
            st.session_state.top_statement_scope = current_id

web_shell.top_shell(
    routes=routes,
    page=page,
    mode=st.session_state.mode,
    imported=imported,
    report_date=st.session_state.report_date,
    report_min=REPORT_START,
    report_max=actual_today(),
    on_report_change=_apply_top_report_date,
    on_ledger_change=_apply_top_ledger_view,
    on_statement_change=_apply_top_statement_scope,
)

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
