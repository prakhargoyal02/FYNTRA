from database import Store
from ledger_scope import scoped_store, statement_imports
from statement_tools import import_rows


def test_main_merged_and_single_statement_views(tmp_path):
    store = Store(tmp_path/"scope.db")
    store.save("accounts",dict(id="bank",name="Bank",opening_date="2026-01-01",opening_balance_paise=100000))
    store.save("transactions",dict(
        id="manual-1",date="2026-10-01",time="12:00",amount_paise=10000,kind="expense",
        category="Food",account_id="bank",merchant="Manual expense"
    ))
    rows = [dict(
        row_key="1",date="2026-10-02",description="Statement expense",amount=250.0,
        kind="expense",category="Shopping",payment_method="Card",balance=650.0,
        reference="r1",confidence=95,transaction_id=""
    )]
    import_rows(store,"statement-123","October Bank","bank",rows)

    imported = statement_imports(store)
    assert imported == {"statement-123":"October Bank"}

    main = scoped_store(store,"main")
    merged = scoped_store(store,"merged")
    single = scoped_store(store,"statement","statement-123")

    assert main.frame("transactions").id.tolist() == ["manual-1"]
    assert len(merged.frame("transactions")) == 2
    assert len(single.frame("transactions")) == 1
    assert single.frame("transactions").iloc[0].merchant == "Statement expense"
    assert single.frame("accounts").iloc[0].opening_balance_paise == 0
