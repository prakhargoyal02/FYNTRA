"""
Simple CSV and backup tools for FYNTRA.

The old project had a very advanced import system.
This rebuild keeps the important portability features while making the code
short enough to understand:
- export transactions.csv
- download a transaction template
- export a full ZIP backup containing one CSV per table
- restore a full FYNTRA backup ZIP
"""

import io
import zipfile

import pandas as pd

import database as db


def transactions_csv():
    """Return all transactions as CSV bytes."""
    frame = pd.DataFrame(db.get_transactions())
    if frame.empty:
        frame = pd.DataFrame(
            columns=[
                "transaction_date",
                "kind",
                "amount",
                "account_name",
                "to_account_name",
                "category",
                "subcategory",
                "merchant",
                "payment_method",
                "tags",
                "notes",
            ]
        )
    return frame.to_csv(index=False).encode("utf-8")


def transaction_template_csv():
    """A small CSV users can fill in manually."""
    template = pd.DataFrame(
        [
            {
                "transaction_date": "2026-10-01",
                "kind": "expense",
                "amount": 250.00,
                "account_name": "Main Bank",
                "to_account_name": "",
                "category": "Food",
                "subcategory": "Lunch",
                "merchant": "Example Cafe",
                "payment_method": "UPI",
                "tags": "work",
                "notes": "",
            }
        ]
    )
    return template.to_csv(index=False).encode("utf-8")


def import_transactions(file_bytes):
    """
    Import a simple transaction CSV.

    Account names must already exist in FYNTRA.
    Existing rows are not deleted.
    """
    frame = pd.read_csv(io.BytesIO(file_bytes))

    required = {"transaction_date", "kind", "amount", "account_name", "category"}
    missing = required - set(frame.columns)

    if missing:
        raise ValueError(
            "Missing required columns: " + ", ".join(sorted(missing))
        )

    account_lookup = {row["name"]: row["id"] for row in db.get_accounts()}
    imported = 0

    for record in frame.fillna("").to_dict("records"):
        account_name = str(record["account_name"]).strip()
        if account_name not in account_lookup:
            raise ValueError(f"Unknown account: {account_name}")

        to_name = str(record.get("to_account_name", "")).strip()
        to_account_id = None

        if record["kind"] == "transfer":
            if to_name not in account_lookup:
                raise ValueError(f"Unknown destination account: {to_name}")
            to_account_id = account_lookup[to_name]

        db.add_transaction(
            str(record["transaction_date"])[:10],
            str(record["kind"]).strip().lower(),
            float(record["amount"]),
            account_lookup[account_name],
            str(record["category"]).strip() or "Other",
            merchant=str(record.get("merchant", "")).strip(),
            notes=str(record.get("notes", "")).strip(),
            to_account_id=to_account_id,
            subcategory=str(record.get("subcategory", "")).strip(),
            payment_method=str(record.get("payment_method", "Other")).strip()
            or "Other",
            tags=str(record.get("tags", "")).strip(),
        )
        imported += 1

    return imported


def export_bundle():
    """Return a ZIP file containing every FYNTRA table as CSV."""
    memory = io.BytesIO()

    with zipfile.ZipFile(memory, "w", zipfile.ZIP_DEFLATED) as archive:
        for table in db.TABLES:
            frame = pd.DataFrame(db.export_table(table))
            archive.writestr(
                f"{table}.csv",
                frame.to_csv(index=False),
            )

    memory.seek(0)
    return memory.getvalue()


def restore_bundle(file_bytes):
    """
    Replace all FYNTRA data using a backup created by export_bundle().

    Tables are restored in relationship-safe order.
    """
    safe_order = [
        "accounts",
        "budgets",
        "goals",
        "debts",
        "bills",
        "subscriptions",
        "recurring_entries",
        "transactions",
    ]

    with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
        names = set(archive.namelist())

        missing = {
            f"{table}.csv" for table in safe_order
            if f"{table}.csv" not in names
        }
        if missing:
            raise ValueError(
                "This is not a complete FYNTRA backup. Missing: "
                + ", ".join(sorted(missing))
            )

        data = {}
        for table in safe_order:
            content = archive.read(f"{table}.csv")
            if not content.strip():
                data[table] = []
                continue

            frame = pd.read_csv(io.BytesIO(content))
            frame = frame.where(pd.notna(frame), None)
            data[table] = frame.to_dict("records")

    db.clear_all_data()

    for table in safe_order:
        db.replace_table(table, data[table])

    return sum(len(records) for records in data.values())
