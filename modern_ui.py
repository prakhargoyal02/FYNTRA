"""Reference-driven presentation helpers for FYNTRA.

This module changes only visual presentation. Finance calculations, persistence and
business rules remain in the existing analytics/database modules.
"""
import altair as alt
import streamlit as st

from ui import (
    balance_stage,
    brand,
    hero,
    insight_panel,
    metrics,
    progress_card,
    rows,
    rupees,
    section_header,
    sidebar_status,
)

# Real-world product palette: blue is brand/interface, green/red are reserved for
# financial meaning, and ochre is reserved for warnings.
ACCENT = "#3F5FCA"
POSITIVE = "#2F7D5A"
NEGATIVE = "#C76555"
WARNING = "#B47A2D"
INK = "#1B2530"
MUTED = "#707772"
GRID = "#D9DAD5"


def chart(data, x, y, kind="bar", color=ACCENT, height=280, title=None):
    """Render Altair with a light editorial finance theme."""
    if data.empty:
        st.caption("Your chart appears when you add records.")
        return
    c = alt.Chart(data)
    if kind == "line":
        c = c.mark_line(
            color=color,
            strokeWidth=2.7,
            point=alt.OverlayMarkDef(size=38, filled=True),
            interpolate="monotone",
        )
    elif kind == "area":
        c = c.mark_area(
            color=color,
            opacity=.10,
            line={"color": color, "strokeWidth": 2.5},
            interpolate="monotone",
        )
    else:
        c = c.mark_bar(color=color, cornerRadiusTopLeft=5, cornerRadiusTopRight=5, opacity=.92)
    c = c.encode(
        x=alt.X(x, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title="₹", axis=alt.Axis(format="~s")),
        tooltip=[x, y],
    ).properties(height=height)
    c = c.configure_view(stroke=None).configure_axis(
        domain=False,
        tickColor="#C9CBC6",
        gridColor=GRID,
        gridOpacity=.7,
        labelColor="#69716E",
        titleColor="#69716E",
        labelFont="Instrument Sans",
        titleFont="Instrument Sans",
        labelFontSize=11,
        titleFontSize=11,
        titleFontWeight=500,
    ).configure_legend(
        labelColor="#69716E",
        titleColor="#69716E",
        labelFont="Instrument Sans",
        titleFont="Instrument Sans",
        orient="bottom",
        padding=8,
    )
    st.altair_chart(c, width="stretch", alt=title or "Financial data from your recorded ledger")
