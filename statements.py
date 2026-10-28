"""Private bank statement workspace: upload, review, save, compare and import."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from database import CATEGORIES
from statement_tools import clean_rows, extract_statement, import_rows, rows_frame, summary
from ui import hero, metrics, rupees, MINT, GOLD


def _cloud():
    cloud = st.session_state.get("cloud")
    if not cloud or not cloud.user_id:
        st.info("Bank statements are available only inside Private sign in.")
        st.stop()
    return cloud


def _accounts():
    frame = st.session_state.store.frame("accounts")
    if frame.empty:
        st.info("Create an account in Accounts before adding a bank statement.")
        st.stop()
    return frame.set_index("id").name.to_dict()


def _list_statements():
    cloud = _cloud()
    result = (cloud.client.table("fyntra_statements")
              .select("id,name,source_filename,source_type,account_id,period_start,period_end,rows,created_at,updated_at")
              .eq("user_id",cloud.user_id).order("created_at",desc=True).execute())
    return result.data or []


def _insert_statement(name, source_filename, source_type, account_id, rows):
    cloud = _cloud()
    dates = sorted(row["date"] for row in rows)
    payload = dict(user_id=cloud.user_id,name=name.strip(),source_filename=source_filename,
                   source_type=source_type,account_id=account_id,
                   period_start=dates[0] if dates else None,period_end=dates[-1] if dates else None,
                   rows=rows,updated_at=datetime.now(timezone.utc).isoformat())
    cloud.client.table("fyntra_statements").insert(payload).execute()


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
            "include": st.column_config.CheckboxColumn("Keep",help="Uncheck a row to exclude it from this statement."),
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
            ("First recorded balance",rupees(info["opening_balance"]),"First balance value available in the statement."),
            ("Last recorded balance",rupees(info["closing_balance"]),"Last balance value available in the statement."),
        ])


def _upload_tab():
    st.subheader("Upload statements or screenshots")
    st.caption("Upload several files at once. Each file stays a separate statement unless you later choose statements in Compare. Raw files are processed in memory and are not stored in FYNTRA cloud storage.")
    files = st.file_uploader(
        "Bank statement files",
        type=["csv","xlsx","pdf","txt","png","jpg","jpeg","webp"],
        accept_multiple_files=True,
        help="CSV/XLSX usually gives the cleanest result. PDFs and screenshots are supported too; OCR rows should be reviewed before saving.",
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
            account_id = st.selectbox("FYNTRA account",list(accounts),format_func=accounts.get,key="statement-account-"+digest)
            edited = _editor(item["frame"],"statement-editor-"+digest)
            try:
                reviewed = clean_rows(edited)
                _statement_metrics(reviewed)
                low = sum(int(row.get("confidence",100))<70 for row in reviewed)
                if low:
                    st.warning(f"{low} row(s) have low read confidence. Review their date, amount and direction before saving.")
                if st.button("Save as separate statement",type="primary",key="statement-save-"+digest):
                    if not name.strip():
                        st.error("Enter a statement name.")
                    else:
                        _insert_statement(name,uploaded.name,item["source_type"],account_id,reviewed)
                        cache.pop(cache_key,None)
                        st.session_state.notice = "Statement saved privately"
                        st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _saved_tab(statements):
    st.subheader("Saved statements")
    if not statements:
        st.info("No saved statements yet. Upload one in Upload & review.")
        return
    accounts = _accounts()
    labels = {row["id"]:f'{row["name"]} · {row.get("period_start") or "?"} → {row.get("period_end") or "?"}' for row in statements}
    selected_id = st.selectbox("Statement",list(labels),format_func=labels.get)
    statement = next(row for row in statements if row["id"]==selected_id)
    rows = statement.get("rows") or []
    st.caption(f'{statement["source_filename"]} · {statement["source_type"].upper()} · {accounts.get(statement["account_id"],"Unknown account")}')
    _statement_metrics(rows)
    frame = rows_frame(rows)
    imported = frame.transaction_id.astype(str).str.len().gt(0) if not frame.empty else pd.Series(dtype=bool)
    imported_count = int(imported.sum()) if len(imported) else 0
    if imported_count:
        st.success(f"{imported_count} row(s) are already linked to Transactions.")
        shown = frame.drop(columns=["include","transaction_id"],errors="ignore")
        st.dataframe(shown,hide_index=True,width="stretch")
        st.caption("After ledger import, statement rows are shown read-only so the saved evidence and the ledger cannot silently drift apart.")
    else:
        edited = _editor(frame,"saved-statement-editor-"+selected_id)
        if st.button("Save statement corrections",key="statement-update-"+selected_id):
            reviewed = clean_rows(edited)
            dates = sorted(row["date"] for row in reviewed)
            _update_statement(selected_id,rows=reviewed,period_start=dates[0],period_end=dates[-1])
            st.session_state.notice = "Statement corrections saved"
            st.rerun()
    st.divider()
    pending = len(rows)-imported_count
    st.subheader("Add reviewed rows to Transactions")
    st.caption("Uploading a statement never changes the ledger by itself. Import only when you are happy with the reviewed rows. FYNTRA uses a unique statement key so retrying does not duplicate a row.")
    if pending <= 0:
        st.info("Every row in this statement is already linked to the ledger.")
    elif st.button(f"Import {pending} pending row(s) to ledger",type="primary",key="statement-import-"+selected_id):
        try:
            updated, count = import_rows(st.session_state.store,selected_id,statement["name"],statement["account_id"],rows)
            cloud = _cloud()
            try:
                cloud.push(st.session_state.store)
                st.session_state.pop("sync_error",None)
            except Exception:
                st.session_state.sync_error = "Statement rows were added in this session, but cloud ledger sync failed. Export a backup before reloading."
                raise
            _update_statement(selected_id,rows=updated)
            st.session_state.notice = f"{count} statement row(s) added to Transactions"
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    st.divider()
    st.subheader("Remove saved statement")
    st.caption("Deleting the saved statement does not delete transactions that were already imported into the ledger.")
    confirm = st.checkbox("I understand and want to delete this saved statement",key="statement-delete-confirm-"+selected_id)
    if st.button("Delete saved statement",disabled=not confirm,key="statement-delete-"+selected_id):
        _delete_statement(selected_id)
        st.session_state.notice = "Saved statement deleted"
        st.rerun()


def _compare_tab(statements):
    st.subheader("Compare statements")
    st.caption("Nothing is combined automatically. Select the exact statements you want to compare; otherwise every statement remains separate.")
    if len(statements)<2:
        st.info("Save at least two statements to compare them.")
        return
    labels = {row["id"]:f'{row["name"]} · {row.get("period_start") or "?"} → {row.get("period_end") or "?"}' for row in statements}
    chosen = st.multiselect("Statements to compare",list(labels),format_func=labels.get)
    if len(chosen)<2:
        st.info("Choose two or more statements.")
        return
    selected = [row for row in statements if row["id"] in chosen]
    summaries = []
    detail_frames = []
    for item in selected:
        info = summary(item.get("rows") or [])
        summaries.append(dict(statement=item["name"],transactions=info["count"],income=info["income"],expenses=info["expenses"],net=info["net"],from_date=info["start"],to_date=info["end"]))
        frame = rows_frame(item.get("rows") or [])
        if not frame.empty:
            frame["statement"] = item["name"]
            detail_frames.append(frame)
    st.dataframe(pd.DataFrame(summaries),hide_index=True,width="stretch")
    if not detail_frames:
        return
    combined = pd.concat(detail_frames,ignore_index=True)
    combined["amount"] = pd.to_numeric(combined.amount,errors="coerce").fillna(0.0)
    combined["date"] = pd.to_datetime(combined.date,errors="coerce")
    st.subheader("Spending by category")
    category = (combined.loc[combined.kind.eq("expense")]
                .groupby(["statement","category"],as_index=False).amount.sum())
    if not category.empty:
        plot = alt.Chart(category).mark_bar().encode(
            x=alt.X("category:N",title=None),y=alt.Y("amount:Q",title="₹"),
            color=alt.Color("statement:N",legend=alt.Legend(orient="bottom")),
            xOffset="statement:N",tooltip=["statement","category","amount"]).properties(height=280)
        st.altair_chart(plot,width="stretch")
    st.subheader("Daily net flow")
    daily = combined.assign(signed=combined.amount.where(combined.kind.eq("income"),-combined.amount))
    daily = daily.groupby(["statement","date"],as_index=False).signed.sum().dropna()
    if not daily.empty:
        plot = alt.Chart(daily).mark_line(point=True).encode(
            x=alt.X("date:T",title=None),y=alt.Y("signed:Q",title="Net ₹"),
            color=alt.Color("statement:N",legend=alt.Legend(orient="bottom")),
            tooltip=["statement",alt.Tooltip("date:T"),alt.Tooltip("signed:Q",format=",.2f")]).properties(height=260)
        st.altair_chart(plot,width="stretch")
    st.subheader("All selected rows")
    shown = combined[["statement","date","description","kind","category","amount","balance","reference"]].sort_values(["date","statement"])
    st.dataframe(shown,hide_index=True,width="stretch")


def statement_page():
    _cloud()
    hero("Statements, without the spreadsheet headache.",
         "Upload a whole bank statement, review extracted transactions once, then keep it separate, compare it, or add approved rows to your ledger.",
         "PRIVATE / BANK STATEMENTS")
    st.caption("For privacy, this workspace is visible only after Private sign in. Source files are processed in memory; FYNTRA stores only the reviewed statement rows and metadata in your protected Supabase account.")
    statements = _list_statements()
    upload, saved, compare = st.tabs(["Upload & review","Saved statements","Compare"])
    with upload:
        _upload_tab()
    with saved:
        _saved_tab(statements)
    with compare:
        _compare_tab(statements)
