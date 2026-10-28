"""Private bank statement workspace: analyze first, link to the ledger only when needed."""
from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

import altair as alt
import pandas as pd
import streamlit as st

from database import ACCOUNT_TYPES, CATEGORIES, money
from statement_tools import clean_rows, extract_statement, import_rows, rows_frame, summary
from ui import hero, metrics, rupees


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


def _list_exports():
    cloud = _cloud()
    result = (cloud.client.table("fyntra_statement_exports")
              .select("id,name,scope,format,account_id,statement_ids,rows,created_at")
              .eq("user_id",cloud.user_id).order("created_at",desc=True).execute())
    return result.data or []


def _insert_statement(name, source_filename, source_type, account_id, rows):
    cloud = _cloud()
    statement_id = str(uuid4())
    dates = sorted(row["date"] for row in rows)
    payload = dict(id=statement_id,user_id=cloud.user_id,name=name.strip(),source_filename=source_filename,
                   source_type=source_type,account_id=account_id or None,
                   period_start=dates[0] if dates else None,period_end=dates[-1] if dates else None,
                   rows=rows,updated_at=datetime.now(timezone.utc).isoformat())
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


def _delete_export(export_id):
    cloud = _cloud()
    (cloud.client.table("fyntra_statement_exports").delete()
     .eq("id",export_id).eq("user_id",cloud.user_id).execute())


def _editor(frame, key):
    frame = frame.copy()
    if "include" not in frame:
        frame.insert(0,"include",True)
    return st.data_editor(
        frame,key=key,hide_index=True,width="stretch",num_rows="dynamic",
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
            x=alt.X("amount:Q",title="₹"),y=alt.Y("category:N",sort="-x",title=None),
            tooltip=["category",alt.Tooltip("amount:Q",format=",.2f")]).properties(height=max(180,min(360,38*len(category))))
        st.altair_chart(plot,width="stretch",key="statement-category-"+key)
    with right:
        st.subheader("Largest expenses")
        top = expenses.nlargest(8,"amount")[["date","description","category","amount"]].copy()
        st.dataframe(top,hide_index=True,width="stretch")
    merchant = (expenses.groupby("description",as_index=False).amount.sum()
                .sort_values("amount",ascending=False).head(8))
    with st.expander("Top merchants / descriptions"):
        st.dataframe(merchant,hide_index=True,width="stretch")


def _account_picker(accounts, key, current=None, label="FYNTRA account (optional)"):
    options = [None] + list(accounts)
    def show(value):
        return "Analyze only · no FYNTRA account" if value is None else accounts[value]
    index = options.index(current) if current in options else 0
    return st.selectbox(label,options,index=index,format_func=show,key=key,
                        help="No account is needed to analyze, classify, save or compare a statement. Choose one only if you plan to import rows into Transactions.")


def _import_saved_rows(statement_id, statement_name, account_id, rows):
    updated, count = import_rows(st.session_state.store,statement_id,statement_name,account_id,rows)
    cloud = _cloud()
    try:
        cloud.push(st.session_state.store)
        st.session_state.pop("sync_error",None)
    except Exception:
        st.session_state.sync_error = "Statement rows were added in this session, but cloud ledger sync failed. Export a backup before reloading."
        raise
    _update_statement(statement_id,rows=updated,account_id=account_id)
    return count


def _upload_tab():
    st.subheader("Upload statements or screenshots")
    st.caption("Analyze without setup, or choose a one-step save/import path after review. Bank files stay separate from FYNTRA backup imports.")
    files = st.file_uploader(
        "Bank statement files",type=["csv","xlsx","pdf","txt","png","jpg","jpeg","webp"],
        accept_multiple_files=True,
        help="CSV/XLSX usually gives the cleanest result. PDFs and screenshots are supported too; review OCR rows before saving.",
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
                    cache[cache_key] = {"frame":None,"source_type":Path(uploaded.name).suffix.lstrip(".") or "text","note":"","error":str(exc)}
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
                    st.warning(f"{low} row(s) have low read confidence. Review their date, amount and direction before saving.")

                action_options = ["Save statement only"]
                if accounts:
                    action_options.append("Save + import to existing account")
                action_options.append("Save + create account + import")
                action = st.radio("After review",action_options,key="statement-action-"+digest)
                target_account = None
                new_account = None
                if action == "Save + import to existing account":
                    target_account = _account_picker(accounts,"statement-account-"+digest,label="Import into account")
                elif action == "Save + create account + import":
                    st.caption("FYNTRA will create the account, add the reviewed rows to Transactions, and keep this statement saved separately.")
                    earliest = min(row["date"] for row in reviewed)
                    new_name = st.text_input("New account name",value=(name.strip() or "Imported bank")+" account",key="statement-new-account-name-"+digest)
                    account_type = st.selectbox("Account type",ACCOUNT_TYPES,index=0,key="statement-new-account-type-"+digest)
                    opening_balance = st.number_input("Opening balance (₹)",value=0.0,step=100.0,key="statement-new-account-balance-"+digest)
                    opening_date = st.date_input("Opening date",value=date.fromisoformat(earliest),key="statement-new-account-date-"+digest)
                    new_account = dict(name=new_name.strip(),account_type=account_type,
                                       opening_balance_paise=money(opening_balance),opening_date=opening_date.isoformat(),
                                       notes=f"Created while importing bank statement: {name.strip() or uploaded.name}")

                button_label = "Save statement" if action == "Save statement only" else "Save and update FYNTRA ledger"
                if st.button(button_label,type="primary",key="statement-save-"+digest):
                    if not name.strip():
                        st.error("Enter a statement name.")
                    elif action == "Save + import to existing account" and target_account is None:
                        st.error("Choose the account that should receive these transactions.")
                    elif new_account is not None and not new_account["name"]:
                        st.error("Enter a name for the new account.")
                    else:
                        statement_id = _insert_statement(name,uploaded.name,item["source_type"],target_account,reviewed)
                        imported = 0
                        if new_account is not None:
                            target_account = st.session_state.store.save("accounts",new_account)
                        if target_account:
                            imported = _import_saved_rows(statement_id,name.strip(),target_account,reviewed)
                        cache.pop(cache_key,None)
                        st.session_state.notice = (f"Statement saved and {imported} row(s) added to Transactions" if target_account else "Statement saved privately")
                        st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _flatten_statements(selected):
    output = []
    for statement in selected:
        for row in statement.get("rows") or []:
            output.append({
                "statement_id":statement["id"],
                "statement_name":statement["name"],
                "source_filename":statement.get("source_filename") or "",
                "account_id":statement.get("account_id") or "",
                "period_start":statement.get("period_start") or "",
                "period_end":statement.get("period_end") or "",
                "date":row.get("date") or "",
                "description":row.get("description") or "",
                "amount":row.get("amount") or 0,
                "kind":row.get("kind") or "",
                "category":row.get("category") or "Other",
                "payment_method":row.get("payment_method") or "Other",
                "balance":row.get("balance"),
                "reference":row.get("reference") or "",
                "confidence":row.get("confidence"),
                "imported_to_ledger":bool(row.get("transaction_id")),
            })
    return output


def _insert_export(name, scope, file_format, account_id, selected):
    cloud = _cloud()
    rows = _flatten_statements(selected)
    if not rows:
        raise ValueError("The selected statements have no rows to export.")
    payload = dict(user_id=cloud.user_id,name=name.strip(),scope=scope,format=file_format,
                   account_id=account_id or None,statement_ids=[row["id"] for row in selected],rows=rows)
    cloud.client.table("fyntra_statement_exports").insert(payload).execute()


def _safe_filename(value):
    value = re.sub(r"[^A-Za-z0-9._-]+","_",str(value or "statement").strip()).strip("._")
    return value[:80] or "statement"


def _export_csv_bytes(rows):
    return pd.DataFrame(rows or []).to_csv(index=False,lineterminator="\n").encode("utf-8-sig")


def _export_zip_bytes(rows):
    frame = pd.DataFrame(rows or [])
    buffer = BytesIO()
    with ZipFile(buffer,"w",ZIP_DEFLATED) as archive:
        if frame.empty:
            archive.writestr("statement.csv","")
        else:
            for (_, name), group in frame.groupby(["statement_id","statement_name"],sort=False,dropna=False):
                archive.writestr(_safe_filename(name)+".csv",group.to_csv(index=False,lineterminator="\n"))
    return buffer.getvalue()


def _export_builder(statements, accounts, current_id):
    with st.expander("Create statement export",expanded=False):
        st.caption("Exports are private snapshots. Deleting an export never deletes the saved statement or ledger transactions.")
        scope_label = st.radio("What do you want to export?",["This statement","Selected statements","All saved statements","By linked account"],key="statement-export-scope-"+current_id)
        selected = []
        scope = "individual"
        account_id = None
        labels = {row["id"]:f'{row["name"]} · {row.get("period_start") or "?"} → {row.get("period_end") or "?"}' for row in statements}
        if scope_label == "This statement":
            selected = [next(row for row in statements if row["id"]==current_id)]
        elif scope_label == "Selected statements":
            scope = "selected"
            chosen = st.multiselect("Choose statements",list(labels),format_func=labels.get,key="statement-export-selected-"+current_id)
            selected = [row for row in statements if row["id"] in chosen]
        elif scope_label == "All saved statements":
            scope = "all"
            selected = list(statements)
        else:
            scope = "account"
            linked = {row.get("account_id") for row in statements if row.get("account_id") in accounts}
            if not linked:
                st.info("No saved statements are linked to a FYNTRA account yet.")
            else:
                account_id = st.selectbox("Account",list(linked),format_func=accounts.get,key="statement-export-account-"+current_id)
                selected = [row for row in statements if row.get("account_id")==account_id]
        if selected:
            st.caption(f"{len(selected)} statement(s) selected.")
        file_format = "csv"
        if len(selected)>1:
            layout = st.radio("File layout",["Combined CSV","Separate CSVs (.zip)"],horizontal=True,key="statement-export-layout-"+current_id)
            file_format = "zip" if layout.startswith("Separate") else "csv"
        default_name = (selected[0]["name"]+" export") if len(selected)==1 else "FYNTRA statement export"
        export_name = st.text_input("Export name",value=default_name,key="statement-export-name-"+current_id)
        if st.button("Create export snapshot",disabled=not selected,key="statement-export-create-"+current_id):
            if not export_name.strip():
                st.error("Enter an export name.")
            else:
                _insert_export(export_name,scope,file_format,account_id,selected)
                st.session_state.notice = "Statement export created"
                st.rerun()


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
    st.caption(f'{statement["source_filename"]} · {statement["source_type"].upper()} · {account_name or "Analysis only · no ledger account linked"}')
    _statement_metrics(rows)
    _expense_breakdown(rows,selected_id[:12])
    frame = rows_frame(rows)
    imported = frame.transaction_id.astype(str).str.len().gt(0) if not frame.empty else pd.Series(dtype=bool)
    imported_count = int(imported.sum()) if len(imported) else 0
    if imported_count:
        st.success(f"{imported_count} row(s) are already linked to Transactions.")
        shown = frame.drop(columns=["include","transaction_id"],errors="ignore")
        st.dataframe(shown,hide_index=True,width="stretch")
        st.caption("After ledger import, statement rows are read-only so the saved evidence and ledger cannot silently drift apart.")
    else:
        edited = _editor(frame,"saved-statement-editor-"+selected_id)
        if st.button("Save statement corrections",key="statement-update-"+selected_id):
            reviewed = clean_rows(edited)
            dates = sorted(row["date"] for row in reviewed)
            _update_statement(selected_id,rows=reviewed,period_start=dates[0],period_end=dates[-1])
            st.session_state.notice = "Statement corrections saved"
            st.rerun()

    _export_builder(statements,accounts,selected_id)
    st.divider()
    pending = len(rows)-imported_count
    st.subheader("Optional: add reviewed rows to Transactions")
    st.caption("Analysis, saving, export and comparison do not require an account. An account is required only for this ledger-import step.")
    if pending <= 0:
        st.info("Every row in this statement is already linked to the ledger.")
    elif not accounts:
        st.info("Want these rows in your FYNTRA ledger? Upload the statement again and choose ‘Save + create account + import’, or create an account in Accounts first.")
    else:
        current_account = statement.get("account_id") if statement.get("account_id") in accounts else None
        target_account = _account_picker(accounts,"statement-import-account-"+selected_id,current=current_account)
        if target_account is None:
            st.caption("Choose an account above only when you want to import this statement into Transactions.")
        elif st.button(f"Import {pending} pending row(s) to ledger",type="primary",key="statement-import-"+selected_id):
            try:
                count = _import_saved_rows(selected_id,statement["name"],target_account,rows)
                st.session_state.notice = f"{count} statement row(s) added to Transactions"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    st.divider()
    st.subheader("Remove saved statement")
    st.caption("Deleting the saved statement does not delete transactions already imported into the ledger, and it does not delete export snapshots created from it.")
    confirm = st.checkbox("I understand and want to delete this saved statement",key="statement-delete-confirm-"+selected_id)
    if st.button("Delete saved statement",disabled=not confirm,key="statement-delete-"+selected_id):
        _delete_statement(selected_id)
        st.session_state.notice = "Saved statement deleted"
        st.rerun()


def _compare_tab(statements):
    st.subheader("Compare statements")
    st.caption("Nothing is combined automatically. Select only the statements you want to compare; no FYNTRA account is required.")
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
        summaries.append(dict(statement=full_name,transactions=info["count"],income=info["income"],expenses=info["expenses"],net=info["net"],from_date=info["start"],to_date=info["end"]))
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
            x=alt.X("category:N",title=None),y=alt.Y("amount:Q",title="₹"),
            color=alt.Color("statement:N",legend=legend),xOffset="statement:N",
            tooltip=["statement","category",alt.Tooltip("amount:Q",format=",.2f")]).properties(height=280)
        st.altair_chart(plot,width="stretch")
    st.subheader("Daily net flow")
    daily = combined.assign(signed=combined.amount.where(combined.kind.eq("income"),-combined.amount))
    daily = daily.groupby(["statement","date"],as_index=False).signed.sum().dropna()
    if not daily.empty:
        plot = alt.Chart(daily).mark_line(point=True).encode(
            x=alt.X("date:T",title=None),y=alt.Y("signed:Q",title="Net ₹"),
            color=alt.Color("statement:N",legend=legend),
            tooltip=["statement",alt.Tooltip("date:T"),alt.Tooltip("signed:Q",format=",.2f")]).properties(height=260)
        st.altair_chart(plot,width="stretch")
    st.subheader("All selected rows")
    shown = combined[["statement","date","description","kind","category","amount","balance","reference"]].sort_values(["date","statement"])
    st.dataframe(shown,hide_index=True,width="stretch")


def _exports_tab(exports):
    st.subheader("Statement exports")
    st.caption("These are independent snapshots. Delete one here without changing Saved statements or Transactions.")
    labels = {row["id"]:f'{row["name"]} · {str(row.get("created_at") or "")[:16].replace("T"," ")}' for row in exports}
    export_id = st.selectbox("Export",list(labels),format_func=labels.get)
    export = next(row for row in exports if row["id"]==export_id)
    rows = export.get("rows") or []
    statement_count = len(export.get("statement_ids") or [])
    metrics([("Statements",str(statement_count),export.get("scope","")),("Rows",str(len(rows)),"Snapshot rows"),("Format",str(export.get("format","csv")).upper(),"Download layout")])
    if export.get("format")=="zip":
        data = _export_zip_bytes(rows)
        filename = _safe_filename(export["name"])+".zip"
        mime = "application/zip"
    else:
        data = _export_csv_bytes(rows)
        filename = _safe_filename(export["name"])+".csv"
        mime = "text/csv"
    st.download_button("Download this export",data,filename,mime,type="primary",key="statement-export-download-"+export_id)
    st.dataframe(pd.DataFrame(rows),hide_index=True,width="stretch")
    confirm = st.checkbox("Delete only this export snapshot",key="statement-export-delete-confirm-"+export_id)
    if st.button("Delete export",disabled=not confirm,key="statement-export-delete-"+export_id):
        _delete_export(export_id)
        st.session_state.notice = "Export deleted; saved statements were not changed"
        st.rerun()


def statement_page():
    _cloud()
    hero("Understand a statement before building a budget.",
         "Upload a bank statement or screenshot to classify spending immediately. Save it separately, compare it, export it, or explicitly add reviewed rows to your FYNTRA ledger.",
         "PRIVATE / BANK STATEMENTS")
    st.caption("Source files are processed in memory. FYNTRA stores reviewed statement rows and metadata only when you explicitly save a statement.")
    statements = _list_statements()
    exports = _list_exports()
    names = ["Upload & analyze","Saved statements","Compare"]
    if exports:
        names.append("Exports")
    tabs = st.tabs(names)
    with tabs[0]:
        _upload_tab()
    with tabs[1]:
        _saved_tab(statements)
    with tabs[2]:
        _compare_tab(statements)
    if exports:
        with tabs[3]:
            _exports_tab(exports)
