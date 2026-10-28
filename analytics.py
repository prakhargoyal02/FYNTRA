"""Pandas prepares tables; NumPy supplies vectorized financial arithmetic.

All public monetary results are rupees. Database values remain integer paise.
Forecasts describe arithmetic assumptions, never AI or investment advice.
"""
from datetime import date, timedelta
import calendar
import numpy as np
import pandas as pd
from database import today, money

def transactions_frame(store, posted=True, as_of=None):
    df = store.frame("transactions")
    accounts = store.frame("accounts")[["id","name"]]
    # merge joins human-readable account labels without duplicating ledger records.
    df = df.merge(accounts.rename(columns={"id":"account_id","name":"account_name"}),on="account_id",how="left")
    df = df.merge(accounts.rename(columns={"id":"to_account_id","name":"to_account_name"}),on="to_account_id",how="left")
    df["date"] = pd.to_datetime(df["date"])
    if posted:
        df = df.loc[df["date"]<=pd.Timestamp(as_of or today())].copy()
    df["amount"] = pd.to_numeric(df["amount_paise"])/100
    df["signed_amount"] = np.select([df["kind"].eq("income"),df["kind"].eq("expense")],
                                     [df["amount"],-df["amount"]],default=0.0)
    df["month"] = df["date"].dt.strftime("%Y-%m")
    return df.sort_values(["date","time","id"],ascending=False)

def month_transactions(store,month):
    df = transactions_frame(store)
    return df.loc[df["month"].eq(month)].copy()

def account_summary(store,as_of=None):
    cutoff = as_of or today()
    a = store.frame("accounts")
    a = a.loc[pd.to_datetime(a["opening_date"])<=pd.Timestamp(cutoff)].copy()
    t = transactions_frame(store,as_of=cutoff)
    a["inflow_paise"] = 0
    a["outflow_paise"] = 0
    a["last_activity"] = ""
    if not t.empty:
        incoming = pd.concat([t.loc[t.kind.eq("income"),["account_id","amount_paise"]],
            t.loc[t.kind.eq("transfer"),["to_account_id","amount_paise"]].rename(columns={"to_account_id":"account_id"})])
        outgoing = t.loc[t.kind.isin(["expense","transfer"]),["account_id","amount_paise"]]
        a["inflow_paise"] = a.id.map(incoming.groupby("account_id").amount_paise.sum()).fillna(0).astype("int64")
        a["outflow_paise"] = a.id.map(outgoing.groupby("account_id").amount_paise.sum()).fillna(0).astype("int64")
        activity = pd.concat([t[["account_id","date"]],t.loc[t.kind.eq("transfer"),["to_account_id","date"]].rename(columns={"to_account_id":"account_id"})])
        a["last_activity"] = a.id.map(activity.groupby("account_id").date.max()).dt.strftime("%d %b %Y").fillna("No activity")
    a["balance_paise"] = a.opening_balance_paise+a.inflow_paise-a.outflow_paise
    a["balance"] = a.balance_paise/100
    return a

def monthly_summary(store):
    t = transactions_frame(store)
    if t.empty:
        return pd.DataFrame(columns=["month","income","expenses","net","savings_rate"])
    # pivot_table is a compact two-dimensional aggregation of month and direction.
    p = t.loc[t.kind.ne("transfer")].pivot_table(index="month",columns="kind",values="amount_paise",aggfunc="sum",fill_value=0)
    months = pd.period_range(t.date.min().to_period("M"),pd.Timestamp(today()).to_period("M"),freq="M").astype(str)
    p = p.reindex(months,fill_value=0)
    income = p.get("income",pd.Series(0,index=p.index)).to_numpy(dtype=float)/100
    expenses = p.get("expense",pd.Series(0,index=p.index)).to_numpy(dtype=float)/100
    net = np.subtract(income,expenses)
    rate = np.divide(net*100,income,out=np.full_like(net,np.nan),where=income!=0)
    return pd.DataFrame({"month":p.index,"income":income,"expenses":expenses,"net":net,"savings_rate":rate})

def category_summary(store,month):
    t = month_transactions(store,month)
    out = t.loc[t.kind.eq("expense")].groupby("category",as_index=False).agg(amount=("amount","sum"),count=("id","count"))
    total = out.amount.sum()
    out["share_pct"] = out.amount/total*100 if total else 0.0
    return out.sort_values("amount",ascending=False)

def budget_summary(store,month):
    b = store.frame("budgets")
    b = b.loc[b.month.eq(month)].copy()
    spending = category_summary(store,month)[["category","amount"]]
    b = b.merge(spending,on="category",how="left").fillna({"amount":0})
    b["limit"] = b.limit_paise/100
    b["spent"] = b["amount"]
    b["remaining"] = b["limit"]-b.spent
    # Divide safely: spending against a zero budget is explicitly over budget.
    limits = b["limit"].to_numpy(dtype=float)
    spent = b.spent.to_numpy(dtype=float)
    b["used_pct"] = np.divide(spent*100,limits,out=np.where(spent>0,np.inf,0.0),where=limits>0)
    b["status"] = np.select([b.used_pct>100,b.used_pct>85,b.used_pct>60],["Over budget","Near limit","Watch"],default="Healthy")
    return b.sort_values("used_pct",ascending=False)

def daily_spending(store,month):
    start = date.fromisoformat(month+"-01")
    end = min(today(),date(start.year,start.month,calendar.monthrange(start.year,start.month)[1]))
    if end<start:
        return pd.DataFrame(columns=["date","amount","rolling_7d"])
    t = month_transactions(store,month)
    values = t.loc[t.kind.eq("expense")].groupby("date").amount.sum()
    days = pd.date_range(start,end)
    values = values.reindex(days,fill_value=0.0)
    # NumPy prefix sums implement a true trailing mean, including zero-spend days.
    arr = values.to_numpy(dtype=float)
    prefix = np.concatenate(([0.0],np.cumsum(arr)))
    right = np.arange(1,len(arr)+1)
    left = np.maximum(right-7,0)
    rolling = (prefix[right]-prefix[left])/(right-left)
    return pd.DataFrame({"date":days,"amount":arr,"rolling_7d":rolling})

def goal_summary(store):
    g = store.frame("savings_goals")
    c = store.frame("goal_contributions")
    c = c.loc[pd.to_datetime(c.date)<=pd.Timestamp(today())]
    sums = c.groupby("goal_id").amount_paise.sum()
    g["saved"] = (g.initial_saved_paise+g.id.map(sums).fillna(0))/100
    g["target"] = g.target_paise/100
    g["remaining"] = np.maximum(g.target-g.saved,0)
    g["progress"] = np.minimum(g.saved/g.target*100,100)
    return g

def debt_summary(store,as_of=None):
    d = store.frame("debts")
    p = store.frame("debt_payments")
    p = p.loc[pd.to_datetime(p.date)<=pd.Timestamp(as_of or today())]
    d["paid"] = d.id.map(p.groupby("debt_id").principal_paise.sum()).fillna(0)/100
    d["remaining"] = d.opening_remaining_paise/100-d.paid
    d["progress"] = (d.original_paise/100-d.remaining)/(d.original_paise/100)*100
    return d

def net_worth_values(store,as_of=None):
    a = account_summary(store,as_of)
    balances = a.balance.to_numpy(dtype=float)
    assets = float(np.maximum(balances,0).sum())
    liabilities = float(-np.minimum(balances,0).sum()+debt_summary(store,as_of).remaining.sum())
    return assets,liabilities

def take_snapshot(store,on=None):
    on = on or today()
    assets,liabilities = net_worth_values(store,on)
    s = store.frame("net_worth_snapshots")
    match = s.loc[s.date.eq(on.isoformat())]
    values = dict(date=on.isoformat(),assets_paise=money(assets),liabilities_paise=money(liabilities))
    if not match.empty:
        values["id"] = match.iloc[0].id
    store.save("net_worth_snapshots",values)

def net_worth_history(store):
    s = store.frame("net_worth_snapshots").sort_values("date")
    s["date"] = pd.to_datetime(s.date)
    s["assets"] = s.assets_paise/100
    s["liabilities"] = s.liabilities_paise/100
    s["net_worth"] = s.assets-s.liabilities
    return s

def subscription_summary(store):
    s = store.frame("subscriptions")
    s = s.loc[s.active.eq(1)].copy()
    factors = {"weekly":52/12,"monthly":1,"quarterly":1/3,"yearly":1/12}
    s["monthly"] = (s.amount_paise/100)*s.frequency.map(factors)
    return dict(monthly_cost=float(s.monthly.sum()),yearly_cost=float(s.monthly.sum()*12),
                next_renewal=None if s.empty else s.next_date.min(),
                most_expensive=None if s.empty else s.loc[s.monthly.idxmax(),"name"],table=s)

def overview(store,month):
    t = month_transactions(store,month)
    income = float(t.loc[t.kind.eq("income"),"amount"].sum())
    expenses = float(t.loc[t.kind.eq("expense"),"amount"].sum())
    net = income-expenses
    accounts = account_summary(store)
    assets,liabilities = net_worth_values(store)
    liquid = float(accounts.loc[~accounts.account_type.isin(["investment","credit_card"]),"balance"].sum())
    b = budget_summary(store,month)
    limit = store.get("profile","profile")["monthly_limit_paise"]/100 or float(b["limit"].sum())
    daily = daily_spending(store,month)
    avg = float(np.mean(daily.amount.to_numpy(dtype=float))) if not daily.empty else 0.0
    start = date.fromisoformat(month+"-01")
    days = calendar.monthrange(start.year,start.month)[1]
    remaining_days = max(0,days-len(daily)) if month==today().strftime("%Y-%m") else 0
    if not len(t):
        pulse,detail = "Start your picture","Add accounts and transactions to build your financial picture."
    elif limit and expenses>limit:
        pulse,detail = "Budget pressure","Recorded spending is above your monthly spending limit."
    elif liquid<avg*14:
        pulse,detail = "Low cash buffer","Recorded cash covers fewer than 14 days at this month's average spending."
    elif (limit and expenses/limit>.85) or (income and net/income<.1):
        pulse,detail = "Watch spending","Review categories close to their limit and upcoming commitments."
    else:
        pulse,detail = "Healthy","Recorded cash flow and spending are within the selected thresholds."
    return dict(balance=liquid,income=income,expenses=expenses,net=net,
        savings_rate=net/income*100 if income else None,budget_limit=limit,budget_remaining=limit-expenses,
        assets=assets,liabilities=liabilities,net_worth=assets-liabilities,debt=liabilities,
        average_daily_spend=avg,projected_month_expense=expenses+avg*remaining_days,
        projected_end_balance=liquid-avg*remaining_days,pulse=pulse,pulse_detail=detail)

def timeline(store,start,end):
    rows = []
    lo,hi = pd.Timestamp(start),pd.Timestamp(end)
    for table,date_field,kind in [("bills","due_date","Bill"),("subscriptions","next_date","Subscription"),
                                  ("recurring_transactions","next_date","Recurring"),("debts","next_date","Debt"),
                                  ("savings_goals","target_date","Goal target")]:
        for r in store.frame(table).to_dict("records"):
            if r.get("active",1)==0 or r.get("paid",0):
                continue
            on = r[date_field]
            if lo<=pd.Timestamp(on)<=hi:
                amount = r.get("amount_paise",r.get("monthly_payment_paise",r.get("target_paise",0)))/100
                status = "Overdue" if on<today().isoformat() else ("Due today" if on==today().isoformat() else "Upcoming")
                rows.append(dict(date=on,name=r["name"],kind=kind,amount=amount,status=status))
    for r in store.frame("goal_contributions").to_dict("records"):
        if lo<=pd.Timestamp(r["date"])<=hi:
            goal = store.get("savings_goals",r["goal_id"])
            rows.append(dict(date=r["date"],name=goal["name"],kind="Goal allocation",amount=r["amount_paise"]/100,status="Recorded"))
    t = transactions_frame(store,posted=False)
    for r in t.loc[(t.date>=lo)&(t.date<=hi)&(t.date>pd.Timestamp(today()))].to_dict("records"):
        rows.append(dict(date=r["date"].strftime("%Y-%m-%d"),name=r["merchant"] or r["category"],kind="Planned "+r["kind"],amount=r["amount"],status="Planned"))
    return pd.DataFrame(rows,columns=["date","name","kind","amount","status"]).sort_values("date")

def monthly_review(store,month):
    result = overview(store,month)
    t = month_transactions(store,month)
    cats = category_summary(store,month)
    b = budget_summary(store,month)
    expense = t.loc[t.kind.eq("expense")]
    largest = None if expense.empty else expense.loc[expense.amount.idxmax()]
    result.update(largest_expense=None if largest is None else (largest["merchant"] or largest["category"]),
        largest_amount=0.0 if expense.empty else float(expense.amount.max()),
        top_category=None if cats.empty else cats.iloc[0].category,
        budgets_exceeded=int((b.used_pct>100).sum()),
        bills_paid=int(t.source_type.eq("bill").sum()),
        subscriptions_paid=int(t.source_type.eq("subscription").sum()))
    payments = store.frame("debt_payments")
    result["debt_reduced"] = float(payments.loc[payments.date.str.startswith(month),"principal_paise"].sum()/100)
    hist = net_worth_history(store)
    before = hist.loc[hist.date<pd.Timestamp(month+"-01")]
    during = hist.loc[hist.date.dt.strftime("%Y-%m").eq(month)]
    result["net_worth_change"] = None if before.empty or during.empty else float(during.iloc[-1].net_worth-before.iloc[-1].net_worth)
    start = pd.Timestamp(month+"-01")
    previous = (start-pd.offsets.MonthBegin(1)).strftime("%Y-%m")
    old = month_transactions(store,previous)
    note = "previous full month"
    if month==today().strftime("%Y-%m"):
        old = old.loc[old.date.dt.day<=today().day]
        note = "the same days last month"
    old_cats = old.loc[old.kind.eq("expense")].groupby("category").amount.sum()
    insights = []
    for row in cats.head(3).itertuples():
        baseline = float(old_cats.get(row.category,0))
        if baseline:
            change = (row.amount-baseline)/baseline*100
            insights.append(f"{row.category} spending {'increased' if change>=0 else 'decreased'} {abs(change):.0f}% against {note}.")
    if not b.empty:
        row = b.iloc[0]
        insights.append(f"{row.category}: {row.spent:,.0f} of {row['limit']:,.0f} rupees budgeted has been used.")
    if not insights:
        insights.append("Add another month of transactions to unlock comparisons.")
    result["insights"] = insights
    return result

