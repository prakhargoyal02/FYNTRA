"""Lazy-loading router for the private bank-statement workspace."""
import streamlit as st

import statements
from ui import hero


def _has_exports():
    """Check only for export existence; never download export row payloads here."""
    cloud = statements._cloud()
    result = (cloud.client.table("fyntra_statement_exports")
              .select("id").eq("user_id",cloud.user_id).limit(1).execute())
    return bool(result.data)


def statement_page():
    statements._cloud()
    hero(
        "Understand a statement before building a budget.",
        "Upload a bank statement or screenshot to classify spending immediately. Save it separately, compare it, export it, or explicitly add reviewed rows to your FYNTRA ledger.",
        "PRIVATE / BANK STATEMENTS",
    )
    st.caption(
        "Source files are processed in memory. FYNTRA stores reviewed statement rows and metadata only when you explicitly save a statement."
    )

    options = ["Upload & analyze", "Saved statements", "Compare"]
    if _has_exports():
        options.append("Exports")

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
    elif view == "Exports":
        statements._exports_tab(statements._list_exports())
    else:
        statements._upload_tab()
