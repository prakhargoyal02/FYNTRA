import pandas as pd

from database import Store
from statement_tools import clean_rows, import_rows, normalize_table, summary
from statement_flow import _earliest_pending_date, _suggest_opening_balance


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
    assert frame.date.tolist() == ["2026-10-01","2026-10-02","2026-10-03"]
    assert frame.kind.tolist() == ["expense","income","expense"]
    assert frame.category.tolist() == ["Food","Salary","Other"]
    assert frame.payment_method.tolist() == ["UPI","Other","Cash"]
    rows = clean_rows(frame)
    result = summary(rows)
    assert result["count"] == 3
    assert result["income"] == 75000
    assert result["expenses"] == 2450
    assert result["net"] == 72550


def test_day_first_statement_dates_stay_in_september():
    raw = pd.DataFrame({
        "Transaction Date":["01/09/2026","02/09/2026","11/09/2026","28/09/2026"],
        "Narration":["A","B","C","D"],
        "Debit":["100","200","300","400"],
        "Credit":["","","",""],
    })
    frame = normalize_table(raw)
    assert frame.date.tolist() == ["2026-09-01","2026-09-02","2026-09-11","2026-09-28"]


def test_statement_history_helpers_use_pending_rows():
    selected = [{
        "id":"statement-1",
        "name":"September bank",
        "rows":[
            dict(row_key="1",date="2026-09-01",description="SALARY",amount=5000.0,
                 kind="income",category="Salary",payment_method="Bank transfer",balance=15000.0,
                 reference="s1",confidence=95,transaction_id=""),
            dict(row_key="2",date="2026-09-02",description="FOOD",amount=500.0,
                 kind="expense",category="Food",payment_method="UPI",balance=14500.0,
                 reference="f1",confidence=95,transaction_id="already-imported"),
        ],
    }]
    assert _earliest_pending_date(selected) == "2026-09-01"
    assert _suggest_opening_balance(selected) == 10000.0


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
