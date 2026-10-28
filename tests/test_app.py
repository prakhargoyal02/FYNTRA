import os
from pathlib import Path
os.environ['FYNTRA_TESTING']='1'
from streamlit.testing.v1 import AppTest

def test_monthly_review_largest_expense_fallback(tmp_path):
    from database import Store, today
    store=Store(tmp_path/'review.db')
    store.save('accounts',dict(id='a',name='Cash',opening_date='2020-01-01'))
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
    app.session_state.store=store
    app.sidebar.radio[0].set_value('Cash flow & insights').run()
    assert not app.exception
    metric=next(m for m in app.metric if m.label=='Largest expense')
    assert metric.value=='₹0'
    assert metric.help=='No expenses'
    store.save('transactions',dict(date=today().isoformat(),amount_paise=12345,
        kind='expense',account_id='a',category='Food',merchant=''))
    app.run()
    assert not app.exception
    metric=next(m for m in app.metric if m.label=='Largest expense')
    assert metric.value=='₹123'
    assert metric.help=='Food'

def test_all_screens_and_transaction_crud():
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
    assert not app.exception
    nav=app.sidebar.radio[0]
    for page in nav.options:
        nav.set_value(page).run()
        assert not app.exception, (page,[e.message for e in app.exception])
    nav.set_value('Transactions').run()
    app.segmented_control[0].set_value('Add transaction').run()
    assert not app.exception
    next(w for w in app.text_input if w.label=='Merchant / source').set_value('QA merchant')
    next(w for w in app.button if w.label=='Save transaction').click().run()
    assert not app.exception
    store=app.session_state.store
    found=store.frame('transactions').query("merchant == 'QA merchant'")
    assert len(found)==1
    ident=found.iloc[0].id
    app.segmented_control[0].set_value('History').run()
    next(w for w in app.selectbox if w.label=='Select a transaction to edit').set_value(ident).run()
    next(w for w in app.text_input if w.label=='Merchant / source').set_value('QA edited')
    next(w for w in app.button if w.label=='Save transaction').click().run()
    assert store.get('transactions',ident)['merchant']=='QA edited'
    next(w for w in app.selectbox if w.label=='Select a transaction to edit').set_value(ident).run()
    next(w for w in app.checkbox if w.label=='Confirm deletion').check().run()
    next(w for w in app.button if w.label=='Delete record').click().run()
    assert store.get('transactions',ident) is None
    assert not app.exception

def test_secondary_views_and_empty_workspace(tmp_path):
    from database import Store
    app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()
    for page,options in [('Transactions',['Recurring','Add transaction']),('Bills & subscriptions',['Subscriptions','Bills']),('Goals & debt',['Debt','Savings goals'])]:
        app.sidebar.radio[0].set_value(page).run()
        for option in options:
            app.segmented_control[0].set_value(option).run()
            assert not app.exception, (page,option,[e.message for e in app.exception])
    app.session_state.store=Store(tmp_path/'empty-private.db')
    for page in app.sidebar.radio[0].options:
        app.sidebar.radio[0].set_value(page).run()
        assert not app.exception, (page,[e.message for e in app.exception])
