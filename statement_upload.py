"""Upload/review flow for bank statements without duplicate destination controls."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path

import streamlit as st

from database import ACCOUNT_TYPES
from statement_tools import clean_rows, extract_statement
import statement_flow
import statements


def _existing_account_fields(reviewed, digest, accounts):
    if not accounts:
        st.info("You do not have an account yet. Choose Create account from statement + import instead.")
        return None, True
    account_id = st.selectbox(
        "Import into account",
        list(accounts),
        format_func=accounts.get,
        key="upload-existing-account-" + digest,
    )
    earliest = min(row["date"] for row in reviewed)
    account = st.session_state.store.get("accounts", account_id)
    blocked = False
    if account and str(account.get("opening_date")) > earliest:
        st.warning(
            f'This statement starts on **{earliest}**, while **{accounts[account_id]}** currently opens on '
            f'**{account["opening_date"]}**.'
        )
        adjust = st.checkbox(
            f"Extend this account's opening date back to {earliest} during import",
            value=True,
            key="upload-extend-history-" + digest,
            help="FYNTRA keeps the opening balance amount unchanged and moves only its effective start date earlier.",
        )
        blocked = not adjust
    return account_id, blocked


def _new_account_fields(reviewed, digest, statement_name):
    preview = {"id": "preview", "name": statement_name, "rows": reviewed}
    earliest = statement_flow._earliest_pending_date([preview])
    suggested = statement_flow._suggest_opening_balance([preview])
    opening_date = date.fromisoformat(earliest) if earliest else date.today()
    name = st.text_input(
        "New account name",
        value=f"{statement_name} account",
        key="upload-new-account-name-" + digest,
    )
    account_type = st.selectbox(
        "Account type",
        ACCOUNT_TYPES,
        index=0,
        key="upload-new-account-type-" + digest,
    )
    opening_balance = st.number_input(
        "Opening balance (₹)",
        value=float(suggested),
        step=100.0,
        key="upload-new-account-balance-" + digest,
        help="Estimated from the earliest running balance when available. You can edit it before import.",
    )
    opening_on = st.date_input(
        "Opening date",
        value=opening_date,
        key="upload-new-account-date-" + digest,
    )
    return dict(
        name=name.strip(),
        account_type=account_type,
        opening_balance=opening_balance,
        opening_date=opening_on,
    )


def upload_view():
    st.subheader("Upload statements or screenshots")
    st.caption(
        "Analyze a statement first, then save it only, merge it into an existing account, or let the statement create a new FYNTRA account."
    )
    files = st.file_uploader(
        "Bank statement files",
        type=["csv", "xlsx", "pdf", "txt", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="statement-fast-upload-v2",
        help="CSV/XLSX is usually fastest and cleanest. PDF and screenshots are supported but OCR takes longer.",
    )
    if not files:
        st.info("Upload a bank CSV/XLSX for the fastest result, or use a PDF/screenshot when that is all you have.")
        return

    accounts = statement_flow._accounts_dict()
    preview_cache = st.session_state.setdefault("statement_previews", {})
    for uploaded in files:
        data = uploaded.getvalue()
        digest = sha256(data).hexdigest()
        cache_key = f"{uploaded.name}:{digest}"
        if cache_key not in preview_cache:
            with st.spinner(f"Reading {uploaded.name}…"):
                try:
                    frame, source_type, note = extract_statement(uploaded.name, data)
                    preview_cache[cache_key] = {
                        "frame": frame,
                        "source_type": source_type,
                        "note": note,
                        "error": None,
                    }
                except Exception as exc:
                    preview_cache[cache_key] = {
                        "frame": None,
                        "source_type": Path(uploaded.name).suffix.lstrip(".") or "text",
                        "note": "",
                        "error": str(exc),
                    }
        item = preview_cache[cache_key]
        with st.expander(uploaded.name, expanded=True):
            if item["error"]:
                st.error(item["error"])
                continue
            st.caption(item["note"])
            default_name = Path(uploaded.name).stem.replace("_", " ").replace("-", " ").strip().title() or "Bank statement"
            statement_name = st.text_input(
                "Statement name",
                value=default_name,
                key="upload-statement-name-" + digest,
            )
            edited = statements._editor(item["frame"], "upload-editor-" + digest)
            try:
                reviewed = clean_rows(edited)
                statements._statement_metrics(reviewed)
                statements._expense_breakdown(reviewed, "upload-" + digest[:12])
                low = sum(int(row.get("confidence", 100)) < 70 for row in reviewed)
                if low:
                    st.warning(f"{low} row(s) have low read confidence. Review their date, amount and direction first.")

                action = st.radio(
                    "After review",
                    ["Save for analysis only", "Import into existing account", "Create account from statement + import"],
                    key="upload-action-" + digest,
                )
                account_id = None
                new_account = None
                blocked = False
                if action == "Import into existing account":
                    account_id, blocked = _existing_account_fields(reviewed, digest, accounts)
                elif action == "Create account from statement + import":
                    new_account = _new_account_fields(
                        reviewed,
                        digest,
                        statement_name.strip() or default_name,
                    )
                    blocked = not new_account["name"]

                button_label = "Save statement" if action == "Save for analysis only" else "Save and import into FYNTRA"
                if st.button(
                    button_label,
                    type="primary",
                    disabled=blocked,
                    key="upload-save-" + digest,
                ):
                    if not statement_name.strip():
                        st.error("Enter a statement name.")
                        continue
                    statement_id = statements._insert_statement(
                        statement_name,
                        uploaded.name,
                        item["source_type"],
                        None,
                        reviewed,
                    )
                    if action == "Save for analysis only":
                        preview_cache.pop(cache_key, None)
                        statement_flow._invalidate_statement_cache()
                        st.session_state.notice = "Statement saved for analysis"
                        st.rerun()

                    saved = {
                        "id": statement_id,
                        "name": statement_name.strip(),
                        "source_filename": uploaded.name,
                        "source_type": item["source_type"],
                        "account_id": None,
                        "rows": reviewed,
                    }
                    try:
                        count, _ = statement_flow._perform_import(
                            [saved],
                            account_id=account_id,
                            new_account=new_account,
                        )
                    except Exception as exc:
                        st.error(f"Statement was saved, but import needs attention: {exc}")
                    else:
                        preview_cache.pop(cache_key, None)
                        statement_flow._invalidate_statement_cache()
                        st.session_state.notice = f"Statement saved and {count} row(s) imported into FYNTRA"
                        st.rerun()
            except Exception as exc:
                st.error(str(exc))
