"""Second-stage visual refinement inspired by modern design-engineered product sites.

This file only overrides presentation. It intentionally leaves FYNTRA's data model,
analytics, forms, routing, and finance rules untouched.
"""
import streamlit as st


def apply_taste_layer():
    st.html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Instrument+Sans:opsz,wght@12..32,400;12..32,500;12..32,600;12..32,700&display=swap');

        :root {
            --f-bg: #090A09;
            --f-bg-soft: #0D0F0E;
            --f-surface: #111412;
            --f-surface-2: #151917;
            --f-line: rgba(238,244,240,.085);
            --f-line-strong: rgba(238,244,240,.15);
            --f-text: #F1F3EE;
            --f-muted: #8D9691;
            --f-muted-2: #646D68;
            --f-accent: #88E8C1;
            --f-positive: #72D6A4;
            --f-negative: #E99188;
            --f-warning: #DDB66B;
            --f-radius: 12px;
            --f-ease: cubic-bezier(.22,.78,.22,1);
        }

        html { background: var(--f-bg); }
        body, .stApp, [data-testid="stAppViewContainer"] {
            font-family: "Instrument Sans", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }
        .stApp {
            background:
                radial-gradient(900px 520px at 73% -12%, rgba(136,232,193,.09), transparent 67%),
                radial-gradient(620px 420px at 8% 38%, rgba(136,232,193,.025), transparent 70%),
                #090A09 !important;
        }
        [data-testid="stAppViewContainer"]::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: .16;
            background-image: linear-gradient(rgba(255,255,255,.016) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.016) 1px, transparent 1px);
            background-size: 72px 72px;
            mask-image: linear-gradient(to bottom, black, transparent 78%);
        }
        [data-testid="stMainBlockContainer"] {
            max-width: 1450px !important;
            padding: 3.2rem 4.4rem 6rem !important;
        }
        [data-testid="stHeader"] {
            background: linear-gradient(to bottom, rgba(9,10,9,.92), rgba(9,10,9,.55), transparent) !important;
            backdrop-filter: blur(12px);
        }

        h1, h2, h3, h4, p, label { font-family: "Instrument Sans", ui-sans-serif, system-ui, sans-serif !important; }
        h1, h2, h3 { letter-spacing: -.045em !important; }
        h2 { font-size: clamp(1.7rem, 2.5vw, 2.65rem) !important; font-weight: 570 !important; }
        h3 { font-size: clamp(1.18rem, 1.7vw, 1.55rem) !important; font-weight: 570 !important; }
        code, pre, .f-mono, .f-kicker, [data-testid="stMetricLabel"] p {
            font-family: "DM Mono", ui-monospace, monospace !important;
        }

        /* Floating product rail. */
        [data-testid="stSidebar"] {
            background: transparent !important;
            border-right: 0 !important;
            padding: 12px 0 12px 12px;
        }
        [data-testid="stSidebar"] > div:first-child {
            background: linear-gradient(180deg, rgba(255,255,255,.018), transparent 25%), #0E100F;
            border: 1px solid var(--f-line) !important;
            border-radius: 18px;
            height: calc(100vh - 24px);
            box-shadow: 0 24px 70px rgba(0,0,0,.24);
            padding-top: 1.05rem !important;
            overflow-y: auto;
        }
        [data-testid="stSidebar"] [data-testid="stImage"] { margin-bottom: .65rem !important; }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #727C77 !important;
            font-size: .7rem !important;
            line-height: 1.55 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] { gap: .12rem !important; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            min-height: 2.55rem;
            padding: .62rem .78rem !important;
            border: 0 !important;
            border-radius: 9px !important;
            background: transparent !important;
            transform: none !important;
            color: #8D9691 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(255,255,255,.032) !important;
            color: #E9ECE7 !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: rgba(136,232,193,.085) !important;
            box-shadow: inset 0 0 0 1px rgba(136,232,193,.10) !important;
            color: #F0F3EE !important;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::after {
            content: "";
            width: 5px;
            height: 5px;
            border-radius: 50%;
            background: var(--f-accent);
            margin-left: auto;
            box-shadow: 0 0 18px rgba(136,232,193,.38);
        }
        [data-testid="stSidebar"] hr { border-color: var(--f-line) !important; margin: .8rem 0 !important; }
        .f-side-status {
            border: 0 !important;
            border-radius: 0 !important;
            background: transparent !important;
            padding: .25rem 0 .35rem !important;
            margin: .25rem 0 .8rem !important;
            letter-spacing: .08em !important;
        }

        /* Hero discipline: oversized type, compact viewport, no decorative card feeling. */
        .f-hero {
            min-height: 0 !important;
            padding: .55rem 0 2.7rem !important;
            margin: 0 0 .5rem !important;
            overflow: visible !important;
            animation: f-taste-rise .72s var(--f-ease) both !important;
        }
        .f-hero::before {
            width: 420px !important;
            height: 420px !important;
            right: -2% !important;
            top: -250px !important;
            border-color: rgba(136,232,193,.055) !important;
            box-shadow: 0 0 110px rgba(136,232,193,.025) !important;
        }
        .f-kicker {
            color: #76817C !important;
            font-size: .62rem !important;
            letter-spacing: .11em !important;
            margin-bottom: 1.05rem !important;
        }
        .f-kicker::before { width: 18px !important; opacity: .62 !important; }
        .f-hero h1 {
            max-width: 980px !important;
            font-size: clamp(3rem, 6vw, 6rem) !important;
            line-height: .92 !important;
            font-weight: 545 !important;
            letter-spacing: -.073em !important;
            text-wrap: balance !important;
        }
        .f-hero p {
            max-width: 620px !important;
            margin-top: 1.25rem !important;
            color: #929B96 !important;
            font-size: clamp(.95rem, 1.15vw, 1.06rem) !important;
            line-height: 1.58 !important;
        }
        .f-hero-rule {
            margin-top: 2rem !important;
            background: linear-gradient(90deg, rgba(136,232,193,.52), rgba(255,255,255,.075) 38%, transparent 88%) !important;
        }

        /* Financial values live in the layout, not generic cards. */
        [data-testid="stMetric"] {
            border-top: 1px solid var(--f-line) !important;
            padding: 1rem .05rem 1.3rem !important;
            min-height: 112px !important;
            background: transparent !important;
        }
        [data-testid="stMetricLabel"] p {
            font-size: .62rem !important;
            letter-spacing: .085em !important;
            color: #737D78 !important;
        }
        [data-testid="stMetricValue"] {
            font-size: clamp(1.7rem, 2.55vw, 2.85rem) !important;
            font-weight: 535 !important;
            letter-spacing: -.06em !important;
        }
        .st-key-fyntra-overview-balance [data-testid="stMetric"] {
            min-height: 190px !important;
            padding: 1.3rem 0 1.9rem !important;
            border-top-color: rgba(136,232,193,.5) !important;
        }
        .st-key-fyntra-overview-balance [data-testid="stMetricValue"] {
            font-size: clamp(4.4rem, 8.5vw, 9rem) !important;
            font-weight: 515 !important;
            line-height: .84 !important;
            letter-spacing: -.082em !important;
        }

        /* Open sections and asymmetric rhythm. */
        .f-section-head {
            margin: 3rem 0 1.05rem !important;
            padding-top: .45rem;
            border-top: 1px solid rgba(255,255,255,.045);
        }
        .f-section-head h3 { font-size: clamp(1.35rem, 2vw, 1.9rem) !important; font-weight: 550 !important; }
        .f-section-head p { color: #7F8984 !important; line-height: 1.55 !important; }
        .f-insight {
            border-left-color: rgba(136,232,193,.42) !important;
            padding: 1rem 0 1rem 1.25rem !important;
        }
        .f-insight strong { font-size: 1.28rem !important; font-weight: 550 !important; letter-spacing: -.025em; }

        .f-row {
            padding: 1rem .05rem !important;
            border-bottom-color: rgba(255,255,255,.05) !important;
        }
        .f-row:hover {
            background: transparent !important;
            padding-left: .45rem !important;
            padding-right: .45rem !important;
            transform: translateX(3px) !important;
        }
        .f-row strong { font-size: .95rem !important; font-weight: 560 !important; }
        .f-row small { color: #747E79 !important; }
        .f-amount { font-size: .94rem; font-weight: 580 !important; }

        .f-progress-card {
            padding: 1.2rem 0 1.35rem !important;
            border-bottom-color: rgba(255,255,255,.055) !important;
        }
        .f-progress-track { height: 4px !important; background: #1B1F1D !important; }
        .f-progress-fill { background: linear-gradient(90deg, #58B68E, var(--f-accent)) !important; }
        .f-progress-name { font-size: .98rem !important; font-weight: 570 !important; }

        /* Existing bordered blocks become restrained product surfaces. */
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: var(--f-radius) !important;
            border-color: rgba(255,255,255,.075) !important;
            background: rgba(255,255,255,.014) !important;
            box-shadow: none !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(136,232,193,.15) !important;
            transform: translateY(-1px);
        }
        [data-testid="stForm"], [data-testid="stExpander"] {
            border-radius: var(--f-radius) !important;
            border-color: rgba(255,255,255,.08) !important;
            background: #0E100F !important;
            box-shadow: none !important;
        }
        [data-testid="stExpander"] summary:hover { background: rgba(255,255,255,.018) !important; }

        /* Controls use one restrained shape language. */
        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
            min-height: 2.7rem !important;
            border-radius: 10px !important;
            border-color: rgba(255,255,255,.105) !important;
            background: #121512 !important;
            box-shadow: none !important;
            font-weight: 570 !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            background: #171B18 !important;
            border-color: rgba(136,232,193,.30) !important;
            transform: translateY(-1px) !important;
        }
        button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: #EAEDE8 !important;
            border-color: #EAEDE8 !important;
            color: #0A0D0B !important;
            box-shadow: 0 10px 30px rgba(0,0,0,.12) !important;
        }
        button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: var(--f-accent) !important;
            border-color: var(--f-accent) !important;
        }
        [data-baseweb="input"] > div, [data-baseweb="select"] > div, textarea {
            background: #0D100E !important;
            border-color: rgba(255,255,255,.09) !important;
            border-radius: 10px !important;
        }
        [data-baseweb="input"] > div:focus-within, [data-baseweb="select"] > div:focus-within, textarea:focus {
            border-color: rgba(136,232,193,.42) !important;
            box-shadow: 0 0 0 3px rgba(136,232,193,.055) !important;
        }
        [data-testid="stSegmentedControl"] {
            width: fit-content;
            max-width: 100%;
            padding: 3px !important;
            border-radius: 11px !important;
            border: 1px solid rgba(255,255,255,.075) !important;
            background: #0D100E !important;
        }
        [data-testid="stSegmentedControl"] button { border-radius: 8px !important; min-height: 2.25rem !important; }
        [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .3rem; border-bottom: 1px solid var(--f-line); }
        [data-testid="stTabs"] [data-baseweb="tab"] { border-radius: 8px 8px 0 0; }

        /* Charts feel embedded into the page rather than framed widgets. */
        [data-testid="stAltairChart"] {
            background: transparent !important;
            border: 0 !important;
            padding: .3rem 0 .1rem !important;
            overflow: visible !important;
        }
        [data-testid="stDataFrame"] {
            border-radius: 10px !important;
            border-color: rgba(255,255,255,.07) !important;
            box-shadow: none !important;
        }
        [data-testid="stFileUploader"] section {
            border-radius: var(--f-radius) !important;
            border-color: rgba(255,255,255,.09) !important;
            background: #0E100F !important;
        }
        [data-testid="stProgressBar"] > div > div { background: var(--f-accent) !important; }
        [data-testid="stAlert"] { border-radius: 10px !important; box-shadow: none !important; }

        /* Layered entrance motion. */
        [data-testid="stMainBlockContainer"] > div > div > div > div:nth-child(2) { animation-delay: .04s; }
        [data-testid="stMainBlockContainer"] > div > div > div > div:nth-child(3) { animation-delay: .08s; }
        [data-testid="stMainBlockContainer"] > div > div > div > div:nth-child(4) { animation-delay: .12s; }
        [data-testid="stMainBlockContainer"] > div > div > div > div:nth-child(5) { animation-delay: .16s; }
        [data-testid="stMetric"], .f-row, .f-progress-card, [data-testid="stDataFrame"], [data-testid="stAltairChart"] {
            animation: f-taste-rise .55s var(--f-ease) both;
        }
        @keyframes f-taste-rise {
            from { opacity: 0; transform: translateY(14px); filter: blur(3px); }
            to { opacity: 1; transform: translateY(0); filter: blur(0); }
        }

        @media (max-width: 1100px) {
            [data-testid="stMainBlockContainer"] { padding: 2.4rem 2.3rem 5rem !important; }
            .f-hero h1 { font-size: clamp(3rem, 7vw, 5.2rem) !important; }
        }
        @media (max-width: 760px) {
            [data-testid="stSidebar"] { padding: 0 !important; }
            [data-testid="stSidebar"] > div:first-child { height: 100vh; border-radius: 0 !important; border-left: 0 !important; border-top: 0 !important; border-bottom: 0 !important; }
            [data-testid="stMainBlockContainer"] { padding: 1.45rem 1rem 4rem !important; }
            .f-hero { padding-bottom: 1.8rem !important; }
            .f-hero h1 { font-size: clamp(2.55rem, 13vw, 4.1rem) !important; }
            .f-hero p { max-width: 94%; }
            .st-key-fyntra-overview-balance [data-testid="stMetric"] { min-height: 150px !important; }
            .st-key-fyntra-overview-balance [data-testid="stMetricValue"] { font-size: clamp(3.6rem, 17vw, 5.8rem) !important; }
            .f-section-head { margin-top: 2.2rem !important; }
        }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
        }
        </style>
        """
    )
