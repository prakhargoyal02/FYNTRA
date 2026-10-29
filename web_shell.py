"""Full-width FYNTRA application shell.

The visible navigation is intentionally separate from the hidden compatibility widgets
kept in app.py for Streamlit state/tests. Buttons only change navigation state.
"""
import streamlit as st

import auth_ui
from ui import brand

PRIMARY = [
    ("Overview", "Overview"),
    ("Transactions", "Transactions"),
    ("Budgets", "Budgets"),
    ("Cash flow & insights", "Insights"),
]


def _go(page):
    st.session_state.page_nav = page


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
    """Render a compact website-style top shell and utility menu."""
    with st.container(key="fyntra-site-header"):
        logo_col, nav_col, utility_col = st.columns([1.1, 3.9, .75], gap="medium", vertical_alignment="center")

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
                auth_ui.login_panel()

    st.html(
        f'<div class="f-context-strip"><span>{page}</span><span>{report_date:%d %b %Y}</span>'
        f'<span>{"Private" if mode == "private" else "Demo"}</span></div>'
    )
