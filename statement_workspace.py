"""Lazy-loading router for the private bank-statement workspace."""
import streamlit as st

import statements
from ui import hero


def statement_page():
    statements._cloud()
    hero(
        "Understand a statement before building a budget.",
        "Upload a bank statement or screenshot, then save it for analysis or import it directly into an existing or new FYNTRA account.",
        "PRIVATE / BANK STATEMENTS",
    )
    st.caption(
        "Source files are processed in memory. Saved statements remain available for analysis and comparison even after you remove their ledger import."
    )

    options = ["Upload & analyze", "Saved statements", "Compare"]
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
        statements._saved_tab(statements._list_statements())
    elif view == "Compare":
        statements._compare_tab(statements._list_statements())
    else:
        statements._upload_tab()
