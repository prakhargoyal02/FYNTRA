"""Template-driven presentation helpers for FYNTRA.

This module changes presentation only. Finance calculations, persistence and business
rules remain in the existing analytics/database modules.
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

# Real-world product palette. Blue anchors the interface; green/red/ochre keep their
# financial meanings instead of becoming decorative brand colors.
ACCENT = "#2F6B8A"
ACCENT_2 = "#527C9D"
POSITIVE = "#327A5F"
NEGATIVE = "#C96C5A"
WARNING = "#B8873D"
INK = "#1A1E22"
MUTED = "#6D7478"
GRID = "#D8D7D1"


def chart(data, x, y, kind="bar", color=ACCENT, height=280, title=None):
    """Render Altair with the template-inspired FYNTRA finance theme."""
    if data.empty:
        st.caption("Your chart appears when you add records.")
        return
    base = alt.Chart(data)
    if kind == "line":
        visual = base.mark_line(
            color=color,
            strokeWidth=3,
            point=alt.OverlayMarkDef(size=44, filled=True, strokeWidth=0),
            interpolate="monotone",
        )
    elif kind == "area":
        visual = base.mark_area(
            color=color,
            opacity=.13,
            line={"color": color, "strokeWidth": 3},
            interpolate="monotone",
        )
    else:
        visual = base.mark_bar(color=color, cornerRadiusTopLeft=7, cornerRadiusTopRight=7, opacity=.92)
    visual = visual.encode(
        x=alt.X(x, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title=None, axis=alt.Axis(format="~s")),
        tooltip=[x, alt.Tooltip(y, format=",.0f")],
    ).properties(height=height)
    visual = visual.configure_view(stroke=None).configure_axis(
        domain=False,
        ticks=False,
        gridColor=GRID,
        gridOpacity=.7,
        labelColor=MUTED,
        titleColor=MUTED,
        labelFont="Host Grotesk",
        titleFont="Host Grotesk",
        labelFontSize=11,
        titleFontSize=11,
        titleFontWeight=500,
        labelPadding=8,
    ).configure_legend(
        labelColor=MUTED,
        titleColor=MUTED,
        labelFont="Host Grotesk",
        titleFont="Host Grotesk",
        orient="bottom",
        padding=8,
        symbolType="circle",
    )
    st.altair_chart(visual, width="stretch", alt=title or "Financial data from your recorded ledger")
