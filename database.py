"""
FYNTRA database layer
=====================

This file is responsible only for storing and changing data.

The rest of the project should not contain SQL.
That keeps the project easier to understand:
UI -> database functions -> SQLite.
"""

import calendar
import sqlite3
from datetime import date
from pathlib import Path

DB_FILE = Path(__file__).with_name("fyntra.db")

TABLES = [
    # Child tables first so clear_all_data() respects foreign keys.
    "transactions",
    "bills",
    "subscriptions",
    "recurring_entries",
    "budgets",
    "goals",
    "debts",
    "accounts",
]


def connect():
    """Open the SQLite database and return rows like dictionaries."""
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def rows(query, params=()):
    """Run a SELECT query and return normal Python dictionaries."""
    with connect() as db:
        result = db.execute(query, params).fetchall()
    return [dict(row) for row in result]


def execute(query, params=()):
    """Run one INSERT, UPDATE or DELETE query."""
    with connect() as db:
        cursor = db.execute(query, params)
        db.commit()
        return cursor.lastrowid


def table_columns(table):
    """Return the column names that currently exist in a table."""
    return {row["name"] for row in rows(f"PRAGMA table_info({table})")}


def ensure_column(table, definition):
    """
    Add a column when an older local database does not have it yet.

    Example:
        ensure_column("transactions", "tags TEXT DEFAULT ''")
    """
    name = definition.split()[0]
    if name not in table_columns(table):
        execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def setup_database():
    """Create the database tables and safely upgrade older local copies."""
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                opening_balance REAL NOT NULL DEFAULT 0,
                opening_date TEXT
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                kind TEXT NOT NULL,
                amount REAL NOT NULL,
                account_id INTEGER NOT NULL,
                to_account_id INTEGER,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                merchant TEXT DEFAULT '',
                payment_method TEXT DEFAULT 'Other',
                tags TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                recurring_id INTEGER,
                bill_id INTEGER,
                subscription_id INTEGER,
                debt_id INTEGER,
                debt_principal REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                saved_amount REAL NOT NULL DEFAULT 0,
                target_date TEXT
            );

            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                total_amount REAL NOT NULL,
                remaining_amount REAL NOT NULL,
                interest_rate REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                due_date TEXT NOT NULL,
                frequency TEXT NOT NULL DEFAULT 'One-time',
                account_id INTEGER,
                category TEXT DEFAULT 'Bills',
                paid INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                billing_cycle TEXT NOT NULL DEFAULT 'Monthly',
                next_payment TEXT,
                account_id INTEGER,
                category TEXT DEFAULT 'Subscriptions',
                payment_method TEXT DEFAULT 'Card',
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS recurring_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                amount REAL NOT NULL,
                account_id INTEGER NOT NULL,
                to_account_id INTEGER,
                category TEXT NOT NULL,
                merchant TEXT DEFAULT '',
                payment_method TEXT DEFAULT 'Other',
                tags TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                frequency TEXT NOT NULL DEFAULT 'Monthly',
                next_date TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id)
            );
            """
        )

    # These upgrades make the new code work even if someone already ran
    # an earlier version of the beginner project.
    upgrades = {
        "accounts": [
            "opening_date TEXT",
        ],
        "transactions": [
            "to_account_id INTEGER",
            "subcategory TEXT DEFAULT ''",
            "payment_method TEXT DEFAULT 'Other'",
            "tags TEXT DEFAULT ''",
            "recurring_id INTEGER",
            "bill_id INTEGER",
            "subscription_id INTEGER",
            "debt_id INTEGER",
            "debt_principal REAL NOT NULL DEFAULT 0",
        ],
        "bills": [
            "frequency TEXT NOT NULL DEFAULT 'One-time'",
            "account_id INTEGER",
        ],
        "subscriptions": [
            "account_id INTEGER",
            "category TEXT DEFAULT 'Subscriptions'",
            "payment_method TEXT DEFAULT 'Card'",
        ],
    }

    for table, definitions in upgrades.items():
        for definition in definitions:
            ensure_column(table, definition)


def advance_date(value, frequency):
    """Move a YYYY-MM-DD date forward by a simple recurring frequency."""
    current = date.fromisoformat(str(value)[:10])

    if frequency == "Weekly":
        return date.fromordinal(current.toordinal() + 7).isoformat()

    if frequency == "Yearly":
        try:
            return current.replace(year=current.year + 1).isoformat()
        except ValueError:
            return current.replace(year=current.year + 1, day=28).isoformat()

    # Monthly is the default.
    year = current.year + (1 if current.month == 12 else 0)
    month = 1 if current.month == 12 else current.month + 1
    day = min(current.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


# ------------------------------------------------------------------
# Accounts
# ------------------------------------------------------------------

def add_account(name, account_type, opening_balance, opening_date=None):
    return execute(
        """
        INSERT INTO accounts (name, account_type, opening_balance, opening_date)
        VALUES (?, ?, ?, ?)
        """,
        (name, account_type, opening_balance, opening_date or date.today().isoformat()),
    )


def get_accounts():
    return rows("SELECT * FROM accounts ORDER BY name")


def delete_account(account_id):
    used = rows(
        """
        SELECT COUNT(*) AS total
        FROM transactions
        WHERE account_id = ? OR to_account_id = ?
        """,
        (account_id, account_id),
    )[0]["total"]

    if used:
        raise ValueError("This account has transactions. Delete those transactions first.")

    execute("DELETE FROM accounts WHERE id = ?", (account_id,))


# ------------------------------------------------------------------
# Transactions
# ------------------------------------------------------------------

def add_transaction(
    transaction_date,
    kind,
    amount,
    account_id,
    category,
    merchant="",
    notes="",
    to_account_id=None,
    subcategory="",
    payment_method="Other",
    tags="",
    recurring_id=None,
    bill_id=None,
    subscription_id=None,
    debt_id=None,
    debt_principal=0,
):
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if kind == "transfer":
        if not to_account_id:
            raise ValueError("Choose the destination account for a transfer.")
        if int(account_id) == int(to_account_id):
            raise ValueError("Transfer accounts must be different.")

    return execute(
        """
        INSERT INTO transactions (
            transaction_date, kind, amount, account_id, to_account_id,
            category, subcategory, merchant, payment_method, tags, notes,
            recurring_id, bill_id, subscription_id, debt_id, debt_principal
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transaction_date,
            kind,
            amount,
            account_id,
            to_account_id,
            category,
            subcategory,
            merchant,
            payment_method,
            tags,
            notes,
            recurring_id,
            bill_id,
            subscription_id,
            debt_id,
            debt_principal,
        ),
    )


def update_transaction(
    transaction_id,
    transaction_date,
    kind,
    amount,
    account_id,
    category,
    merchant="",
    notes="",
    to_account_id=None,
    subcategory="",
    payment_method="Other",
    tags="",
):
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")

    if kind == "transfer" and (
        not to_account_id or int(account_id) == int(to_account_id)
    ):
        raise ValueError("Choose a different destination account.")

    execute(
        """
        UPDATE transactions
        SET transaction_date = ?, kind = ?, amount = ?, account_id = ?,
            to_account_id = ?, category = ?, subcategory = ?, merchant = ?,
            payment_method = ?, tags = ?, notes = ?
        WHERE id = ?
        """,
        (
            transaction_date,
            kind,
            amount,
            account_id,
            to_account_id,
            category,
            subcategory,
            merchant,
            payment_method,
            tags,
            notes,
            transaction_id,
        ),
    )


def get_transactions():
    return rows(
        """
        SELECT
            t.*,
            source.name AS account_name,
            destination.name AS to_account_name
        FROM transactions t
        JOIN accounts source ON source.id = t.account_id
        LEFT JOIN accounts destination ON destination.id = t.to_account_id
        ORDER BY t.transaction_date DESC, t.id DESC
        """
    )


def get_transaction(transaction_id):
    result = rows("SELECT * FROM transactions WHERE id = ?", (transaction_id,))
    return result[0] if result else None


def duplicate_transaction(transaction_id):
    tx = get_transaction(transaction_id)
    if not tx:
        raise ValueError("Transaction not found.")

    return add_transaction(
        tx["transaction_date"],
        tx["kind"],
        tx["amount"],
        tx["account_id"],
        tx["category"],
        tx["merchant"],
        tx["notes"],
        tx["to_account_id"],
        tx["subcategory"],
        tx["payment_method"],
        tx["tags"],
    )


def delete_transaction(transaction_id):
    """
    Delete a transaction.

    If it was a debt payment, put the principal back into the debt balance.
    This keeps a linked debt payment reversible.
    """
    tx = get_transaction(transaction_id)

    if tx and tx.get("debt_id") and float(tx.get("debt_principal") or 0) > 0:
        execute(
            """
            UPDATE debts
            SET remaining_amount = MIN(total_amount, remaining_amount + ?)
            WHERE id = ?
            """,
            (float(tx["debt_principal"]), tx["debt_id"]),
        )

    execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))


# ------------------------------------------------------------------
# Budgets
# ------------------------------------------------------------------

def save_budget(category, monthly_limit):
    existing = rows("SELECT id FROM budgets WHERE category = ?", (category,))

    if existing:
        execute(
            "UPDATE budgets SET monthly_limit = ? WHERE category = ?",
            (monthly_limit, category),
        )
    else:
        execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)",
            (category, monthly_limit),
        )


def get_budgets():
    return rows("SELECT * FROM budgets ORDER BY category")


def delete_budget(budget_id):
    execute("DELETE FROM budgets WHERE id = ?", (budget_id,))


# ------------------------------------------------------------------
# Goals
# ------------------------------------------------------------------

def add_goal(name, target_amount, saved_amount, target_date):
    return execute(
        """
        INSERT INTO goals (name, target_amount, saved_amount, target_date)
        VALUES (?, ?, ?, ?)
        """,
        (name, target_amount, saved_amount, target_date),
    )


def get_goals():
    return rows("SELECT * FROM goals ORDER BY target_date, id")


def update_goal_saved(goal_id, saved_amount):
    execute(
        "UPDATE goals SET saved_amount = ? WHERE id = ?",
        (saved_amount, goal_id),
    )


def delete_goal(goal_id):
    execute("DELETE FROM goals WHERE id = ?", (goal_id,))


# ------------------------------------------------------------------
# Debt
# ------------------------------------------------------------------

def add_debt(name, total_amount, remaining_amount, interest_rate):
    return execute(
        """
        INSERT INTO debts (name, total_amount, remaining_amount, interest_rate)
        VALUES (?, ?, ?, ?)
        """,
        (name, total_amount, remaining_amount, interest_rate),
    )


def get_debts():
    return rows("SELECT * FROM debts ORDER BY id DESC")


def update_debt_remaining(debt_id, remaining_amount):
    execute(
        "UPDATE debts SET remaining_amount = ? WHERE id = ?",
        (remaining_amount, debt_id),
    )


def record_debt_payment(debt_id, principal, interest, account_id, payment_date):
    if principal < 0 or interest < 0 or principal + interest <= 0:
        raise ValueError("Enter a principal or interest payment.")

    debt = rows("SELECT * FROM debts WHERE id = ?", (debt_id,))
    if not debt:
        raise ValueError("Debt not found.")

    debt = debt[0]
    principal = min(float(principal), float(debt["remaining_amount"]))
    new_balance = max(float(debt["remaining_amount"]) - principal, 0)

    execute(
        "UPDATE debts SET remaining_amount = ? WHERE id = ?",
        (new_balance, debt_id),
    )

    return add_transaction(
        payment_date,
        "expense",
        principal + float(interest),
        account_id,
        "Debt payment",
        merchant=debt["name"],
        notes=f"Principal ₹{principal:.2f}; interest ₹{float(interest):.2f}",
        payment_method="Bank transfer",
        debt_id=debt_id,
        debt_principal=principal,
    )


def delete_debt(debt_id):
    linked = rows(
        "SELECT COUNT(*) AS total FROM transactions WHERE debt_id = ?",
        (debt_id,),
    )[0]["total"]

    if linked:
        raise ValueError("Delete linked debt-payment transactions first.")

    execute("DELETE FROM debts WHERE id = ?", (debt_id,))


# ------------------------------------------------------------------
# Bills
# ------------------------------------------------------------------

def add_bill(name, amount, due_date, category, frequency="One-time", account_id=None):
    return execute(
        """
        INSERT INTO bills (name, amount, due_date, frequency, account_id, category)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, amount, due_date, frequency, account_id, category),
    )


def get_bills():
    return rows(
        """
        SELECT bills.*, accounts.name AS account_name
        FROM bills
        LEFT JOIN accounts ON accounts.id = bills.account_id
        ORDER BY paid, due_date, bills.id
        """
    )


def pay_bill(bill_id, payment_date=None):
    bill = rows("SELECT * FROM bills WHERE id = ?", (bill_id,))
    if not bill:
        raise ValueError("Bill not found.")

    bill = bill[0]

    if not bill["account_id"]:
        raise ValueError("Choose an account for this bill before recording payment.")

    payment_date = payment_date or date.today().isoformat()

    transaction_id = add_transaction(
        payment_date,
        "expense",
        float(bill["amount"]),
        bill["account_id"],
        bill["category"] or "Bills",
        merchant=bill["name"],
        payment_method="Other",
        bill_id=bill_id,
    )

    if bill["frequency"] == "One-time":
        execute("UPDATE bills SET paid = 1 WHERE id = ?", (bill_id,))
    else:
        execute(
            "UPDATE bills SET due_date = ?, paid = 0 WHERE id = ?",
            (advance_date(bill["due_date"], bill["frequency"]), bill_id),
        )

    return transaction_id


def set_bill_paid(bill_id, paid):
    execute(
        "UPDATE bills SET paid = ? WHERE id = ?",
        (1 if paid else 0, bill_id),
    )


def delete_bill(bill_id):
    execute("DELETE FROM bills WHERE id = ?", (bill_id,))


# ------------------------------------------------------------------
# Subscriptions
# ------------------------------------------------------------------

def add_subscription(
    name,
    amount,
    billing_cycle,
    next_payment,
    account_id=None,
    category="Subscriptions",
    payment_method="Card",
):
    return execute(
        """
        INSERT INTO subscriptions (
            name, amount, billing_cycle, next_payment,
            account_id, category, payment_method
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            amount,
            billing_cycle,
            next_payment,
            account_id,
            category,
            payment_method,
        ),
    )


def get_subscriptions():
    return rows(
        """
        SELECT subscriptions.*, accounts.name AS account_name
        FROM subscriptions
        LEFT JOIN accounts ON accounts.id = subscriptions.account_id
        ORDER BY active DESC, next_payment, subscriptions.name
        """
    )


def record_subscription_payment(subscription_id, payment_date=None):
    result = rows(
        "SELECT * FROM subscriptions WHERE id = ?",
        (subscription_id,),
    )
    if not result:
        raise ValueError("Subscription not found.")

    item = result[0]
    if not item["account_id"]:
        raise ValueError("Choose an account for this subscription first.")

    payment_date = payment_date or date.today().isoformat()

    transaction_id = add_transaction(
        payment_date,
        "expense",
        float(item["amount"]),
        item["account_id"],
        item["category"] or "Subscriptions",
        merchant=item["name"],
        payment_method=item["payment_method"] or "Card",
        subscription_id=subscription_id,
    )

    if item["next_payment"]:
        execute(
            "UPDATE subscriptions SET next_payment = ? WHERE id = ?",
            (
                advance_date(item["next_payment"], item["billing_cycle"]),
                subscription_id,
            ),
        )

    return transaction_id


def set_subscription_active(subscription_id, active):
    execute(
        "UPDATE subscriptions SET active = ? WHERE id = ?",
        (1 if active else 0, subscription_id),
    )


def delete_subscription(subscription_id):
    execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))


# ------------------------------------------------------------------
# Recurring transaction schedules
# ------------------------------------------------------------------

def add_recurring_entry(
    name,
    kind,
    amount,
    account_id,
    category,
    frequency,
    next_date,
    to_account_id=None,
    merchant="",
    payment_method="Other",
    tags="",
    notes="",
):
    return execute(
        """
        INSERT INTO recurring_entries (
            name, kind, amount, account_id, to_account_id,
            category, merchant, payment_method, tags, notes,
            frequency, next_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            kind,
            amount,
            account_id,
            to_account_id,
            category,
            merchant,
            payment_method,
            tags,
            notes,
            frequency,
            next_date,
        ),
    )


def get_recurring_entries():
    return rows(
        """
        SELECT
            recurring_entries.*,
            source.name AS account_name,
            destination.name AS to_account_name
        FROM recurring_entries
        JOIN accounts source ON source.id = recurring_entries.account_id
        LEFT JOIN accounts destination ON destination.id = recurring_entries.to_account_id
        ORDER BY active DESC, next_date, recurring_entries.name
        """
    )


def set_recurring_active(recurring_id, active):
    execute(
        "UPDATE recurring_entries SET active = ? WHERE id = ?",
        (1 if active else 0, recurring_id),
    )


def delete_recurring_entry(recurring_id):
    execute("DELETE FROM recurring_entries WHERE id = ?", (recurring_id,))


def generate_due_recurring(until_date=None):
    """
    Create every recurring entry due on or before until_date.

    Duplicate protection:
    before creating a scheduled transaction, check whether the same
    schedule already generated one for that exact due date.
    """
    until_date = until_date or date.today().isoformat()
    created = 0

    schedules = rows(
        """
        SELECT * FROM recurring_entries
        WHERE active = 1 AND next_date <= ?
        ORDER BY next_date, id
        """,
        (until_date,),
    )

    for schedule in schedules:
        next_date = schedule["next_date"]

        # Generate missed occurrences one by one.
        while next_date <= until_date:
            exists = rows(
                """
                SELECT id FROM transactions
                WHERE recurring_id = ? AND transaction_date = ?
                """,
                (schedule["id"], next_date),
            )

            if not exists:
                add_transaction(
                    next_date,
                    schedule["kind"],
                    float(schedule["amount"]),
                    schedule["account_id"],
                    schedule["category"],
                    merchant=schedule["merchant"],
                    notes=schedule["notes"],
                    to_account_id=schedule["to_account_id"],
                    payment_method=schedule["payment_method"],
                    tags=schedule["tags"],
                    recurring_id=schedule["id"],
                )
                created += 1

            next_date = advance_date(next_date, schedule["frequency"])

        execute(
            "UPDATE recurring_entries SET next_date = ? WHERE id = ?",
            (next_date, schedule["id"]),
        )

    return created


# ------------------------------------------------------------------
# Backup / restore helpers
# ------------------------------------------------------------------

def export_table(table):
    if table not in TABLES:
        raise ValueError("Unknown table.")
    return rows(f"SELECT * FROM {table} ORDER BY id")


def replace_table(table, records):
    """
    Replace one table using records from a trusted FYNTRA backup.

    This is intentionally small and explicit, not a general SQL loader.
    """
    if table not in TABLES:
        raise ValueError("Unknown table.")

    with connect() as db:
        db.execute(f"DELETE FROM {table}")

        if not records:
            db.commit()
            return

        columns = [column for column in records[0] if column in table_columns(table)]
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(columns)

        for record in records:
            values = [record.get(column) for column in columns]
            db.execute(
                f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
                values,
            )

        db.commit()


def clear_all_data():
    """Delete all user-created data but keep the table structure."""
    with connect() as db:
        for table in TABLES:
            db.execute(f"DELETE FROM {table}")
        db.commit()
