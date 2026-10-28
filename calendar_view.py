"""Stable calendar controls for historical timeline browsing."""
from datetime import date, timedelta

import streamlit as st

import analytics as an
from database import today as actual_today
from ui import hero, rupees


REPORT_START = date(2002, 12, 2)


def _report_date():
    value = st.session_state.get("report_date")
    return value if isinstance(value, date) else actual_today()


def _ensure_calendar_state():
    center = _report_date()
    start = st.session_state.get("calendar_timeline_from")
    end = st.session_state.get("calendar_timeline_through")
    if not isinstance(start, date):
        st.session_state.calendar_timeline_from = center - timedelta(days=7)
    if not isinstance(end, date):
        st.session_state.calendar_timeline_through = center + timedelta(days=45)


def calendar_page():
    hero(
        "Know what's coming.",
        "A timeline of money commitments, planned entries and savings milestones.",
        "FINANCIAL CALENDAR",
    )
    _ensure_calendar_state()
    left, right = st.columns(2)
    start = left.date_input(
        "Timeline from",
        key="calendar_timeline_from",
        format="DD/MM/YYYY",
        help="Choose the first day of the timeline. The selection applies immediately.",
    )
    end = right.date_input(
        "Timeline through",
        key="calendar_timeline_through",
        format="DD/MM/YYYY",
        help="Choose the last day of the timeline. The selection applies immediately.",
    )
    if end < start:
        st.error("Timeline through must be on or after Timeline from.")
        return

    events = an.timeline(st.session_state.store, start, end)
    if events.empty:
        st.info("No recorded events in this window.")
    else:
        for on, group in events.groupby("date", sort=True):
            display_date = date.fromisoformat(str(on)[:10])
            st.subheader(display_date.strftime("%d %b · %A"))
            for row in group.to_dict("records"):
                with st.container(border=True):
                    st.write(f'**{row["name"]}** · {rupees(row["amount"])}')
                    st.caption(f'{row["kind"]} · {row["status"]}')
    st.caption(
        "Shows the next occurrence of each recurring commitment, not every future repetition. "
        "Goal target amounts are milestones, not scheduled charges."
    )
