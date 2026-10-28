"""Lossless, formula-safe CSV portability with an atomic prospective-state import."""
from copy import deepcopy
from io import StringIO
import re
from uuid import uuid4
import pandas as pd
from database import TABLES,money

SIGNATURES = {
"profile":{"display_name","currency"},
"accounts":{"name","account_type","opening_balance_paise"},
"transactions":{"date","kind","amount_paise","account_id"},
"budgets":{"month","category","limit_paise"},
"bills":{"due_date","paid","amount_paise"},
"subscriptions":{"next_date","active","frequency","amount_paise","name"},
"savings_goals":{"target_paise","initial_saved_paise","target_date"},
"goal_contributions":{"goal_id","date","amount_paise"},
"debts":{"original_paise","opening_remaining_paise","debt_type"},
"debt_payments":{"debt_id","principal_paise","interest_paise"},
"recurring_transactions":{"next_date","active","kind","amount_paise"},
"net_worth_snapshots":{"date","assets_paise","liabilities_paise"}
}
REFERENCES = {
"account_id":"accounts","to_account_id":"accounts","recurring_id":"recurring_transactions",
"goal_id":"savings_goals","debt_id":"debts","transaction_id":"transactions","parent_id":"bills"
}
BANK_DATE_HEADERS = {"date","transaction date","txn date","value date","posting date","tran date"}
BANK_MONEY_HEADERS = {"debit","credit","withdrawal","deposit","withdrawal amount","deposit amount","debit amount","credit amount","amount","transaction amount","txn amount"}

def _header(value):
    value = re.sub(r"[^a-z0-9]+"," ",str(value or "").strip().casefold())
    return re.sub(r"\s+"," ",value).strip()

def looks_like_bank_statement(columns):
    cols = {_header(col) for col in columns}
    has_date = any(any(alias==col or alias in col for alias in BANK_DATE_HEADERS) for col in cols)
    has_money = any(any(alias==col or alias in col for alias in BANK_MONEY_HEADERS) for col in cols)
    return has_date and has_money

def _safe(value):
    if isinstance(value,str) and value.startswith(("=","+","-","@","\t","\r","'")):
        return "'"+value
    return value

def _unsafed(value):
    if isinstance(value,str) and len(value)>1 and value[0]=="'" and value[1] in "=+-@\t\r'":
        return value[1:]
    return value

def _csv(records):
    frame = pd.DataFrame(records).fillna("")
    return frame.map(_safe).to_csv(index=False,lineterminator="\n").encode("utf-8-sig")

def export_table(store,table):
    rows = store.frame(table).astype(object).to_dict("records")
    if not rows:
        return (",".join(store.columns(table))+"\n").encode()
    return _csv(rows)

def export_bundle(store):
    rows = []
    for table in TABLES:
        records = store.frame(table).astype(object).to_dict("records")
        rows.extend([{"record_type":table,**r} for r in records] or [{"record_type":table,"__empty__":"1"}])
    return _csv(rows)

def detect_type(columns):
    cols = set(columns)
    matches = [t for t,required in SIGNATURES.items() if required<=cols]
    if "kind" in cols and "recurring_transactions" in matches:
        matches = ["recurring_transactions"]
    if len(matches)!=1:
        if looks_like_bank_statement(columns):
            raise ValueError("This looks like a bank statement, not a FYNTRA backup CSV. In Private sign in, open Bank statements → Upload & review. You can analyze a statement there without creating an account.")
        raise ValueError("Cannot identify this CSV from its columns. Use an exported FYNTRA template or the simple transaction template.")
    return matches[0]

def parse_files(store,files):
    incoming = {}
    for name,content in files:
        if len(content)>10*1024*1024:
            raise ValueError(f"{name}: maximum file size is 10 MB.")
        frame = pd.read_csv(StringIO(content.decode("utf-8-sig")),dtype=str,keep_default_na=False)
        if len(frame)>50000:
            raise ValueError("CSV has too many rows.")
        frame = frame.map(_unsafed)
        if "record_type" not in frame and {"date","amount","kind","category","account_name"}<=set(frame.columns):
            accounts = store.frame("accounts").set_index("name").id.to_dict()
            converted = []
            for row in frame.to_dict("records"):
                account = accounts.get(row.pop("account_name"))
                if not account:
                    raise ValueError("Unknown account name. Create the account before importing transactions.")
                row["account_id"] = account
                row["amount_paise"] = money(row.pop("amount"))
                converted.append(row)
            incoming.setdefault("transactions",[]).extend(converted)
            continue
        if "record_type" in frame:
            types = frame.record_type.unique()
            for table in types:
                if table not in TABLES:
                    raise ValueError(f"Unknown record type: {table}")
                cols = store.columns(table)
                part = frame.loc[frame.record_type.eq(table)]
                incoming.setdefault(table,[])
                for row in part.to_dict("records"):
                    if row.get("__empty__")=="1":
                        continue
                    incoming[table].append({k:v for k,v in row.items() if k in cols and (v!="" or k in {"notes","merchant","tags","subcategory","payment_method","source_type","source_id"})})
        else:
            table = detect_type(frame.columns)
            incoming.setdefault(table,[]).extend(frame.to_dict("records"))
    return incoming

def fingerprint(row):
    keys = ("date","time","amount_paise","kind","category","account_id","to_account_id","merchant","notes","tags")
    return tuple(str(row.get(k,"12:00" if k=="time" else "") or "").strip().casefold() for k in keys)

def import_csvs(store,files,mode="add"):
    if mode not in {"add","replace"}:
        raise ValueError("Choose add or replace.")
    incoming = parse_files(store,files)
    candidate = deepcopy(store.dump_state())
    counts = {"added":0,"updated":0,"skipped":0,"types":list(incoming)}
    remaps = {t:{} for t in TABLES}
    for table in TABLES:
        if table not in incoming:
            continue
        existing = candidate["tables"][table] if mode=="add" else []
        by_id = {r["id"]:r for r in existing}
        for row in incoming[table]:
            row = {k:v for k,v in row.items() if v!="" or k not in {"id","source_key","recurring_id","to_account_id","paid_date","transaction_id","parent_id"}}
            row = store._normalize(table,row)
            had_id = bool(row.get("id"))
            old_id = row.setdefault("id",str(uuid4()))
            for key,target in REFERENCES.items():
                if row.get(key):
                    row[key] = remaps[target].get(row[key],row[key])
            duplicate = None
            if table=="accounts":
                duplicate = next((r for r in by_id.values() if r["name"]==row.get("name")),None)
            if table=="budgets":
                duplicate = next((r for r in by_id.values() if (r["month"],r["category"])==(row.get("month"),row.get("category"))),None)
            if table=="transactions" and not had_id:
                # Only ID-less external rows use a content fingerprint. Distinct IDs
                # may represent legitimate identical purchases and must survive backups.
                pool = list(by_id.values())
                duplicate = next((r for r in pool if fingerprint(r)==fingerprint(row)),None)
            if old_id in by_id:
                counts["skipped"] += 1
                continue
            if duplicate:
                remaps[table][old_id] = duplicate["id"]
                counts["skipped"] += 1
                continue
            by_id[old_id] = row
            counts["added"] += 1
        # Pandas dedup is also useful for non-financial records with repeated IDs.
        candidate["tables"][table] = pd.DataFrame(list(by_id.values())).drop_duplicates(subset=["id"]).to_dict("records") if by_id else []
    store.restore_state(candidate)
    return counts
