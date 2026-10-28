"""FYNTRA: Streamlit presentation over a session-isolated SQLite ledger."""
import tempfile
from pathlib import Path
import pandas as pd
import streamlit as st
from database import Store, today
from demo_data import seed_demo
from ui import brand, style
import auth_ui
import views

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
          "Data & settings":views.data_page, "Learning guide":views.learning_page}
with st.sidebar:
    brand()
    st.caption("Know where your money goes. Decide where it goes next.")
    st.caption("FICTIONAL DEMO · YOUR OWN SESSION" if st.session_state.mode=="demo" else "PRIVATE · YOUR ACCOUNT")
    page = st.radio("Workspace", list(routes), label_visibility="collapsed")
    months = pd.period_range(end=today(), periods=24, freq="M").astype(str)[::-1].tolist()
    st.selectbox("Report month", months, key="report_month")
    auth_ui.login_panel()
    st.caption("FYNTRA v1.0 · By Prakhar Goyal")
if st.session_state.get("sync_error"):
    st.error(st.session_state.sync_error)
if st.session_state.get("notice"):
    st.toast(st.session_state.pop("notice"))
routes[page]()
st.caption("Based on recorded data. Budgeting education, not investment or lending advice.")
