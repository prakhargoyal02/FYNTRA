"""Deterministic fictional fixtures. No owner or banking information is used."""
from datetime import date,timedelta
import calendar
import numpy as np
import pandas as pd
from database import today,money
from analytics import take_snapshot

def seed_demo(store,as_of=None):
    if not store.frame("accounts").empty:
        return
    now = as_of or today()
    periods = pd.period_range(end=pd.Timestamp(now).to_period("M"),periods=6,freq="M")
    start = periods[0].start_time.date()
    store.save("profile",dict(id="profile",display_name="Alex • fictional demo",monthly_limit_paise=money(42000)))
    account_ids = {}
    for name,kind,balance in [("Everyday account","bank",28000),("Reserve account","savings",42000),
                               ("Pocket cash","cash",3500),("Long-term holdings","investment",55000),
                               ("Credit line","credit_card",-6000)]:
        account_ids[name] = store.save("accounts",dict(name=name,account_type=kind,
            opening_balance_paise=money(balance),opening_date=start.isoformat(),notes="Fictional demonstration account"))
    bank = account_ids["Everyday account"]
    reserve = account_ids["Reserve account"]
    debt = store.save("debts",dict(name="Learning loan",debt_type="Education loan",original_paise=money(120000),
        opening_remaining_paise=money(96000),annual_rate=10.5,monthly_payment_paise=money(4000),
        next_date=(now+timedelta(days=8)).isoformat(),notes="Fictional loan. Interest entered manually."))
    goals = []
    for name,target,saved,days in [("Emergency fund",120000,35000,240),("Next adventure",40000,9000,150),("Creative setup",85000,18000,300)]:
        goals.append(store.save("savings_goals",dict(name=name,target_paise=money(target),
            initial_saved_paise=money(saved),target_date=(now+timedelta(days=days)).isoformat(),notes="Fictional savings allocation")))
    subs = []
    for name,price,day in [("Streamwave Music",149,8),("Frame+ Cinema",299,15),("Nimbus Storage",129,22)]:
        subs.append(store.save("subscriptions",dict(name=name,amount_paise=money(price),account_id=bank,
            next_date=date(start.year,start.month,day).isoformat(),frequency="monthly",anchor_day=day,
            notes="Fictional subscription; no real billing connection.")))
    rng = np.random.default_rng(42)
    merchants = {"Food":["Green Bowl","Corner Kitchen","The Daily Cafe"],
                 "Groceries":["Market Lane","Fresh Basket"],"Transport":["Metro pass","City ride"],
                 "Shopping":["Studio supplies","Everyday Store"],"Entertainment":["Cinema evening","Weekend books"],
                 "Healthcare":["Wellness pharmacy"],"Personal care":["Local salon"]}
    for idx,period in enumerate(periods):
        first = period.start_time.date()
        last = min(period.end_time.date(),now)
        if first<=now:
            store.save("transactions",dict(date=first.isoformat(),kind="income",amount_paise=money(64000),
                category="Salary",account_id=bank,merchant="Northstar Studio (fictional)",payment_method="Bank transfer"))
        for name,amount,day,category in [("Home rent",14500,2,"Rent"),("Electricity",1800,11,"Utilities"),("Internet",799,18,"Utilities")]:
            on = date(first.year,first.month,day)
            if on<=now:
                bill = store.save("bills",dict(name=name,amount_paise=money(amount),due_date=on.isoformat(),
                    frequency="once",category=category,account_id=bank,notes="Fictional demo bill"))
                store.pay_bill(bill,on.isoformat())
        for day in range(3,last.day+1,2):
            for cat,base in [("Food",380),("Groceries",650 if day%3==0 else 0),("Transport",110)]:
                if not base:
                    continue
                amount = int(rng.integers(int(base*.7),int(base*1.3)+1))
                store.save("transactions",dict(date=date(first.year,first.month,day).isoformat(),time="18:30",
                    kind="expense",amount_paise=money(amount),category=cat,account_id=bank,
                    merchant=str(rng.choice(merchants[cat])),payment_method="UPI",tags="everyday"))
        for cat,amount,day in [("Shopping",2400+idx*180,14),("Entertainment",1250,20),("Healthcare",650,6),("Personal care",550,24)]:
            if day<=last.day:
                store.save("transactions",dict(date=date(first.year,first.month,day).isoformat(),kind="expense",
                    amount_paise=money(amount),category=cat,account_id=bank,merchant=merchants[cat][0],payment_method="Card"))
        if last.day>=5:
            store.save("transactions",dict(date=date(first.year,first.month,5).isoformat(),kind="transfer",
                amount_paise=money(10000),category="Transfer",account_id=bank,to_account_id=reserve,merchant="Monthly reserve"))
            for g,amount in zip(goals,[5000,1000,2000]):
                store.save("goal_contributions",dict(goal_id=g,date=date(first.year,first.month,5).isoformat(),amount_paise=money(amount)))
            store.pay_debt(debt,bank,money(3500),money(500),date(first.year,first.month,5).isoformat())
        for sub_id in subs:
            row = store.get("subscriptions",sub_id)
            if date.fromisoformat(row["next_date"])<=last:
                store.pay_subscription(sub_id,row["next_date"],row["next_date"])
        for category,limit in [("Food",6500),("Groceries",5500),("Rent",14500),("Transport",2500),("Shopping",3500),
                               ("Utilities",3000),("Subscriptions",800),("Entertainment",2000),("EMI/debt",4500)]:
            store.save("budgets",dict(month=str(period),category=category,limit_paise=money(limit)))
        take_snapshot(store,last)
    store.save("bills",dict(name="Electricity • next bill",amount_paise=money(1850),due_date=(now+timedelta(days=3)).isoformat(),
        frequency="monthly",anchor_day=(now+timedelta(days=3)).day,category="Utilities",account_id=bank))
    store.save("bills",dict(name="Internet • next bill",amount_paise=money(799),due_date=(now+timedelta(days=6)).isoformat(),
        frequency="monthly",anchor_day=(now+timedelta(days=6)).day,category="Utilities",account_id=bank))
    next_month = (pd.Timestamp(now)+pd.offsets.MonthBegin(1)).date()
    store.save("recurring_transactions",dict(name="Monthly salary",kind="income",amount_paise=money(64000),
        category="Salary",account_id=bank,next_date=next_month.isoformat(),frequency="monthly",anchor_day=1,
        merchant="Northstar Studio (fictional)"))

