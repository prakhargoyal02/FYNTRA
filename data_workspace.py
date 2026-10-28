"""Unified data workspace for backups and bank-statement analysis."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import statements
import views
from csv_tools import export_bundle, export_table, import_csvs, parse_files
from database import CATEGORIES, TABLES, money
from statement_tools import clean_rows, extract_statement, summary
from ui import GOLD, MINT, hero, metrics, rupees


SUPPORTED_UPLOADS = ["csv", "xlsx", "pdf", "txt", "png", "jpg", "jpeg", "webp"]


def classify_file(store, filename, data):
    """Identify a FYNTRA CSV or parse a bank statement without changing user data."""
    suffix = Path(filename).suffix.casefold()
    if suffix == ".csv":
        try:
            parsed = parse_files(store, [(filename, data)])
            return {"kind": "fyntra", "parsed": parsed}
        except Exception as backup_exc:
            message = str(backup_exc)
            # These errors mean the CSV structure itself was recognized as FYNTRA data.
            if "Unknown account name" in message or "Unknown record type" in message:
                return {"kind": "fyntra_error", "error": message}
            try:
                frame, source_type, note = extract_statement(filename, data)
                return {"kind": "statement", "frame": frame, "source_type": source_type, "note": note}
            except Exception as statement_exc:
                return {
                    "kind": "unknown",
                    "error": (
                        "FYNTRA could not identify this CSV as either a backup/template or a bank statement. "
                        f"Backup reader: {message} Statement reader: {statement_exc}"
                    ),
                }
    try:
        frame, source_type, note = extract_statement(filename, data)
        return {"kind": "statement", "frame": frame, "source_type": source_type, "note": note}
    except Exception as exc:
        return {"kind": "unknown", "error": str(exc)}


def _statement_editor(frame, key):
    return st.data_editor(
        frame,
        key=key,
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        column_config={
            "include": st.column_config.CheckboxColumn("Keep"),
            "date": st.column_config.TextColumn("Date", help="YYYY-MM-DD"),
            "description": st.column_config.TextColumn("Description", width="large"),
            "amount": st.column_config.NumberColumn("Amount ₹", min_value=0.01, format="%.2f"),
            "kind": st.column_config.SelectboxColumn("Direction", options=["expense", "income"], required=True),
            "category": st.column_config.SelectboxColumn("Category", options=CATEGORIES, required=True),
            "payment_method": st.column_config.SelectboxColumn(
                "Method", options=["UPI", "Card", "Cash", "Bank transfer", "Other"]
            ),
            "balance": st.column_config.NumberColumn("Balance ₹", format="%.2f"),
            "reference": st.column_config.TextColumn("Reference"),
            "confidence": st.column_config.ProgressColumn(
                "Read confidence", min_value=0, max_value=100, format="%d%%"
            ),
            "transaction_id": None,
        },
        disabled=["confidence", "transaction_id"],
    )


def _statement_analysis(rows):
    info = summary(rows)
    metrics([
        ("Transactions", str(info["count"]), f'{info["start"] or "—"} to {info["end"] or "—"}'),
        ("Money in", rupees(info["income"]), "Credits detected."),
        ("Money out", rupees(info["expenses"]), "Debits detected."),
        ("Net flow", rupees(info["net"]), "Money in minus money out."),
    ])

    frame = pd.DataFrame(rows)
    if frame.empty:
        return
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce").fillna(0.0)
    expenses = frame.loc[frame["kind"].eq("expense")].copy()
    left, right = st.columns(2)
    with left:
        st.markdown("**Spending by category**")
        category = expenses.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
        if category.empty:
            st.caption("No expenses detected.")
        else:
            plot = alt.Chart(category).mark_bar().encode(
                x=alt.X("amount:Q", title="₹"),
                y=alt.Y("category:N", sort="-x", title=None),
                tooltip=["category", alt.Tooltip("amount:Q", format=",.2f")],
                color=alt.value(MINT),
            ).properties(height=250)
            st.altair_chart(plot, width="stretch")
    with right:
        st.markdown("**Largest expenses**")
        largest = expenses.nlargest(7, "amount")[["date", "description", "category", "amount"]]
        if largest.empty:
            st.caption("No expenses detected.")
        else:
            st.dataframe(largest, hide_index=True, width="stretch")

    merchant = (
        expenses.groupby("description", as_index=False)["amount"].sum()
        .sort_values("amount", ascending=False)
        .head(8)
    )
    if not merchant.empty:
        st.markdown("**Top merchants / descriptions**")
        st.dataframe(merchant, hide_index=True, width="stretch")


def _render_statement(uploaded, result, digest):
    st.success("Detected: bank statement / transaction history")
    st.caption(result["note"] + " No FYNTRA account is required to analyze this file.")
    edited = _statement_editor(result["frame"], "unified-statement-editor-" + digest)
    try:
        reviewed = clean_rows(edited)
    except Exception as exc:
        st.error(str(exc))
        return None

    _statement_analysis(reviewed)
    low = sum(int(row.get("confidence", 100)) < 70 for row in reviewed)
    if low:
        st.warning(f"{low} row(s) have low read confidence. Check date, amount and direction before saving.")

    cloud = st.session_state.get("cloud")
    if cloud and cloud.user_id:
        default_name = Path(uploaded.name).stem.replace("_", " ").replace("-", " ").strip().title()
        name = st.text_input(
            "Statement name",
            value=default_name or "Bank statement",
            key="unified-statement-name-" + digest,
        )
        if st.button("Save this analysis privately", key="unified-save-statement-" + digest):
            if not name.strip():
                st.error("Enter a statement name.")
            else:
                statements._insert_statement(
                    name.strip(), uploaded.name, result["source_type"], None, reviewed
                )
                st.session_state.notice = "Statement saved privately"
                st.rerun()
    else:
        st.caption("Analysis is temporary in demo mode. Private sign in lets you save statements for later comparison.")
    return reviewed


def _render_fyntra_file(uploaded, result, digest):
    st.success("Detected: FYNTRA backup / import file")
    st.write({table: len(rows) for table, rows in result["parsed"].items()})
    mode = st.radio(
        "Import mode",
        ["Add safely", "Replace matching types"],
        horizontal=True,
        key="unified-import-mode-" + digest,
    )
    confirm = True
    if mode == "Replace matching types":
        confirm = st.checkbox(
            "I exported a backup and want to replace the included record types",
            key="unified-import-confirm-" + digest,
        )
    if st.button(
        "Import validated FYNTRA data",
        disabled=not confirm,
        type="primary",
        key="unified-import-button-" + digest,
    ):
        data = uploaded.getvalue()
        views.commit_action(
            lambda: import_csvs(
                views.current(),
                [(uploaded.name, data)],
                "add" if mode == "Add safely" else "replace",
            ),
            "Data import complete",
        )


def _upload_workspace():
    st.subheader("Upload any finance file")
    st.caption(
        "Drop a FYNTRA backup or a bank statement here. FYNTRA auto-detects the file instead of making you choose a separate importer. "
        "Bank-statement analysis does not require an account."
    )
    files = st.file_uploader(
        "CSV, XLSX, PDF, TXT, or statement screenshot",
        type=SUPPORTED_UPLOADS,
        accept_multiple_files=True,
        help="Supported statement images: PNG, JPG, JPEG and WEBP. CSV can also be a FYNTRA backup/template.",
        key="unified-finance-upload",
    )
    if not files:
        st.info("You can upload a bank export, a statement PDF, a screenshot, or a FYNTRA backup CSV.")
        return

    cache = st.session_state.setdefault("unified_file_cache", {})
    comparisons = []
    for uploaded in files:
        data = uploaded.getvalue()
        digest = sha256(data).hexdigest()
        cache_key = f"{uploaded.name}:{digest}"
        if cache_key not in cache:
            with st.spinner(f"Reading {uploaded.name}…"):
                cache[cache_key] = classify_file(views.current(), uploaded.name, data)
        result = cache[cache_key]
        with st.expander(uploaded.name, expanded=True):
            if result["kind"] == "fyntra":
                _render_fyntra_file(uploaded, result, digest)
            elif result["kind"] == "fyntra_error":
                st.error(result["error"])
            elif result["kind"] == "statement":
                reviewed = _render_statement(uploaded, result, digest)
                if reviewed:
                    info = summary(reviewed)
                    comparisons.append({
                        "file": uploaded.name,
                        "transactions": info["count"],
                        "money_in": info["income"],
                        "money_out": info["expenses"],
                        "net": info["net"],
                        "from": info["start"],
                        "to": info["end"],
                    })
            else:
                st.error(result["error"])

    if len(comparisons) >= 2:
        st.subheader("Quick comparison of uploaded statements")
        st.caption("This comparison is temporary. Saving statements privately keeps them available in the dedicated Compare tab.")
        st.dataframe(pd.DataFrame(comparisons), hide_index=True, width="stretch")


def data_page():
    hero(
        "Your data. Your control.",
        "One upload area for bank statements, screenshots and FYNTRA backups.",
        "DATA & SETTINGS",
    )
    profile = views.current().get("profile", "profile")
    with st.form("settings"):
        name = st.text_input("Display name", profile["display_name"])
        limit = st.number_input(
            "Total monthly spending limit (₹)",
            min_value=0.0,
            value=profile["monthly_limit_paise"] / 100,
            help="Zero uses the sum of this month's category budgets.",
        )
        st.caption("Currency: INR. Other currencies are planned; v1 never mixes currencies or converts rates.")
        submitted = st.form_submit_button("Save preferences")
    if submitted:
        views.save(
            "profile",
            profile,
            dict(display_name=name, monthly_limit_paise=money(limit)),
        )

    st.subheader("Export a backup")
    st.download_button(
        "Download full FYNTRA Bundle",
        export_bundle(views.current()),
        "fyntra_bundle.csv",
        "text/csv",
        type="primary",
    )
    choice = st.selectbox("Individual record type", TABLES)
    st.download_button(
        "Download selected CSV",
        export_table(views.current(), choice),
        choice + ".csv",
        "text/csv",
    )

    _upload_workspace()

    with st.expander("FYNTRA simple transaction template"):
        st.download_button(
            "Download template",
            "date,amount,kind,category,account_name,merchant,notes,tags\n",
            "transaction_template.csv",
            "text/csv",
        )
        st.caption("This template is for direct ledger import. Bank statements do not need to follow this template.")

    cloud = st.session_state.get("cloud")
    if cloud:
        st.subheader("Cloud sync")
        st.caption("Concurrent edits are detected before overwriting another session. Export this session before reloading cloud data.")
        if st.button("Retry sync"):
            views.commit_action(lambda: None, "Cloud sync attempted")
        if st.checkbox("I exported local changes and want to reload the cloud copy"):
            if st.button("Reload cloud copy"):
                try:
                    cloud.pull(views.current())
                    st.session_state.pop("sync_error", None)
                    st.rerun()
                except Exception:
                    st.error("Cloud reload failed. Your local copy remains available.")
    else:
        st.subheader("Reset fictional demo")
        if st.checkbox("Replace this session's demo edits with fresh fictional data"):
            if st.button("Reset demo"):
                directory = st.session_state.pop("demo_directory", None)
                st.session_state.pop("store", None)
                if directory:
                    directory.cleanup()
                st.rerun()

    st.caption(
        "Demo sessions are temporary. Private sessions can save analyzed statements and use ownership-protected cloud sync."
    )
