"""DashboardKit-style finance layouts over FYNTRA's existing domain functions."""
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
            y=alt.Y("Amount:Q", title=None, axis=alt.Axis(format="~s", domain=False, gridColor="#E8EAF0")),
            color=alt.Color("Flow:N", scale=alt.Scale(domain=["income", "expenses"], range=[POSITIVE, NEGATIVE]), legend=alt.Legend(orient="bottom", title=None)),
            tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("Flow:N"), alt.Tooltip("Amount:Q", format=",.0f")],
        )
        .properties(height=300)
        .configure_view(stroke=None)
    )
    st.altair_chart(flow, width="stretch", alt="Income and expenses over recent months")


def overview_page():
    month = _month()
    store = _store()
    o = an.overview(store, month)
    period = pd.Period(month).strftime("%B %Y")
    sub = an.subscription_summary(store)

    _page_header("Financial overview", "A clean read on cash, movement, budget pressure and upcoming commitments.", f"{period.upper()} / OVERVIEW")

    balance_col, income_col, expense_col = st.columns([1.5, .75, .75], gap="medium")
    with balance_col:
        with st.container(border=True, key="dk-balance-card"):
            st.caption("AVAILABLE CASH")
            st.metric("Available cash", rupees(o["balance"]), label_visibility="collapsed")
            a, b = st.columns(2)
            a.metric("Net worth", rupees(o["net_worth"]))
            b.metric("Savings rate", f'{o["savings_rate"]:.1f}%' if o["savings_rate"] is not None else "—")
    with income_col:
        with st.container(border=True, key="dk-income-card"):
            st.caption("MONEY IN")
            st.metric("Money in", rupees(o["income"]), label_visibility="collapsed")
            st.caption("Recorded income this month")
    with expense_col:
        with st.container(border=True, key="dk-expense-card"):
            st.caption("MONEY OUT")
            st.metric("Money out", rupees(o["expenses"]), label_visibility="collapsed")
            st.caption("Transfers excluded")

    chart_col, side_col = st.columns([1.55, .65], gap="medium")
    with chart_col:
        with st.container(border=True, key="dk-cashflow-card"):
            section_header("Cash flow", "Income and spending across the last six months.")
            _cash_flow_chart(an.monthly_summary(store).tail(6))
    with side_col:
        with st.container(border=True, key="dk-budget-card"):
            section_header("Budget", "Current month position.")
            st.metric("Remaining", rupees(o["budget_remaining"]))
            st.metric("Monthly limit", rupees(o["budget_limit"]))
            st.metric("Subscriptions", rupees(sub["monthly_cost"]))
            st.caption(o["pulse"])
            st.write(o["pulse_detail"])

    category_col, activity_col = st.columns([.85, 1.15], gap="medium")
    with category_col:
        with st.container(border=True, key="dk-category-card"):
            section_header("Spending by category", "Selected report month.")
            chart(an.category_summary(store, month), "category:N", "amount:Q", color=NEGATIVE, height=280, title="Spending by category")
    with activity_col:
        with st.container(border=True, key="dk-activity-card"):
            section_header("Recent transactions", "Latest movements in this data view.")
            recent = an.transactions_frame(store)
            if recent.empty:
                st.info("Add your first transaction to see activity here.")
            else:
                rows(recent, limit=8)

    with st.container(border=True, key="dk-horizon-card"):
        section_header("Upcoming", "Bills, renewals and commitments around the selected report date.")
        upcoming = an.timeline(store, views.today() - timedelta(days=30), views.today() + timedelta(days=14))
        upcoming = upcoming.loc[upcoming.status.ne("Recorded")]
        if upcoming.empty:
            st.caption("No upcoming recorded commitments.")
        else:
            cols = st.columns(min(4, len(upcoming.head(4))), gap="medium")
            for column, item in zip(cols, upcoming.head(4).to_dict("records")):
                with column:
                    st.caption(item["status"].upper())
                    st.write(f'**{item["name"]}**')
                    st.metric("Amount", rupees(item["amount"]), label_visibility="collapsed")
                    st.caption(str(item["date"]))

    goals = an.goal_summary(store)
    if not goals.empty or o["debt"]:
        with st.expander("Savings goals & debt"):
            st.write(f'Total liabilities: **{rupees(o["debt"])}**')
            for goal in goals.to_dict("records"):
                progress_card(goal["name"], goal["saved"], goal["target"], str(goal["target_date"]))


def transactions_page():
    _page_header("Transactions", "Search, filter and edit the ledger without losing context.", "LEDGER")
    mode = st.segmented_control("View", ["History", "Add transaction", "Recurring"], default="History")
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
