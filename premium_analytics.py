"""Template-driven financial-intelligence composition over the existing analytics layer."""
import streamlit as st

import analytics as an
import views
from modern_ui import ACCENT, ACCENT_2, NEGATIVE, POSITIVE, WARNING, chart, hero, insight_panel, metrics, rupees, section_header


def analytics_page():
    store = views.current()
    month = views.month()
    review = an.monthly_review(store, month)
    summary = an.monthly_summary(store)
    daily = an.daily_spending(store, month)

    with st.container(key="analytics-hero-stage"):
        intro, headline = st.columns([1.35, .65], gap="large", vertical_alignment="bottom")
        with intro:
            hero(
                "Turn the ledger into a clearer signal.",
                "Movement, pressure, recurring costs and change over time, organized for decisions instead of decoration.",
                f"CASH FLOW & INSIGHTS / {month}",
            )
        with headline:
            st.caption("MONTHLY CASH FLOW")
            st.metric("Net cash flow", rupees(review["net"]), label_visibility="collapsed")
            st.caption("Income minus expenses in the selected month.")

    with st.container(border=True, key="analytics-cashflow-panel"):
        section_header("Cash flow over time", "One wide view first. The rest of the page explains what created the movement.")
        chart(summary, "month:N", "net:Q", "area", color=ACCENT, height=360, title="Monthly net cash flow")
        metrics([
            ("Income", rupees(review["income"]), "Recorded income in the selected month."),
            ("Expenses", rupees(review["expenses"]), "Recorded expenses; transfers excluded."),
            ("Daily average", rupees(review["average_daily_spend"]), "Average spending per day in this month."),
        ])

    left, right = st.columns([1.15, .85], gap="medium")
    with left:
        with st.container(border=True, key="analytics-category-panel"):
            section_header("Where money went", "Selected-month spending by category.")
            chart(an.category_summary(store, month), "category:N", "amount:Q", "bar", color=NEGATIVE, height=315, title="Category spending")
        with st.container(border=True, key="analytics-rhythm-panel"):
            section_header("Daily rhythm", "Daily spending with the seven-day trailing average underneath.")
            chart(daily, "date:T", "amount:Q", "bar", color=WARNING, height=235, title="Daily spending")
            chart(daily, "date:T", "rolling_7d:Q", "line", color=ACCENT_2, height=145, title="Seven-day trailing average spending")
    with right:
        with st.container(border=True, key="analytics-fastread-panel"):
            section_header("Fast read", "The facts that explain this month fastest.")
            st.metric("Largest expense", rupees(review["largest_amount"]), help=review["largest_expense"] or "No expenses")
            st.metric("Top category", review["top_category"] or "—")
            st.metric("Budgets exceeded", str(review["budgets_exceeded"]))
        with st.container(border=True, key="analytics-position-panel"):
            section_header("Longer position", "The view beyond one month.")
            chart(an.net_worth_history(store), "date:T", "net_worth:Q", "line", color=POSITIVE, height=220, title="Recorded net worth")
            chart(an.account_summary(store), "name:N", "balance:Q", "bar", color=ACCENT, height=210, title="Account balances")

    if month == views.today().strftime("%Y-%m"):
        with st.container(border=True, key="analytics-projection-panel"):
            section_header("If this pace continues", "Simple arithmetic using recorded spending pace, not a prediction.")
            metrics([
                ("Month-end spending", rupees(review["projected_month_expense"]), "Expenses so far plus average daily spend times remaining days."),
                ("Month-end cash", rupees(review["projected_end_balance"]), "Current cash minus projected remaining spending, assuming no new income."),
            ])
            st.caption("Upcoming bills are not added again because the average already represents spending. Timing and one-off purchases can change the result.")

    with st.container(border=True, key="analytics-review-panel"):
        section_header("Monthly review", "A concise set of facts to explain what actually changed.")
        metrics([
            ("Debt principal reduced", rupees(review["debt_reduced"]), "Recorded principal payments this month."),
            ("Net-worth change", rupees(review["net_worth_change"]), "Requires a snapshot before and within this month."),
            ("Largest expense", review["largest_expense"] or "—", "Largest recorded expense description."),
        ])
        st.caption(f'Bills paid: {review["bills_paid"]} · Subscription renewals recorded: {review["subscriptions_paid"]}')

    insights = review.get("insights") or []
    if insights:
        section_header("What changed this month?", "Generated from recorded comparisons, not hidden recommendation logic.")
        insight_columns = st.columns(2, gap="medium")
        for index, text in enumerate(insights):
            with insight_columns[index % 2]:
                insight_panel(f"Insight {index + 1:02d}", text)

    with st.expander("Budget, subscriptions and detailed month-by-month figures"):
        budget = an.budget_summary(store, month)
        if not budget.empty:
            views.table(budget[["category", "limit", "spent", "remaining", "used_pct", "status"]])
        subscriptions = an.subscription_summary(store)["table"]
        chart(subscriptions, "name:N", "monthly:Q", "bar", color=WARNING, height=220, title="Monthly subscription equivalents")
        views.table(summary)
        chart(summary, "month:N", "income:Q", "line", color=POSITIVE, height=190, title="Monthly income")
        if not daily.empty:
            st.write("Highest spending days")
            views.table(daily.nlargest(5, "amount")[["date", "amount"]])
