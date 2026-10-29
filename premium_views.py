"""Responsive finance workspace over FYNTRA's existing domain functions."""
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

import analytics as an
import views
from database import money
from modern_ui import ACCENT, NEGATIVE, POSITIVE, chart, metrics, progress_card, rows, rupees, section_header


def _month():
    return views.month()


def _store():
    return views.current()


def _page_header(title, copy, kicker):
    st.html(
        f'<section class="dk-page-head"><div><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></div></section>'
    )


def _cash_flow_chart(summary):
    if summary.empty:
        st.caption("Your cash-flow chart appears when you add transactions.")
        return
    plot = summary.melt("month", ["income", "expenses"], var_name="Flow", value_name="Amount")
    flow = (
        alt.Chart(plot)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("month:N", title=None, axis=alt.Axis(labelAngle=0, domain=False, ticks=False)),
            xOffset="Flow:N",
            y=alt.Y("Amount:Q", title=None, axis=alt.Axis(format="~s", domain=False, gridColor="#273532")),
            color=alt.Color("Flow:N", scale=alt.Scale(domain=["income", "expenses"], range=[POSITIVE, "#627E73"]), legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("Flow:N"), alt.Tooltip("Amount:Q", format=",.0f")],
        )
        .properties(height=260)
        .configure_view(stroke=None)
    )
    st.altair_chart(flow, width="stretch", alt="Income and expenses over recent months")


from html import escape


def _navigate(page, transaction_mode=None):
    st.session_state.page_nav = page
    if transaction_mode:
        st.session_state.transaction_view = transaction_mode


def _trend_bars(values, expense=False):
    """Tiny, honestly scaled history bars; never synthetic sparkline data."""
    values = [max(0, float(value)) for value in values]
    maximum = max(values, default=0)
    if not maximum:
        return
    bars = ''.join(f'<span style="height:{max(3, value / maximum * 100):.2f}%"></span>' for value in values)
    st.html(f'<div class="f-mini-bars {"out" if expense else ""}" aria-hidden="true">{bars}</div>')


def overview_page():
    month, store = _month(), _store()
    o = an.overview(store, month)
    period = pd.Period(month).strftime("%B %Y")
    summary = an.monthly_summary(store)
    summary = summary.loc[summary.month.le(month)].tail(6)
    sub = an.subscription_summary(store)

    _page_header("Make room for what’s next.", "Your money, in perspective. A little clarity for every decision ahead.", f"{period.upper()} / YOUR FINANCIAL OVERVIEW")
    with st.container(horizontal=True, gap="small", key="overview-actions"):
        st.button("Add transaction", type="primary", icon=":material/add:", key="overview-add", on_click=_navigate, args=("Transactions", "Add transaction"))
        st.button("Explore insights", icon=":material/insights:", key="overview-insights", on_click=_navigate, args=("Cash flow & insights",))
        st.button("Manage accounts", icon=":material/account_balance_wallet:", key="overview-accounts", on_click=_navigate, args=("Accounts",))

    balance_col, income_col, expense_col = st.columns([1.45, 1, 1], gap="medium")
    with balance_col:
        with st.container(border=True, key="dk-balance-card", height="stretch"):
            st.caption("YOUR AVAILABLE CASH")
            with st.container(key="balance-main"):
                st.metric("Available cash", rupees(o["balance"]), label_visibility="collapsed", help="Recorded cash, bank and wallet balances as of the report date.")
            with st.container(key="balance-detail"):
                a, b = st.columns(2)
                a.metric("Net worth", rupees(o["net_worth"]))
                b.metric("Savings rate", f'{o["savings_rate"]:.1f}%' if o["savings_rate"] is not None else "—")
    for column, field, label, icon in [(income_col, "income", "Money in", "↙"), (expense_col, "expenses", "Money out", "↗")]:
        expense = field == "expenses"
        with column:
            with st.container(border=True, key="dk-expense-card" if expense else "dk-income-card", height="stretch"):
                st.html(f'<div class="f-card-eyebrow">{label}<span class="f-card-icon {"out" if expense else ""}">{icon}</span></div>')
                st.metric(label, rupees(o[field]), label_visibility="collapsed")
                st.caption("Spent this month · transfers excluded" if expense else "Recorded income this month")
                if not summary.empty:
                    _trend_bars(summary[field].tolist(), expense)
                st.html('<p class="f-delta">Monthly history · up to six months</p>')

    chart_col, budget_col = st.columns([1.65, 1], gap="medium")
    with chart_col:
        with st.container(border=True, key="dk-cashflow-card", height="stretch"):
            section_header("Money in motion", "Income and spending · recent months")
            _cash_flow_chart(summary)
            st.caption(f'Net cash flow this month: {rupees(o["net"])}')
    with budget_col:
        with st.container(border=True, key="dk-budget-card", height="stretch"):
            section_header("Room to spend", "Your monthly budget")
            st.metric("Budget left", rupees(o["budget_remaining"]) if o["budget_limit"] else "Not set")
            if o["budget_limit"]:
                used = o["expenses"] / o["budget_limit"]
                st.progress(min(1.0, max(0.0, used)))
                st.caption(f'{used:.0%} used · {rupees(o["expenses"])} of {rupees(o["budget_limit"])}')
            else:
                st.caption("Set a monthly limit to see your spending room.")
            st.html(f'<div class="f-pulse"><strong>Financial pulse · {escape(o["pulse"])}</strong><p>{escape(o["pulse_detail"])}</p></div>')
            st.button("Review budgets", icon=":material/arrow_forward:", key="overview-budgets", on_click=_navigate, args=("Budgets",))

    category_col, activity_col = st.columns([1, 1.65], gap="medium")
    with category_col:
        with st.container(border=True, key="dk-category-card", height="stretch"):
            section_header("Where it went", "Spending by category")
            categories = an.category_summary(store, month)
            if categories.empty:
                st.caption("Record an expense to see your category breakdown.")
            else:
                plot = alt.Chart(categories).mark_bar(cornerRadiusEnd=4, size=14, color=POSITIVE).encode(
                    y=alt.Y("category:N", sort="-x", title=None, axis=alt.Axis(domain=False, ticks=False, labelLimit=110)),
                    x=alt.X("amount:Q", title=None, axis=alt.Axis(format="~s", domain=False, gridColor="#273532")),
                    tooltip=[alt.Tooltip("category:N", title="Category"), alt.Tooltip("amount:Q", title="Amount (₹)", format=",.0f")],
                ).properties(height=250).configure_view(stroke=None)
                st.altair_chart(plot, width="stretch", alt="Recorded spending by category in the selected month")
    with activity_col:
        with st.container(border=True, key="dk-activity-card", height="stretch"):
            section_header("Latest activity", "Your most recent money moves")
            recent = an.transactions_frame(store)
            if recent.empty:
                st.info("Your first transaction starts the story. Add one above.")
            else:
                rows(recent, limit=5)
            st.button("View all transactions", key="overview-history", on_click=_navigate, args=("Transactions", "History"))

    upcoming = an.timeline(store, views.today() - timedelta(days=30), views.today() + timedelta(days=14))
    upcoming = upcoming.loc[upcoming.status.ne("Recorded")]
    with st.container(border=True, key="dk-horizon-card"):
        section_header("On the horizon", "Overdue items and the next 14 days")
        if upcoming.empty:
            st.caption("All clear. No recorded commitments in this window.")
        else:
            cols = st.columns(min(4, len(upcoming.head(4))), gap="medium")
            for column, item in zip(cols, upcoming.head(4).to_dict("records")):
                with column:
                    st.caption(item["status"].upper())
                    st.write(f'**{item["name"]}**')
                    st.metric("Amount", rupees(item["amount"]), label_visibility="collapsed")
                    st.caption(str(item["date"]))
        st.button("Open calendar", key="overview-calendar", on_click=_navigate, args=("Calendar",))
    with st.expander("The bigger picture · savings, subscriptions & debt"):
        metrics([("Subscriptions / month", rupees(sub["monthly_cost"]), "Monthly equivalent of active subscriptions."),
                 ("Debt remaining", rupees(o["debt"]), "Recorded liabilities."),
                 ("Cash saved", rupees(o["net"]), "This month's income minus spending.")])
        for goal in an.goal_summary(store).to_dict("records"):
            progress_card(goal["name"], goal["saved"], goal["target"], str(goal["target_date"]))



def transactions_page():
    _page_header("Transactions", "Search, filter and edit the ledger without losing context.", "LEDGER")
    mode = st.segmented_control("View", ["History", "Add transaction", "Recurring"], default="History", key="transaction_view")
    if mode == "Add transaction":
        views.transaction_form()
        return
    if mode == "Recurring":
        views.recurring_page()
        return

    frame = an.transactions_frame(_store(), posted=False)
    search_col, sort_col = st.columns([1.6, .4], gap="medium", vertical_alignment="bottom")
    with search_col:
        search = st.text_input("Search transactions", placeholder="Merchant, note, category, tag or amount")
    with sort_col:
        order = st.selectbox("Sort", ["Newest", "Oldest", "Largest", "Smallest"])
    if search:
        text = frame[["merchant", "notes", "category", "tags", "amount"]].astype(str).agg(" ".join, axis=1)
        frame = frame.loc[text.str.contains(search, case=False, regex=False)]

    with st.expander("Filters", expanded=False):
        a, b = st.columns(2)
        start = a.date_input("From", views.d(_month() + "-01"))
        end = b.date_input("To", pd.Period(_month()).end_time.date())
        cats = st.multiselect("Categories", sorted(frame.category.unique().tolist()))
        accts = st.multiselect("Accounts", _store().frame("accounts").name.tolist())
        kinds = st.multiselect("Types", ["income", "expense", "transfer"])
        methods = st.multiselect("Payment methods", sorted(frame.payment_method.unique().tolist()))
        tag = st.text_input("Tag filter")
        low = st.number_input("Minimum amount", min_value=0.0, value=0.0)
        high = st.number_input("Maximum amount", min_value=0.0, value=max(100000.0, float(frame.amount.max()) if not frame.empty else 100000.0))

    frame = frame.loc[frame.date.between(pd.Timestamp(start), pd.Timestamp(end)) & frame.amount.between(low, high)]
    for field, values in [("category", cats), ("account_name", accts), ("kind", kinds), ("payment_method", methods)]:
        if values:
            frame = frame.loc[frame[field].isin(values)]
    if tag:
        frame = frame.loc[frame.tags.fillna("").str.contains(tag, case=False, regex=False)]
    frame = frame.sort_values("date" if order in {"Newest", "Oldest"} else "amount", ascending=order in {"Oldest", "Smallest"})

    income = float(frame.loc[frame.kind.eq("income"), "amount"].sum()) if not frame.empty else 0.0
    expense = float(frame.loc[frame.kind.eq("expense"), "amount"].sum()) if not frame.empty else 0.0
    metrics([("Rows", str(len(frame)), "Filtered ledger rows."), ("Income", rupees(income), "Visible income."), ("Spending", rupees(expense), "Visible expenses.")])

    with st.container(border=True, key="dk-ledger-card"):
        if frame.empty:
            st.info("No transactions match these filters.")
        else:
            shown = frame[["date", "merchant", "kind", "category", "account_name", "amount", "tags"]].copy()
            shown["date"] = shown.date.dt.strftime("%d %b %Y")
            shown["amount"] = shown.amount.map(lambda value: rupees(value, True))
            views.table(shown)

    if not frame.empty:
        labels = {row.id: f'{row.date:%d %b} · {row.merchant or row.category} · {rupees(row.amount)}' for row in frame.itertuples()}
        selected = st.selectbox("Select a transaction to edit", [None] + list(labels), format_func=lambda value: "Choose a transaction" if value is None else labels[value])
        if selected:
            with st.container(border=True, key="dk-editor-card"):
                views.transaction_form(_store().get("transactions", selected))

    with st.expander("Monthly category and daily totals"):
        views.table(an.category_summary(_store(), _month()))
        views.table(an.daily_spending(_store(), _month()))


def budgets_page():
    month = _month()
    store = _store()
    budget = an.budget_summary(store, month)
    overview = an.overview(store, month)
    _page_header("Budgets", "Track category pressure and test purchases against the monthly plan.", f"{month} / PLANNING")

    metrics([
        ("Monthly limit", rupees(overview["budget_limit"]), "Profile limit or category-budget total."),
        ("Spent", rupees(overview["expenses"]), "Recorded expenses this month."),
        ("Remaining", rupees(overview["budget_remaining"]), "Limit minus spending."),
    ])

    main_col, planner_col = st.columns([1.45, .55], gap="medium")
    with main_col:
        with st.container(border=True, key="dk-budget-list"):
            section_header("Category budgets", "Used, remaining and current status.")
            if budget.empty:
                st.info("Create a category budget to see utilization here.")
            else:
                for item in budget.to_dict("records"):
                    progress_card(item["category"], item["spent"], item["limit"], f'{rupees(item["remaining"])} remaining · {item["used_pct"]:.0f}% used · {item["status"]}')
    with planner_col:
        with st.container(border=True, key="dk-purchase-card"):
            section_header("Purchase check", "Test a planned purchase.")
            spend = st.number_input("Planned purchase (₹)", min_value=0.0, value=1000.0, step=100.0)
            st.metric("Left after purchase", rupees(overview["budget_remaining"] - spend))
            st.caption("Arithmetic against your plan, not lending or investment advice.")

    with st.expander("Create or edit a budget", expanded=budget.empty):
        row = views.picker("budgets", name="category")
        with st.form("budget"):
            budget_month = st.text_input("Budget month (YYYY-MM)", row.get("month", month))
            category = st.text_input("Budget category", row.get("category", "Food"))
            limit = st.number_input("Category limit (₹)", min_value=0.0, value=float(row.get("limit_paise", 500000) / 100))
            submitted = st.form_submit_button("Save budget", type="primary")
        if submitted:
            views.save("budgets", row, dict(month=budget_month, category=category, limit_paise=money(limit)))
        views.deletion("budgets", row)
