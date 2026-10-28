"""Reusable presentation helpers for FYNTRA.

This file contains visual helpers only.
Finance rules stay in database.py and analytics.py so the project remains
beginner-readable and easy to explain.
"""

from html import escape
import math

import altair as alt
import streamlit as st


MINT = "#68E8B6"
GOLD = "#DCC58B"


def rupees(value, decimals=False):
    """Format money using Indian number grouping."""
    if value is None:
        return "—"

    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    if not math.isfinite(number):
        return "—"

    negative = number < 0
    text = f"{abs(number):.2f}"
    whole, fraction = text.split(".")

    if len(whole) > 3:
        end = whole[-3:]
        head = whole[:-3]
        groups = []
        while head:
            groups.insert(0, head[-2:])
            head = head[:-2]
        whole = ",".join(groups + [end])

    sign = "−" if negative else ""
    return sign + "₹" + whole + ("." + fraction if decimals else "")


def style():
    """Apply the shared FYNTRA visual language."""
    st.html(
        """
        <style>
        :root {
            --fyntra-mint: #68E8B6;
            --fyntra-gold: #DCC58B;
            --fyntra-ink: #F4F1E8;
            --fyntra-muted: #9CB4A8;
            --fyntra-panel: #14231E;
            --fyntra-panel-2: #18372A;
            --fyntra-line: #2D4B3E;
        }

        .fyntra-brand {
            display:flex;
            align-items:center;
            gap:10px;
            font-size:22px;
            font-weight:800;
            letter-spacing:.13em;
            color:var(--fyntra-ink);
            margin-bottom:4px;
        }

        .fyntra-mark {
            width:28px;
            height:28px;
            border-radius:9px;
            background:
                linear-gradient(135deg, rgba(104,232,182,.95), rgba(104,232,182,.22)),
                #16372a;
            border:1px solid rgba(104,232,182,.45);
            box-shadow:0 0 28px rgba(104,232,182,.14);
            position:relative;
        }

        .fyntra-mark::after {
            content:"";
            position:absolute;
            inset:7px;
            border:1px solid rgba(244,241,232,.7);
            border-radius:50% 50% 42% 58%;
            transform:rotate(-24deg);
        }

        .f-kicker {
            color:#86AA9B;
            font-size:11px;
            letter-spacing:.18em;
            text-transform:uppercase;
            margin-bottom:10px;
        }

        .f-hero {
            border:1px solid #355C4C;
            border-radius:22px;
            padding:27px 29px;
            background:
                radial-gradient(circle at 92% 5%, rgba(104,232,182,.10), transparent 30%),
                linear-gradient(115deg,#18372A,#14231E 72%);
            position:relative;
            overflow:hidden;
            margin-bottom:18px;
        }

        .f-hero::after {
            content:"";
            position:absolute;
            width:42%;
            height:230px;
            right:-7%;
            top:-35px;
            border:1px solid rgba(104,232,181,.18);
            transform:rotate(-28deg);
            border-radius:30%;
            pointer-events:none;
            animation:fyntra-flow 16s ease-in-out infinite;
        }

        .f-hero h2 {
            font-size:clamp(25px,3vw,40px);
            font-weight:560;
            margin:0 0 8px;
            letter-spacing:-.04em;
            max-width:760px;
        }

        .f-hero p {
            color:#B2C6BA;
            margin:0;
            font-size:14px;
            max-width:700px;
            line-height:1.65;
        }

        .f-row {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:18px;
            padding:13px 0;
            border-bottom:1px solid #26382F;
        }

        .f-row:last-child { border-bottom:0; }
        .f-row strong { font-size:14px; overflow-wrap:anywhere; }
        .f-row small {
            display:block;
            color:#8EAA9B;
            font-size:11px;
            margin-top:4px;
        }

        .f-amount {
            font-variant-numeric:tabular-nums;
            font-weight:650;
            white-space:nowrap;
        }

        .f-positive { color:#80DCB0; }
        .f-negative { color:#EED4A9; }

        [data-testid="stMetric"] {
            background:linear-gradient(180deg, rgba(31,55,45,.55), rgba(17,32,26,.25));
            border:1px solid rgba(73,112,94,.45);
            padding:14px 15px;
            border-radius:16px;
        }

        [data-testid="stMetricValue"] {
            font-variant-numeric:tabular-nums;
            letter-spacing:-.03em;
        }

        section[data-testid="stSidebar"] {
            border-right:1px solid rgba(66,98,84,.35);
        }

        @keyframes fyntra-flow {
            50% { transform:rotate(-23deg) translateX(-12px); }
        }

        @media(prefers-reduced-motion:reduce) {
            .f-hero::after { animation:none; }
        }

        @media(max-width:640px) {
            .f-hero { padding:21px; }
            .f-row { gap:10px; }
            .f-amount { font-size:14px; }
        }
        </style>
        """
    )


def brand():
    """Render a compact text-based FYNTRA brand mark."""
    st.html(
        '<div class="fyntra-brand"><span class="fyntra-mark"></span>'
        '<span>FYNTRA</span></div>'
    )


def hero(title, subtitle, kicker="YOUR MONEY, WITH CLARITY"):
    """Large reusable page heading."""
    st.html(
        f'<section class="f-hero">'
        f'<div class="f-kicker">{escape(str(kicker))}</div>'
        f'<h2>{escape(str(title))}</h2>'
        f'<p>{escape(str(subtitle))}</p>'
        f'</section>'
    )


def metrics(items):
    """Render metric cards in rows of at most four."""
    for offset in range(0, len(items), 4):
        batch = items[offset : offset + 4]
        columns = st.columns(len(batch))
        for column, (label, value, help_text) in zip(columns, batch):
            column.metric(label, value, border=True, help=help_text)


def rows(frame, limit=8):
    """Render recent transactions as compact activity rows."""
    if frame.empty:
        st.caption("No activity yet.")
        return

    for record in frame.head(limit).to_dict("records"):
        kind = str(record.get("kind", "expense"))
        label = (
            record.get("merchant")
            or record.get("name")
            or record.get("category")
            or "Transaction"
        )
        on = str(record.get("transaction_date", record.get("date", "")))[:10]
        subtitle = f'{record.get("category", kind)} · {on}'
        amount = rupees(record.get("amount", 0), decimals=True)
        sign = "+" if kind == "income" else ("↔ " if kind == "transfer" else "−")
        css = "f-positive" if kind == "income" else "f-negative"

        st.html(
            f'<div class="f-row">'
            f'<div><strong>{escape(str(label))}</strong>'
            f'<small>{escape(subtitle)}</small></div>'
            f'<span class="f-amount {css}">{sign}{escape(amount)}</span>'
            f'</div>'
        )


def progress_card(name, value, target, caption=""):
    """Reusable savings/debt progress card."""
    target = float(target)
    value = float(value)
    progress = 0 if target <= 0 else min(1, max(0, value / target))

    with st.container(border=True):
        st.markdown("**" + str(name).replace("*", "") + "**")
        st.metric("Progress", rupees(value), label_visibility="collapsed")
        st.progress(progress)
        st.caption(f"{progress * 100:.0f}% of {rupees(target)} · {caption}")


def cash_flow_chart(data):
    """Build the branded monthly income/expense chart."""
    if data.empty:
        return None

    plot = data.melt(
        "month",
        ["income", "expenses"],
        var_name="Flow",
        value_name="Amount",
    )

    return (
        alt.Chart(plot)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("month:N", title=None),
            xOffset="Flow:N",
            y=alt.Y("Amount:Q", title="₹"),
            color=alt.Color(
                "Flow:N",
                scale=alt.Scale(
                    domain=["income", "expenses"],
                    range=[MINT, GOLD],
                ),
                legend=alt.Legend(orient="bottom"),
            ),
            tooltip=["month", "Flow", "Amount"],
        )
        .properties(height=275)
    )
