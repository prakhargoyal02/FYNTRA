"""Premium presentation compositions built on the existing FYNTRA domain functions.

This module deliberately contains no database rules. It reads the same analytics and
calls the same reusable actions as views.py, but gives the primary experience a more
editorial visual hierarchy.
"""
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

import analytics as an
import views
from database import money
from ui import ACCENT, NEGATIVE, POSITIVE, chart, hero, insight_panel, metrics, progress_card, rows, rupees, section_header


def _month():
    return views.month()


def _store():
    return views.current()


def _cash_flow_chart(summary):
    if summary.empty:
        st.caption("Your cash-flow story appears when you add transactions.")
        return
    plot = summary.melt("month", ["income", "expenses"], var_name="Flow", value_name="Amount")
    flow = (
        alt.Chart(plot)
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, opacity=.88)
        .encode(
            x=alt.X("month:N", title=None, axis=alt.Axis(labelAngle=0, domain=False, ticks=False, labelColor="#87938E")),
            xOffset="Flow:N",
            y=alt.Y("Amount:Q", title=None, axis=alt.Axis(format="~s", domain=False, gridColor="#1E2724", tickColor="#29332F", labelColor="#87938E")),
            color=alt.Color(
                "Flow:N",
                scale=alt.Scale(domain=["income", "expenses"], range=[POSITIVE, NEGATIVE]),
                legend=alt.Legend(orient="bottom", title=None, labelColor="#8F9B96", padding=10),
            ),
            tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("Flow:N"), alt.Tooltip("Amount:Q", format=",.0f")],
        )
        .properties(height=330)
        .configure_view(stroke=None)
    )
    st.altair_chart(flow, width="stretch", alt="Income and expenses over recent months")


def overview_page():
    """Financial story first: position, movement, spending, activity and what is next."""
    month = _month()
    store = _store()
    o = an.overview(store, month)
    period = pd.Period(month).strftime("%B %Y")

    hero(
        "Your money, without the noise.",
        "A single view of what changed, what remains, and what deserves your attention next.",
        f"{period.upper()} / OVERVIEW",
    )

    balance_col, pulse_col = st.columns([1.6, .72], gap="large", vertical_alignment="bottom")
    with balance_col:
        with st.container(key="fyntra-overview-balance"):
            st.metric(
                "Available cash",
                rupees(o["balance"]),
                help="Current non-investment, non-card account balances through the selected report date.",
            )
            st.caption("Liquid position across the accounts currently in this data view.")
    with pulse_col:
        insight_panel(o["pulse"], o["pulse_detail"])

    metrics([
        ("Money in", rupees(o["income"]), "Recorded income this report month."),
        ("Money out", rupees(o["expenses"]), "Recorded expenses; transfers excluded."),
        ("Budget left", rupees(o["budget_remaining"]), "Monthly spending limit minus expenses."),
        ("Savings rate", f'{o["savings_rate"]:.1f}%' if o["savings_rate"] is not None else "—", "Net cash flow divided by income."),
    ])

    section_header("Money in motion", "Six recent months, stripped back to the movement that matters.")
    _cash_flow_chart(an.monthly_summary(store).tail(6))

    spend_col, position_col = st.columns([1.55, .85], gap="large")
    with spend_col:
        section_header("Where spending went", "Category totals for the selected report month.")
        chart(an.category_summary(store, month), "category:N", "amount:Q", color=ACCENT, height=285, title="Spending by category")
    with position_col:
        section_header("Position", "A compact read on wealth, cash creation and recurring commitments.")
        sub = an.subscription_summary(store)
        metrics([
            ("Net worth", rupees(o["net_worth"]), "Assets minus negative balances and standalone debts."),
            ("Cash saved", rupees(o["net"]), "Income minus expenses for the report month."),
            ("Subscriptions", rupees(sub["monthly_cost"]), "Monthly equivalent of active subscriptions."),
        ])

    activity_col, horizon_col = st.columns([1.45, .8], gap="large")
    with activity_col:
        section_header("Latest activity", "The newest recorded movements in this data view.")
        recent = an.transactions_frame(store)
        if recent.empty:
            st.info("Add your first transaction to see activity here.")
        else:
            rows(recent, limit=7)
    with horizon_col:
        section_header("On the horizon", "Recorded commitments approaching the selected report date.")
        upcoming = an.timeline(store, views.today() - timedelta(days=30), views.today() + timedelta(days=14))
        upcoming = upcoming.loc[upcoming.status.ne("Recorded")]
        if upcoming.empty:
            st.caption("No upcoming recorded commitments.")
        else:
            for item in upcoming.head(5).to_dict("records"):
                with st.container(border=True):
                    st.write(f'**{item["name"]}**')
                    st.metric("Amount", rupees(item["amount"]), label_visibility="collapsed")
                    st.caption(f'{item["date"]} · {item["status"]}')

    goals = an.goal_summary(store)
    if not goals.empty or o["debt"]:
        with st.expander("Savings goals & debt"):
            st.write(f'Total liabilities: **{rupees(o["debt"])}**')
            for goal in goals.to_dict("records"):
                progress_card(goal["name"], goal["saved"], goal["target"], str(goal["target_date"]))


def transactions_page():
    """Keep transaction CRUD intact while presenting the ledger as a readable stream."""
    hero(
        "Every move, accounted for.",
        "Search the ledger, record a movement, or manage predictable recurring entries.",
        "TRANSACTIONS",
    )
    mode = st.segmented_control("View", ["History", "Add transaction", "Recurring"], default="History")
    if mode == "Add transaction":
        views.transaction_form()
        return
    if mode == "Recurring":
        views.recurring_page()
        return

    frame = an.transactions_frame(_store(), posted=False)
    search = st.text_input("Search transactions", placeholder="Merchant, note, category, tag or amount")
    if search:
        text = frame[["merchant", "notes", "category", "tags", "amount"]].astype(str).agg(" ".join, axis=1)
        frame = frame.loc[text.str.contains(search, case=False, regex=False)]

    with st.expander("Filters", expanded=False):
        first, second = st.columns(2)
        start = first.date_input("From", views.d(_month() + "-01"))
        end = second.date_input("To", pd.Period(_month()).end_time.date())
        cats = st.multiselect("Categories", sorted(frame.category.unique().tolist()))
        accts = st.multiselect("Accounts", _store().frame("accounts").name.tolist())
        kinds = st.multiselect("Types", ["income", "expense", "transfer"])
        methods = st.multiselect("Payment methods", sorted(frame.payment_method.unique().tolist()))
        tag = st.text_input("Tag filter")
        low = st.number_input("Minimum amount", min_value=0.0, value=0.0)
        high = st.number_input(
            "Maximum amount",
            min_value=0.0,
            value=max(100000.0, float(frame.amount.max()) if not frame.empty else 100000.0),
        )

    frame = frame.loc[frame.date.between(pd.Timestamp(start), pd.Timestamp(end)) & frame.amount.between(low, high)]
    for field, values in [("category", cats), ("account_name", accts), ("kind", kinds), ("payment_method", methods)]:
        if values:
            frame = frame.loc[frame[field].isin(values)]
    if tag:
        frame = frame.loc[frame.tags.fillna("").str.contains(tag, case=False, regex=False)]

    sort_col, summary_col = st.columns([.78, 1.22], gap="large", vertical_alignment="bottom")
    with sort_col:
        order = st.selectbox("Sort by", ["Newest", "Oldest", "Largest", "Smallest"])
    frame = frame.sort_values(
        "date" if order in {"Newest", "Oldest"} else "amount",
        ascending=order in {"Oldest", "Smallest"},
    )
    with summary_col:
        visible_income = float(frame.loc[frame.kind.eq("income"), "amount"].sum()) if not frame.empty else 0.0
        visible_expense = float(frame.loc[frame.kind.eq("expense"), "amount"].sum()) if not frame.empty else 0.0
        metrics([
            ("Visible rows", str(len(frame)), "Transactions after the current search and filters."),
            ("Income", rupees(visible_income), "Income inside the filtered result."),
            ("Spending", rupees(visible_expense), "Expenses inside the filtered result."),
        ])

    section_header("Ledger", "Future entries remain planned and do not affect current balances.")
    if frame.empty:
        st.info("No transactions match these filters.")
    else:
        rows(frame, limit=20)
        if len(frame) > 20:
            st.caption(f"Showing the first 20 of {len(frame)} filtered transactions. Open Detailed ledger for every row.")

    with st.expander("Detailed ledger"):
        shown = frame[["date", "merchant", "kind", "category", "account_name", "amount", "tags"]].copy()
        shown["date"] = shown.date.dt.strftime("%d %b %Y")
        shown["amount"] = shown.amount.map(lambda value: rupees(value, True))
        views.table(shown)

    if not frame.empty:
        labels = {
            row.id: f'{row.date:%d %b} · {row.merchant or row.category} · {rupees(row.amount)} · {str(row.id)[:6]}'
            for row in frame.itertuples()
        }
        selected = st.selectbox(
            "Select a transaction to edit",
            [None] + list(labels),
            format_func=lambda value: "Choose a transaction" if value is None else labels[value],
        )
        if selected:
            views.transaction_form(_store().get("transactions", selected))

    with st.expander("Monthly category and daily totals"):
        views.table(an.category_summary(_store(), _month()))
        views.table(an.daily_spending(_store(), _month()))


def budgets_page():
    """Show budget pressure as a scan-friendly progression instead of stacked cards."""
    month = _month()
    store = _store()
    budget = an.budget_summary(store, month)
    overview = an.overview(store, month)
    hero(
        "Give your money direction.",
        "See the room left in every category before the month decides for you.",
        f"BUDGETS / {month}",
    )
    metrics([
        ("Monthly limit", rupees(overview["budget_limit"]), "Profile limit, or the sum of category budgets."),
        ("Spent", rupees(overview["expenses"]), "All expenses, including unbudgeted categories."),
        ("Remaining", rupees(overview["budget_remaining"]), "Limit minus recorded spending."),
    ])

    section_header("Category pressure", "Progress is calm when healthy and becomes more important as a limit approaches.")
    if budget.empty:
        st.info("Create a category budget to see utilization here.")
    else:
        for item in budget.to_dict("records"):
            progress_card(
                item["category"],
                item["spent"],
                item["limit"],
                f'{rupees(item["remaining"])} remaining · {item["used_pct"]:.0f}% used · {item["status"]}',
            )
    st.caption("Healthy ≤60% · Watch >60–85% · Near limit >85–100% · Over budget >100%.")

    edit_col, fit_col = st.columns([1.12, .88], gap="large")
    with edit_col:
        with st.expander("Create or edit a budget", expanded=budget.empty):
            row = views.picker("budgets", name="category")
            with st.form("budget"):
                budget_month = st.text_input("Budget month (YYYY-MM)", row.get("month", month))
                category = st.text_input("Budget category", row.get("category", "Food"))
                limit = st.number_input(
                    "Category limit (₹)",
                    min_value=0.0,
                    value=float(row.get("limit_paise", 500000) / 100),
                )
                submitted = st.form_submit_button("Save budget", type="primary")
            if submitted:
                views.save("budgets", row, dict(month=budget_month, category=category, limit_paise=money(limit)))
            views.deletion("budgets", row)
    with fit_col:
        section_header("Can it fit?", "A quick affordability check against the remaining monthly budget.")
        spend = st.number_input("Planned purchase (₹)", min_value=0.0, value=1000.0, step=100.0)
        st.metric("Budget left after purchase", rupees(overview["budget_remaining"] - spend))
        st.caption("This is arithmetic against your budget, not lending or investment advice.")
