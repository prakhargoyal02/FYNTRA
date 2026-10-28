"""Readable Streamlit screens. Business rules live in database.py, not widgets."""
from datetime import date, datetime, timedelta
import sqlite3
import pandas as pd
import altair as alt
import streamlit as st
import analytics as an
from database import today, money, CATEGORIES, ACCOUNT_TYPES, FREQUENCIES, TABLES
from csv_tools import export_bundle, export_table, import_csvs, parse_files
from ui import hero, metrics, rows, rupees, chart, progress_card, MINT, GOLD


def current():
    return st.session_state.store

def month():
    return st.session_state.report_month

def d(value=None):
    return date.fromisoformat(str(value)[:10]) if value else today()

def commit_action(fn, message="Saved"):
    try:
        fn()
        an.take_snapshot(current())
    except (ValueError, sqlite3.Error, KeyError, TypeError) as exc:
        st.error(str(exc))
        return
    cloud = st.session_state.get("cloud")
    if cloud:
        try:
            cloud.push(current())
            st.session_state.pop("sync_error", None)
        except Exception:
            st.session_state.sync_error = "Saved in this session; cloud sync failed or another session changed your data. Export a backup in Data & settings before reloading."
    st.session_state.notice = message
    st.rerun()

def table(frame):
    st.dataframe(frame, hide_index=True, width="stretch")

def account_select(label="Account", value=None, key=None):
    a = current().frame("accounts")
    if a.empty:
        st.info("Create an account first in Accounts.")
        st.stop()
    labels = a.set_index("id").name.to_dict()
    options = list(labels)
    return st.selectbox(label, options, index=options.index(value) if value in options else 0, format_func=labels.get, key=key)

def picker(table_name, label="Create or edit", name="name", key=None):
    frame = current().frame(table_name)
    labels = {r["id"]:str(r.get(name,r["id"])) for r in frame.to_dict("records")}
    selected = st.selectbox(label, [None]+list(labels), format_func=lambda x: "New record" if x is None else labels[x], key=key or table_name+"-picker")
    return current().get(table_name, selected) if selected else {}

def deletion(table_name, row):
    if row and st.checkbox("Confirm deletion", key=table_name+row["id"]+"confirm"):
        if st.button("Delete record", key=table_name+row["id"]+"delete"):
            commit_action(lambda: current().delete(table_name,row["id"]),"Deleted")

def save(table_name,row,values):
    if row:
        values["id"] = row["id"]
    commit_action(lambda: current().save(table_name,values))

def overview_page():
    o=an.overview(current(),month())
    hero("A clearer view. A calmer month.","Know where your money goes. Decide where it goes next.",pd.Period(month()).strftime("%B %Y").upper()+" / OVERVIEW")
    st.space("small")
    metrics([("Available cash",rupees(o["balance"]),"Current non-investment, non-card account balances."),
             ("Money in",rupees(o["income"]),"Recorded income this report month."),
             ("Money out",rupees(o["expenses"]),"Recorded expenses; transfers excluded."),
             ("Budget left",rupees(o["budget_remaining"]),"Monthly spending limit minus expenses.")])
    left,right=st.columns([1.8,1],gap="large")
    with left:
        st.subheader("Your money in motion")
        summary=an.monthly_summary(current()).tail(6)
        if not summary.empty:
            plot=summary.melt("month",["income","expenses"],var_name="Flow",value_name="Amount")
            chart_=alt.Chart(plot).mark_bar(cornerRadiusTopLeft=4,cornerRadiusTopRight=4).encode(x=alt.X("month:N",title=None),xOffset="Flow:N",y=alt.Y("Amount:Q",title="₹"),color=alt.Color("Flow:N",scale=alt.Scale(domain=["income","expenses"],range=[MINT,GOLD]),legend=alt.Legend(orient="bottom")),tooltip=["month","Flow","Amount"]).properties(height=265)
            st.altair_chart(chart_,width="stretch")
        st.subheader("Latest activity")
        recent=an.transactions_frame(current())
        if recent.empty: st.info("Add your first transaction to see it here.")
        rows(recent)
    with right:
        with st.container(border=True):
            st.caption("FINANCIAL PULSE")
            st.subheader(o["pulse"])
            st.write(o["pulse_detail"])
            if o["budget_limit"]:
                st.progress(min(1,max(0,o["expenses"]/o["budget_limit"])))
                st.caption(f'{rupees(o["expenses"])} of {rupees(o["budget_limit"])} spent')
        st.subheader("On the horizon")
        upcoming=an.timeline(current(),today()-timedelta(days=30),today()+timedelta(days=14))
        upcoming=upcoming.loc[upcoming.status.ne("Recorded")]
        if upcoming.empty: st.caption("No upcoming recorded commitments.")
        else:
            for r in upcoming.head(4).to_dict("records"):
                with st.container(border=True):
                    st.write(f'**{r["name"]}** · {rupees(r["amount"])}')
                    st.caption(f'{r["date"]} · {r["status"]}')
    sub=an.subscription_summary(current())
    metrics([("Cash saved",rupees(o["net"]),"Income minus expenses, including debt payments."),
             ("Savings rate",f'{o["savings_rate"]:.1f}%' if o["savings_rate"] is not None else "—","Net cash flow divided by income."),
             ("Net worth",rupees(o["net_worth"]),"Account assets minus negative balances and standalone debts."),
             ("Subscriptions / month",rupees(sub["monthly_cost"]),"Monthly equivalent of active subscriptions.")])
    with st.expander("Savings goals & debt"):
        st.write(f'Total liabilities: **{rupees(o["debt"])}**')
        for r in an.goal_summary(current()).to_dict("records"):
            progress_card(r["name"],r["saved"],r["target"],str(r["target_date"]))

def transaction_form(row=None):
    row=row or {}
    if row.get("source_type"):
        st.info("This entry is linked to a payment or recurring schedule. Undo it here before changing its source.")
        if st.button("Undo linked payment"):
            commit_action(lambda:current().undo_payment(row["id"]),"Payment undone")
        return
    kind=st.segmented_control("Direction",["expense","income","transfer"],default=row.get("kind","expense"),key="tx-kind-"+row.get("id","new"),selection_mode="single") or "expense"
    with st.form("transaction-"+row.get("id","new")):
        c1,c2=st.columns(2)
        on=c1.date_input("Date",value=d(row.get("date")))
        at=c2.time_input("Time",value=datetime.strptime(row.get("time","12:00"),"%H:%M").time())
        amount=st.number_input("Amount (₹)",min_value=.01,value=float(row.get("amount_paise",10000)/100),step=100.0)
        account=account_select(value=row.get("account_id"))
        destination=account_select("To account",row.get("to_account_id")) if kind=="transfer" else None
        category=st.text_input("Category",row.get("category","Transfer" if kind=="transfer" else "Food"),help="Use any category name; match your budget category spelling.")
        subcategory=st.text_input("Subcategory",row.get("subcategory",""))
        merchant=st.text_input("Merchant / source",row.get("merchant",""))
        method=st.selectbox("Payment method",["UPI","Card","Cash","Bank transfer","Other"],index=["UPI","Card","Cash","Bank transfer","Other"].index(row.get("payment_method","Other")) if row.get("payment_method","Other") in ["UPI","Card","Cash","Bank transfer","Other"] else 4)
        tags=st.text_input("Tags (comma separated)",row.get("tags",""))
        notes=st.text_area("Notes",row.get("notes",""))
        submitted=st.form_submit_button("Save transaction",type="primary",width="stretch")
    if submitted:
        save("transactions",row,dict(date=on.isoformat(),time=at.strftime("%H:%M"),amount_paise=money(amount),kind=kind,category=category,subcategory=subcategory,account_id=account,to_account_id=destination,merchant=merchant,payment_method=method,tags=tags,notes=notes))
    if row:
        if st.button("Duplicate transaction"):
            clone={k:v for k,v in row.items() if k!="id"}
            commit_action(lambda:current().save("transactions",clone),"Transaction duplicated")
        deletion("transactions",row)

def transactions_page():
    hero("Every move, accounted for.","Search your ledger, record a payment, or plan a recurring entry.","TRANSACTIONS")
    mode=st.segmented_control("View",["History","Add transaction","Recurring"],default="History")
    if mode=="Add transaction":
        transaction_form(); return
    if mode=="Recurring":
        recurring_page(); return
    frame=an.transactions_frame(current(),posted=False)
    search=st.text_input("Search transactions",placeholder="Merchant, note, category, tag or amount")
    if search:
        text=frame[["merchant","notes","category","tags","amount"]].astype(str).agg(" ".join,axis=1)
        frame=frame.loc[text.str.contains(search,case=False,regex=False)]
    with st.expander("Filters",expanded=False):
        c1,c2=st.columns(2)
        start=c1.date_input("From",d(month()+"-01"))
        end=c2.date_input("To",pd.Period(month()).end_time.date())
        cats=st.multiselect("Categories",sorted(frame.category.unique().tolist()))
        accts=st.multiselect("Accounts",current().frame("accounts").name.tolist())
        kinds=st.multiselect("Types",["income","expense","transfer"])
        methods=st.multiselect("Payment methods",sorted(frame.payment_method.unique().tolist()))
        tag=st.text_input("Tag filter")
        lo=st.number_input("Minimum amount",min_value=0.0,value=0.0)
        hi=st.number_input("Maximum amount",min_value=0.0,value=max(100000.0,float(frame.amount.max()) if not frame.empty else 100000.0))
    frame=frame.loc[frame.date.between(pd.Timestamp(start),pd.Timestamp(end)) & frame.amount.between(lo,hi)]
    for field,values in [("category",cats),("account_name",accts),("kind",kinds),("payment_method",methods)]:
        if values: frame=frame.loc[frame[field].isin(values)]
    if tag: frame=frame.loc[frame.tags.str.contains(tag,case=False,regex=False)]
    order=st.selectbox("Sort by",["Newest","Oldest","Largest","Smallest"])
    frame=frame.sort_values("date" if order in {"Newest","Oldest"} else "amount",ascending=order in {"Oldest","Smallest"})
    st.caption(f"{len(frame)} transactions · Future entries are planned and excluded from current balances.")
    shown=frame[["date","merchant","kind","category","account_name","amount","tags"]].copy()
    shown["date"]=shown.date.dt.strftime("%d %b %Y")
    shown["amount"]=shown.amount.map(lambda x:rupees(x,True))
    table(shown)
    if not frame.empty:
        labels={r.id:f'{r.date:%d %b} · {r.merchant or r.category} · {rupees(r.amount)} · {str(r.id)[:6]}' for r in frame.itertuples()}
        selected=st.selectbox("Select a transaction to edit",[None]+list(labels),format_func=lambda x:"Choose a transaction" if x is None else labels[x])
        if selected: transaction_form(current().get("transactions",selected))
    with st.expander("Monthly category and daily totals"):
        table(an.category_summary(current(),month()))
        table(an.daily_spending(current(),month()))

def budgets_page():
    hero("Give your money direction.","Set category limits and see how much room remains.","BUDGETS / "+month())
    b=an.budget_summary(current(),month())
    o=an.overview(current(),month())
    metrics([("Monthly limit",rupees(o["budget_limit"]),"Profile limit, or the sum of category budgets."),("Spent",rupees(o["expenses"]),"All expenses, including unbudgeted categories."),("Remaining",rupees(o["budget_remaining"]),"Limit minus recorded spending.")])
    for r in b.to_dict("records"):
        with st.container(border=True):
            a,c=st.columns([2,1])
            a.write(f'**{r["category"]}** · {r["status"]}')
            c.write(f'{rupees(r["spent"])} / {rupees(r["limit"])}')
            st.progress(min(1,max(0,r["used_pct"]/100)))
            st.caption(f'{rupees(r["remaining"])} remaining · {r["used_pct"]:.0f}% used')
    st.caption("Healthy ≤60% · Watch >60–85% · Near limit >85–100% · Over budget >100%. Rollover is reserved for v2.")
    with st.expander("Create or edit a budget"):
        row=picker("budgets",name="category")
        with st.form("budget"):
            m=st.text_input("Budget month (YYYY-MM)",row.get("month",month()))
            category=st.text_input("Budget category",row.get("category","Food"))
            limit=st.number_input("Category limit (₹)",min_value=0.0,value=float(row.get("limit_paise",500000)/100))
            submitted=st.form_submit_button("Save budget",type="primary")
        if submitted: save("budgets",row,dict(month=m,category=category,limit_paise=money(limit)))
        deletion("budgets",row)
    st.subheader("Can it fit this month?")
    spend=st.number_input("Planned purchase (₹)",min_value=0.0,value=1000.0,step=100.0)
    st.metric("Budget left after purchase",rupees(o["budget_remaining"]-spend))
    st.caption("Subtracts your purchase from the remaining monthly budget. It does not assess credit or investment suitability.")

def accounts_page():
    hero("One view of every account.","Balances come from opening amounts and your recorded money movements.","ACCOUNTS")
    accounts=an.account_summary(current())
    for r in accounts.to_dict("records"):
        with st.container(border=True):
            st.subheader(r["name"])
            metrics([("Balance",rupees(r["balance"]),r["account_type"]),("Inflow",rupees(r["inflow_paise"]/100),"Includes incoming transfers."),("Outflow",rupees(r["outflow_paise"]/100),"Includes outgoing transfers.")])
            st.caption("Latest activity: "+str(r["last_activity"]))
    st.caption("Credit cards use negative balances for amounts owed. A card repayment is a transfer to that account. Do not also enter the same card balance as a standalone debt. Investment balances are manually maintained; market prices are not fetched.")
    with st.expander("Create or edit an account",expanded=accounts.empty):
        row=picker("accounts")
        with st.form("account"):
            name=st.text_input("Account name",row.get("name",""))
            kind=st.selectbox("Account type",ACCOUNT_TYPES,index=ACCOUNT_TYPES.index(row.get("account_type","bank")))
            balance=st.number_input("Opening balance (₹)",value=float(row.get("opening_balance_paise",0)/100),help="For debt on a credit card, enter a negative balance.")
            on=st.date_input("Opening balance date",d(row.get("opening_date")))
            notes=st.text_area("Account notes",row.get("notes",""))
            submit=st.form_submit_button("Save account",type="primary")
        if submit: save("accounts",row,dict(name=name,account_type=kind,opening_balance_paise=money(balance),opening_date=on.isoformat(),notes=notes))
        deletion("accounts",row)
    st.info("To move money, choose Transactions → Add transaction → transfer.")

def commitments_page():
    hero("Nothing slips past you.","Track renewals, upcoming bills and the payments you have recorded.","BILLS & SUBSCRIPTIONS")
    mode=st.segmented_control("Commitment type",["Bills","Subscriptions"],default="Bills")
    is_bill=mode!="Subscriptions"
    table_name="bills" if is_bill else "subscriptions"
    frame=current().frame(table_name)
    if not is_bill:
        totals=an.subscription_summary(current())
        metrics([("Monthly equivalent",rupees(totals["monthly_cost"]),"Active subscriptions only."),("Yearly equivalent",rupees(totals["yearly_cost"]),"Weekly uses 52 payments per year."),("Next renewal",totals["next_renewal"] or "—","Next recorded renewal."),("Largest monthly cost",totals["most_expensive"] or "—","Compared using monthly equivalents.")])
    else:
        status=st.selectbox("Bill status",["All","Upcoming","Due today","Overdue","Paid"])
        frame["status"]=frame.apply(lambda r:"Paid" if r.paid else "Overdue" if r.due_date<today().isoformat() else "Due today" if r.due_date==today().isoformat() else "Upcoming",axis=1) if not frame.empty else pd.Series(dtype=str)
        if status!="All": frame=frame.loc[frame.status.eq(status)]
    for r in frame.sort_values("due_date" if is_bill else "next_date").to_dict("records"):
        with st.container(border=True):
            st.write(f'**{r["name"]}** · {rupees(r["amount_paise"]/100)}')
            st.caption(f'{r["due_date" if is_bill else "next_date"]} · {r["frequency"]} · '+(r["status"] if is_bill else "Active" if r["active"] else "Cancelled"))
            if (is_bill and not r["paid"]) or (not is_bill and r["active"]):
                if st.button("Record payment today",key="pay"+r["id"]):
                    if is_bill: commit_action(lambda r=r:current().pay_bill(r["id"],today().isoformat()),"Bill paid")
                    else: commit_action(lambda r=r:current().pay_subscription(r["id"],today().isoformat(),r["next_date"]),"Renewal recorded")
    with st.expander("Create or edit "+("bill" if is_bill else "subscription")):
        row=picker(table_name)
        if row.get("paid"):
            st.info("Undo the payment in Transactions before editing this paid bill."); return
        with st.form("commitment"):
            name=st.text_input("Name",row.get("name",""))
            amount=st.number_input("Amount (₹)",min_value=.01,value=float(row.get("amount_paise",100000)/100))
            frequencies=FREQUENCIES if is_bill else FREQUENCIES[1:]
            frequency=st.selectbox("Frequency",frequencies,index=frequencies.index(row.get("frequency","monthly")))
            on=st.date_input("Due date" if is_bill else "Next renewal",d(row.get("due_date" if is_bill else "next_date")))
            account=account_select(value=row.get("account_id"))
            category=st.text_input("Category",row.get("category","Utilities" if is_bill else "Subscriptions"))
            active=st.checkbox("Active",bool(row.get("active",1))) if not is_bill else None
            notes=st.text_area("Notes",row.get("notes",""))
            submitted=st.form_submit_button("Save commitment",type="primary")
        if submitted:
            values=dict(name=name,amount_paise=money(amount),frequency=frequency,anchor_day=on.day,account_id=account,category=category,notes=notes)
            values["due_date" if is_bill else "next_date"]=on.isoformat()
            if not is_bill: values["active"]=int(active)
            save(table_name,row,values)
        deletion(table_name,row)
    st.caption("Payment buttons record money already paid; they never charge an account. Avoid creating a second recurring schedule for the same bill or subscription.")

def goals_page():
    hero("Make room for what matters.","Track purposeful savings and see debt coming down.","GOALS & DEBT")
    mode=st.segmented_control("Planning view",["Savings goals","Debt"],default="Savings goals")
    if mode!="Debt":
        g=an.goal_summary(current())
        st.caption("Goals earmark money already in your accounts. Contributions do not move cash or increase net worth; record a separate transfer if money actually moves.")
        for r in g.to_dict("records"):
            progress_card(r["name"],r["saved"],r["target"],f'{rupees(r["remaining"])} left · {r["target_date"]}')
        with st.expander("Create or edit goal"):
            row=picker("savings_goals")
            with st.form("goal"):
                name=st.text_input("Goal name",row.get("name",""))
                target=st.number_input("Target (₹)",min_value=.01,value=float(row.get("target_paise",10000000)/100))
                initial=st.number_input("Already saved before tracking (₹)",min_value=0.0,value=float(row.get("initial_saved_paise",0)/100))
                on=st.date_input("Target date",d(row.get("target_date")))
                notes=st.text_area("Goal notes",row.get("notes",""))
                submitted=st.form_submit_button("Save goal",type="primary")
            if submitted: save("savings_goals",row,dict(name=name,target_paise=money(target),initial_saved_paise=money(initial),target_date=on.isoformat(),notes=notes))
            deletion("savings_goals",row)
        if not g.empty:
            with st.expander("Add or edit a contribution"):
                row=picker("goal_contributions",name="date")
                with st.form("contribution"):
                    labels=g.set_index("id").name.to_dict()
                    ids=list(labels)
                    goal=st.selectbox("Goal",ids,index=ids.index(row["goal_id"]) if row else 0,format_func=labels.get)
                    on=st.date_input("Contribution date",d(row.get("date")))
                    amount=st.number_input("Contribution (₹)",min_value=.01,value=float(row.get("amount_paise",100000)/100))
                    notes=st.text_input("Contribution note",row.get("notes",""))
                    submitted=st.form_submit_button("Save contribution",type="primary")
                if submitted: save("goal_contributions",row,dict(goal_id=goal,date=on.isoformat(),amount_paise=money(amount),notes=notes))
                deletion("goal_contributions",row)
    else:
        debts=an.debt_summary(current())
        st.caption("Track standalone loans here. Card balances already recorded in Accounts must not be entered twice. Interest is entered when paid; no automatic interest accrual is assumed.")
        metrics([("Debt remaining",rupees(debts.remaining.sum()),"Standalone debts only."),("Principal repaid",rupees((debts.original_paise/100-debts.remaining).sum()),"Includes repayments before tracking began.")])
        for r in debts.to_dict("records"):
            progress_card(r["name"],r["original_paise"]/100-r["remaining"],r["original_paise"]/100,f'{rupees(r["remaining"])} remaining')
        with st.expander("Create or edit debt"):
            row=picker("debts")
            with st.form("debt"):
                name=st.text_input("Debt name",row.get("name",""))
                kind=st.text_input("Debt type",row.get("debt_type","Personal loan"))
                original=st.number_input("Original amount (₹)",min_value=.01,value=float(row.get("original_paise",10000000)/100))
                remaining=st.number_input("Balance when tracking started (₹)",min_value=0.0,value=float(row.get("opening_remaining_paise",10000000)/100))
                rate=st.number_input("Annual interest rate (%) — optional",min_value=0.0,max_value=1000.0,value=float(row.get("annual_rate",0)))
                payment=st.number_input("Scheduled monthly payment (₹)",min_value=0.0,value=float(row.get("monthly_payment_paise",0)/100))
                on=st.date_input("Next payment date",d(row.get("next_date")))
                notes=st.text_area("Debt notes",row.get("notes",""))
                submitted=st.form_submit_button("Save debt",type="primary")
            if submitted: save("debts",row,dict(name=name,debt_type=kind,original_paise=money(original),opening_remaining_paise=money(remaining),annual_rate=rate,monthly_payment_paise=money(payment),next_date=on.isoformat(),notes=notes))
            deletion("debts",row)
        if not debts.empty:
            with st.expander("Record a debt payment"):
                with st.form("debt-payment"):
                    labels=debts.set_index("id").name.to_dict()
                    debt=st.selectbox("Debt",list(labels),format_func=labels.get)
                    account=account_select()
                    principal=st.number_input("Principal repaid (₹)",min_value=.01,value=1000.0)
                    interest=st.number_input("Interest paid (₹)",min_value=0.0,value=0.0)
                    on=st.date_input("Paid on",today())
                    submitted=st.form_submit_button("Record debt payment",type="primary")
                if submitted: commit_action(lambda:current().pay_debt(debt,account,money(principal),money(interest),on.isoformat()),"Debt payment recorded")
            st.caption("Undo a payment from its linked entry in Transactions. Update the next payment date in the debt editor after payment.")

def recurring_page():
    st.subheader("Predictable money movements")
    st.caption("Schedules appear in Calendar. Post due entries explicitly; opening a page never creates transactions. Do not duplicate bills or subscriptions here.")
    frame=current().frame("recurring_transactions")
    table(frame[["name","kind","amount_paise","next_date","frequency","active"]].assign(amount=lambda x:x.amount_paise/100).drop(columns="amount_paise"))
    if st.button("Post all entries due through today",type="primary"):
        commit_action(lambda:current().generate_recurring(today().isoformat()),"Due entries posted once")
    row=picker("recurring_transactions")
    kind=st.selectbox("Recurring direction",["income","expense","transfer"],index=["income","expense","transfer"].index(row.get("kind","income")))
    with st.form("recurring"):
        name=st.text_input("Schedule name",row.get("name",""))
        amount=st.number_input("Recurring amount (₹)",min_value=.01,value=float(row.get("amount_paise",100000)/100))
        account=account_select(value=row.get("account_id"))
        dest=account_select("Destination account",row.get("to_account_id")) if kind=="transfer" else None
        category=st.text_input("Recurring category",row.get("category","Salary"))
        frequency=st.selectbox("Repeat",FREQUENCIES[1:],index=FREQUENCIES[1:].index(row.get("frequency","monthly")))
        on=st.date_input("Next occurrence",d(row.get("next_date")))
        active=st.checkbox("Schedule active",bool(row.get("active",1)))
        notes=st.text_area("Schedule notes",row.get("notes",""))
        submitted=st.form_submit_button("Save schedule",type="primary")
    if submitted: save("recurring_transactions",row,dict(name=name,kind=kind,amount_paise=money(amount),account_id=account,to_account_id=dest,category=category,frequency=frequency,next_date=on.isoformat(),anchor_day=on.day,active=int(active),notes=notes))
    deletion("recurring_transactions",row)

def analytics_page():
    hero("See the pattern. Shape the next month.","Every chart comes from your ledger. Every projection states its assumptions.","CASH FLOW & INSIGHTS / "+month())
    o=an.monthly_review(current(),month())
    metrics([("Income",rupees(o["income"]),"Selected month."),("Expenses",rupees(o["expenses"]),"Transfers excluded."),("Net cash flow",rupees(o["net"]),"Income minus expenses."),("Daily average",rupees(o["average_daily_spend"]),"Includes zero-spend days through today or month end.")])
    a,b=st.columns(2)
    with a:
        st.subheader("Where money went")
        chart(an.category_summary(current(),month()),"category:N","amount:Q")
        st.subheader("Cash flow over time")
        chart(an.monthly_summary(current()),"month:N","net:Q","line")
        st.subheader("Daily spending")
        daily=an.daily_spending(current(),month())
        chart(daily,"date:T","amount:Q","bar")
        chart(daily,"date:T","rolling_7d:Q","line",height=160,title="Seven-day trailing average spending")
    with b:
        st.subheader("Monthly spending")
        chart(an.monthly_summary(current()),"month:N","expenses:Q","area",color=GOLD)
        st.subheader("Recorded net worth")
        chart(an.net_worth_history(current()),"date:T","net_worth:Q","line")
        st.caption("Snapshots are recorded after changes. Past snapshots are historical observations; later edits do not rewrite them.")
        st.subheader("Account distribution")
        chart(an.account_summary(current()),"name:N","balance:Q")
    with st.expander("Budget & subscription detail"):
        table(an.budget_summary(current(),month())[["category","limit","spent","remaining","used_pct","status"]])
        sub=an.subscription_summary(current())["table"]
        chart(sub,"name:N","monthly:Q")
    if month()==today().strftime("%Y-%m"):
        st.subheader("If this spending pace continues")
        metrics([("Month-end spending",rupees(o["projected_month_expense"]),"Expenses so far + average daily spend × remaining days."),("Month-end cash",rupees(o["projected_end_balance"]),"Current cash minus projected remaining spending; assumes no new income or transfers from investments.")])
        st.caption("Simple arithmetic, not a prediction. Upcoming bills are not added again because the daily average already represents spending; timing and one-off purchases can change this estimate.")
    st.subheader("Your monthly review")
    metrics([("Largest expense",rupees(o["largest_amount"]),o["largest_expense"] or "No expenses"),("Top category",o["top_category"] or "—","Highest recorded category total."),("Budgets exceeded",str(o["budgets_exceeded"]),"Categories over 100%."),("Debt principal reduced",rupees(o["debt_reduced"]),"Recorded principal payments this month."),("Net-worth change",rupees(o["net_worth_change"]),"Requires a snapshot before and within this month.")])
    st.write(f'Bills paid: **{o["bills_paid"]}** · Subscription renewals recorded: **{o["subscriptions_paid"]}**')
    st.subheader("What changed this month?")
    for insight in o["insights"]: st.write("• "+insight)
    summary=an.monthly_summary(current())
    with st.expander("Income, savings and month-by-month figures"):
        table(summary)
        chart(summary,"month:N","income:Q","line")
        chart(summary,"month:N","net:Q","line",title="Monthly savings as net cash flow")
        if not daily.empty: st.write("Highest spending days"); table(daily.nlargest(5,"amount")[["date","amount"]])

def calendar_page():
    hero("Know what's coming.","A timeline of money commitments, planned entries and savings milestones.","FINANCIAL CALENDAR")
    a,b=st.columns(2)
    start=a.date_input("Timeline from",today()-timedelta(days=7))
    end=b.date_input("Timeline through",today()+timedelta(days=45))
    events=an.timeline(current(),start,end)
    if events.empty: st.info("No recorded events in this window.")
    else:
        for on,group in events.groupby("date",sort=True):
            st.subheader(d(on).strftime("%d %b · %A"))
            for r in group.to_dict("records"):
                with st.container(border=True):
                    st.write(f'**{r["name"]}** · {rupees(r["amount"])}')
                    st.caption(f'{r["kind"]} · {r["status"]}')
    st.caption("Shows the next occurrence of each recurring commitment, not every future repetition. Goal target amounts are milestones, not scheduled charges.")

def data_page():
    hero("Your data. Your control.","Portable backups, clear settings and an independent fictional demo.","DATA & SETTINGS")
    profile=current().get("profile","profile")
    with st.form("settings"):
        name=st.text_input("Display name",profile["display_name"])
        limit=st.number_input("Total monthly spending limit (₹)",min_value=0.0,value=profile["monthly_limit_paise"]/100,help="Zero uses the sum of this month's category budgets.")
        st.caption("Currency: INR. Other currencies are planned; v1 never mixes currencies or converts rates.")
        submitted=st.form_submit_button("Save preferences")
    if submitted: save("profile",profile,dict(display_name=name,monthly_limit_paise=money(limit)))
    st.subheader("Export a backup")
    st.download_button("Download full FYNTRA Bundle",export_bundle(current()),"fyntra_bundle.csv","text/csv",type="primary")
    choice=st.selectbox("Individual record type",TABLES)
    st.download_button("Download selected CSV",export_table(current(),choice),choice+".csv","text/csv")
    st.subheader("Import CSV files")
    st.caption("Files are identified by columns. Exported monetary columns use integer paise; the simple transaction template below uses rupees. A whole batch is validated before anything changes.")
    files=st.file_uploader("Choose bundle or separate CSVs",type="csv",accept_multiple_files=True)
    mode=st.radio("Import mode",["Add safely","Replace matching types"],horizontal=True)
    confirm=st.checkbox("I have exported a backup and want to replace the included record types") if mode=="Replace matching types" else True
    if files:
        try:
            prepared=[(f.name,f.getvalue()) for f in files]
            parsed=parse_files(current(),prepared)
            st.write({k:len(v) for k,v in parsed.items()})
            if st.button("Import validated files",disabled=not confirm,type="primary"):
                commit_action(lambda:import_csvs(current(),prepared,"add" if mode=="Add safely" else "replace"),"CSV import complete")
        except Exception as exc: st.error(str(exc))
    st.download_button("Simple transaction template","date,amount,kind,category,account_name,merchant,notes,tags\n","transaction_template.csv","text/csv")
    st.caption("Account names must already exist. Use a full bundle for related payments, transfers and schedules. Add safely retains existing IDs; use replace to restore edits. Identical transactions with distinct IDs remain distinct.")
    cloud=st.session_state.get("cloud")
    if cloud:
        st.subheader("Cloud sync")
        st.caption("Concurrent edits are detected before overwriting another session. Export this session before reloading cloud data.")
        if st.button("Retry sync"):
            commit_action(lambda:None,"Cloud sync attempted")
        if st.checkbox("I exported local changes and want to reload the cloud copy"):
            if st.button("Reload cloud copy"):
                try:
                    cloud.pull(current()); st.session_state.pop("sync_error",None); st.rerun()
                except Exception: st.error("Cloud reload failed. Your local copy remains available.")
    else:
        st.subheader("Reset fictional demo")
        if st.checkbox("Replace this session's demo edits with fresh fictional data"):
            if st.button("Reset demo"):
                directory=st.session_state.pop("demo_directory",None)
                st.session_state.pop("store",None)
                if directory: directory.cleanup()
                st.rerun()
    st.caption("Demo sessions are temporary. Export changes you want to keep before closing or reloading the browser. Private sessions use an isolated SQLite working copy and ownership-protected cloud sync.")

def learning_page():
    hero("Built to understand, not just use.","A practical map of the technologies powering FYNTRA.","PROJECT 02 / LEARNING GUIDE")
    for title,text in [
        ("Python · the application rules","database.py validates amounts, dates and relationships. Payment functions group related writes into one transaction, so partial payments cannot leave inconsistent balances."),
        ("SQLite · one coherent ledger","Related tables store accounts, transactions, budgets, commitments, goals and debts. Money is integer paise; foreign keys protect relationships. Transfers have a source and destination, without being income or expenses."),
        ("Pandas · structured financial data","analytics.py joins account names with merge, filters with loc, parses dates with to_datetime, groups categories with groupby and aggregation, builds monthly pivot tables and sorts results. csv_tools.py uses DataFrames and drop_duplicates for portable imports."),
        ("NumPy · numerical reasoning","Vectorized arithmetic calculates savings rates and budget usage with guarded divide, balances with maximum/minimum, projections with mean, and rolling spending with cumulative sums. Zero-income and zero-budget cases are handled explicitly."),
        ("Streamlit · the product interface","app.py routes screens; views.py composes forms, charts and responsive containers. Each browser session owns its own store. Widgets call domain functions instead of embedding financial rules."),
        ("Supabase · optional private persistence","Auth verifies identity. Row Level Security restricts the cloud state to that user. Revision checks prevent silently overwriting changes from another device. SQLite remains the structured working database.")]:
        with st.container(border=True): st.subheader(title); st.write(text)
    st.info("No machine learning is used. FYNTRA focuses on NumPy, stronger Pandas and structured financial processing. Recommendation algorithms belong to Project 03.")
    st.markdown("Built by [Prakhar Goyal](https://github.com/prakhargoyal02) · [GitHub source](https://github.com/prakhargoyal02/FYNTRA) · [LinkedIn](https://www.linkedin.com/in/prakhar-goyal-d2002/)")
