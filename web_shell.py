"""Responsive navigation. All actions use Streamlit callbacks and existing routes."""
from html import escape
import streamlit as st
import auth_ui
import workspace_tools
from ui import brand

PRIMARY = [("Overview", "Overview"), ("Transactions", "Transactions"),
           ("Budgets", "Budgets"), ("Cash flow & insights", "Insights")]


def _go(page):
    st.session_state.page_nav = page


def _account_button(mode):
    if mode != "private":
        return "Sign in"
    name, _ = auth_ui.account_identity()
    return name[:18] or "Account"


def top_shell(routes, page, mode, imported, report_date, report_min, report_max,
              on_report_change, on_ledger_change, on_statement_change):
    with st.container(key="fyntra-site-header", horizontal=True, vertical_alignment="center", gap="small"):
        with st.container(width=180):
            brand()
        with st.container(key="desktop-navigation", horizontal=True, vertical_alignment="center", width="stretch", gap="small"):
            for route, label in PRIMARY:
                if route in routes:
                    st.button(label, key=f"top-nav-{route}", type="primary" if page == route else "secondary",
                              on_click=_go, args=(route,))
        with st.popover("Menu", icon=":material/menu:"):
            st.caption("YOUR WORKSPACE")
            # The same menu works on desktop and phone; no destinations disappear.
            for route in routes:
                st.button(route, key=f"menu-nav-{route}", width="stretch",
                          type="primary" if page == route else "secondary", on_click=_go, args=(route,))
            with st.expander("Quick tools"):
                workspace_tools.tools_panel()
        with st.popover(_account_button(mode), icon=":material/account_circle:"):
            auth_ui.login_panel(compact=True)

    with st.container(horizontal=True, vertical_alignment="center", gap="small", key="report-controls"):
        with st.container(width="stretch"):
            status = "Private workspace" if mode == "private" else "Fictional demo · your own session"
            st.html(f'<div class="f-context-strip"><span>Workspace / {escape(page)}</span><span class="f-status">{status}</span></div>')
        with st.popover(report_date.strftime("%d %b %Y"), icon=":material/calendar_today:"):
            st.date_input("Report date", min_value=report_min, max_value=report_max, key="top_report_date",
                          on_change=on_report_change, format="DD/MM/YYYY", help="Inspect recorded data as of this date.")
            if imported:
                st.segmented_control("Data view", ["Main ledger", "Merged", "One statement"],
                                     key="top_ledger_view", on_change=on_ledger_change)
                if st.session_state.get("ledger_view") == "statement":
                    st.selectbox("Imported statement", list(imported), format_func=imported.get,
                                 key="top_statement_scope", on_change=on_statement_change)
