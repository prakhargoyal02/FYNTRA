"""Lazy-loading router for the private bank-statement workspace."""
import streamlit as st

from ui import hero
import statement_flow


def statement_page():
    statement_flow._cloud()
    hero(
        "Understand a statement before building a budget.",
        "Upload a bank statement or screenshot, then save it for analysis or import it directly into an existing or new FYNTRA account.",
        "PRIVATE / BANK STATEMENTS",
    )
    st.caption(
        "Source files are processed in memory. Saved statements remain available for analysis and comparison even after you remove their ledger import."
    )

    options = ["Upload & analyze", "Saved statements", "Compare", "Manage"]
    current = st.session_state.get("statement_workspace_view")
    if current not in options:
        st.session_state.statement_workspace_view = options[0]
    view = st.segmented_control(
        "Statement workspace",
        options,
        key="statement_workspace_view",
        label_visibility="collapsed",
    )

    if view == "Saved statements":
        statement_flow.saved_view()
    elif view == "Compare":
        statement_flow.compare_view()
    elif view == "Manage":
        statement_flow.manage_view()
    else:
        statement_flow.upload_view()
