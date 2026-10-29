"""FYNTRA presentation primitives and the shared visual system.

Business rules stay in database.py and analytics.py. This module owns typography,
spacing, chart presentation and reusable interface pieces only.
"""
from html import escape
import base64
from pathlib import Path
import math
import altair as alt
import streamlit as st

ACCENT = "#B5F3CF"
POSITIVE = "#B5F3CF"
NEGATIVE = "#F4B4A5"
WARNING = "#E7C887"
INK = "#F2F4EF"
MUTED = "#8F9B96"
SURFACE = "#101413"
GRID = "#222B28"

# Backward-compatible names used by existing views.
MINT = POSITIVE
GOLD = WARNING


def rupees(value, decimals=False):
    if value is None or not math.isfinite(float(value)):
        return "—"
    negative = float(value) < 0
    text = f"{abs(float(value)):.2f}"
    whole, fraction = text.split(".")
    if len(whole) > 3:
        end, head = whole[-3:], whole[:-3]
        groups = []
        while head:
            groups.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(groups + [end])
    return ("−" if negative else "") + "₹" + whole + ("." + fraction if decimals else "")


def style():
    """A single local stylesheet, backed by native Streamlit theme tokens."""
    st.html(Path(__file__).parent / "assets" / "clarity.css")


def brand():
    mark = base64.b64encode((Path(__file__).parent / "assets" / "mark.svg").read_bytes()).decode("ascii")
    st.html(f'<div class="f-brand"><img src="data:image/svg+xml;base64,{mark}" width="34" height="34" alt=""><span>FYNTRA</span></div>')


def sidebar_status(mode):
    label = "Private cloud" if mode == "private" else "Fictional demo"
    qualifier = "Synced workspace" if mode == "private" else "Isolated session"
    st.html(f'<div class="f-side-status"><strong>{escape(label)}</strong><br>{escape(qualifier)}</div>')


def hero(title, subtitle, kicker="YOUR MONEY, WITH CLARITY"):
    st.html(
        f'<section class="f-hero">'
        f'<div class="f-kicker">{escape(kicker)}</div>'
        f'<h1>{escape(title)}</h1>'
        f'<p>{escape(subtitle)}</p>'
        f'<div class="f-hero-rule"></div>'
        f'</section>'
    )


def balance_stage(value, label="Available cash", copy="Liquid money across your recorded accounts."):
    st.html(
        f'<section class="f-balance-stage">'
        f'<div><div class="f-balance-label">{escape(label)}</div>'
        f'<div class="f-balance-value">{escape(value)}</div></div>'
        f'<div class="f-balance-copy"><strong>Current position.</strong><br>{escape(copy)}</div>'
        f'</section>'
    )


def section_header(title, copy=""):
    st.html(f'<div class="f-section-head"><h3>{escape(title)}</h3><p>{escape(copy)}</p></div>')


def insight_panel(title, copy):
    st.html(f'<div class="f-insight"><strong>{escape(str(title))}</strong><span>{escape(str(copy))}</span></div>')


def metrics(items):
    """Native metric cards retain accessible labels and responsive stacking."""
    if not items:
        return
    weights = [1.0] * len(items)
    for column, (label, value, help_text) in zip(st.columns(weights, gap="medium"), items):
        column.metric(label, value, border=True, help=help_text)


def rows(frame, limit=6):
    for r in frame.head(limit).to_dict("records"):
        kind = r.get("kind", "expense")
        label = r.get("merchant") or r.get("name") or r.get("category", "Transaction")
        on = str(r.get("date", ""))[:10]
        subtitle = f"{r.get('category', kind)} · {on}"
        amount = rupees(r.get("amount", 0))
        sign = "+" if kind == "income" else ("↔ " if kind == "transfer" else "−")
        css = "f-positive" if kind == "income" else ("f-neutral" if kind == "transfer" else "f-negative")
        st.html(
            f'<div class="f-row"><div class="f-row-copy"><span class="f-avatar" aria-hidden="true">{escape(str(label)[:2].upper())}</span><div><strong>{escape(str(label))}</strong>'
            f'<small>{escape(subtitle)}</small></div></div>'
            f'<span class="f-amount {css}">{sign}{escape(amount)}</span></div>'
        )


def _chart_base(c):
    return c.configure_view(stroke=None).configure_axis(
        domain=False,
        tickColor="#2A3431",
        gridColor="#1E2724",
        gridOpacity=.65,
        labelColor="#85918C",
        titleColor="#85918C",
        labelFont="Manrope",
        titleFont="Manrope",
        labelFontSize=11,
        titleFontSize=11,
        titleFontWeight=500,
    ).configure_legend(
        labelColor="#929E99",
        titleColor="#929E99",
        labelFont="Manrope",
        titleFont="Manrope",
        orient="bottom",
        padding=8,
    )


def chart(data, x, y, kind="bar", color=ACCENT, height=280, title=None):
    if data.empty:
        st.caption("Your chart appears when you add records.")
        return
    c = alt.Chart(data)
    if kind == "line":
        c = c.mark_line(color=color, strokeWidth=2.6, point=alt.OverlayMarkDef(size=42, filled=True), interpolate="monotone")
    elif kind == "area":
        c = c.mark_area(color=color, opacity=.12, line={"color": color, "strokeWidth": 2.3}, interpolate="monotone")
    else:
        c = c.mark_bar(color=color, cornerRadiusTopLeft=5, cornerRadiusTopRight=5, opacity=.9)
    c = c.encode(
        x=alt.X(x, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(y, title="₹", axis=alt.Axis(format="~s")),
        tooltip=[x, y],
    ).properties(height=height)
    c = _chart_base(c)
    st.altair_chart(c, width="stretch", alt=title or "Financial data from your recorded ledger")


def progress_card(name, value, target, caption=""):
    pct = 0 if target <= 0 else min(1, max(0, value / target))
    st.html(
        f'<div class="f-progress-card">'
        f'<div class="f-progress-top"><span class="f-progress-name">{escape(str(name))}</span>'
        f'<span class="f-progress-value">{escape(rupees(value))}</span></div>'
        f'<div class="f-progress-track"><div class="f-progress-fill" style="width:{pct * 100:.2f}%"></div></div>'
        f'<div class="f-progress-caption">{pct * 100:.0f}% of {escape(rupees(target))} · {escape(str(caption))}</div>'
        f'</div>'
    )
