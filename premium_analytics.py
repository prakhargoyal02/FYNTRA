"""Premium financial-intelligence composition over the existing analytics layer."""
import streamlit as st

import analytics as an
import views
from ui import ACCENT, NEGATIVE, POSITIVE, WARNING, chart, hero, insight_panel, metrics, rupees, section_header


def analytics_page():
    store = views.current()
    month = views.month()
    review = an.monthly_review(store, month)
    summary = an.monthly_summary(store)
    daily = an.daily_spending(store, month)

    hero(
        "See the pattern. Shape what comes next.",
        "Financial intelligence from the ledger you already own, with every number traceable back to recorded data.",
        f"CASH FLOW & INSIGHTS / {month}",
    )

    metrics([
        ("Net cash flow", rupees(review["net"]), "Income minus expenses in the selected month."),
        ("Income", rupees(review["income"]), "Recorded income in the selected month."),
        ("Expenses", rupees(review["expenses"]), "Recorded expenses; transfers excluded."),
        ("Daily average", rupees(review["average_daily_spend"]), "Average spend including zero-spend days through the report date."),
    ])

    section_header("Cash flow over time", "The long view first. Net movement shows whether each month created or consumed cash.")
    chart(summary, "month:N", "net:Q", "area", color=ACCENT, height=350, title="Monthly net cash flow")

    left, right = st.columns([1.18, .82], gap="large")
    with left:
        section_header("Where money went", "Selected-month spending by category.")
        chart(an.category_summary(store, month), "category:N", "amount:Q", "bar", color=NEGATIVE, height=300, title="Category spending")

        section_header("Daily spending rhythm", "Daily values first, then the seven-day trailing average.")
        chart(daily, "date:T", "amount:Q", "bar", color=WARNING, height=235, title="Daily spending")
        chart(daily, "date:T", "rolling_7d:Q", "line", color=ACCENT, height=150, title="Seven-day trailing average spending")

    with right:
        section_header("Monthly spending", "Expense pressure across the full recorded history.")
        chart(summary, "month:N", "expenses:Q", "area", color=NEGATIVE, height=245, title="Monthly expenses")

        section_header("Recorded net worth", "Snapshots are observations, so later edits do not rewrite old snapshots.")
        chart(an.net_worth_history(store), "date:T", "net_worth:Q", "line", color=POSITIVE, height=245, title="Recorded net worth")

        section_header("Account distribution", "Current balances in this data view.")
        chart(an.account_summary(store), "name:N", "balance:Q", "bar", color=ACCENT, height=230, title="Account balances")

    if month == views.today().strftime("%Y-%m"):
        section_header("If this pace continues", "Simple arithmetic using recorded spending pace, not a prediction.")
        metrics([
            ("Month-end spending", rupees(review["projected_month_expense"]), "Expenses so far plus average daily spend times remaining days."),
            ("Month-end cash", rupees(review["projected_end_balance"]), "Current cash minus projected remaining spending, assuming no new income."),
        ])
        st.caption("Upcoming bills are not added again because the average already represents spending. Timing and one-off purchases can change the result.")

    section_header("Monthly review", "A concise set of facts to explain what actually changed.")
    metrics([
        ("Largest expense", rupees(review["largest_amount"]), review["largest_expense"] or "No expenses"),
        ("Top category", review["top_category"] or "—", "Highest recorded category total."),
        ("Budgets exceeded", str(review["budgets_exceeded"]), "Categories over 100%."),
        ("Debt principal reduced", rupees(review["debt_reduced"]), "Recorded principal payments this month."),
        ("Net-worth change", rupees(review["net_worth_change"]), "Requires a snapshot before and within this month."),
    ])
    st.caption(
        f'Bills paid: {review["bills_paid"]} · Subscription renewals recorded: {review["subscriptions_paid"]}'
    )

    insights = review.get("insights") or []
    if insights:
        section_header("What changed this month?", "Generated from recorded comparisons, not hidden recommendation logic.")
        insight_columns = st.columns(2, gap="large")
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
