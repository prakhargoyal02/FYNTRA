"""Backup-focused Data & settings screen."""
import streamlit as st

import views
from csv_tools import export_bundle, export_table, import_csvs, parse_files
from database import TABLES, money
from ui import hero


def _account_dependencies(store, account_id):
    counts = {}

    transactions = store.frame("transactions")
    if transactions.empty:
        counts["Transactions / transfers"] = 0
    else:
        linked = transactions["account_id"].astype(str).eq(str(account_id))
        if "to_account_id" in transactions:
            linked = linked | transactions["to_account_id"].fillna("").astype(str).eq(str(account_id))
        counts["Transactions / transfers"] = int(linked.sum())

    recurring = store.frame("recurring_transactions")
    if recurring.empty:
        counts["Recurring schedules"] = 0
    else:
        linked = recurring["account_id"].astype(str).eq(str(account_id))
        if "to_account_id" in recurring:
            linked = linked | recurring["to_account_id"].fillna("").astype(str).eq(str(account_id))
        counts["Recurring schedules"] = int(linked.sum())

    for table, label in [
        ("bills", "Bills"),
        ("subscriptions", "Subscriptions"),
        ("debt_payments", "Debt payments"),
    ]:
        frame = store.frame(table)
        counts[label] = 0 if frame.empty else int(frame["account_id"].astype(str).eq(str(account_id)).sum())

    return counts


def _account_cleanup():
    store = views.current()
    accounts = store.frame("accounts")
    st.subheader("Delete an account")
    st.caption(
        "Account deletion is deliberately safe. FYNTRA will not remove an account while transactions, transfers, bills, "
        "subscriptions, recurring schedules or debt payments still depend on it."
    )
    if accounts.empty:
        st.info("There are no accounts to delete.")
        return

    labels = accounts.set_index("id").name.to_dict()
    account_id = st.selectbox(
        "Account to delete",
        list(labels),
        format_func=labels.get,
        key="settings-delete-account",
    )
    dependencies = _account_dependencies(store, account_id)
    st.dataframe(
        [{"Linked data": label, "Count": count} for label, count in dependencies.items()],
        hide_index=True,
        width="stretch",
    )
    blocked = sum(dependencies.values()) > 0
    if blocked:
        st.warning(
            "This account still has linked data. Remove statement imports in Bank statements → Manage, or delete/move the linked records first."
        )
        return

    st.info("No linked ledger records remain. Deleting this account will not delete any saved bank statement analysis.")
    typed = st.text_input(
        f'Type “{labels[account_id]}” to confirm',
        key="settings-delete-account-name",
    )
    if st.button(
        "Delete this account",
        disabled=typed.strip() != labels[account_id],
        key="settings-delete-account-button",
    ):
        views.commit_action(lambda: store.delete("accounts", account_id), "Account deleted")


def data_page():
    hero(
        "Your data. Your control.",
        "Export and restore FYNTRA data without mixing backup files with bank statements.",
        "DATA & SETTINGS",
    )
    profile=views.current().get("profile","profile")
    with st.form("settings"):
        name=st.text_input("Display name",profile["display_name"])
        limit=st.number_input(
            "Total monthly spending limit (₹)",min_value=0.0,
            value=profile["monthly_limit_paise"]/100,
            help="Zero uses the sum of this month's category budgets.",
        )
        st.caption("Currency: INR. Other currencies are planned; v1 never mixes currencies or converts rates.")
        submitted=st.form_submit_button("Save preferences")
    if submitted:
        views.save("profile",profile,dict(display_name=name,monthly_limit_paise=money(limit)))

    st.subheader("Export a FYNTRA backup")
    st.download_button(
        "Download full FYNTRA Bundle",export_bundle(views.current()),
        "fyntra_bundle.csv","text/csv",type="primary",
    )
    choice=st.selectbox("Individual record type",TABLES)
    st.download_button(
        "Download selected CSV",export_table(views.current(),choice),
        choice+".csv","text/csv",
    )

    st.subheader("Import a FYNTRA backup")
    st.caption(
        "Use this only for FYNTRA bundle/export CSVs or the FYNTRA transaction template. "
        "Bank statements, PDFs and screenshots belong in Bank statements."
    )
    files=st.file_uploader(
        "Choose FYNTRA backup CSVs",type="csv",accept_multiple_files=True,
        key="fyntra-backup-upload",
    )
    mode=st.radio("Import mode",["Add safely","Replace matching types"],horizontal=True,key="fyntra-backup-mode")
    confirm=(st.checkbox(
        "I exported a backup and want to replace the included record types",
        key="fyntra-backup-replace-confirm",
    ) if mode=="Replace matching types" else True)
    if files:
        try:
            prepared=[(f.name,f.getvalue()) for f in files]
            parsed=parse_files(views.current(),prepared)
            st.write({k:len(v) for k,v in parsed.items()})
            if st.button("Import validated FYNTRA backup",disabled=not confirm,type="primary"):
                views.commit_action(
                    lambda:import_csvs(views.current(),prepared,"add" if mode=="Add safely" else "replace"),
                    "FYNTRA backup import complete",
                )
        except Exception as exc:
            st.error(str(exc))

    with st.expander("Simple FYNTRA transaction template"):
        st.download_button(
            "Download template",
            "date,amount,kind,category,account_name,merchant,notes,tags\n",
            "transaction_template.csv","text/csv",
        )
        st.caption("Account names in this template must already exist. A full FYNTRA bundle can include accounts and related records together.")

    st.divider()
    _account_cleanup()

    cloud=st.session_state.get("cloud")
    if cloud:
        st.subheader("Cloud sync")
        st.caption("Concurrent edits are detected before overwriting another session. Export a backup before reloading cloud data if you have unsynced local changes.")
        if st.button("Retry sync"):
            views.commit_action(lambda:None,"Cloud sync attempted")
        if st.checkbox("I exported local changes and want to reload the cloud copy"):
            if st.button("Reload cloud copy"):
                try:
                    cloud.pull(views.current())
                    st.session_state.pop("sync_error",None)
                    st.rerun()
                except Exception:
                    st.error("Cloud reload failed. Your local copy remains available.")
    else:
        st.subheader("Reset fictional demo")
        if st.checkbox("Replace this session's demo edits with fresh fictional data"):
            if st.button("Reset demo"):
                directory=st.session_state.pop("demo_directory",None)
                st.session_state.pop("store",None)
                if directory:
                    directory.cleanup()
                st.rerun()

    st.caption("Demo sessions are temporary. Private sessions use an isolated SQLite working copy and ownership-protected cloud sync.")
