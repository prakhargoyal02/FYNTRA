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
    period = pd.Period(month()).strftime("%B %Y")

    hero(
        "Your money, without the noise.",
        "A single view of what changed, what remains, and what deserves your attention next.",
        f"{period.upper()} / OVERVIEW",
    )

    balance_col, pulse_col = st.columns([1.6, .72], gap="large", vertical_alignment="bottom")
    with balance_col:
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
