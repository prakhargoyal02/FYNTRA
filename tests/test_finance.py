import os
os.environ['FYNTRA_TESTING']='1'
from datetime import date
from copy import deepcopy
import pytest
import sqlite3
import numpy as np
from database import Store, money, advance, today
from demo_data import seed_demo
from csv_tools import export_bundle, import_csvs
import analytics as an

@pytest.fixture
def store(tmp_path):
    s=Store(tmp_path/'test.db')
    s.save('accounts',dict(id='a',name='Cash',opening_date='2020-01-01',opening_balance_paise=100000))
    s.save('accounts',dict(id='b',name='Savings',opening_date='2020-01-01'))
    return s

def tx(s,**kw):
    return s.save('transactions',dict(date=today().isoformat(),amount_paise=10000,kind='expense',account_id='a',category='Food',**kw))

def test_money_and_transfer(store):
    assert money('10.125')==1013
    for bad in ['NaN','Infinity','bad']:
        with pytest.raises(ValueError): money(bad)
    store.save('transactions',dict(date=today().isoformat(),amount_paise=10000,kind='transfer',account_id='a',to_account_id='b'))
    assert an.account_summary(store).balance.sum()==1000
    assert an.overview(store,today().strftime('%Y-%m'))['expenses']==0
    with pytest.raises(ValueError): store.save('transactions',dict(date=today().isoformat(),amount_paise=1,kind='transfer',account_id='a',to_account_id='a'))

@pytest.mark.parametrize('spent,status',[(6000,'Healthy'),(6001,'Watch'),(8500,'Watch'),(8501,'Near limit'),(10000,'Near limit'),(10001,'Over budget')])
def test_budget_thresholds(store,spent,status):
    store.save('budgets',dict(month=today().strftime('%Y-%m'),category='Food',limit_paise=10000))
    store.save('transactions',dict(date=today().isoformat(),amount_paise=spent,kind='expense',account_id='a',category='Food'))
    assert an.budget_summary(store,today().strftime('%Y-%m')).iloc[0].status==status

def test_zero_income_and_empty(tmp_path):
    s=Store(tmp_path/'empty.db')
    assert an.overview(s,today().strftime('%Y-%m'))['savings_rate'] is None
    assert an.monthly_summary(s).empty
    for fn in [an.goal_summary,an.debt_summary,an.account_summary,an.net_worth_history]: assert fn(s).empty

@pytest.mark.parametrize('merchant,expected', [('Cafe', 'Cafe'), ('', 'Food'), ('   ', 'Food')])
def test_monthly_review_largest_expense_label(store,merchant,expected):
    tx(store,merchant=merchant)
    store.save('transactions',dict(date=today().isoformat(),amount_paise=5000,
        kind='expense',account_id='a',category='Shopping',merchant='Smaller purchase'))
    store.save('transactions',dict(date=today().isoformat(),amount_paise=50000,
        kind='income',account_id='a',merchant='Salary'))
    review=an.monthly_review(store,today().strftime('%Y-%m'))
    assert review['largest_expense']==expected
    assert review['largest_amount']==100.0

def test_monthly_review_without_expenses(store):
    store.save('transactions',dict(date=today().isoformat(),amount_paise=50000,
        kind='income',account_id='a',merchant='Salary'))
    review=an.monthly_review(store,today().strftime('%Y-%m'))
    assert review['largest_expense'] is None
    assert review['largest_amount']==0.0

def test_bill_idempotent_and_undo(store):
    bill=store.save('bills',dict(name='Rent',amount_paise=10000,due_date=today().isoformat(),frequency='monthly',anchor_day=31,account_id='a'))
    first=store.pay_bill(bill,today().isoformat())
    assert store.pay_bill(bill,today().isoformat())==first
    assert len(store.frame('transactions'))==1
    assert len(store.frame('bills'))==2
    store.undo_payment(first)
    assert len(store.frame('bills'))==1
    assert not store.get('bills',bill)['paid']
    assert store.frame('transactions').empty

def test_subscription_stale_guard(store):
    sub=store.save('subscriptions',dict(name='Example',amount_paise=10000,next_date=today().isoformat(),account_id='a',frequency='monthly',anchor_day=31))
    first=store.pay_subscription(sub,today().isoformat(),today().isoformat())
    with pytest.raises(ValueError): store.pay_subscription(sub,today().isoformat(),today().isoformat())
    store.undo_payment(first)
    assert store.get('subscriptions',sub)['next_date']==today().isoformat()

def test_debt_atomic_payment(store):
    debt=store.save('debts',dict(name='Loan',original_paise=100000,opening_remaining_paise=50000,next_date=today().isoformat()))
    before=store.dump_state()
    with pytest.raises(ValueError): store.pay_debt(debt,'a',50001,0,today().isoformat())
    assert store.dump_state()==before
    first=store.pay_debt(debt,'a',10000,1000,today().isoformat())
    assert an.debt_summary(store).iloc[0].remaining==400
    assert an.overview(store,today().strftime('%Y-%m'))['expenses']==110
    store.undo_payment(first)
    assert an.debt_summary(store).iloc[0].remaining==500

def test_recurring_clipping_idempotency(store):
    assert advance('2024-01-31','monthly',31)=='2024-02-29'
    assert advance('2024-02-29','monthly',31)=='2024-03-31'
    rid=store.save('recurring_transactions',dict(name='Salary',kind='income',amount_paise=10000,account_id='a',next_date=today().isoformat(),frequency='monthly',anchor_day=today().day))
    assert store.generate_recurring(today().isoformat())==1
    assert store.generate_recurring(today().isoformat())==0
    store.undo_payment(store.frame('transactions').iloc[0].id)
    assert store.get('recurring_transactions',rid)['next_date']==today().isoformat()

def canonical(s):
    return {t:sorted(rows,key=lambda r:r['id']) for t,rows in s.dump_state()['tables'].items()}

def test_bundle_exact_roundtrip_and_duplicate_ids(store,tmp_path):
    tx(store,merchant='=SUM(A1)',notes="'literal")
    tx(store,merchant='=SUM(A1)',notes="'literal")
    target=Store(tmp_path/'target.db')
    blob=export_bundle(store)
    import_csvs(target,[('anything.csv',blob)],'replace')
    assert canonical(target)==canonical(store)
    import_csvs(target,[('again.csv',blob)],'add')
    assert canonical(target)==canonical(store)

def test_demo_roundtrip(tmp_path):
    source=Store(tmp_path/'source.db');seed_demo(source)
    target=Store(tmp_path/'target.db')
    import_csvs(target,[('bundle.csv',export_bundle(source))],'replace')
    assert canonical(source)==canonical(target)
    assert all(an.monthly_summary(target).income>0)

def test_import_rollback_and_external_dedup(store):
    csv=b'date,amount,kind,category,account_name,merchant\n2026-01-10,10.50,expense,Food,Cash,Cafe\n'
    import_csvs(store,[('unknown.csv',csv)])
    import_csvs(store,[('unknown.csv',csv)])
    assert len(store.frame('transactions'))==1
    before=store.dump_state()
    bad=deepcopy(before);bad['tables']['transactions'][0]['account_id']='missing'
    with pytest.raises((ValueError,sqlite3.IntegrityError)): store.restore_state(bad)
    assert store.dump_state()==before

def test_isolated_sessions(tmp_path):
    a=Store(tmp_path/'a.db');b=Store(tmp_path/'b.db');seed_demo(a);seed_demo(b)
    a.save('profile',dict(id='profile',display_name='Private'))
    assert b.get('profile','profile')['display_name']!='Private'
