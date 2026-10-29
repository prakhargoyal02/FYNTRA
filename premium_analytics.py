"""Premium financial-intelligence composition over the existing analytics layer."""
import streamlit as st

import analytics as an
import views
from modern_ui import ACCENT, NEGATIVE, POSITIVE, WARNING, chart, hero, insight_panel, metrics, rupees, section_header


def analytics_page():
    store = views.current()
    month = views.month()
    review = an.monthly_review(store, month)
    summary = an.monthly_summary(store)
    daily = an.daily_spending(store, month)

    hero(
        "Patterns are easier to act on when they breathe.",
        "Financial intelligence from the ledger you already own, arranged around movement, pressure and change.",
        f"CASH FLOW & INSIGHTS / {month}",
    )

    lead_col, review_col = st.columns([1.4, .8], gap="medium")
    with lead_col:
        with st.container(border=True, key="bento-balance"):
            st.caption("MONTHLY CASH FLOW")
            st.metric("Net cash flow", rupees(review["net"]), help="Income minus expenses in the selected month.")
            left, right = st.columns(2)
            left.metric("Income", rupees(review["income"]), help="Recorded income in the selected month.")
            right.metric("Expenses", rupees(review["expenses"]), help="Recorded expenses; transfers excluded.")
    with review_col:
        with st.container(border=True, key="bento-pulse"):
            section_header("Fast read", "The facts that explain this month fastest.")
            st.metric("Largest expense", rupees(review["largest_amount"]), help=review["largest_expense"] or "No expenses")
            st.metric("Top category", review["top_category"] or "—")
            st.metric("Daily average", rupees(review["average_daily_spend"]))

    with st.container(border=True, key="bento-motion"):
        section_header("Cash flow over time", "Net movement shows whether each month created or consumed cash.")
        chart(summary, "month:N", "net:Q", "area", color=ACCENT, height=350, title="Monthly net cash flow")

    left, right = st.columns([1.15, .85], gap="medium")
    with left:
        with st.container(border=True, key="bento-spending"):
            section_header("Where money went", "Selected-month spending by category.")
            chart(an.category_summary(store, month), "category:N", "amount:Q", "bar", color=NEGATIVE, height=300, title="Category spending")

        with st.container(border=True, key="bento-activity"):
            section_header("Daily spending rhythm", "Daily values first, then the seven-day trailing average.")
            chart(daily, "date:T", "amount:Q", "bar", color=WARNING, height=230, title="Daily spending")
            chart(daily, "date:T", "rolling_7d:Q", "line", color=ACCENT, height=145, title="Seven-day trailing average spending")

    with right:
        with st.container(border=True, key="bento-position"):
            section_header("Longer position", "Monthly pressure, recorded wealth and account distribution.")
            chart(summary, "month:N", "expenses:Q", "area", color=NEGATIVE, height=220, title="Monthly expenses")
            chart(an.net_worth_history(store), "date:T", "net_worth:Q", "line", color=POSITIVE, height=220, title="Recorded net worth")
            chart(an.account_summary(store), "name:N", "balance:Q", "bar", color=ACCENT, height=215, title="Account balances")

    if month == views.today().strftime("%Y-%m"):
        with st.container(border=True, key="bento-budget"):
            section_header("If this pace continues", "Simple arithmetic using recorded spending pace, not a prediction.")
            metrics([
                ("Month-end spending", rupees(review["projected_month_expense"]), "Expenses so far plus average daily spend times remaining days."),
                ("Month-end cash", rupees(review["projected_end_balance"]), "Current cash minus projected remaining spending, assuming no new income."),
            ])
            st.caption("Upcoming bills are not added again because the average already represents spending. Timing and one-off purchases can change the result.")

    with st.container(border=True, key="bento-horizon"):
        section_header("Monthly review", "A concise set of facts to explain what actually changed.")
        metrics([
            ("Budgets exceeded", str(review["budgets_exceeded"]), "Categories over 100%."),
            ("Debt principal reduced", rupees(review["debt_reduced"]), "Recorded principal payments this month."),
            ("Net-worth change", rupees(review["net_worth_change"]), "Requires a snapshot before and within this month."),
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
