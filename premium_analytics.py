"""DashboardKit-style analytics workspace over FYNTRA's existing analytics layer."""
import altair as alt
import pandas as pd
import streamlit as st

import analytics as an
import views
from modern_ui import ACCENT, NEGATIVE, POSITIVE, WARNING, chart, metrics, rupees, section_header


def _page_header(title, copy, kicker):
    st.html(
        f'<section class="dk-page-head"><div><span>{kicker}</span><h1>{title}</h1><p>{copy}</p></div></section>'
    )


def _budget_donut(spent, limit):
    """Compact budget chart with a separate legend so labels never overlap."""
    limit = float(limit or 0)
    spent = max(0.0, float(spent or 0))
    if limit <= 0:
        st.caption("Set a monthly budget to see utilization here.")
        return

    used = min(spent, limit)
    remaining = max(0.0, limit - spent)
    over = max(0.0, spent - limit)
    records = [{"Part": "Used", "Amount": used}]
    if remaining:
        records.append({"Part": "Remaining", "Amount": remaining})
    if over:
        records.append({"Part": "Over", "Amount": over})

    frame = pd.DataFrame(records)
    palette = alt.Scale(
        domain=["Used", "Remaining", "Over"],
        range=[POSITIVE, "#2A3B32", NEGATIVE],
    )

    chart_col, legend_col = st.columns([0.95, 1.05], gap="small", vertical_alignment="center")
    with chart_col:
        arc = (
            alt.Chart(frame)
            .mark_arc(innerRadius=42, outerRadius=69, cornerRadius=4)
            .encode(
                theta=alt.Theta("Amount:Q", stack=True),
                color=alt.Color("Part:N", scale=palette, legend=None),
                tooltip=[
                    "Part:N",
                    alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f"),
                ],
            )
        )
        label = pd.DataFrame({"Label": [f"{spent / limit:.0%}"]})
        center = (
            alt.Chart(label)
            .mark_text(color="#F3F3E9", fontSize=20, fontWeight=600)
            .encode(text="Label:N")
        )
        donut = (
            (arc + center)
            .properties(height=170)
            .configure(background="transparent")
            .configure_view(stroke=None, fill="transparent")
        )
        st.altair_chart(
            donut,
            width="stretch",
            alt="Budget used and remaining",
        )

    with legend_col:
        st.markdown(f"**Used**  \n{rupees(used)} · {used / limit:.0%}")
        st.caption("Remaining")
        st.write(f"**{rupees(remaining)}** · {remaining / limit:.0%}")
        if over:
            st.caption("Over")
            st.write(f"**{rupees(over)}**")


def analytics_page():
    store = views.current()
    month = views.month()
    review = an.monthly_review(store, month)
    overview = an.overview(store, month)
    summary = an.monthly_summary(store)
    daily = an.daily_spending(store, month)

    _page_header(
        "Cash flow & insights",
        "Explore movement, spending patterns, net worth and monthly changes from the ledger you already own.",
        f"{month} / ANALYTICS",
    )

    metrics(
        [
            ("Net cash flow", rupees(review["net"]), "Income minus expenses."),
            (
                "Income",
                rupees(review["income"]),
                "Recorded income in the selected month.",
            ),
            (
                "Expenses",
                rupees(review["expenses"]),
                "Recorded expenses; transfers excluded.",
            ),
            (
                "Daily average",
                rupees(review["average_daily_spend"]),
                "Average daily spending this month.",
            ),
        ]
    )

    main_col, side_col = st.columns([1.55, 0.65], gap="medium")
    with main_col:
        with st.container(border=True, key="dk-analytics-cashflow"):
            section_header(
                "Cash flow over time",
                "Monthly net movement across your recorded history.",
            )
            chart(
                summary,
                "month:N",
                "net:Q",
                "area",
                color=ACCENT,
                height=300,
                title="Monthly net cash flow",
            )
    with side_col:
        with st.container(border=True, key="dk-analytics-summary"):
            section_header(
                "Month summary",
                "The facts that explain this month fastest.",
            )
            st.metric(
                "Largest expense",
                rupees(review["largest_amount"]),
                help=review["largest_expense"] or "No expenses",
            )
            st.metric("Top category", review["top_category"] or "—")
            st.metric("Budgets exceeded", str(review["budgets_exceeded"]))

    budget_col, review_col = st.columns([0.72, 1.28], gap="medium")
    with budget_col:
        with st.container(border=True, key="dk-analytics-budget"):
            section_header(
                "Budget utilization",
                "Used versus remaining this month.",
            )
            _budget_donut(overview["expenses"], overview["budget_limit"])
            if overview["budget_limit"]:
                st.caption(
                    f'{rupees(overview["budget_remaining"])} remaining of {rupees(overview["budget_limit"])}'
                )
    with review_col:
        with st.container(border=True, key="dk-analytics-review-fast"):
            section_header(
                "This month at a glance",
                "A compact operational read.",
            )
            metrics(
                [
                    (
                        "Budget remaining",
                        rupees(overview["budget_remaining"]),
                        "Monthly limit minus expenses.",
                    ),
                    (
                        "Savings rate",
                        f'{overview["savings_rate"]:.1f}%'
                        if overview["savings_rate"] is not None
                        else "—",
                        "Net cash flow divided by income.",
                    ),
                    (
                        "Debt remaining",
                        rupees(overview["debt"]),
                        "Recorded liabilities.",
                    ),
                ]
            )

    left, right = st.columns(2, gap="medium")
    with left:
        with st.container(border=True, key="dk-analytics-category"):
            section_header(
                "Category spending",
                "Where money went in the selected month.",
            )
            chart(
                an.category_summary(store, month),
                "category:N",
                "amount:Q",
                "bar",
                color=NEGATIVE,
                height=250,
                title="Category spending",
            )
        with st.container(border=True, key="dk-analytics-daily"):
            section_header(
                "Daily spending",
                "Daily values and seven-day trailing average.",
            )
            chart(
                daily,
                "date:T",
                "amount:Q",
                "bar",
                color=WARNING,
                height=200,
                title="Daily spending",
            )
            chart(
                daily,
                "date:T",
                "rolling_7d:Q",
                "line",
                color=ACCENT,
                height=125,
                title="Seven-day trailing average",
            )
    with right:
        with st.container(border=True, key="dk-analytics-position"):
            section_header(
                "Position",
                "Longer-term spending, wealth and account distribution.",
            )
            chart(
                summary,
                "month:N",
                "expenses:Q",
                "area",
                color=NEGATIVE,
                height=190,
                title="Monthly expenses",
            )
            chart(
                an.net_worth_history(store),
                "date:T",
                "net_worth:Q",
                "line",
                color=POSITIVE,
                height=190,
                title="Net worth",
            )
            chart(
                an.account_summary(store),
                "name:N",
                "balance:Q",
                "bar",
                color=ACCENT,
                height=190,
                title="Account balances",
            )

    if month == views.today().strftime("%Y-%m"):
        with st.container(border=True, key="dk-analytics-projection"):
            section_header(
                "If this pace continues",
                "Simple arithmetic using recorded spending pace, not a prediction.",
            )
            metrics(
                [
                    (
                        "Month-end spending",
                        rupees(review["projected_month_expense"]),
                        "Expenses so far plus average daily spend times remaining days.",
                    ),
                    (
                        "Month-end cash",
                        rupees(review["projected_end_balance"]),
                        "Current cash minus projected remaining spending, assuming no new income.",
                    ),
                ]
            )

    with st.container(border=True, key="dk-analytics-review"):
        section_header(
            "Monthly review",
            "A concise summary of what changed.",
        )
        metrics(
            [
                (
                    "Debt principal reduced",
                    rupees(review["debt_reduced"]),
                    "Recorded principal payments this month.",
                ),
                (
                    "Net-worth change",
                    rupees(review["net_worth_change"]),
                    "Requires a snapshot before and within this month.",
                ),
                (
                    "Bills paid",
                    str(review["bills_paid"]),
                    "Recorded bill payments this month.",
                ),
                (
                    "Renewals",
                    str(review["subscriptions_paid"]),
                    "Subscription renewals recorded this month.",
                ),
            ]
        )

    insights = review.get("insights") or []
    if insights:
        with st.expander("What changed this month?"):
            for text in insights:
                st.write("• " + text)

    with st.expander("Detailed month-by-month figures"):
        budget = an.budget_summary(store, month)
        if not budget.empty:
            views.table(
                budget[
                    [
                        "category",
                        "limit",
                        "spent",
                        "remaining",
                        "used_pct",
                        "status",
                    ]
                ]
            )
        subscriptions = an.subscription_summary(store)["table"]
        chart(
            subscriptions,
            "name:N",
            "monthly:Q",
            "bar",
            color=WARNING,
            height=200,
            title="Monthly subscription equivalents",
        )
        views.table(summary)
        if not daily.empty:
            st.write("Highest spending days")
            views.table(daily.nlargest(5, "amount")[["date", "amount"]])
