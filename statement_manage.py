"""Safe cleanup tools for imported bank statements."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import statements
import statement_flow


def _source_statement_id(value):
    text = str(value or "")
    if not text.startswith("statement:"):
        return None
    parts = text.split(":", 2)
    return parts[1] if len(parts) >= 3 and parts[1] else None


def _orphaned_imports(meta_rows):
    saved_ids = {row["id"] for row in meta_rows}
    frame = st.session_state.store.frame("transactions")
    if frame.empty or "source_key" not in frame:
        return frame.iloc[0:0].copy()
    ids = frame["source_key"].map(_source_statement_id)
    return frame.loc[ids.notna() & ~ids.isin(saved_ids)].copy()


def _delete_local_imports(selected):
    store = st.session_state.store
    deleted = 0
    account_ids = set()
    transaction_ids = set()
    statement_ids = set()
    for statement in selected:
        statement_ids.add(statement["id"])
        if statement.get("account_id"):
            account_ids.add(statement["account_id"])
        for row in statement.get("rows") or []:
            tx_id = str(row.get("transaction_id") or "").strip()
            if tx_id:
                transaction_ids.add(tx_id)

    with store.connect() as con, con:
        if transaction_ids:
            placeholders = ",".join("?" for _ in transaction_ids)
            before = con.total_changes
            con.execute(
                f"DELETE FROM transactions WHERE id IN ({placeholders})",
                tuple(transaction_ids),
            )
            deleted += con.total_changes - before
        for statement_id in statement_ids:
            before = con.total_changes
            con.execute(
                "DELETE FROM transactions WHERE source_key LIKE ?",
                (f"statement:{statement_id}:%",),
            )
            deleted += con.total_changes - before

    if deleted:
        store.revision += 1
    return deleted, account_ids


def _cleanup_auto_accounts(account_ids):
    removed = 0
    for account_id in account_ids:
        if statements._maybe_delete_empty_auto_account(account_id):
            removed += 1
    return removed


def _batch_remove(selected, delete_completely=False):
    deleted, account_ids = _delete_local_imports(selected)

    if delete_completely:
        for statement in selected:
            statements._delete_statement(statement["id"])
    else:
        for statement in selected:
            cleaned = [dict(row, transaction_id="") for row in statement.get("rows") or []]
            statements._update_statement(statement["id"], rows=cleaned, account_id=None)

    removed_accounts = _cleanup_auto_accounts(account_ids)
    if deleted or removed_accounts:
        statements._sync_store()
    statement_flow._invalidate_statement_cache([statement["id"] for statement in selected])
    return deleted, removed_accounts


def _clean_orphans(orphaned):
    if orphaned.empty:
        return 0, 0
    store = st.session_state.store
    ids = orphaned["id"].astype(str).tolist()
    account_ids = set(orphaned["account_id"].dropna().astype(str))
    with store.connect() as con, con:
        placeholders = ",".join("?" for _ in ids)
        con.execute(f"DELETE FROM transactions WHERE id IN ({placeholders})", tuple(ids))
    store.revision += 1
    removed_accounts = _cleanup_auto_accounts(account_ids)
    statements._sync_store()
    return len(ids), removed_accounts


def manage_view():
    st.subheader("Manage statement data")
    st.caption(
        "Remove imports without losing saved statements, or delete selected statements completely. "
        "Cleanup never touches unrelated manual or FYNTRA-backup transactions."
    )

    meta_rows = statement_flow._statement_meta(force=True)
    orphaned = _orphaned_imports(meta_rows)
    if not orphaned.empty:
        st.warning(
            f"Found {len(orphaned)} imported statement transaction(s) whose saved statement was already deleted. "
            "These can keep old balances visible after a statement is gone."
        )
        preview = orphaned[["date", "merchant", "amount_paise", "account_id"]].copy()
        preview["amount"] = pd.to_numeric(preview.pop("amount_paise"), errors="coerce").fillna(0) / 100
        st.dataframe(preview, hide_index=True, width="stretch")
        confirm_orphans = st.checkbox(
            "Remove these orphaned statement imports",
            key="statement-orphan-confirm",
        )
        if st.button(
            "Clean orphaned statement imports",
            disabled=not confirm_orphans,
            type="primary",
            key="statement-orphan-clean",
        ):
            try:
                removed, accounts = _clean_orphans(orphaned)
                st.session_state.notice = (
                    f"Removed {removed} leftover statement transaction(s)"
                    + (f" and {accounts} empty statement-created account(s)" if accounts else "")
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        st.divider()

    if not meta_rows:
        if orphaned.empty:
            st.info("No saved statements or leftover statement imports to manage.")
        return

    labels = statement_flow._labels(meta_rows)
    chosen = st.multiselect(
        "Statements",
        list(labels),
        format_func=labels.get,
        key="statement-manage-selected-v2",
    )
    action = st.radio(
        "Action",
        ["Remove import only", "Delete completely"],
        horizontal=True,
        key="statement-manage-action-v2",
    )
    if not chosen:
        st.info("Choose one or more statements first.")
        return

    selected_meta = [row for row in meta_rows if row["id"] in chosen]
    selected = statement_flow._fetch_many(selected_meta)
    linked_rows = sum(
        1
        for statement in selected
        for row in statement.get("rows") or []
        if str(row.get("transaction_id") or "")
    )
    st.caption(f"{len(selected)} statement(s) selected · {linked_rows} linked transaction row(s).")

    if action == "Remove import only":
        st.info(
            "Only the ledger import is removed. Saved statements remain available in Saved statements and Compare."
        )
        confirm_text = "I understand and want to remove only these imports"
        button_text = "Remove selected imports"
    else:
        st.warning(
            "This removes imported ledger rows and deletes the selected saved statements. "
            "Unrelated manual/CSV transactions stay untouched."
        )
        confirm_text = "I understand and want to delete these statements completely"
        button_text = "Delete selected statements completely"

    confirmed = st.checkbox(confirm_text, key="statement-manage-confirm-v2")
    if st.button(
        button_text,
        disabled=not confirmed,
        type="primary",
        key="statement-manage-run-v2",
    ):
        try:
            removed, accounts = _batch_remove(
                selected,
                delete_completely=action == "Delete completely",
            )
            if action == "Remove import only":
                message = f"Removed {removed} imported transaction(s); saved statements kept"
            else:
                message = f"Deleted {len(selected)} statement(s) and removed {removed} imported transaction(s)"
            if accounts:
                message += f"; removed {accounts} empty statement-created account(s)"
            st.session_state.notice = message
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
