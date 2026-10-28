"""SQLite ledger: integer paise, parameterized SQL and atomic workflows.

Learning: balances are calculated from the ledger, never independently edited.
Each browser session owns its Store; private stores are never globally cached.
"""
from __future__ import annotations
import calendar
import math
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import pandas as pd

CATEGORIES = ["Food","Rent","Groceries","Shopping","Entertainment","Transport","Fuel",
              "Utilities","Subscriptions","Healthcare","Education","EMI/debt","Travel",
              "Personal care","Gifts","Salary","Freelance","Other"]
ACCOUNT_TYPES = ["bank","savings","cash","credit_card","wallet","investment","other"]
FREQUENCIES = ["once","weekly","monthly","quarterly","yearly"]
SCHEMA = {
"profile": "id TEXT PRIMARY KEY, display_name TEXT NOT NULL DEFAULT 'My finances', currency TEXT NOT NULL DEFAULT 'INR' CHECK(currency='INR'), monthly_limit_paise INTEGER NOT NULL DEFAULT 0 CHECK(monthly_limit_paise>=0)",
"accounts": "id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, account_type TEXT NOT NULL DEFAULT 'bank', opening_balance_paise INTEGER NOT NULL DEFAULT 0, opening_date TEXT NOT NULL, notes TEXT NOT NULL DEFAULT ''",
"recurring_transactions": "id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('income','expense','transfer')), amount_paise INTEGER NOT NULL CHECK(amount_paise>0), category TEXT NOT NULL DEFAULT 'Other', account_id TEXT NOT NULL REFERENCES accounts(id), to_account_id TEXT REFERENCES accounts(id), next_date TEXT NOT NULL, frequency TEXT NOT NULL DEFAULT 'monthly', anchor_day INTEGER NOT NULL DEFAULT 1, active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)), merchant TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT ''",
"transactions": "id TEXT PRIMARY KEY, date TEXT NOT NULL, time TEXT NOT NULL DEFAULT '12:00', amount_paise INTEGER NOT NULL CHECK(amount_paise>0), kind TEXT NOT NULL CHECK(kind IN ('income','expense','transfer')), category TEXT NOT NULL DEFAULT 'Other', subcategory TEXT NOT NULL DEFAULT '', account_id TEXT NOT NULL REFERENCES accounts(id), to_account_id TEXT REFERENCES accounts(id), merchant TEXT NOT NULL DEFAULT '', payment_method TEXT NOT NULL DEFAULT 'Other', notes TEXT NOT NULL DEFAULT '', tags TEXT NOT NULL DEFAULT '', recurring_id TEXT REFERENCES recurring_transactions(id), source_type TEXT NOT NULL DEFAULT '', source_id TEXT NOT NULL DEFAULT '', source_key TEXT UNIQUE, CHECK((kind='transfer' AND to_account_id IS NOT NULL AND account_id<>to_account_id) OR (kind<>'transfer' AND to_account_id IS NULL))",
"budgets": "id TEXT PRIMARY KEY, month TEXT NOT NULL, category TEXT NOT NULL, limit_paise INTEGER NOT NULL CHECK(limit_paise>=0), UNIQUE(month,category)",
"subscriptions": "id TEXT PRIMARY KEY, name TEXT NOT NULL, amount_paise INTEGER NOT NULL CHECK(amount_paise>0), frequency TEXT NOT NULL DEFAULT 'monthly', anchor_day INTEGER NOT NULL DEFAULT 1, account_id TEXT NOT NULL REFERENCES accounts(id), next_date TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'Subscriptions', active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)), notes TEXT NOT NULL DEFAULT ''",
"bills": "id TEXT PRIMARY KEY, name TEXT NOT NULL, amount_paise INTEGER NOT NULL CHECK(amount_paise>0), due_date TEXT NOT NULL, frequency TEXT NOT NULL DEFAULT 'once', anchor_day INTEGER NOT NULL DEFAULT 1, category TEXT NOT NULL DEFAULT 'Utilities', account_id TEXT NOT NULL REFERENCES accounts(id), paid INTEGER NOT NULL DEFAULT 0 CHECK(paid IN (0,1)), paid_date TEXT, transaction_id TEXT REFERENCES transactions(id), parent_id TEXT, notes TEXT NOT NULL DEFAULT ''",
"savings_goals": "id TEXT PRIMARY KEY, name TEXT NOT NULL, target_paise INTEGER NOT NULL CHECK(target_paise>0), initial_saved_paise INTEGER NOT NULL DEFAULT 0 CHECK(initial_saved_paise>=0), target_date TEXT NOT NULL, notes TEXT NOT NULL DEFAULT ''",
"goal_contributions": "id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES savings_goals(id), date TEXT NOT NULL, amount_paise INTEGER NOT NULL CHECK(amount_paise>0), notes TEXT NOT NULL DEFAULT ''",
"debts": "id TEXT PRIMARY KEY, name TEXT NOT NULL, debt_type TEXT NOT NULL DEFAULT 'loan', original_paise INTEGER NOT NULL CHECK(original_paise>0), opening_remaining_paise INTEGER NOT NULL CHECK(opening_remaining_paise>=0), annual_rate REAL NOT NULL DEFAULT 0 CHECK(annual_rate>=0), monthly_payment_paise INTEGER NOT NULL DEFAULT 0 CHECK(monthly_payment_paise>=0), next_date TEXT NOT NULL, notes TEXT NOT NULL DEFAULT ''",
"debt_payments": "id TEXT PRIMARY KEY, debt_id TEXT NOT NULL REFERENCES debts(id), date TEXT NOT NULL, principal_paise INTEGER NOT NULL CHECK(principal_paise>0), interest_paise INTEGER NOT NULL DEFAULT 0 CHECK(interest_paise>=0), account_id TEXT NOT NULL REFERENCES accounts(id), transaction_id TEXT NOT NULL UNIQUE REFERENCES transactions(id), notes TEXT NOT NULL DEFAULT ''",
"net_worth_snapshots": "id TEXT PRIMARY KEY, date TEXT NOT NULL UNIQUE, assets_paise INTEGER NOT NULL, liabilities_paise INTEGER NOT NULL CHECK(liabilities_paise>=0)"
}
TABLES = tuple(SCHEMA)
DATE_FIELDS = {"date","opening_date","next_date","due_date","paid_date","target_date"}
NULLABLE = {"to_account_id","recurring_id","source_key","paid_date","transaction_id","parent_id"}


def today():
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def money(value):
    """Convert rupees to paise with Decimal at the input boundary."""
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or abs(amount) > Decimal("1000000000000"):
            raise ValueError("Amount is outside the supported range.")
        return int((amount*100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Enter a valid amount.") from exc


def advance(value, frequency, anchor=None):
    current = date.fromisoformat(value)
    if frequency == "weekly":
        return (current+timedelta(days=7)).isoformat()
    steps = {"monthly":1,"quarterly":3,"yearly":12}
    if frequency not in steps:
        raise ValueError("Choose a repeating frequency.")
    year, month0 = divmod(current.year*12+current.month-1+steps[frequency],12)
    month = month0+1
    return date(year,month,min(anchor or current.day,calendar.monthrange(year,month)[1])).isoformat()


class Store:
    def __init__(self,path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.revision = 0
        with self.connect() as con, con:
            for table,ddl in SCHEMA.items():
                con.execute(f'CREATE TABLE IF NOT EXISTS "{table}" ({ddl})')
            con.execute("CREATE INDEX IF NOT EXISTS tx_date_idx ON transactions(date)")
            con.execute("CREATE INDEX IF NOT EXISTS tx_account_idx ON transactions(account_id)")
            con.execute("INSERT OR IGNORE INTO profile(id) VALUES ('profile')")

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path,timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
        finally:
            con.close()

    @staticmethod
    def _table(table):
        if table not in SCHEMA:
            raise ValueError("Unsupported record type.")

    def columns(self,table):
        self._table(table)
        with self.connect() as con:
            return [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]

    def frame(self,table):
        self._table(table)
        with self.connect() as con:
            return pd.read_sql_query(f'SELECT * FROM "{table}"',con)

    def get(self,table,record_id):
        self._table(table)
        with self.connect() as con:
            row = con.execute(f'SELECT * FROM "{table}" WHERE id=?',(record_id,)).fetchone()
            return dict(row) if row else None

    def _normalize(self,table,values):
        if set(values)-set(self.columns(table)):
            raise ValueError(f"Unknown columns in {table}.")
        result = {}
        for key,value in values.items():
            if value is None or (isinstance(value,float) and math.isnan(value)):
                if key in NULLABLE:
                    result[key] = None
                continue
            if key.endswith("_paise") or key in {"active","paid","anchor_day"}:
                num = Decimal(str(value))
                if not num.is_finite() or num != num.to_integral_value() or abs(num)>10**14:
                    raise ValueError(f"{key} must be a whole number in range.")
                result[key] = int(num)
            elif key == "annual_rate":
                value = float(value)
                if not math.isfinite(value) or not 0<=value<=1000:
                    raise ValueError("Interest rate must be between 0 and 1000%.")
                result[key] = value
            else:
                result[key] = str(value).strip()
                if len(result[key])>5000:
                    raise ValueError("Text must be 5,000 characters or fewer.")
                if key in DATE_FIELDS and key not in NULLABLE and not result[key]:
                    raise ValueError("A date is required.")
                if key in DATE_FIELDS and result[key]:
                    date.fromisoformat(result[key])
                    if len(result[key])!=10:
                        raise ValueError("Use ISO dates: YYYY-MM-DD.")
                if key in NULLABLE and not result[key]:
                    result[key] = None
        if "category" in result and not result["category"]:
            raise ValueError("A category is required.")
        if "name" in result and not result["name"]:
            raise ValueError("A name is required.")
        if "month" in result:
            date.fromisoformat(result["month"]+"-01")
        if "time" in result:
            datetime.strptime(result["time"],"%H:%M")
        if "frequency" in result and result["frequency"] not in FREQUENCIES:
            raise ValueError("Unsupported frequency.")
        if "account_type" in result and result["account_type"] not in ACCOUNT_TYPES:
            raise ValueError("Unsupported account type.")
        if table in {"subscriptions","recurring_transactions"} and result.get("frequency")=="once":
            raise ValueError("A repeating frequency is required.")
        if "anchor_day" in result and not 1<=result["anchor_day"]<=31:
            raise ValueError("Invalid renewal day.")
        return result

    def _put(self,con,table,values):
        values = self._normalize(table,values)
        record_id = values.setdefault("id",str(uuid4()))
        if not record_id:
            raise ValueError("Record ID cannot be blank.")
        existing = con.execute(f'SELECT * FROM "{table}" WHERE id=?',(record_id,)).fetchone()
        merged = {**(dict(existing) if existing else {}),**values}
        if table=="profile" and record_id!="profile":
            raise ValueError("The profile ID must be 'profile'.")
        if table in {"transactions","recurring_transactions"}:
            if merged.get("kind")=="transfer":
                if not merged.get("to_account_id") or merged["to_account_id"]==merged.get("account_id"):
                    raise ValueError("Transfers require two different accounts.")
            elif merged.get("to_account_id"):
                raise ValueError("Only transfers have a destination account.")
            tx_date = merged.get("date",merged.get("next_date"))
            for field in ("account_id","to_account_id"):
                if merged.get(field):
                    account = con.execute("SELECT opening_date FROM accounts WHERE id=?",(merged[field],)).fetchone()
                    if account and tx_date<account[0]:
                        raise ValueError("Transaction cannot predate its account opening balance.")
        if table=="debts":
            opening = merged.get("opening_remaining_paise",0)
            paid = con.execute("SELECT COALESCE(SUM(principal_paise),0) FROM debt_payments WHERE debt_id=?",(record_id,)).fetchone()[0]
            if opening>merged.get("original_paise",0) or opening<paid:
                raise ValueError("Debt remaining must fit the original debt and recorded payments.")
        keys = list(values)
        placeholders = ",".join("?" for _ in keys)
        updates = ",".join(f'"{k}"=excluded."{k}"' for k in keys if k!="id")
        conflict = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
        con.execute(f'INSERT INTO "{table}" ({",".join(keys)}) VALUES ({placeholders}) ON CONFLICT(id) {conflict}',list(values.values()))
        return record_id

    def save(self,table,values):
        self._table(table)
        existing = self.get(table,values.get("id")) if values.get("id") else None
        if table=="transactions" and existing and existing["source_type"]:
            raise ValueError("This is a linked payment. Undo it before changing its source.")
        if table=="bills" and existing and existing["paid"]:
            raise ValueError("Undo the bill payment before editing this bill.")
        if table=="debt_payments":
            raise ValueError("Use the debt payment form.")
        with self.connect() as con,con:
            record_id = self._put(con,table,values)
            self._validate_graph(con)
        self.revision += 1
        return record_id

    def delete(self,table,record_id):
        self._table(table)
        row = self.get(table,record_id)
        if row is None:
            return
        if table=="profile":
            raise ValueError("The profile cannot be deleted.")
        if table=="transactions" and row["source_type"]:
            raise ValueError("Use Undo payment for this linked transaction.")
        if table=="bills" and row["paid"]:
            raise ValueError("Undo its payment before deleting this bill.")
        if table=="debt_payments":
            return self.undo_payment(row["transaction_id"])
        if table in {"subscriptions","recurring_transactions"}:
            with self.connect() as con:
                if con.execute("SELECT 1 FROM transactions WHERE source_id=?",(record_id,)).fetchone():
                    raise ValueError("This record has payment history. Deactivate it or undo its payments before deleting.")
        with self.connect() as con,con:
            con.execute(f'DELETE FROM "{table}" WHERE id=?',(record_id,))
            self._validate_graph(con)
        self.revision += 1

    def _payment(self,con,*,source_type,source_id,key,amount,account,on,category,name):
        prior = con.execute("SELECT id FROM transactions WHERE source_key=?",(key,)).fetchone()
        if prior:
            return prior[0]
        return self._put(con,"transactions",dict(date=on,amount_paise=amount,kind="expense",
            category=category,account_id=account,merchant=name,source_type=source_type,
            source_id=source_id,source_key=key))

    def pay_bill(self,bill_id,on):
        with self.connect() as con,con:
            bill = dict(con.execute("SELECT * FROM bills WHERE id=?",(bill_id,)).fetchone())
            if bill["paid"]:
                return bill["transaction_id"]
            tx = self._payment(con,source_type="bill",source_id=bill_id,key="bill:"+bill_id,
                amount=bill["amount_paise"],account=bill["account_id"],on=on,category=bill["category"],name=bill["name"])
            con.execute("UPDATE bills SET paid=1,paid_date=?,transaction_id=? WHERE id=?",(on,tx,bill_id))
            if bill["frequency"]!="once":
                nxt = {**bill,"id":str(uuid4()),"due_date":advance(bill["due_date"],bill["frequency"],bill["anchor_day"]),"parent_id":bill_id}
                self._put(con,"bills",nxt)
        self.revision += 1
        return tx

    def pay_subscription(self,subscription_id,on,expected_date=None):
        with self.connect() as con,con:
            sub = dict(con.execute("SELECT * FROM subscriptions WHERE id=?",(subscription_id,)).fetchone())
            if not sub["active"]:
                raise ValueError("Reactivate the subscription before recording payment.")
            if expected_date and expected_date!=sub["next_date"]:
                raise ValueError("Renewal already changed. Refresh before paying again.")
            tx = self._payment(con,source_type="subscription",source_id=subscription_id,
                key=f"subscription:{subscription_id}:{sub['next_date']}",amount=sub["amount_paise"],
                account=sub["account_id"],on=on,category=sub["category"],name=sub["name"])
            con.execute("UPDATE subscriptions SET next_date=? WHERE id=?",(advance(sub["next_date"],sub["frequency"],sub["anchor_day"]),subscription_id))
        self.revision += 1
        return tx

    def pay_debt(self,debt_id,account_id,principal,interest,on):
        with self.connect() as con,con:
            debt = dict(con.execute("SELECT * FROM debts WHERE id=?",(debt_id,)).fetchone())
            paid = con.execute("SELECT COALESCE(SUM(principal_paise),0) FROM debt_payments WHERE debt_id=?",(debt_id,)).fetchone()[0]
            if principal<=0 or interest<0 or principal>debt["opening_remaining_paise"]-paid:
                raise ValueError("Principal must be positive and cannot exceed the debt remaining.")
            payment_id = str(uuid4())
            tx = self._payment(con,source_type="debt",source_id=payment_id,key="debt:"+payment_id,
                amount=principal+interest,account=account_id,on=on,category="EMI/debt",name=debt["name"])
            self._put(con,"debt_payments",dict(id=payment_id,debt_id=debt_id,date=on,principal_paise=principal,
                interest_paise=interest,account_id=account_id,transaction_id=tx))
        self.revision += 1
        return tx

    def undo_payment(self,tx_id):
        with self.connect() as con,con:
            tx = dict(con.execute("SELECT * FROM transactions WHERE id=?",(tx_id,)).fetchone())
            kind = tx["source_type"]
            if kind=="bill":
                children = con.execute("SELECT * FROM bills WHERE parent_id=?",(tx["source_id"],)).fetchall()
                if any(row["paid"] for row in children):
                    raise ValueError("Undo later bill occurrences first.")
                con.execute("DELETE FROM bills WHERE parent_id=?",(tx["source_id"],))
                con.execute("UPDATE bills SET paid=0,paid_date=NULL,transaction_id=NULL WHERE id=?",(tx["source_id"],))
            elif kind=="subscription":
                sub = con.execute("SELECT * FROM subscriptions WHERE id=?",(tx["source_id"],)).fetchone()
                scheduled = tx["source_key"].rsplit(":",1)[1]
                if sub and sub["next_date"]!=advance(scheduled,sub["frequency"],sub["anchor_day"]):
                    raise ValueError("Undo the latest subscription payment first.")
                con.execute("UPDATE subscriptions SET next_date=? WHERE id=?",(scheduled,tx["source_id"]))
            elif kind=="debt":
                con.execute("DELETE FROM debt_payments WHERE transaction_id=?",(tx_id,))
            elif kind=="recurring":
                schedule = con.execute("SELECT * FROM recurring_transactions WHERE id=?",(tx["source_id"],)).fetchone()
                scheduled = tx["source_key"].rsplit(":",1)[1]
                if not schedule or schedule["next_date"]!=advance(scheduled,schedule["frequency"],schedule["anchor_day"]):
                    raise ValueError("Undo the latest generated occurrence first, before changing the schedule.")
                con.execute("UPDATE recurring_transactions SET next_date=? WHERE id=?",(scheduled,tx["source_id"]))
            con.execute("DELETE FROM transactions WHERE id=?",(tx_id,))
        self.revision += 1

    def generate_recurring(self,through):
        end = date.fromisoformat(through)
        if end>today():
            raise ValueError("Only post up to today. Future entries stay on the calendar.")
        count = 0
        with self.connect() as con,con:
            for raw in con.execute("SELECT * FROM recurring_transactions WHERE active=1").fetchall():
                row = dict(raw)
                generated = 0
                while date.fromisoformat(row["next_date"])<=end:
                    if generated>=120:
                        raise ValueError("More than 120 overdue entries. Move the schedule start forward.")
                    key = f"recurring:{row['id']}:{row['next_date']}"
                    if not con.execute("SELECT 1 FROM transactions WHERE source_key=?",(key,)).fetchone():
                        self._put(con,"transactions",dict(date=row["next_date"],kind=row["kind"],amount_paise=row["amount_paise"],
                            category=row["category"],account_id=row["account_id"],to_account_id=row["to_account_id"],
                            merchant=row["merchant"] or row["name"],notes=row["notes"],recurring_id=row["id"],
                            source_type="recurring",source_id=row["id"],source_key=key))
                        count += 1
                    generated += 1
                    row["next_date"] = advance(row["next_date"],row["frequency"],row["anchor_day"])
                con.execute("UPDATE recurring_transactions SET next_date=? WHERE id=?",(row["next_date"],row["id"]))
        self.revision += bool(count)
        return count

    def _validate_graph(self,con):
        if con.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("Related records are missing. Include their accounts and sources.")
        for row in con.execute("SELECT id,opening_remaining_paise FROM debts"):
            paid = con.execute("SELECT COALESCE(SUM(principal_paise),0) FROM debt_payments WHERE debt_id=?",(row[0],)).fetchone()[0]
            if paid>row[1]:
                raise ValueError("Debt payments exceed the recorded debt.")
        invalid = con.execute("""SELECT t.id FROM transactions t JOIN accounts a ON a.id=t.account_id
            LEFT JOIN accounts b ON b.id=t.to_account_id WHERE t.date<a.opening_date OR t.date<b.opening_date""").fetchone()
        if invalid:
            raise ValueError("Account opening date is after a transaction.")
        for tx in con.execute("SELECT * FROM transactions WHERE source_type<>''"):
            targets = {"bill":"bills","subscription":"subscriptions","debt":"debt_payments","recurring":"recurring_transactions"}
            target = targets.get(tx["source_type"])
            if not target or not con.execute(f"SELECT 1 FROM {target} WHERE id=?",(tx["source_id"],)).fetchone():
                raise ValueError("A linked transaction is missing its source record.")
        for p in con.execute("SELECT p.*,t.amount_paise,t.kind,t.source_type,t.source_id,t.account_id AS tx_account,t.date AS tx_date FROM debt_payments p JOIN transactions t ON p.transaction_id=t.id"):
            if p["principal_paise"]+p["interest_paise"]!=p["amount_paise"] or p["source_type"]!="debt" or p["kind"]!="expense" or p["source_id"]!=p["id"] or p["account_id"]!=p["tx_account"] or p["date"]!=p["tx_date"]:
                raise ValueError("Debt payment and ledger entry do not agree.")
        for b in con.execute("SELECT b.*,t.amount_paise AS tx_amount,t.source_type FROM bills b LEFT JOIN transactions t ON t.id=b.transaction_id"):
            if b["paid"] and (b["tx_amount"]!=b["amount_paise"] or b["source_type"]!="bill"):
                raise ValueError("A paid bill must have its matching ledger entry.")

    def dump_state(self):
        return {"schema_version":1,"tables":{t:self.frame(t).to_dict("records") for t in TABLES}}

    def restore_state(self,state):
        """Validate the entire candidate in one transaction; never execute uploaded SQL."""
        if state.get("schema_version")!=1 or set(state.get("tables",{}))!=set(TABLES):
            raise ValueError("Unsupported or incomplete FYNTRA backup.")
        if sum(len(v) for v in state["tables"].values())>50000:
            raise ValueError("Backup exceeds the 50,000-record limit.")
        with self.connect() as con,con:
            con.execute("PRAGMA defer_foreign_keys=ON")
            for table in reversed(TABLES):
                con.execute(f'DELETE FROM "{table}"')
            for table in TABLES:
                seen = set()
                for record in state["tables"][table]:
                    if not record.get("id") or record["id"] in seen:
                        raise ValueError("Missing or duplicate record ID.")
                    seen.add(record["id"])
                    self._put(con,table,record)
            if con.execute("SELECT count(*) FROM profile").fetchone()[0]!=1:
                raise ValueError("A backup must contain exactly one profile.")
            self._validate_graph(con)
        self.revision += 1

