"""Template-driven page compositions over the existing FYNTRA domain functions."""
from datetime import timedelta

import altair as alt
import pandas as pd
import streamlit as st

import analytics as an
import views
from database import money
from modern_ui import (
    ACCENT,
    ACCENT_2,
    NEGATIVE,
    POSITIVE,
    WARNING,
    chart,
    hero,
    insight_panel,
    metrics,
    progress_card,
    rows,
    rupees,
    section_header,
)


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
        .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7, opacity=.94)
        .encode(
            x=alt.X("month:N", title=None, axis=alt.Axis(labelAngle=0, domain=False, ticks=False, labelColor="#697176")),
            xOffset="Flow:N",
            y=alt.Y("Amount:Q", title=None, axis=alt.Axis(format="~s", domain=False, ticks=False, gridColor="#D8D7D1", labelColor="#697176")),
            color=alt.Color(
                "Flow:N",
                scale=alt.Scale(domain=["income", "expenses"], range=[POSITIVE, NEGATIVE]),
                legend=alt.Legend(orient="bottom", title=None, labelColor="#697176", padding=12),
            ),
            tooltip=[alt.Tooltip("month:N", title="Month"), alt.Tooltip("Flow:N"), alt.Tooltip("Amount:Q", format=",.0f")],
        )
        .properties(height=330)
        .configure_view(stroke=None)
    )
    st.altair_chart(flow, width="stretch", alt="Income and expenses over recent months")


def overview_page():
    """Landing-page rhythm plus finance-dashboard density, using existing data."""
    month = _month()
    store = _store()
    o = an.overview(store, month)
    period = pd.Period(month).strftime("%B %Y")
    sub = an.subscription_summary(store)

    with st.container(key="overview-hero-stage"):
        intro, brief = st.columns([1.42, .58], gap="large", vertical_alignment="bottom")
        with intro:
            hero(
                "Know where your money goes. Decide where it goes next.",
                "One financial workspace for position, movement, pressure and what is coming up next.",
                f"{period.upper()} / OVERVIEW",
            )
        with brief:
            st.caption("THIS MONTH")
            st.metric("Net movement", rupees(o["net"]), help="Income minus expenses in the selected month.")
            insight_panel(o["pulse"], o["pulse_detail"])

    position, inflow, outflow = st.columns([1.55, .72, .72], gap="medium")
    with position:
        with st.container(border=True, key="overview-position-card"):
            st.caption("AVAILABLE CASH")
            st.metric(
                "Available cash",
                rupees(o["balance"]),
                label_visibility="collapsed",
                help="Current non-investment, non-card account balances through the selected report date.",
            )
            low_left, low_right = st.columns(2)
            low_left.metric("Net worth", rupees(o["net_worth"]), help="Assets minus negative balances and standalone debts.")
            low_right.metric("Savings rate", f'{o["savings_rate"]:.1f}%' if o["savings_rate"] is not None else "—")
    with inflow:
        with st.container(border=True, key="overview-income-card"):
            st.caption("MONEY IN")
            st.metric("Money in", rupees(o["income"]), label_visibility="collapsed")
            st.caption("Recorded income this report month.")
    with outflow:
        with st.container(border=True, key="overview-expense-card"):
            st.caption("MONEY OUT")
            st.metric("Money out", rupees(o["expenses"]), label_visibility="collapsed")
            st.caption("Recorded spending. Transfers excluded.")

    movement, pressure = st.columns([1.45, .75], gap="medium")
    with movement:
        with st.container(border=True, key="overview-cashflow-panel"):
            section_header("Cash flow", "Six recent months. Income and spending share one scale so the relationship is obvious.")
            _cash_flow_chart(an.monthly_summary(store).tail(6))
    with pressure:
        with st.container(border=True, key="overview-budget-panel"):
            section_header("Budget pressure", "How much of the monthly plan is still yours to use.")
            st.metric("Budget left", rupees(o["budget_remaining"]))
            st.metric("Monthly limit", rupees(o["budget_limit"]))
            st.metric("Subscriptions / month", rupees(sub["monthly_cost"]))

    category_col, activity_col = st.columns([.9, 1.1], gap="medium")
    with category_col:
        with st.container(border=True, key="overview-category-panel"):
            section_header("Where it went", "Selected-month spending by category.")
            chart(an.category_summary(store, month), "category:N", "amount:Q", color=NEGATIVE, height=300, title="Spending by category")
    with activity_col:
        with st.container(border=True, key="overview-activity-panel"):
            section_header("Latest activity", "The newest recorded movements in the current data view.")
            recent = an.transactions_frame(store)
            if recent.empty:
                st.info("Add your first transaction to see activity here.")
            else:
                rows(recent, limit=8)

    with st.container(border=True, key="overview-horizon-panel"):
        section_header("On the horizon", "Upcoming commitments around the selected report date.")
        upcoming = an.timeline(store, views.today() - timedelta(days=30), views.today() + timedelta(days=14))
        upcoming = upcoming.loc[upcoming.status.ne("Recorded")]
        if upcoming.empty:
            st.caption("No upcoming recorded commitments.")
        else:
            horizon_cols = st.columns(min(4, len(upcoming.head(4))), gap="medium")
            for column, item in zip(horizon_cols, upcoming.head(4).to_dict("records")):
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
    """Admin-style ledger workspace while keeping the original transaction workflows."""
    frame_all = an.transactions_frame(_store(), posted=False)
    month_income = float(frame_all.loc[frame_all.kind.eq("income"), "amount"].sum()) if not frame_all.empty else 0.0
    month_expense = float(frame_all.loc[frame_all.kind.eq("expense"), "amount"].sum()) if not frame_all.empty else 0.0

    with st.container(key="transactions-hero-stage"):
        intro, quick = st.columns([1.35, .65], gap="large", vertical_alignment="bottom")
        with intro:
            hero(
                "Every move, accounted for.",
                "Search the ledger, record a movement, or manage predictable recurring entries without losing the big picture.",
                "TRANSACTIONS",
            )
        with quick:
            st.caption("LEDGER SNAPSHOT")
            metrics([
                ("Income", rupees(month_income), "Visible ledger income."),
                ("Spending", rupees(month_expense), "Visible ledger expenses."),
            ])

    mode = st.segmented_control("View", ["History", "Add transaction", "Recurring"], default="History")
    if mode == "Add transaction":
        views.transaction_form()
        return
    if mode == "Recurring":
        views.recurring_page()
        return

    frame = frame_all
    search_col, filter_col = st.columns([1.55, .45], gap="medium", vertical_alignment="bottom")
    with search_col:
        search = st.text_input("Search transactions", placeholder="Merchant, note, category, tag or amount")
    with filter_col:
        order = st.selectbox("Sort", ["Newest", "Oldest", "Largest", "Smallest"])

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
        high = st.number_input("Maximum amount", min_value=0.0, value=max(100000.0, float(frame.amount.max()) if not frame.empty else 100000.0))

    frame = frame.loc[frame.date.between(pd.Timestamp(start), pd.Timestamp(end)) & frame.amount.between(low, high)]
    for field, values in [("category", cats), ("account_name", accts), ("kind", kinds), ("payment_method", methods)]:
        if values:
            frame = frame.loc[frame[field].isin(values)]
    if tag:
        frame = frame.loc[frame.tags.fillna("").str.contains(tag, case=False, regex=False)]

    frame = frame.sort_values("date" if order in {"Newest", "Oldest"} else "amount", ascending=order in {"Oldest", "Smallest"})
    visible_income = float(frame.loc[frame.kind.eq("income"), "amount"].sum()) if not frame.empty else 0.0
    visible_expense = float(frame.loc[frame.kind.eq("expense"), "amount"].sum()) if not frame.empty else 0.0

    ledger_col, summary_col = st.columns([1.5, .7], gap="medium")
    with ledger_col:
        with st.container(border=True, key="transactions-ledger-panel"):
            section_header("Ledger", "Future entries stay planned and do not affect current balances.")
            if frame.empty:
                st.info("No transactions match these filters.")
            else:
                rows(frame, limit=28)
                if len(frame) > 28:
                    st.caption(f"Showing 28 of {len(frame)} filtered transactions. Detailed ledger contains every row.")
    with summary_col:
        with st.container(border=True, key="transactions-summary-panel"):
            section_header("Selection", "Live totals for what you are looking at.")
            st.metric("Rows", str(len(frame)))
            st.metric("Income", rupees(visible_income))
            st.metric("Spending", rupees(visible_expense))

            if not frame.empty:
                labels = {
                    row.id: f'{row.date:%d %b} · {row.merchant or row.category} · {rupees(row.amount)}'
                    for row in frame.itertuples()
                }
                selected = st.selectbox(
                    "Select a transaction to edit",
                    [None] + list(labels),
                    format_func=lambda value: "Choose a transaction" if value is None else labels[value],
                )
                if selected:
                    views.transaction_form(_store().get("transactions", selected))

    with st.expander("Detailed ledger"):
        shown = frame[["date", "merchant", "kind", "category", "account_name", "amount", "tags"]].copy()
        shown["date"] = shown.date.dt.strftime("%d %b %Y")
        shown["amount"] = shown.amount.map(lambda value: rupees(value, True))
        views.table(shown)

    with st.expander("Monthly category and daily totals"):
        views.table(an.category_summary(_store(), _month()))
        views.table(an.daily_spending(_store(), _month()))


def budgets_page():
    """Budget planning presented as a responsive product story rather than repeated cards."""
    month = _month()
    store = _store()
    budget = an.budget_summary(store, month)
    overview = an.overview(store, month)

    with st.container(key="budgets-hero-stage"):
        intro, headline = st.columns([1.3, .7], gap="large", vertical_alignment="bottom")
        with intro:
            hero(
                "Give every rupee a little room.",
                "See how the plan is holding up, then test a purchase before it becomes a transaction.",
                f"BUDGETS / {month}",
            )
        with headline:
            st.caption("MONTHLY ROOM")
            st.metric("Remaining", rupees(overview["budget_remaining"]), label_visibility="collapsed")
            st.caption("What remains after recorded spending.")

    summary_col, planner_col = st.columns([1.2, .8], gap="medium")
    with summary_col:
        with st.container(border=True, key="budgets-summary-panel"):
            section_header("Budget position", "The total plan and the amount already consumed.")
            a, b = st.columns(2)
            a.metric("Monthly limit", rupees(overview["budget_limit"]))
            b.metric("Spent", rupees(overview["expenses"]))
            st.metric("Remaining", rupees(overview["budget_remaining"]))
    with planner_col:
        with st.container(border=True, key="budgets-planner-panel"):
            section_header("Can it fit?", "Test a purchase against the remaining monthly budget.")
            spend = st.number_input("Planned purchase (₹)", min_value=0.0, value=1000.0, step=100.0)
            st.metric("Left after purchase", rupees(overview["budget_remaining"] - spend))
            st.caption("Arithmetic against your plan, not lending or investment advice.")

    with st.container(border=True, key="budgets-category-panel"):
        section_header("Category pressure", "Scan the categories that are consuming the plan fastest.")
        if budget.empty:
            st.info("Create a category budget to see utilization here.")
        else:
            budget_columns = st.columns(2, gap="large")
            for index, item in enumerate(budget.to_dict("records")):
                with budget_columns[index % 2]:
                    progress_card(
                        item["category"],
                        item["spent"],
                        item["limit"],
                        f'{rupees(item["remaining"])} remaining · {item["used_pct"]:.0f}% used · {item["status"]}',
                    )
        st.caption("Healthy ≤60% · Watch >60–85% · Near limit >85–100% · Over budget >100%.")

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
