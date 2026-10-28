import pandas as pd

from data_workspace import classify_file
from database import Store
from csv_tools import export_bundle


def test_unified_upload_detects_realistic_bank_csv(tmp_path):
    store = Store(tmp_path / "unified-bank.db")
    content = (
        "FYNTRA SAMPLE BANK,,,,,\n"
        "Account Number,XXXX4821,,Statement Period,01/10/2026 - 31/10/2026,\n"
        "Account Holder,Demo User,,Currency,INR,\n"
        "Transaction Date,Transaction Remarks,Withdrawal Amt.,Deposit Amt.,Closing Balance,Chq./Ref.No.\n"
        "01/10/2026,SALARY CREDIT NEFT ACME,,55000.00,105000.00,NEFT-1\n"
        "02/10/2026,UPI SWIGGY,620.00,,104380.00,UPI-2\n"
    ).encode("utf-8-sig")

    result = classify_file(store, "bank_statement.csv", content)

    assert result["kind"] == "statement"
    frame = result["frame"]
    assert len(frame) == 2
    assert frame.kind.tolist() == ["income", "expense"]
    assert frame.amount.tolist() == [55000.0, 620.0]


def test_unified_upload_keeps_fyntra_backup_path(tmp_path):
    store = Store(tmp_path / "unified-backup.db")
    store.save("accounts", {"name": "Wallet", "account_type": "cash", "opening_date": "2026-01-01"})
    bundle = export_bundle(store)

    result = classify_file(store, "fyntra_bundle.csv", bundle)

    assert result["kind"] == "fyntra"
    assert "accounts" in result["parsed"]
