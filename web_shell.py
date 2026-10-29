"""Full-width FYNTRA application shell.

The visible navigation is intentionally separate from the hidden compatibility widgets
kept in app.py for Streamlit state/tests. Buttons only change navigation state.
"""
import streamlit as st

import auth_ui
import workspace_tools
from ui import brand

PRIMARY = [
    ("Overview", "Overview"),
    ("Transactions", "Transactions"),
    ("Budgets", "Budgets"),
    ("Cash flow & insights", "Insights"),
]


def _go(page):
    st.session_state.page_nav = page


def _account_button(mode):
    if mode != "private":
        return "Sign in"
    name, _ = auth_ui.account_identity()
    return name[:18] or "Account"


def top_shell(
    routes,
    page,
    mode,
    imported,
    report_date,
    report_min,
    report_max,
    on_report_change,
    on_ledger_change,
    on_statement_change,
):
    """Render a compact website-style top shell and utility menus."""
    with st.container(key="fyntra-site-header"):
        logo_col, nav_col, tools_col, account_col, utility_col = st.columns(
            [1.05, 3.35, .62, .78, .78],
            gap="small",
            vertical_alignment="center",
        )

        with logo_col:
            brand()
            st.caption("PERSONAL FINANCE / ANALYTICS")

        with nav_col:
            visible = [(route, label) for route, label in PRIMARY if route in routes]
            nav_columns = st.columns(len(visible), gap="small") if visible else []
            for column, (route, label) in zip(nav_columns, visible):
                with column:
                    st.button(
                        label,
                        key=f"top-nav-{route}",
                        type="primary" if page == route else "secondary",
                        use_container_width=True,
                        on_click=_go,
                        args=(route,),
                    )

        with tools_col:
            with st.popover("Tools", use_container_width=True):
                workspace_tools.tools_panel()

        with account_col:
            with st.popover(_account_button(mode), use_container_width=True):
                auth_ui.login_panel(compact=True)

        with utility_col:
            with st.popover("Workspace", use_container_width=True):
                st.caption("NAVIGATE")
                secondary = [route for route in routes if route not in {item[0] for item in PRIMARY}]
                for route in secondary:
                    label = {
                        "Bills & subscriptions": "Bills & subscriptions",
                        "Goals & debt": "Goals & debt",
                        "Data & settings": "Data & settings",
                        "Bank statements": "Bank statements",
                        "About FYNTRA": "About FYNTRA",
                    }.get(route, route)
                    st.button(
                        label,
                        key=f"menu-nav-{route}",
                        type="primary" if page == route else "secondary",
                        use_container_width=True,
                        on_click=_go,
                        args=(route,),
                    )

                st.divider()
                st.caption("REPORTING")
                st.date_input(
                    "Report date",
                    min_value=report_min,
                    max_value=report_max,
                    key="top_report_date",
                    on_change=on_report_change,
                    format="DD/MM/YYYY",
                    help="Inspect FYNTRA as it stood on this date.",
                )

                if imported:
                    st.caption("DATA VIEW")
                    st.segmented_control(
                        "Data view",
                        ["Main ledger", "Merged", "One statement"],
                        key="top_ledger_view",
                        on_change=on_ledger_change,
                        label_visibility="collapsed",
                    )
                    if st.session_state.get("ledger_view") == "statement":
                        statement_ids = list(imported)
                        st.selectbox(
                            "Imported statement",
                            statement_ids,
                            format_func=lambda value: imported[value],
                            key="top_statement_scope",
                            on_change=on_statement_change,
                        )

                st.divider()
                status = "Private cloud" if mode == "private" else "Demo workspace"
                st.caption(status.upper())
                if mode == "private":
                    name, email = auth_ui.account_identity()
                    st.write(f"**{name}**")
                    if email:
                        st.caption(email)
                else:
                    st.caption("Use the Account control in the top bar to sign in.")

    st.html(
        f'<div class="f-context-strip"><span>{page}</span><span>{report_date:%d %b %Y}</span>'
        f'<span>{"Private" if mode == "private" else "Demo"}</span></div>'
    )
