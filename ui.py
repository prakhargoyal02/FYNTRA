"""FYNTRA presentation primitives and the shared visual system.

Business rules stay in database.py and analytics.py. This module owns typography,
spacing, chart presentation and reusable interface pieces only.
"""
from html import escape
from pathlib import Path
import math
import altair as alt
import streamlit as st

ACCENT = "#8CF0CB"
POSITIVE = "#69D8A0"
NEGATIVE = "#F08C83"
WARNING = "#E2B66B"
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
    """Install FYNTRA's dark editorial design system without changing app logic."""
    st.html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

        :root {
            --f-bg: #080B0A;
            --f-bg-soft: #0C100F;
            --f-surface: #101413;
            --f-surface-2: #141918;
            --f-surface-3: #19201E;
            --f-line: #222B28;
            --f-line-strong: #31403B;
            --f-text: #F2F4EF;
            --f-muted: #8F9B96;
            --f-muted-2: #66716D;
            --f-accent: #8CF0CB;
            --f-accent-soft: rgba(140,240,203,.10);
            --f-positive: #69D8A0;
            --f-negative: #F08C83;
            --f-warning: #E2B66B;
            --f-shadow: 0 24px 70px rgba(0,0,0,.28);
            --f-ease: cubic-bezier(.2,.75,.25,1);
        }

        html { scroll-behavior: smooth; }
        body, .stApp, [data-testid="stAppViewContainer"] {
            font-family: "Manrope", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            color: var(--f-text);
        }
        .stApp {
            background:
                radial-gradient(850px 480px at 78% -8%, rgba(70,151,123,.13), transparent 64%),
                radial-gradient(680px 420px at 12% 28%, rgba(140,240,203,.035), transparent 66%),
                linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px),
                var(--f-bg);
            background-size: auto, auto, 54px 54px, 54px 54px, auto;
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1320px;
            padding: 2.4rem 3.4rem 5.5rem;
        }
        [data-testid="stHeader"] { background: rgba(8,11,10,.72); backdrop-filter: blur(14px); }
        h1, h2, h3, h4, p { text-wrap: pretty; }
        h1, h2, h3 { letter-spacing: -.035em; }
        h2 { font-weight: 650; }
        h3 { font-weight: 620; }
        a { color: var(--f-accent); }
        code, pre, .f-mono { font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace; }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(140,240,203,.035), transparent 24%), #0A0D0C;
            border-right: 1px solid var(--f-line) !important;
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }
        [data-testid="stSidebar"] [data-testid="stImage"] { margin-bottom: .45rem; }
        [data-testid="stSidebar"] .stRadio > label { display: none; }
        [data-testid="stSidebar"] [role="radiogroup"] { gap: .24rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: .66rem .72rem;
            border: 1px solid transparent;
            border-radius: 11px;
            color: #98A39F;
            transition: color .18s ease, background .18s ease, border-color .18s ease, transform .18s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            color: var(--f-text);
            background: rgba(255,255,255,.025);
            transform: translateX(2px);
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            color: var(--f-text);
            background: linear-gradient(90deg, rgba(140,240,203,.105), rgba(140,240,203,.025));
            border-color: rgba(140,240,203,.16);
            box-shadow: inset 2px 0 0 var(--f-accent);
        }
        [data-testid="stSidebar"] [role="radiogroup"] [data-testid="stMarkdownContainer"] p {
            font-size: .87rem;
            font-weight: 600;
            letter-spacing: -.01em;
        }
        [data-testid="stSidebar"] hr { border-color: var(--f-line); }
        .f-side-status {
            margin: .5rem 0 .9rem;
            padding: .55rem .7rem;
            border: 1px solid var(--f-line);
            border-radius: 10px;
            color: var(--f-muted);
            background: rgba(255,255,255,.018);
            font-size: .68rem;
            letter-spacing: .12em;
            text-transform: uppercase;
        }
        .f-side-status strong { color: var(--f-accent); font-weight: 700; }

        .f-hero {
            position: relative;
            padding: .65rem 0 2.2rem;
            margin-bottom: .5rem;
            overflow: hidden;
            isolation: isolate;
            animation: f-rise .72s var(--f-ease) both;
        }
        .f-hero::before {
            content: "";
            position: absolute;
            width: 260px;
            height: 260px;
            right: 3%;
            top: -138px;
            border: 1px solid rgba(140,240,203,.10);
            border-radius: 50%;
            box-shadow: 0 0 90px rgba(140,240,203,.045);
            pointer-events: none;
        }
        .f-kicker {
            display: flex;
            align-items: center;
            gap: .65rem;
            margin-bottom: 1rem;
            color: #82908A;
            font-family: "DM Mono", ui-monospace, monospace;
            font-size: .66rem;
            letter-spacing: .13em;
            text-transform: uppercase;
        }
        .f-kicker::before { content:""; width: 28px; height: 1px; background: var(--f-accent); opacity: .75; }
        .f-hero h1 {
            margin: 0;
            max-width: 880px;
            font-size: clamp(2.45rem, 5.2vw, 5.2rem);
            line-height: .98;
            font-weight: 620;
            letter-spacing: -.065em;
            color: var(--f-text);
        }
        .f-hero p {
            margin: 1.1rem 0 0;
            max-width: 680px;
            color: #98A39F;
            font-size: clamp(.94rem, 1.3vw, 1.08rem);
            line-height: 1.65;
        }
        .f-hero-rule {
            width: 100%;
            height: 1px;
            margin-top: 1.8rem;
            background: linear-gradient(90deg, var(--f-line-strong), var(--f-line) 56%, transparent);
            transform-origin: left;
            animation: f-rule .9s .12s var(--f-ease) both;
        }

        [data-testid="stMetric"] {
            background: transparent !important;
            border: 0 !important;
            border-top: 1px solid var(--f-line) !important;
            border-radius: 0 !important;
            padding: .9rem .15rem 1rem !important;
            box-shadow: none !important;
            min-height: 104px;
            animation: f-rise .55s var(--f-ease) both;
        }
        [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stMetric"] { border-top-color: rgba(140,240,203,.56) !important; }
        [data-testid="stMetricLabel"] p {
            color: var(--f-muted) !important;
            font-family: "DM Mono", ui-monospace, monospace !important;
            font-size: .67rem !important;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: var(--f-text) !important;
            font-size: clamp(1.55rem, 2.4vw, 2.55rem) !important;
            font-weight: 590 !important;
            letter-spacing: -.055em !important;
            font-variant-numeric: tabular-nums;
        }
        [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stMetricValue"] { font-size: clamp(2rem, 3.15vw, 3.45rem) !important; }
        [data-testid="stMetricDelta"] { font-size: .78rem; }
        .st-key-fyntra-overview-balance [data-testid="stMetric"] {
            border-top-color: rgba(140,240,203,.58) !important;
            padding-top: 1.15rem !important;
            min-height: 150px;
        }
        .st-key-fyntra-overview-balance [data-testid="stMetricValue"] {
            font-size: clamp(3.6rem, 7vw, 7.2rem) !important;
            line-height: .9 !important;
            letter-spacing: -.075em !important;
        }

        .f-balance-stage {
            display: grid;
            grid-template-columns: minmax(0,1.45fr) minmax(240px,.55fr);
            gap: 2rem;
            align-items: end;
            padding: .2rem 0 2.4rem;
            border-bottom: 1px solid var(--f-line);
            margin-bottom: 1.2rem;
            animation: f-rise .72s .05s var(--f-ease) both;
        }
        .f-balance-label { color: var(--f-muted); font-family: "DM Mono", ui-monospace, monospace; font-size: .69rem; letter-spacing: .11em; text-transform: uppercase; margin-bottom: .4rem; }
        .f-balance-value { font-size: clamp(3.55rem, 8vw, 7.8rem); line-height: .9; letter-spacing: -.075em; font-weight: 610; font-variant-numeric: tabular-nums; }
        .f-balance-copy { color: #9DA8A3; font-size: .88rem; line-height: 1.65; max-width: 320px; padding-bottom: .25rem; }
        .f-balance-copy strong { color: var(--f-accent); font-weight: 650; }

        .f-section-head { display:flex; align-items:end; justify-content:space-between; gap:1rem; margin:2.1rem 0 .85rem; }
        .f-section-head h3 { margin:0; font-size:clamp(1.25rem,2vw,1.75rem); }
        .f-section-head p { margin:0; color:var(--f-muted); font-size:.82rem; max-width:440px; }
        .f-row { display:grid; grid-template-columns:1fr auto; align-items:center; gap:1.25rem; padding:.88rem .15rem; border-bottom:1px solid rgba(255,255,255,.055); transition:background .2s ease,padding .2s ease,transform .2s ease; }
        .f-row:hover { background:rgba(255,255,255,.018); padding-left:.55rem; padding-right:.55rem; transform:translateX(2px); }
        .f-row strong { font-size:.9rem; font-weight:630; overflow-wrap:anywhere; }
        .f-row small { display:block; color:#78847F; font-size:.72rem; margin-top:.28rem; }
        .f-amount { font-variant-numeric:tabular-nums; font-weight:650; white-space:nowrap; letter-spacing:-.025em; }
        .f-positive { color:var(--f-positive); }
        .f-negative { color:#E9B4AE; }
        .f-neutral { color:var(--f-text); }

        .f-progress-card { padding:1.05rem 0 1.15rem; border-bottom:1px solid var(--f-line); }
        .f-progress-top { display:flex; justify-content:space-between; gap:1rem; align-items:baseline; }
        .f-progress-name { font-size:.94rem; font-weight:650; }
        .f-progress-value { font-size:1.05rem; font-weight:650; font-variant-numeric:tabular-nums; }
        .f-progress-track { height:5px; background:#1B2320; overflow:hidden; border-radius:999px; margin:.75rem 0 .55rem; }
        .f-progress-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#51B990,var(--f-accent)); transform-origin:left; animation:f-fill .8s var(--f-ease) both; }
        .f-progress-caption { color:var(--f-muted); font-size:.72rem; }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: linear-gradient(180deg, rgba(255,255,255,.018), rgba(255,255,255,.008));
            border-color: var(--f-line) !important;
            border-radius: 17px !important;
            box-shadow: 0 16px 38px rgba(0,0,0,.13);
            transition: border-color .2s ease, transform .2s ease, box-shadow .2s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover { border-color:#2E3A36 !important; }
        [data-testid="stForm"] { background:#0E1211; border:1px solid var(--f-line); border-radius:18px; padding:1.15rem 1.15rem .45rem; }
        [data-testid="stExpander"] { border:1px solid var(--f-line) !important; border-radius:14px !important; background:#0D1110; overflow:hidden; }
        [data-testid="stExpander"] details summary { padding-top:.15rem; padding-bottom:.15rem; }

        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
            border-radius:11px !important;
            border:1px solid #2B3733 !important;
            background:#121715 !important;
            color:var(--f-text) !important;
            min-height:2.65rem;
            font-weight:650;
            letter-spacing:-.01em;
            transition:transform .18s var(--f-ease),border-color .18s ease,background .18s ease,box-shadow .18s ease;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] button:hover { transform:translateY(-1px); border-color:rgba(140,240,203,.42) !important; background:#17201D !important; box-shadow:0 10px 26px rgba(0,0,0,.22); }
        .stButton > button:active, .stDownloadButton > button:active { transform:translateY(0) scale(.985); }
        button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] { background:var(--f-accent) !important; border-color:var(--f-accent) !important; color:#07110D !important; box-shadow:0 9px 28px rgba(140,240,203,.10); }
        button[kind="primary"]:hover { background:#A1F5D6 !important; border-color:#A1F5D6 !important; }
        input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div { border-radius:10px !important; }
        [data-baseweb="input"] > div, [data-baseweb="select"] > div, textarea { background-color:#0D1110 !important; border-color:var(--f-line) !important; transition:border-color .18s ease,box-shadow .18s ease; }
        [data-baseweb="input"] > div:focus-within, [data-baseweb="select"] > div:focus-within, textarea:focus { border-color:rgba(140,240,203,.52) !important; box-shadow:0 0 0 3px rgba(140,240,203,.07) !important; }
        [data-testid="stSegmentedControl"] { background:#0D1110; border:1px solid var(--f-line); border-radius:12px; padding:3px; }
        [data-testid="stSegmentedControl"] button { border-radius:9px !important; }
        [data-testid="stFileUploader"] section { background:#0D1110; border-color:#2A3531; border-radius:15px; }
        [data-testid="stDateInput"] button, [data-testid="stTimeInput"] button { color:var(--f-muted); }

        [data-testid="stDataFrame"] { border:1px solid var(--f-line); border-radius:14px; overflow:hidden; box-shadow:0 12px 32px rgba(0,0,0,.10); animation:f-rise .5s var(--f-ease) both; }
        [data-testid="stDataFrame"] canvas { border-radius:14px; }
        [data-testid="stProgressBar"] > div > div { background:linear-gradient(90deg,#4EAE88,var(--f-accent)) !important; }
        [data-testid="stAlert"] { border-radius:13px; border:1px solid var(--f-line); }
        [data-testid="stAltairChart"] { background:linear-gradient(180deg,rgba(255,255,255,.012),transparent); border-top:1px solid rgba(255,255,255,.04); padding-top:.45rem; animation:f-rise .62s var(--f-ease) both; }
        [data-testid="stSpinner"] { color:var(--f-accent); }
        [data-testid="stToast"] { border:1px solid var(--f-line); background:#111615; }

        .f-pill { display:inline-flex; align-items:center; border:1px solid var(--f-line-strong); border-radius:999px; padding:.34rem .58rem; color:#A4B0AB; background:#101514; font-size:.67rem; }
        .f-foot { font-size:.7rem; color:#66716D; margin-top:1.6rem; line-height:1.7; }
        .f-insight { padding:1rem 0 1rem 1rem; border-left:1px solid rgba(140,240,203,.48); }
        .f-insight strong { display:block; font-size:1.15rem; margin-bottom:.25rem; }
        .f-insight span { color:var(--f-muted); font-size:.82rem; line-height:1.55; }
        ::selection { background:rgba(140,240,203,.24); color:var(--f-text); }
        ::-webkit-scrollbar { width:10px; height:10px; }
        ::-webkit-scrollbar-track { background:#090C0B; }
        ::-webkit-scrollbar-thumb { background:#28332F; border-radius:999px; border:2px solid #090C0B; }

        @keyframes f-rise { from { opacity:0; transform:translateY(11px); } to { opacity:1; transform:translateY(0); } }
        @keyframes f-rule { from { transform:scaleX(0); opacity:0; } to { transform:scaleX(1); opacity:1; } }
        @keyframes f-fill { from { transform:scaleX(0); } to { transform:scaleX(1); } }

        @supports (animation-timeline: view()) {
            [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stDataFrame"], [data-testid="stAltairChart"] {
                animation:f-rise linear both;
                animation-timeline:view();
                animation-range:entry 5% cover 24%;
            }
        }

        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] { padding:1.7rem 1.35rem 4rem; }
            .f-balance-stage { grid-template-columns:1fr; gap:1rem; }
            .f-balance-copy { max-width:620px; }
            .f-section-head { align-items:flex-start; flex-direction:column; }
        }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] { padding:1.15rem .9rem 3.5rem; }
            .f-hero { padding-top:.25rem; padding-bottom:1.45rem; }
            .f-hero h1 { font-size:clamp(2.2rem,12vw,3.45rem); }
            .f-balance-value { font-size:clamp(3rem,17vw,5rem); }
            .f-row { gap:.7rem; }
            [data-testid="stMetricValue"] { font-size:1.6rem !important; }
            [data-testid="stHorizontalBlock"] > div:first-child [data-testid="stMetricValue"] { font-size:2rem !important; }
            .st-key-fyntra-overview-balance [data-testid="stMetricValue"] { font-size:clamp(3rem,16vw,4.8rem) !important; }
        }
        @media (prefers-reduced-motion: reduce) {
            html { scroll-behavior:auto; }
            *, *::before, *::after { animation:none !important; transition:none !important; }
        }
        </style>
        """
    )


def brand():
    st.image(str(Path(__file__).parent / "assets" / "wordmark.svg"), width=176)


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
    """Render native metrics in an intentionally uneven editorial rail."""
    if not items:
        return
    weights = [1.38] + [1.0] * (len(items) - 1)
    for column, (label, value, help_text) in zip(st.columns(weights, gap="medium"), items):
        column.metric(label, value, border=False, help=help_text)


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
            f'<div class="f-row"><div><strong>{escape(str(label))}</strong>'
            f'<small>{escape(subtitle)}</small></div>'
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
