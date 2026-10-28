"""Private bank-statement workspace: analyze, save, compare and import into FYNTRA."""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import altair as alt
import pandas as pd
import streamlit as st

from database import ACCOUNT_TYPES, CATEGORIES, money
from statement_tools import clean_rows, extract_statement, import_rows, rows_frame, summary
from ui import metrics, rupees

AUTO_ACCOUNT_PREFIXES = (
    "Created from bank statement import:",
    "Created while importing bank statement:",
)


def _cloud():
    cloud = st.session_state.get("cloud")
    if not cloud or not cloud.user_id:
        st.info("Bank statements are available only inside Private sign in.")
        st.stop()
    return cloud


def _accounts():
    frame = st.session_state.store.frame("accounts")
    return {} if frame.empty else frame.set_index("id").name.to_dict()


def _list_statements():
    cloud = _cloud()
    result = (cloud.client.table("fyntra_statements")
              .select("id,name,source_filename,source_type,account_id,period_start,period_end,rows,created_at,updated_at")
              .eq("user_id",cloud.user_id).order("created_at",desc=True).execute())
    return result.data or []


def _insert_statement(name, source_filename, source_type, account_id, rows):
    cloud = _cloud()
    statement_id = str(uuid4())
    dates = sorted(row["date"] for row in rows)
    payload = dict(
        id=statement_id,
        user_id=cloud.user_id,
        name=name.strip(),
        source_filename=source_filename,
        source_type=source_type,
        account_id=account_id or None,
        period_start=dates[0] if dates else None,
        period_end=dates[-1] if dates else None,
        rows=rows,
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    cloud.client.table("fyntra_statements").insert(payload).execute()
    return statement_id


def _update_statement(statement_id, **changes):
    cloud = _cloud()
    changes["updated_at"] = datetime.now(timezone.utc).isoformat()
    (cloud.client.table("fyntra_statements").update(changes)
     .eq("id",statement_id).eq("user_id",cloud.user_id).execute())


def _delete_statement(statement_id):
    cloud = _cloud()
    (cloud.client.table("fyntra_statements").delete()
     .eq("id",statement_id).eq("user_id",cloud.user_id).execute())


def _editor(frame, key):
    frame = frame.copy()
    if "include" not in frame:
        frame.insert(0,"include",True)
    return st.data_editor(
        frame,
        key=key,
        hide_index=True,
        width="stretch",
        num_rows="dynamic",
        column_config={
            "include": st.column_config.CheckboxColumn("Keep",help="Uncheck a row to exclude it."),
            "date": st.column_config.TextColumn("Date",help="YYYY-MM-DD"),
            "description": st.column_config.TextColumn("Description",width="large"),
            "amount": st.column_config.NumberColumn("Amount ₹",min_value=0.01,format="%.2f"),
            "kind": st.column_config.SelectboxColumn("Direction",options=["expense","income"],required=True),
            "category": st.column_config.SelectboxColumn("Category",options=CATEGORIES,required=True),
            "payment_method": st.column_config.SelectboxColumn("Method",options=["UPI","Card","Cash","Bank transfer","Other"]),
            "balance": st.column_config.NumberColumn("Balance ₹",format="%.2f"),
            "reference": st.column_config.TextColumn("Reference"),
            "confidence": st.column_config.ProgressColumn("Read confidence",min_value=0,max_value=100,format="%d%%"),
            "transaction_id": None,
        },
        disabled=["confidence","transaction_id"],
    )


def _statement_metrics(rows):
    info = summary(rows)
    metrics([
        ("Transactions",str(info["count"]),f'{info["start"] or "—"} to {info["end"] or "—"}'),
        ("Money in",rupees(info["income"]),"Credits detected in this statement."),
        ("Money out",rupees(info["expenses"]),"Debits detected in this statement."),
        ("Net flow",rupees(info["net"]),"Credits minus debits for this statement."),
    ])
    if info["opening_balance"] is not None or info["closing_balance"] is not None:
        metrics([
            ("First recorded balance",rupees(info["opening_balance"]),"First balance value available."),
            ("Last recorded balance",rupees(info["closing_balance"]),"Last balance value available."),
        ])


def _expense_breakdown(rows, key):
    frame = rows_frame(rows)
    if frame.empty:
        return
    frame["amount"] = pd.to_numeric(frame.amount,errors="coerce").fillna(0.0)
    expenses = frame.loc[frame.kind.eq("expense")].copy()
    if expenses.empty:
        st.caption("No expenses detected in this statement.")
        return
    left,right = st.columns(2,gap="large")
    with left:
        st.subheader("Where your money went")
        category = expenses.groupby("category",as_index=False).amount.sum().sort_values("amount",ascending=False)
        plot = alt.Chart(category).mark_bar().encode(
            x=alt.X("amount:Q",title="₹"),
            y=alt.Y("category:N",sort="-x",title=None),
            tooltip=["category",alt.Tooltip("amount:Q",format=",.2f")],
        ).properties(height=max(180,min(360,38*len(category))))
        st.altair_chart(plot,width="stretch",key="statement-category-"+key)
    with right:
        st.subheader("Largest expenses")
        top = expenses.nlargest(8,"amount")[["date","description","category","amount"]].copy()
        st.dataframe(top,hide_index=True,width="stretch")
    merchant = (expenses.groupby("description",as_index=False).amount.sum()
                .sort_values("amount",ascending=False).head(8))
    with st.expander("Top merchants / descriptions"):
        st.dataframe(merchant,hide_index=True,width="stretch")


def _account_picker(accounts, key, current=None, label="Import into account"):
    options = list(accounts)
    if not options:
        return None
    index = options.index(current) if current in options else 0
    return st.selectbox(label,options,index=index,format_func=accounts.get,key=key)


def _sync_store():
    cloud = _cloud()
    try:
        cloud.push(st.session_state.store)
        st.session_state.pop("sync_error",None)
    except Exception:
        st.session_state.sync_error = (
            "The local ledger changed, but cloud sync failed. Export a FYNTRA backup before reloading."
        )
        raise


def _imported_count(rows):
    return sum(bool(str(row.get("transaction_id") or "")) for row in rows or [])


def _pending_count(rows):
    return len(rows or []) - _imported_count(rows)


def _import_selected(selected, account_id):
    if not selected:
        return 0
    store = st.session_state.store
    updates = []
    total = 0
    for statement in selected:
        rows = statement.get("rows") or []
        if _pending_count(rows) <= 0:
            continue
        linked = statement.get("account_id")
        if _imported_count(rows) and linked and linked != account_id:
            raise ValueError(
                f'{statement["name"]} already has imported rows in another account. Remove its import first before moving it.'
            )
        updated, count = import_rows(store,statement["id"],statement["name"],account_id,rows)
        updates.append((statement["id"],updated))
        total += count
    if total:
        _sync_store()
    for statement_id, updated in updates:
        _update_statement(statement_id,rows=updated,account_id=account_id)
    return total


def _create_account(name, account_type, opening_balance, opening_date, statement_name):
    values = dict(
        name=name.strip(),
        account_type=account_type,
        opening_balance_paise=money(opening_balance),
        opening_date=opening_date.isoformat(),
        notes=f"Created from bank statement import: {statement_name}",
    )
    return st.session_state.store.save("accounts",values)


def _remove_import(statement, keep_statement=True):
    statement_id = statement["id"]
    store = st.session_state.store
    prefix = f"statement:{statement_id}:%"
    with store.connect() as con,con:
        found = con.execute("SELECT id FROM transactions WHERE source_key LIKE ?",(prefix,)).fetchall()
        con.execute("DELETE FROM transactions WHERE source_key LIKE ?",(prefix,))
    if found:
        store.revision += 1
    cleaned = [dict(row,transaction_id="") for row in statement.get("rows") or []]
    if keep_statement:
        _update_statement(statement_id,rows=cleaned,account_id=None)
    if found:
        _sync_store()
    return len(found), cleaned


def _maybe_delete_empty_auto_account(account_id):
    if not account_id:
        return False
    store = st.session_state.store
    account = store.get("accounts",account_id)
    if not account:
        return False
    notes = str(account.get("notes") or "")
    if not notes.startswith(AUTO_ACCOUNT_PREFIXES):
        return False
    tx = store.frame("transactions")
    if not tx.empty:
        used = tx["account_id"].astype(str).eq(str(account_id))
        if "to_account_id" in tx:
            used = used | tx["to_account_id"].fillna("").astype(str).eq(str(account_id))
        if used.any():
            return False
    try:
        store.delete("accounts",account_id)
        return True
    except Exception:
        return False


def _upload_tab():
    st.subheader("Upload statements or screenshots")
    st.caption(
        "A statement can create a FYNTRA account for you, merge into an existing account, or stay saved only for analysis."
    )
    files = st.file_uploader(
        "Bank statement files",
        type=["csv","xlsx","pdf","txt","png","jpg","jpeg","webp"],
        accept_multiple_files=True,
        help="CSV/XLSX usually gives the cleanest result. PDFs and screenshots are supported too; review OCR rows before importing.",
    )
    if not files:
        st.info("Best option: export CSV or XLSX from your bank. PDF and screenshots work when a spreadsheet export is not available.")
        return
    accounts = _accounts()
    cache = st.session_state.setdefault("statement_previews",{})
    for uploaded in files:
        data = uploaded.getvalue()
        digest = sha256(data).hexdigest()
        cache_key = f"{uploaded.name}:{digest}"
        if cache_key not in cache:
            with st.spinner(f"Reading {uploaded.name}…"):
                try:
                    frame, source_type, note = extract_statement(uploaded.name,data)
                    cache[cache_key] = {"frame":frame,"source_type":source_type,"note":note,"error":None}
                except Exception as exc:
                    cache[cache_key] = {
                        "frame":None,
                        "source_type":Path(uploaded.name).suffix.lstrip(".") or "text",
                        "note":"",
                        "error":str(exc),
                    }
        item = cache[cache_key]
        with st.expander(uploaded.name,expanded=True):
            if item["error"]:
                st.error(item["error"])
                continue
            st.caption(item["note"])
            default_name = Path(uploaded.name).stem.replace("_"," ").replace("-"," ").strip().title() or "Bank statement"
            name = st.text_input("Statement name",value=default_name,key="statement-name-"+digest)
            edited = _editor(item["frame"],"statement-editor-"+digest)
            try:
                reviewed = clean_rows(edited)
                _statement_metrics(reviewed)
                _expense_breakdown(reviewed,digest[:12])
                low = sum(int(row.get("confidence",100))<70 for row in reviewed)
                if low:
                    st.warning(f"{low} row(s) have low read confidence. Review their date, amount and direction before importing.")

                actions = []
                if accounts:
                    actions.append("Import into existing account")
                actions.extend(["Create account from statement + import","Save for analysis only"])
                action = st.radio("What should FYNTRA do?",actions,key="statement-action-"+digest)
                target_account = None
                new_account = None
                if action == "Import into existing account":
                    target_account = _account_picker(accounts,"statement-account-"+digest)
                elif action == "Create account from statement + import":
                    earliest = min(row["date"] for row in reviewed)
                    st.caption("This creates the account and adds every approved statement row to Transactions in one step.")
                    new_name = st.text_input("New account name",value=(name.strip() or "Imported bank")+" account",key="statement-new-account-name-"+digest)
                    account_type = st.selectbox("Account type",ACCOUNT_TYPES,index=0,key="statement-new-account-type-"+digest)
                    opening_balance = st.number_input("Opening balance (₹)",value=0.0,step=100.0,key="statement-new-account-balance-"+digest)
                    opening_date = st.date_input("Opening date",value=date.fromisoformat(earliest),key="statement-new-account-date-"+digest)
                    new_account = (new_name,account_type,opening_balance,opening_date)

                button_label = "Save statement only" if action == "Save for analysis only" else "Import statement into FYNTRA"
                if st.button(button_label,type="primary",key="statement-save-"+digest):
                    if not name.strip():
                        st.error("Enter a statement name.")
                    elif action == "Import into existing account" and target_account is None:
                        st.error("Choose the account that should receive these transactions.")
                    elif new_account and not new_account[0].strip():
                        st.error("Enter a name for the new account.")
                    else:
                        statement_id = _insert_statement(name,uploaded.name,item["source_type"],target_account,reviewed)
                        imported = 0
                        if new_account:
                            target_account = _create_account(*new_account,name.strip())
                        if target_account:
                            temp = dict(id=statement_id,name=name.strip(),account_id=target_account,rows=reviewed)
                            imported = _import_selected([temp],target_account)
                        cache.pop(cache_key,None)
                        st.session_state.notice = (
                            f"Statement imported: {imported} row(s) added to FYNTRA" if target_account else "Statement saved for analysis"
                        )
                        st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _import_builder(statements, accounts, current_id):
    st.subheader("Import saved statement into FYNTRA")
    st.caption(
        "Choose one statement or combine several into the same FYNTRA account. Imported rows become normal ledger transactions while the saved statements remain available for Compare."
    )
    labels = {row["id"]:f'{row["name"]} · {row.get("period_start") or "?"} → {row.get("period_end") or "?"}' for row in statements}
    scope = st.radio(
        "Statements to import",
        ["This statement","Selected statements","All saved statements"],
        horizontal=True,
        key="statement-import-scope-"+current_id,
    )
    if scope == "This statement":
        selected = [next(row for row in statements if row["id"]==current_id)]
    elif scope == "Selected statements":
        chosen = st.multiselect(
            "Choose statements",
            list(labels),
            format_func=labels.get,
            key="statement-import-selected-"+current_id,
        )
        selected = [row for row in statements if row["id"] in chosen]
    else:
        selected = list(statements)

    pending = sum(_pending_count(row.get("rows") or []) for row in selected)
    if selected:
        st.caption(f"{len(selected)} statement(s) selected · {pending} row(s) still available to import.")
    if not selected or pending <= 0:
        st.info("Choose at least one statement with pending rows.")
        return

    destinations = ["Existing account","Create new account"] if accounts else ["Create new account"]
    destination = st.radio("Destination",destinations,horizontal=True,key="statement-import-destination-"+current_id)
    target_account = None
    new_account = None
    if destination == "Existing account":
        target_account = _account_picker(accounts,"statement-import-account-"+current_id)
    else:
        earliest = min(row["date"] for item in selected for row in item.get("rows") or [])
        default_name = selected[0]["name"]+" account" if len(selected)==1 else "Imported statements account"
        new_name = st.text_input("New account name",value=default_name,key="saved-import-new-name-"+current_id)
        account_type = st.selectbox("Account type",ACCOUNT_TYPES,index=0,key="saved-import-new-type-"+current_id)
        opening_balance = st.number_input("Opening balance (₹)",value=0.0,step=100.0,key="saved-import-new-balance-"+current_id)
        opening_date = st.date_input("Opening date",value=date.fromisoformat(earliest),key="saved-import-new-date-"+current_id)
        new_account = (new_name,account_type,opening_balance,opening_date)

    if st.button("Import selected statements into FYNTRA",type="primary",key="statement-import-run-"+current_id):
        try:
            if new_account:
                if not new_account[0].strip():
                    raise ValueError("Enter a name for the new account.")
                target_account = _create_account(*new_account,"combined saved statements")
            count = _import_selected(selected,target_account)
            st.session_state.notice = f"{count} statement row(s) imported into FYNTRA"
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _saved_tab(statements):
    st.subheader("Saved statements")
    if not statements:
        st.info("No saved statements yet. Upload one in Upload & analyze.")
        return
    accounts = _accounts()
    labels = {row["id"]:f'{row["name"]} · {row.get("period_start") or "?"} → {row.get("period_end") or "?"}' for row in statements}
    selected_id = st.selectbox("Statement",list(labels),format_func=labels.get)
    statement = next(row for row in statements if row["id"]==selected_id)
    rows = statement.get("rows") or []
    account_name = accounts.get(statement.get("account_id")) if statement.get("account_id") else None
    st.caption(f'{statement["source_filename"]} · {statement["source_type"].upper()} · {account_name or "Saved only · not imported into a ledger account"}')
    _statement_metrics(rows)
    _expense_breakdown(rows,selected_id[:12])

    frame = rows_frame(rows)
    imported_count = _imported_count(rows)
    if imported_count:
        st.success(f"{imported_count} row(s) are imported into FYNTRA Transactions.")
        shown = frame.drop(columns=["include","transaction_id"],errors="ignore")
        st.dataframe(shown,hide_index=True,width="stretch")
        st.caption("Imported rows stay read-only here so the statement evidence and ledger do not silently drift apart.")
    else:
        edited = _editor(frame,"saved-statement-editor-"+selected_id)
        if st.button("Save statement corrections",key="statement-update-"+selected_id):
            reviewed = clean_rows(edited)
            dates = sorted(row["date"] for row in reviewed)
            _update_statement(selected_id,rows=reviewed,period_start=dates[0],period_end=dates[-1])
            st.session_state.notice = "Statement corrections saved"
            st.rerun()

    st.divider()
    _import_builder(statements,accounts,selected_id)

    st.divider()
    st.subheader("Remove statement data")
    delete_mode = st.radio(
        "What should be removed?",
        ["Remove import only","Delete statement completely"],
        key="statement-delete-mode-"+selected_id,
        help="Remove import only keeps the saved statement for analysis and comparison. Delete completely removes both the imported ledger rows and the saved statement.",
    )
    if delete_mode == "Remove import only":
        st.caption("Imported Transactions are removed, but this saved statement remains available in Saved statements and Compare.")
        disabled = imported_count == 0
        if disabled:
            st.info("This statement has no imported ledger rows to remove.")
    else:
        st.caption("This removes the saved statement and any Transactions that were imported from it. Unrelated account data is never removed.")
        disabled = False
    confirm = st.checkbox("I understand this removal",key="statement-delete-confirm-"+selected_id)
    if st.button("Remove selected statement data",disabled=disabled or not confirm,key="statement-delete-"+selected_id):
        try:
            account_id = statement.get("account_id")
            removed, _ = _remove_import(statement,keep_statement=(delete_mode=="Remove import only"))
            account_removed = False
            if delete_mode == "Delete statement completely":
                _delete_statement(selected_id)
                account_removed = _maybe_delete_empty_auto_account(account_id)
                if account_removed:
                    _sync_store()
                message = f"Statement deleted completely; {removed} imported row(s) removed"
                if account_removed:
                    message += " and the empty auto-created account was removed"
            else:
                message = f"Import removed; saved statement kept ({removed} ledger row(s) removed)"
            st.session_state.notice = message
            st.rerun()
        except Exception as exc:
            st.error(str(exc))


def _compare_tab(statements):
    st.subheader("Compare statements")
    st.caption("Nothing is combined automatically. Select only the statements you want to compare.")
    if len(statements)<2:
        st.info("Save at least two statements to compare them.")
        return
    labels = {row["id"]:f'{row["name"]} · {row.get("period_start") or "?"} → {row.get("period_end") or "?"}' for row in statements}
    chosen = st.multiselect("Statements to compare",list(labels),format_func=labels.get)
    if len(chosen)<2:
        st.info("Choose two or more statements.")
        return
    selected = [row for row in statements if row["id"] in chosen]
    summaries, detail_frames = [], []
    for item in selected:
        full_name = labels[item["id"]]
        info = summary(item.get("rows") or [])
        summaries.append(dict(
            statement=full_name,
            transactions=info["count"],
            income=info["income"],
            expenses=info["expenses"],
            net=info["net"],
            from_date=info["start"],
            to_date=info["end"],
        ))
        frame = rows_frame(item.get("rows") or [])
        if not frame.empty:
            frame["statement"] = full_name
            detail_frames.append(frame)
    st.dataframe(pd.DataFrame(summaries),hide_index=True,width="stretch")
    if not detail_frames:
        return
    combined = pd.concat(detail_frames,ignore_index=True)
    combined["amount"] = pd.to_numeric(combined.amount,errors="coerce").fillna(0.0)
    combined["date"] = pd.to_datetime(combined.date,errors="coerce")
    legend = alt.Legend(orient="bottom",title=None,labelLimit=0,columns=1)
    st.subheader("Spending by category")
    category = combined.loc[combined.kind.eq("expense")].groupby(["statement","category"],as_index=False).amount.sum()
    if not category.empty:
        plot = alt.Chart(category).mark_bar().encode(
            x=alt.X("category:N",title=None),
            y=alt.Y("amount:Q",title="₹"),
            color=alt.Color("statement:N",legend=legend),
            xOffset="statement:N",
            tooltip=["statement","category",alt.Tooltip("amount:Q",format=",.2f")],
        ).properties(height=280)
        st.altair_chart(plot,width="stretch")
    st.subheader("Daily net flow")
    daily = combined.assign(signed=combined.amount.where(combined.kind.eq("income"),-combined.amount))
    daily = daily.groupby(["statement","date"],as_index=False).signed.sum().dropna()
    if not daily.empty:
        plot = alt.Chart(daily).mark_line(point=True).encode(
            x=alt.X("date:T",title=None),
            y=alt.Y("signed:Q",title="Net ₹"),
            color=alt.Color("statement:N",legend=legend),
            tooltip=["statement",alt.Tooltip("date:T"),alt.Tooltip("signed:Q",format=",.2f")],
        ).properties(height=260)
        st.altair_chart(plot,width="stretch")
    st.subheader("All selected rows")
    shown = combined[["statement","date","description","kind","category","amount","balance","reference"]].sort_values(["date","statement"])
    st.dataframe(shown,hide_index=True,width="stretch")
