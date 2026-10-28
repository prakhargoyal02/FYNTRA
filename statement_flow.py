"""Fast private statement workflow with lazy reads and safe ledger imports."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path
import time

import altair as alt
import pandas as pd
import streamlit as st

from database import ACCOUNT_TYPES, money
from statement_tools import clean_rows, extract_statement, rows_frame, summary
import statements


META_TTL_SECONDS = 30


def _cloud():
    return statements._cloud()


def _invalidate_statement_cache(statement_ids=None):
    if statement_ids is None:
        st.session_state.pop("statement_meta_cache", None)
        st.session_state.pop("statement_row_cache", None)
        return
    cache = st.session_state.get("statement_row_cache", {})
    for statement_id in statement_ids:
        cache.pop(statement_id, None)
    st.session_state.pop("statement_meta_cache", None)


def _statement_meta(force=False):
    cloud = _cloud()
    now = time.monotonic()
    cached = st.session_state.get("statement_meta_cache")
    if (
        not force
        and cached
        and cached.get("user_id") == cloud.user_id
        and now - cached.get("loaded_at", 0) < META_TTL_SECONDS
    ):
        return cached["rows"]
    result = (
        cloud.client.table("fyntra_statements")
        .select("id,name,source_filename,source_type,account_id,period_start,period_end,created_at,updated_at")
        .eq("user_id", cloud.user_id)
        .order("created_at", desc=True)
        .execute()
    )
    rows = result.data or []
    st.session_state.statement_meta_cache = {
        "user_id": cloud.user_id,
        "loaded_at": now,
        "rows": rows,
    }
    return rows


def _fetch_statement(meta):
    statement_id = meta["id"]
    updated_at = meta.get("updated_at")
    cache = st.session_state.setdefault("statement_row_cache", {})
    cached = cache.get(statement_id)
    if cached and cached.get("updated_at") == updated_at:
        return cached["row"]
    cloud = _cloud()
    result = (
        cloud.client.table("fyntra_statements")
        .select("id,name,source_filename,source_type,account_id,period_start,period_end,rows,created_at,updated_at")
        .eq("user_id", cloud.user_id)
        .eq("id", statement_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise ValueError("This saved statement no longer exists. Refresh the statement list.")
    row = result.data[0]
    cache[statement_id] = {"updated_at": row.get("updated_at"), "row": row}
    return row


def _fetch_many(meta_rows):
    return [_fetch_statement(meta) for meta in meta_rows]


def _labels(meta_rows):
    return {
        row["id"]: f'{row["name"]} · {row.get("period_start") or "?"} → {row.get("period_end") or "?"}'
        for row in meta_rows
    }


def _accounts_frame():
    return st.session_state.store.frame("accounts")


def _accounts_dict():
    frame = _accounts_frame()
    return {} if frame.empty else frame.set_index("id").name.to_dict()


def _pending_rows(statement):
    return [row for row in statement.get("rows") or [] if not str(row.get("transaction_id") or "")]


def _earliest_pending_date(selected):
    dates = [row.get("date") for statement in selected for row in _pending_rows(statement) if row.get("date")]
    return min(dates) if dates else None


def _suggest_opening_balance(selected):
    rows = [row for statement in selected for row in _pending_rows(statement) if row.get("date")]
    if not rows:
        return 0.0
    row = min(rows, key=lambda item: (str(item.get("date")), str(item.get("row_key") or "")))
    try:
        balance = float(row.get("balance"))
        amount = float(row.get("amount"))
    except (TypeError, ValueError):
        return 0.0
    if pd.isna(balance) or pd.isna(amount):
        return 0.0
    if row.get("kind") == "income":
        return round(balance - amount, 2)
    if row.get("kind") == "expense":
        return round(balance + amount, 2)
    return round(balance, 2)


def _adjust_account_opening_date(account_id, earliest_date):
    if not account_id or not earliest_date:
        return False
    store = st.session_state.store
    account = store.get("accounts", account_id)
    if not account or str(account.get("opening_date")) <= earliest_date:
        return False
    updated = dict(account)
    updated["opening_date"] = earliest_date
    store.save("accounts", updated)
    return True


def _selected_for_import(meta_rows, current_id, scope, chosen_ids):
    if scope == "This statement":
        ids = [current_id]
    elif scope == "Selected statements":
        ids = list(chosen_ids or [])
    else:
        ids = [row["id"] for row in meta_rows]
    lookup = {row["id"]: row for row in meta_rows}
    return [lookup[statement_id] for statement_id in ids if statement_id in lookup]


def _import_destination(selected, key_prefix, accounts):
    earliest = _earliest_pending_date(selected)
    destination = st.radio(
        "Destination",
        ["Existing account", "Create new account"],
        horizontal=True,
        key=key_prefix + "-destination",
    )
    if destination == "Existing account":
        if not accounts:
            st.info("No account exists yet. Choose Create new account and FYNTRA will build one from the statement.")
            return None, None, False
        account_id = st.selectbox(
            "Import into account",
            list(accounts),
            format_func=accounts.get,
            key=key_prefix + "-existing-account",
        )
        account = st.session_state.store.get("accounts", account_id)
        needs_history_extension = bool(
            earliest and account and str(account.get("opening_date")) > earliest
        )
        adjust = False
        if needs_history_extension:
            st.warning(
                f'This statement starts on **{earliest}**, before **{accounts[account_id]}** currently opens on '
                f'**{account["opening_date"]}**. A historical statement can only be imported after the account history is extended.'
            )
            adjust = st.checkbox(
                f"Extend this account's opening date back to {earliest} during import",
                value=True,
                key=key_prefix + "-extend-history",
                help="The opening balance amount is kept unchanged; only its effective start date moves earlier.",
            )
        return account_id, None, needs_history_extension and not adjust

    opening_date = date.fromisoformat(earliest) if earliest else date.today()
    suggested = _suggest_opening_balance(selected)
    first_name = selected[0]["name"] if selected else "Imported bank"
    new_name = st.text_input(
        "New account name",
        value=f"{first_name} account",
        key=key_prefix + "-new-name",
    )
    account_type = st.selectbox(
        "Account type",
        ACCOUNT_TYPES,
        index=0,
        key=key_prefix + "-new-type",
    )
    opening_balance = st.number_input(
        "Opening balance (₹)",
        value=float(suggested),
        step=100.0,
        key=key_prefix + "-new-balance",
        help="FYNTRA estimates this from the earliest running balance when the statement provides one. You can edit it before import.",
    )
    opening_on = st.date_input(
        "Opening date",
        value=opening_date,
        key=key_prefix + "-new-date",
    )
    new_account = dict(
        name=new_name.strip(),
        account_type=account_type,
        opening_balance=opening_balance,
        opening_date=opening_on,
    )
    return None, new_account, False


def _perform_import(selected, account_id=None, new_account=None):
    if not selected:
        raise ValueError("Choose at least one statement to import.")
    earliest = _earliest_pending_date(selected)
    created_account_id = None
    if new_account is not None:
        if not new_account["name"]:
            raise ValueError("Enter a name for the new account.")
        created_account_id = statements._create_account(
            new_account["name"],
            new_account["account_type"],
            new_account["opening_balance"],
            new_account["opening_date"],
            selected[0]["name"],
        )
        account_id = created_account_id
    elif account_id:
        _adjust_account_opening_date(account_id, earliest)
    if not account_id:
        raise ValueError("Choose or create an account for this import.")
    try:
        count = statements._import_selected(selected, account_id)
    except Exception:
        if created_account_id:
            statements._maybe_delete_empty_auto_account(created_account_id)
        raise
    _invalidate_statement_cache([row["id"] for row in selected])
    return count, account_id


def upload_view():
    st.subheader("Upload statements or screenshots")
    st.caption(
        "Analyze a statement first, then save it only, merge it into an existing account, or let the statement create a new FYNTRA account."
    )
    files = st.file_uploader(
        "Bank statement files",
        type=["csv", "xlsx", "pdf", "txt", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        key="statement-fast-upload",
        help="CSV/XLSX is usually fastest and cleanest. PDF and screenshots are supported but OCR takes longer.",
    )
    if not files:
        st.info("Upload a bank CSV/XLSX for the fastest result, or use a PDF/screenshot when that is all you have.")
        return
    accounts = _accounts_dict()
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
            name = st.text_input("Statement name", value=default_name, key="flow-name-" + digest)
            edited = statements._editor(item["frame"], "flow-editor-" + digest)
            try:
                reviewed = clean_rows(edited)
                statements._statement_metrics(reviewed)
                statements._expense_breakdown(reviewed, "flow-" + digest[:12])
                low = sum(int(row.get("confidence", 100)) < 70 for row in reviewed)
                if low:
                    st.warning(f"{low} row(s) have low read confidence. Review their date, amount and direction first.")
                action = st.radio(
                    "After review",
                    ["Save for analysis only", "Import into existing account", "Create account from statement + import"],
                    key="flow-action-" + digest,
                )
                account_id = None
                new_account = None
                blocked = False
                preview_statement = {
                    "id": "preview",
                    "name": name.strip() or default_name,
                    "rows": reviewed,
                }
                if action == "Import into existing account":
                    if accounts:
                        account_id, new_account, blocked = _import_destination(
                            [preview_statement], "flow-dest-" + digest, accounts
                        )
                    else:
                        st.info("You do not have an account yet. Choose Create account from statement + import instead.")
                        blocked = True
                elif action == "Create account from statement + import":
                    _, new_account, blocked = _import_destination(
                        [preview_statement], "flow-new-" + digest, {}
                    )

                label = "Save statement" if action == "Save for analysis only" else "Save and import into FYNTRA"
                if st.button(label, type="primary", disabled=blocked, key="flow-save-" + digest):
                    if not name.strip():
                        st.error("Enter a statement name.")
                    else:
                        statement_id = statements._insert_statement(
                            name, uploaded.name, item["source_type"], None, reviewed
                        )
                        if action == "Save for analysis only":
                            preview_cache.pop(cache_key, None)
                            _invalidate_statement_cache()
                            st.session_state.notice = "Statement saved for analysis"
                            st.rerun()
                        saved = {
                            "id": statement_id,
                            "name": name.strip(),
                            "source_filename": uploaded.name,
                            "source_type": item["source_type"],
                            "account_id": None,
                            "rows": reviewed,
                        }
                        try:
                            count, _ = _perform_import([saved], account_id=account_id, new_account=new_account)
                        except Exception as exc:
                            st.error(f"Statement was saved, but import needs attention: {exc}")
                        else:
                            preview_cache.pop(cache_key, None)
                            _invalidate_statement_cache()
                            st.session_state.notice = f"Statement saved and {count} row(s) imported into FYNTRA"
                            st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _import_panel(meta_rows, current_id):
    labels = _labels(meta_rows)
    scope = st.radio(
        "Statements to import",
        ["This statement", "Selected statements", "All saved statements"],
        horizontal=True,
        key="flow-import-scope-" + current_id,
    )
    chosen_ids = []
    if scope == "Selected statements":
        chosen_ids = st.multiselect(
            "Choose statements",
            list(labels),
            default=[current_id],
            format_func=labels.get,
            key="flow-import-selected-" + current_id,
        )
    selected_meta = _selected_for_import(meta_rows, current_id, scope, chosen_ids)
    if not selected_meta:
        st.info("Choose at least one statement.")
        return
    selected = _fetch_many(selected_meta)
    pending = sum(len(_pending_rows(statement)) for statement in selected)
    st.caption(f"{len(selected)} statement(s) selected · {pending} row(s) available to import.")
    if pending <= 0:
        st.info("Every selected row is already imported into FYNTRA.")
        return
    accounts = _accounts_dict()
    account_id, new_account, blocked = _import_destination(
        selected, "flow-import-" + current_id, accounts
    )
    if st.button(
        "Import selected statements into FYNTRA",
        type="primary",
        disabled=blocked,
        key="flow-import-button-" + current_id,
    ):
        try:
            count, _ = _perform_import(selected, account_id=account_id, new_account=new_account)
            st.session_state.notice = f"{count} statement row(s) imported into FYNTRA"
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def saved_view():
    st.subheader("Saved statements")
    meta_rows = _statement_meta()
    if not meta_rows:
        st.info("No saved statements yet. Upload one in Upload & analyze.")
        return
    labels = _labels(meta_rows)
    selected_id = st.selectbox(
        "Statement",
        list(labels),
        format_func=labels.get,
        key="flow-saved-statement",
    )
    meta = next(row for row in meta_rows if row["id"] == selected_id)
    statement = _fetch_statement(meta)
    rows = statement.get("rows") or []
    accounts = _accounts_dict()
    account_name = accounts.get(statement.get("account_id")) if statement.get("account_id") else None
    st.caption(
        f'{statement["source_filename"]} · {statement["source_type"].upper()} · '
        f'{account_name or "Saved for analysis · not imported"}'
    )
    statements._statement_metrics(rows)
    statements._expense_breakdown(rows, "saved-" + selected_id[:12])
    imported_count = statements._imported_count(rows)
    if imported_count:
        st.success(f"{imported_count} row(s) are currently imported into FYNTRA.")
        shown = rows_frame(rows).drop(columns=["include", "transaction_id"], errors="ignore")
        st.dataframe(shown, hide_index=True, width="stretch")
    else:
        edited = statements._editor(rows_frame(rows), "flow-saved-editor-" + selected_id)
        if st.button("Save statement corrections", key="flow-save-corrections-" + selected_id):
            try:
                reviewed = clean_rows(edited)
                dates = sorted(row["date"] for row in reviewed)
                statements._update_statement(
                    selected_id,
                    rows=reviewed,
                    period_start=dates[0],
                    period_end=dates[-1],
                )
                _invalidate_statement_cache([selected_id])
                st.session_state.notice = "Statement corrections saved"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.divider()
    st.subheader("Import into FYNTRA")
    st.caption("Merge one or several saved statements into an existing account, or create a new account directly from them.")
    _import_panel(meta_rows, selected_id)


def compare_view():
    st.subheader("Compare statements")
    meta_rows = _statement_meta()
    if len(meta_rows) < 2:
        st.info("Save at least two statements to compare them.")
        return
    labels = _labels(meta_rows)
    chosen = st.multiselect(
        "Statements to compare",
        list(labels),
        format_func=labels.get,
        key="flow-compare-selected",
    )
    if len(chosen) < 2:
        st.info("Choose two or more statements.")
        return
    selected_meta = [row for row in meta_rows if row["id"] in chosen]
    selected = _fetch_many(selected_meta)
    summaries = []
    detail_frames = []
    for item in selected:
        full_name = labels[item["id"]]
        info = summary(item.get("rows") or [])
        summaries.append({
            "statement": full_name,
            "transactions": info["count"],
            "income": info["income"],
            "expenses": info["expenses"],
            "net": info["net"],
            "from_date": info["start"],
            "to_date": info["end"],
        })
        frame = rows_frame(item.get("rows") or [])
        if not frame.empty:
            frame["statement"] = full_name
            detail_frames.append(frame)
    st.dataframe(pd.DataFrame(summaries), hide_index=True, width="stretch")
    if not detail_frames:
        return
    combined = pd.concat(detail_frames, ignore_index=True)
    combined["amount"] = pd.to_numeric(combined.amount, errors="coerce").fillna(0.0)
    combined["date"] = pd.to_datetime(combined.date, errors="coerce")
    legend = alt.Legend(orient="bottom", title=None, labelLimit=0, columns=1)
    st.subheader("Spending by category")
    category = (
        combined.loc[combined.kind.eq("expense")]
        .groupby(["statement", "category"], as_index=False)
        .amount.sum()
    )
    if not category.empty:
        plot = alt.Chart(category).mark_bar().encode(
            x=alt.X("category:N", title=None),
            y=alt.Y("amount:Q", title="₹"),
            color=alt.Color("statement:N", legend=legend),
            xOffset="statement:N",
            tooltip=["statement", "category", alt.Tooltip("amount:Q", format=",.2f")],
        ).properties(height=280)
        st.altair_chart(plot, width="stretch")
    st.subheader("Daily net flow")
    daily = combined.assign(
        signed=combined.amount.where(combined.kind.eq("income"), -combined.amount)
    )
    daily = daily.groupby(["statement", "date"], as_index=False).signed.sum().dropna()
    if not daily.empty:
        plot = alt.Chart(daily).mark_line(point=True).encode(
            x=alt.X("date:T", title=None),
            y=alt.Y("signed:Q", title="Net ₹"),
            color=alt.Color("statement:N", legend=legend),
            tooltip=["statement", alt.Tooltip("date:T"), alt.Tooltip("signed:Q", format=",.2f")],
        ).properties(height=260)
        st.altair_chart(plot, width="stretch")
    st.subheader("All selected rows")
    shown = combined[[
        "statement", "date", "description", "kind", "category", "amount", "balance", "reference"
    ]].sort_values(["date", "statement"])
    st.dataframe(shown, hide_index=True, width="stretch")


def _batch_remove(selected, delete_completely=False):
    store = st.session_state.store
    total = 0
    account_ids = {statement.get("account_id") for statement in selected if statement.get("account_id")}
    with store.connect() as con, con:
        for statement in selected:
            prefix = f'statement:{statement["id"]}:%'
            found = con.execute(
                "SELECT id FROM transactions WHERE source_key LIKE ?", (prefix,)
            ).fetchall()
            if found:
                total += len(found)
                con.execute("DELETE FROM transactions WHERE source_key LIKE ?", (prefix,))
    if total:
        store.revision += 1

    if delete_completely:
        for statement in selected:
            statements._delete_statement(statement["id"])
        for account_id in account_ids:
            statements._maybe_delete_empty_auto_account(account_id)
    else:
        for statement in selected:
            cleaned = [dict(row, transaction_id="") for row in statement.get("rows") or []]
            statements._update_statement(statement["id"], rows=cleaned, account_id=None)

    if total or delete_completely:
        statements._sync_store()
    _invalidate_statement_cache([statement["id"] for statement in selected])
    return total


def manage_view():
    st.subheader("Manage statement data")
    st.caption(
        "Select one or several statements. Remove import only keeps the saved statement for analysis/Compare. Delete completely removes the saved statement too."
    )
    meta_rows = _statement_meta()
    if not meta_rows:
        st.info("No saved statements to manage.")
        return
    labels = _labels(meta_rows)
    chosen = st.multiselect(
        "Statements",
        list(labels),
        format_func=labels.get,
        key="flow-manage-selected",
    )
    action = st.radio(
        "Action",
        ["Remove import only", "Delete completely"],
        horizontal=True,
        key="flow-manage-action",
    )
    if not chosen:
        st.info("Choose one or more statements first.")
        return
    selected_meta = [row for row in meta_rows if row["id"] in chosen]
    imported_count = 0
    for meta in selected_meta:
        account_id = meta.get("account_id")
        if account_id:
            imported_count += 1
    st.caption(
        f"{len(selected_meta)} statement(s) selected · {imported_count} currently linked to a FYNTRA account."
    )
    if action == "Remove import only":
        st.info("This removes only transactions imported from the selected statements. The statements stay saved and remain available in Compare.")
        confirm_label = "I understand and want to remove these statement imports"
        button_label = "Remove selected imports"
    else:
        st.warning("This removes imported transactions and deletes the selected saved statements. Unrelated account/manual/CSV data is not touched.")
        confirm_label = "I understand and want to delete the selected statements completely"
        button_label = "Delete selected statements completely"
    confirmed = st.checkbox(confirm_label, key="flow-manage-confirm")
    if st.button(
        button_label,
        type="primary" if action == "Remove import only" else "secondary",
        disabled=not confirmed,
        key="flow-manage-button",
    ):
        try:
            selected = _fetch_many(selected_meta)
            removed = _batch_remove(selected, delete_completely=action == "Delete completely")
            st.session_state.notice = (
                f"Removed {removed} imported transaction(s); saved statements kept"
                if action == "Remove import only"
                else f"Deleted {len(selected)} statement(s) and removed {removed} imported transaction(s)"
            )
            st.session_state.flow_manage_selected = []
            st.session_state.flow_manage_confirm = False
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
