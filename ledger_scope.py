"""Local read views for normal ledger data and imported bank statements."""
from __future__ import annotations

import pandas as pd

STATEMENT_PREFIX = "statement:"
NOTE_PREFIX = "Imported from bank statement: "


def statement_imports(store):
    """Return imported statement ids and readable names using only local SQLite data."""
    frame = store.frame("transactions")
    if frame.empty or "source_key" not in frame:
        return {}
    keys = frame["source_key"].fillna("").astype(str)
    imported = frame.loc[keys.str.startswith(STATEMENT_PREFIX)].copy()
    if imported.empty:
        return {}
    result = {}
    for row in imported.to_dict("records"):
        parts = str(row.get("source_key") or "").split(":", 2)
        if len(parts) < 3:
            continue
        statement_id = parts[1]
        notes = str(row.get("notes") or "")
        name = notes[len(NOTE_PREFIX):].strip() if notes.startswith(NOTE_PREFIX) else statement_id
        result.setdefault(statement_id, name or statement_id)
    return result


class ScopedStore:
    """Read-filter transactions while delegating all writes to the underlying Store."""

    def __init__(self, store, mode="main", statement_id=None):
        self._store = store
        self._mode = mode if mode in {"main", "merged", "statement"} else "main"
        self._statement_id = statement_id

    def frame(self, table):
        frame = self._store.frame(table)
        if table == "transactions":
            if frame.empty or "source_key" not in frame:
                return frame
            keys = frame["source_key"].fillna("").astype(str)
            imported = keys.str.startswith(STATEMENT_PREFIX)
            if self._mode == "main":
                return frame.loc[~imported].copy()
            if self._mode == "statement":
                prefix = f"{STATEMENT_PREFIX}{self._statement_id}:" if self._statement_id else ""
                return frame.loc[keys.str.startswith(prefix)].copy() if prefix else frame.iloc[0:0].copy()
            return frame
        if table == "accounts" and self._mode == "statement":
            tx = self.frame("transactions")
            if tx.empty:
                return frame.iloc[0:0].copy()
            ids = set(tx["account_id"].dropna().astype(str))
            if "to_account_id" in tx:
                ids.update(tx["to_account_id"].dropna().astype(str))
            out = frame.loc[frame["id"].astype(str).isin(ids)].copy()
            if "opening_balance_paise" in out:
                out["opening_balance_paise"] = 0
            return out
        return frame

    def __getattr__(self, name):
        return getattr(self._store, name)


def scoped_store(store, mode="main", statement_id=None):
    return ScopedStore(store, mode, statement_id)
