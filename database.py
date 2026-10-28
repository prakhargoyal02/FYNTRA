"""
FYNTRA database layer
=====================

This file has one job:
store and read data from SQLite.

Why SQLite?
- It comes with Python.
- It saves everything in one local file: fyntra.db
- It is perfect for a learning project and a portfolio app.
"""

import sqlite3
from pathlib import Path
from datetime import date

DB_FILE = Path(__file__).with_name("fyntra.db")


def connect():
    """Open a connection to the FYNTRA database."""
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def setup_database():
    """Create all tables the first time the app runs."""
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                opening_balance REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_date TEXT NOT NULL,
                kind TEXT NOT NULL,
                amount REAL NOT NULL,
                account_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                merchant TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
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
                category TEXT DEFAULT 'Bills',
                paid INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                billing_cycle TEXT NOT NULL DEFAULT 'Monthly',
                next_payment TEXT,
                active INTEGER NOT NULL DEFAULT 1
            );
            """
        )


def rows(query, params=()):
    """Run a SELECT query and return normal Python dictionaries."""
    with connect() as db:
        result = db.execute(query, params).fetchall()
    return [dict(row) for row in result]


def execute(query, params=()):
    """Run INSERT, UPDATE, or DELETE SQL."""
    with connect() as db:
        cursor = db.execute(query, params)
        db.commit()
        return cursor.lastrowid


def add_account(name, account_type, opening_balance):
    return execute(
        "INSERT INTO accounts (name, account_type, opening_balance) VALUES (?, ?, ?)",
        (name, account_type, opening_balance),
    )


def get_accounts():
    return rows("SELECT * FROM accounts ORDER BY name")


def delete_account(account_id):
    used = rows(
        "SELECT COUNT(*) AS total FROM transactions WHERE account_id = ?",
        (account_id,),
    )[0]["total"]
    if used:
        raise ValueError("This account has transactions. Delete those transactions first.")
    execute("DELETE FROM accounts WHERE id = ?", (account_id,))


def add_transaction(transaction_date, kind, amount, account_id, category, merchant="", notes=""):
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    return execute(
        """
        INSERT INTO transactions
        (transaction_date, kind, amount, account_id, category, merchant, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (transaction_date, kind, amount, account_id, category, merchant, notes),
    )


def get_transactions():
    return rows(
        """
        SELECT t.*, a.name AS account_name
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        ORDER BY t.transaction_date DESC, t.id DESC
        """
    )


def delete_transaction(transaction_id):
    execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))


def save_budget(category, monthly_limit):
    existing = rows("SELECT id FROM budgets WHERE category = ?", (category,))
    if existing:
        execute("UPDATE budgets SET monthly_limit = ? WHERE category = ?", (monthly_limit, category))
    else:
        execute("INSERT INTO budgets (category, monthly_limit) VALUES (?, ?)", (category, monthly_limit))


def get_budgets():
    return rows("SELECT * FROM budgets ORDER BY category")


def delete_budget(budget_id):
    execute("DELETE FROM budgets WHERE id = ?", (budget_id,))


def add_goal(name, target_amount, saved_amount, target_date):
    return execute(
        "INSERT INTO goals (name, target_amount, saved_amount, target_date) VALUES (?, ?, ?, ?)",
        (name, target_amount, saved_amount, target_date),
    )


def get_goals():
    return rows("SELECT * FROM goals ORDER BY id DESC")


def update_goal_saved(goal_id, saved_amount):
    execute("UPDATE goals SET saved_amount = ? WHERE id = ?", (saved_amount, goal_id))


def delete_goal(goal_id):
    execute("DELETE FROM goals WHERE id = ?", (goal_id,))


def add_debt(name, total_amount, remaining_amount, interest_rate):
    return execute(
        "INSERT INTO debts (name, total_amount, remaining_amount, interest_rate) VALUES (?, ?, ?, ?)",
        (name, total_amount, remaining_amount, interest_rate),
    )


def get_debts():
    return rows("SELECT * FROM debts ORDER BY id DESC")


def update_debt_remaining(debt_id, remaining_amount):
    execute("UPDATE debts SET remaining_amount = ? WHERE id = ?", (remaining_amount, debt_id))


def delete_debt(debt_id):
    execute("DELETE FROM debts WHERE id = ?", (debt_id,))


def add_bill(name, amount, due_date, category):
    return execute(
        "INSERT INTO bills (name, amount, due_date, category) VALUES (?, ?, ?, ?)",
        (name, amount, due_date, category),
    )


def get_bills():
    return rows("SELECT * FROM bills ORDER BY due_date, id")


def set_bill_paid(bill_id, paid):
    execute("UPDATE bills SET paid = ? WHERE id = ?", (1 if paid else 0, bill_id))


def delete_bill(bill_id):
    execute("DELETE FROM bills WHERE id = ?", (bill_id,))


def add_subscription(name, amount, billing_cycle, next_payment):
    return execute(
        "INSERT INTO subscriptions (name, amount, billing_cycle, next_payment) VALUES (?, ?, ?, ?)",
        (name, amount, billing_cycle, next_payment),
    )


def get_subscriptions():
    return rows("SELECT * FROM subscriptions ORDER BY active DESC, next_payment, name")


def set_subscription_active(subscription_id, active):
    execute("UPDATE subscriptions SET active = ? WHERE id = ?", (1 if active else 0, subscription_id))


def delete_subscription(subscription_id):
    execute("DELETE FROM subscriptions WHERE id = ?", (subscription_id,))


def clear_all_data():
    """Delete app data but keep the database tables."""
    with connect() as db:
        for table in [
            "transactions",
            "accounts",
            "budgets",
            "goals",
            "debts",
            "bills",
            "subscriptions",
        ]:
            db.execute(f"DELETE FROM {table}")
        db.commit()
