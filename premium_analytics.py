"""DashboardKit-style analytics workspace over FYNTRA's existing analytics layer."""
import streamlit as st

import analytics as an
import views
from modern_ui import ACCENT, NEGATIVE, POSITIVE, WARNING, chart, metrics, rupees, section_header


def _page_header(title, copy, kicker):
    st.html(f'<section class="dk-page-head"><div><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></div></section>')


def analytics_page():
    store = views.current()
    month = views.month()
    review = an.monthly_review(store, month)
    summary = an.monthly_summary(store)
    daily = an.daily_spending(store, month)

    _page_header("Cash flow & insights", "Explore movement, spending patterns, net worth and monthly changes from the ledger you already own.", f"{month} / ANALYTICS")

    metrics([
        ("Net cash flow", rupees(review["net"]), "Income minus expenses."),
        ("Income", rupees(review["income"]), "Recorded income in the selected month."),
        ("Expenses", rupees(review["expenses"]), "Recorded expenses; transfers excluded."),
        ("Daily average", rupees(review["average_daily_spend"]), "Average daily spending this month."),
    ])

    main_col, side_col = st.columns([1.55, .65], gap="medium")
    with main_col:
        with st.container(border=True, key="dk-analytics-cashflow"):
            section_header("Cash flow over time", "Monthly net movement across your recorded history.")
            chart(summary, "month:N", "net:Q", "area", color=ACCENT, height=330, title="Monthly net cash flow")
    with side_col:
        with st.container(border=True, key="dk-analytics-summary"):
            section_header("Month summary", "The facts that explain this month fastest.")
            st.metric("Largest expense", rupees(review["largest_amount"]), help=review["largest_expense"] or "No expenses")
            st.metric("Top category", review["top_category"] or "—")
            st.metric("Budgets exceeded", str(review["budgets_exceeded"]))

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True, key="dk-analytics-category"):
            section_header("Category spending", "Where money went in the selected month.")
            chart(an.category_summary(store, month), "category:N", "amount:Q", "bar", color=NEGATIVE, height=280, title="Category spending")
        with st.container(border=True, key="dk-analytics-daily"):
            section_header("Daily spending", "Daily values and seven-day trailing average.")
            chart(daily, "date:T", "amount:Q", "bar", color=WARNING, height=220, title="Daily spending")
            chart(daily, "date:T", "rolling_7d:Q", "line", color=ACCENT, height=140, title="Seven-day trailing average")
    with right:
        with st.container(border=True, key="dk-analytics-position"):
            section_header("Position", "Longer-term spending, wealth and account distribution.")
            chart(summary, "month:N", "expenses:Q", "area", color=NEGATIVE, height=210, title="Monthly expenses")
            chart(an.net_worth_history(store), "date:T", "net_worth:Q", "line", color=POSITIVE, height=210, title="Net worth")
            chart(an.account_summary(store), "name:N", "balance:Q", "bar", color=ACCENT, height=210, title="Account balances")

    if month == views.today().strftime("%Y-%m"):
        with st.container(border=True, key="dk-analytics-projection"):
            section_header("If this pace continues", "Simple arithmetic using recorded spending pace, not a prediction.")
            metrics([
                ("Month-end spending", rupees(review["projected_month_expense"]), "Expenses so far plus average daily spend times remaining days."),
                ("Month-end cash", rupees(review["projected_end_balance"]), "Current cash minus projected remaining spending, assuming no new income."),
            ])

    with st.container(border=True, key="dk-analytics-review"):
        section_header("Monthly review", "A concise summary of what changed.")
        metrics([
            ("Debt principal reduced", rupees(review["debt_reduced"]), "Recorded principal payments this month."),
            ("Net-worth change", rupees(review["net_worth_change"]), "Requires a snapshot before and within this month."),
            ("Bills paid", str(review["bills_paid"]), "Recorded bill payments this month."),
            ("Renewals", str(review["subscriptions_paid"]), "Subscription renewals recorded this month."),
        ])

    insights = review.get("insights") or []
    if insights:
        with st.expander("What changed this month?"):
            for text in insights:
                st.write("• " + text)

    with st.expander("Detailed month-by-month figures"):
        budget = an.budget_summary(store, month)
        if not budget.empty:
            views.table(budget[["category", "limit", "spent", "remaining", "used_pct", "status"]])
        subscriptions = an.subscription_summary(store)["table"]
        chart(subscriptions, "name:N", "monthly:Q", "bar", color=WARNING, height=220, title="Monthly subscription equivalents")
        views.table(summary)
        if not daily.empty:
            st.write("Highest spending days")
            views.table(daily.nlargest(5, "amount")[["date", "amount"]])
