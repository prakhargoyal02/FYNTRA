import io
import zipfile
import pandas as pd

from database import Store
from statement_tools import clean_rows, import_rows, normalize_table, summary
from statements import _export_csv_bytes, _export_zip_bytes, _flatten_statements


def test_normalize_bank_export_and_summary():
    raw = pd.DataFrame({
        "Txn Date":["01/10/2026","02/10/2026","03/10/2026"],
        "Narration":["UPI ZOMATO","SALARY CREDIT","ATM CASH WITHDRAWAL"],
        "Withdrawal Amt.":["450.00","","2000"],
        "Deposit Amt.":["","75000.00",""],
        "Balance":["10000","85000","83000"],
        "Reference No":["u1","s1","a1"],
    })
    frame = normalize_table(raw)
    assert frame.kind.tolist() == ["expense","income","expense"]
    assert frame.category.tolist() == ["Food","Salary","Other"]
    assert frame.payment_method.tolist() == ["UPI","Other","Cash"]
    rows = clean_rows(frame)
    result = summary(rows)
    assert result["count"] == 3
    assert result["income"] == 75000
    assert result["expenses"] == 2450
    assert result["net"] == 72550


def test_statement_import_is_idempotent(tmp_path):
    store = Store(tmp_path/"statement.db")
    store.save("accounts",dict(id="bank",name="Bank",opening_date="2026-01-01"))
    rows = [
        dict(row_key="1",date="2026-10-01",description="UPI ZOMATO",amount=450.0,
             kind="expense",category="Food",payment_method="UPI",balance=10000,
             reference="u1",confidence=95,transaction_id=""),
        dict(row_key="2",date="2026-10-02",description="SALARY CREDIT",amount=75000.0,
             kind="income",category="Salary",payment_method="Other",balance=85000,
             reference="s1",confidence=95,transaction_id=""),
    ]
    updated, count = import_rows(store,"statement-1","October bank","bank",rows)
    assert count == 2
    assert len(store.frame("transactions")) == 2
    assert all(row["transaction_id"] for row in updated)

    retried = [dict(row,transaction_id="") for row in rows]
    updated_again, count_again = import_rows(store,"statement-1","October bank","bank",retried)
    assert count_again == 0
    assert len(store.frame("transactions")) == 2
    assert all(row["transaction_id"] for row in updated_again)


def test_statement_export_snapshot_can_be_combined_or_separate():
    statements = [
        {"id":"s1","name":"September Salary Account","source_filename":"sep.csv","account_id":"a1",
         "period_start":"2026-09-01","period_end":"2026-09-30","rows":[
             {"date":"2026-09-02","description":"Groceries","amount":500.0,"kind":"expense","category":"Groceries",
              "payment_method":"UPI","balance":9500,"reference":"r1","confidence":95,"transaction_id":""}]},
        {"id":"s2","name":"October Salary Account","source_filename":"oct.csv","account_id":"a1",
         "period_start":"2026-10-01","period_end":"2026-10-31","rows":[
             {"date":"2026-10-02","description":"Food","amount":350.0,"kind":"expense","category":"Food",
              "payment_method":"Card","balance":9150,"reference":"r2","confidence":95,"transaction_id":"tx1"}]},
    ]
    rows = _flatten_statements(statements)
    assert len(rows) == 2
    assert rows[0]["statement_name"] == "September Salary Account"
    assert rows[1]["imported_to_ledger"] is True

    csv_bytes = _export_csv_bytes(rows)
    frame = pd.read_csv(io.BytesIO(csv_bytes))
    assert frame.statement_name.tolist() == ["September Salary Account","October Salary Account"]

    zipped = _export_zip_bytes(rows)
    with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
        assert sorted(archive.namelist()) == ["October_Salary_Account.csv","September_Salary_Account.csv"]
