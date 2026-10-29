"""Reference-driven FYNTRA visual layer.

Presentation only. The palette and shell intentionally move away from neon finance UI
into a warm, real-world product system inspired by editorial SaaS and finance tools.
"""
import streamlit as st


def apply_taste_layer():
    st.html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Instrument+Sans:opsz,wght@12..32,400;12..32,500;12..32,600;12..32,700&display=swap');

        :root {
            --f-canvas: #F2EFE8;
            --f-paper: #FBFAF7;
            --f-paper-2: #F7F4ED;
            --f-ink: #1B2530;
            --f-ink-2: #33404A;
            --f-muted: #707772;
            --f-line: #D9D8D1;
            --f-line-strong: #C8C8C0;
            --f-navy: #192735;
            --f-navy-2: #223545;
            --f-blue: #3F5FCA;
            --f-blue-soft: #E5EAF8;
            --f-sand: #E9E1D2;
            --f-sage: #DDE7DF;
            --f-blush: #EFE0DC;
            --f-lilac: #E8E4F1;
            --f-positive: #2F7D5A;
            --f-negative: #C76555;
            --f-warning: #B47A2D;
            --f-radius: 18px;
            --f-ease: cubic-bezier(.22,.78,.22,1);
        }

        html { background: var(--f-canvas); scroll-behavior: smooth; }
        body, .stApp, [data-testid="stAppViewContainer"] {
            font-family: "Instrument Sans", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
            color: var(--f-ink) !important;
        }
        .stApp {
            background:
                radial-gradient(900px 520px at 85% -8%, rgba(63,95,202,.09), transparent 66%),
                radial-gradient(700px 500px at 5% 42%, rgba(180,122,45,.055), transparent 70%),
                var(--f-canvas) !important;
        }
        [data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stMainBlockContainer"] {
            max-width: 1540px !important;
            padding: .85rem 2.2rem 5rem !important;
        }
        [data-testid="stAppViewContainer"] > .main { overflow: visible !important; }

        h1, h2, h3, h4, p, label { font-family: "Instrument Sans", ui-sans-serif, system-ui, sans-serif !important; }
        h1, h2, h3 { color: var(--f-ink) !important; letter-spacing: -.045em !important; }
        h2 { font-size: clamp(1.65rem, 2.5vw, 2.6rem) !important; font-weight: 590 !important; }
        h3 { font-size: clamp(1.18rem, 1.7vw, 1.55rem) !important; font-weight: 600 !important; }
        p, label, [data-testid="stCaptionContainer"] p { color: var(--f-muted); }
        code, pre, .f-mono, .f-kicker, [data-testid="stMetricLabel"] p {
            font-family: "DM Mono", ui-monospace, monospace !important;
        }
        a { color: var(--f-blue) !important; }

        /* Full-width website shell. */
        .st-key-fyntra-site-header {
            position: sticky;
            top: .65rem;
            z-index: 999;
            padding: .65rem .72rem !important;
            margin-bottom: .55rem;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 20px;
            background: rgba(25,39,53,.965);
            box-shadow: 0 18px 50px rgba(39,46,55,.16);
            backdrop-filter: blur(18px);
            transform-origin: top center;
        }
        .st-key-fyntra-site-header [data-testid="stImage"] { margin: 0 !important; }
        .st-key-fyntra-site-header [data-testid="stCaptionContainer"] p {
            color: #A9B3BA !important;
            font-size: .56rem !important;
            letter-spacing: .12em;
            margin-top: -.25rem !important;
        }
        .st-key-fyntra-site-header .stButton > button,
        .st-key-fyntra-site-header [data-testid="stPopover"] > button {
            min-height: 2.45rem !important;
            border-radius: 11px !important;
            border: 1px solid transparent !important;
            background: transparent !important;
            color: #C8D0D5 !important;
            box-shadow: none !important;
            font-size: .82rem !important;
            font-weight: 570 !important;
            transition: background .18s ease, color .18s ease, transform .18s ease !important;
        }
        .st-key-fyntra-site-header .stButton > button:hover,
        .st-key-fyntra-site-header [data-testid="stPopover"] > button:hover {
            background: rgba(255,255,255,.07) !important;
            color: #FFFFFF !important;
            transform: translateY(-1px);
        }
        .st-key-fyntra-site-header .stButton > button[kind="primary"] {
            background: #F6F2E9 !important;
            color: #1B2530 !important;
            border-color: #F6F2E9 !important;
        }
        .f-context-strip {
            display: flex;
            align-items: center;
            gap: .55rem;
            padding: .3rem .25rem .75rem;
            color: #7A7E78;
            font-family: "DM Mono", ui-monospace, monospace;
            font-size: .59rem;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .f-context-strip span:not(:last-child)::after { content: " /"; color: #AAA9A2; }

        /* Page openings: editorial, not neon. */
        .f-hero {
            padding: 2.6rem 0 2.15rem !important;
            margin: 0 !important;
            min-height: 0 !important;
            overflow: visible !important;
            animation: f-rise-soft .62s var(--f-ease) both !important;
        }
        .f-hero::before {
            width: 360px !important;
            height: 360px !important;
            right: 2% !important;
            top: -205px !important;
            border-color: rgba(63,95,202,.08) !important;
            box-shadow: 0 0 100px rgba(63,95,202,.045) !important;
        }
        .f-kicker {
            color: #7B7B75 !important;
            font-size: .61rem !important;
            letter-spacing: .10em !important;
            margin-bottom: .9rem !important;
        }
        .f-kicker::before { width: 18px !important; background: var(--f-blue) !important; }
        .f-hero h1 {
            max-width: 1000px !important;
            font-size: clamp(3rem, 5.7vw, 5.8rem) !important;
            line-height: .94 !important;
            font-weight: 570 !important;
            letter-spacing: -.068em !important;
            color: var(--f-ink) !important;
        }
        .f-hero p {
            max-width: 650px !important;
            margin-top: 1.05rem !important;
            color: #686E6B !important;
            font-size: clamp(.96rem, 1.15vw, 1.08rem) !important;
            line-height: 1.62 !important;
        }
        .f-hero-rule {
            margin-top: 1.75rem !important;
            background: linear-gradient(90deg, rgba(63,95,202,.55), rgba(27,37,48,.12) 38%, transparent 90%) !important;
        }

        /* General metrics live cleanly on the canvas. */
        [data-testid="stMetric"] {
            background: transparent !important;
            border: 0 !important;
            border-top: 1px solid var(--f-line) !important;
            border-radius: 0 !important;
            padding: .9rem .05rem 1.1rem !important;
            min-height: 100px !important;
            box-shadow: none !important;
        }
        [data-testid="stMetricLabel"] p {
            color: #777B76 !important;
            font-size: .61rem !important;
            letter-spacing: .08em !important;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: var(--f-ink) !important;
            font-size: clamp(1.65rem, 2.55vw, 2.75rem) !important;
            line-height: 1 !important;
            font-weight: 590 !important;
            letter-spacing: -.055em !important;
            font-variant-numeric: tabular-nums;
        }
        [data-testid="stMetricDelta"] { color: var(--f-muted) !important; }

        /* Bento surfaces. These are intentionally different, like a designed website. */
        .st-key-bento-balance,
        .st-key-bento-month,
        .st-key-bento-pulse,
        .st-key-bento-motion,
        .st-key-bento-budget,
        .st-key-bento-spending,
        .st-key-bento-position,
        .st-key-bento-activity,
        .st-key-bento-horizon,
        .st-key-transaction-summary,
        .st-key-transaction-ledger,
        .st-key-budget-summary,
        .st-key-budget-pressure,
        .st-key-budget-planner {
            border-radius: 22px;
            border: 1px solid rgba(27,37,48,.075);
            padding: 1.35rem 1.45rem !important;
            overflow: hidden;
            box-shadow: 0 12px 35px rgba(50,55,60,.055);
            animation: f-rise-soft .58s var(--f-ease) both;
        }
        .st-key-bento-balance { background: var(--f-navy); color: #F8F7F2; min-height: 305px; }
        .st-key-bento-balance p, .st-key-bento-balance [data-testid="stCaptionContainer"] p { color: #B8C1C6 !important; }
        .st-key-bento-balance [data-testid="stMetric"] { border-top-color: rgba(255,255,255,.15) !important; }
        .st-key-bento-balance [data-testid="stMetricLabel"] p { color: #AAB5BB !important; }
        .st-key-bento-balance [data-testid="stMetricValue"] { color: #FCFBF7 !important; }
        .st-key-bento-balance > div > div:first-child [data-testid="stMetricValue"] {
            font-size: clamp(4rem, 7vw, 7.7rem) !important;
            line-height: .84 !important;
            letter-spacing: -.075em !important;
        }
        .st-key-bento-month { background: var(--f-sand); min-height: 190px; }
        .st-key-bento-pulse { background: var(--f-blue-soft); min-height: 118px; }
        .st-key-bento-motion { background: var(--f-paper); }
        .st-key-bento-budget { background: #E6E7DE; }
        .st-key-bento-spending { background: #FCFBF8; }
        .st-key-bento-position { background: var(--f-blush); }
        .st-key-bento-activity { background: var(--f-paper); }
        .st-key-bento-horizon { background: var(--f-lilac); }
        .st-key-transaction-summary { background: #E5EAF8; }
        .st-key-transaction-ledger { background: var(--f-paper); }
        .st-key-budget-summary { background: var(--f-navy); }
        .st-key-budget-summary [data-testid="stMetricValue"], .st-key-budget-summary h3 { color: #FFFFFF !important; }
        .st-key-budget-summary [data-testid="stMetricLabel"] p, .st-key-budget-summary p { color: #B7C0C5 !important; }
        .st-key-budget-summary [data-testid="stMetric"] { border-top-color: rgba(255,255,255,.15) !important; }
        .st-key-budget-pressure { background: var(--f-paper); }
        .st-key-budget-planner { background: var(--f-sand); }

        .f-section-head {
            margin: 2.4rem 0 .85rem !important;
            padding-top: 0 !important;
            border-top: 0 !important;
        }
        .f-section-head h3 { color: var(--f-ink) !important; font-size: clamp(1.3rem, 1.9vw, 1.85rem) !important; font-weight: 600 !important; }
        .f-section-head p { color: #717773 !important; line-height: 1.55 !important; }
        .f-insight { border-left: 2px solid var(--f-blue) !important; padding-left: 1rem !important; }
        .f-insight strong { color: var(--f-ink) !important; font-size: 1.25rem !important; font-weight: 600 !important; }
        .f-insight span { color: #666D69 !important; }

        /* Transaction rows and progress. */
        .f-row {
            padding: .9rem .1rem !important;
            border-bottom: 1px solid #E2E0D9 !important;
            transition: background .18s ease, padding .18s ease, transform .18s ease !important;
        }
        .f-row:hover {
            background: #F2F0E9 !important;
            padding-left: .55rem !important;
            padding-right: .55rem !important;
            transform: translateX(2px) !important;
        }
        .f-row strong { color: var(--f-ink) !important; font-weight: 600 !important; }
        .f-row small { color: #7B817D !important; }
        .f-amount { font-weight: 620 !important; }
        .f-positive { color: var(--f-positive) !important; }
        .f-negative { color: var(--f-negative) !important; }
        .f-neutral { color: var(--f-ink-2) !important; }

        .f-progress-card { border-bottom: 1px solid #E2E0D9 !important; padding: 1rem 0 1.15rem !important; }
        .f-progress-name, .f-progress-value { color: var(--f-ink) !important; }
        .f-progress-track { background: #DEDCD5 !important; height: 5px !important; }
        .f-progress-fill { background: var(--f-blue) !important; }
        .f-progress-caption { color: #757B77 !important; }

        /* Native Streamlit surfaces. */
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--f-paper) !important;
            border: 1px solid rgba(27,37,48,.09) !important;
            border-radius: 18px !important;
            box-shadow: 0 8px 28px rgba(50,55,60,.045) !important;
        }
        [data-testid="stForm"], [data-testid="stExpander"] {
            background: var(--f-paper) !important;
            border: 1px solid rgba(27,37,48,.09) !important;
            border-radius: 16px !important;
            box-shadow: none !important;
        }
        [data-testid="stExpander"] summary:hover { background: #F5F2EB !important; }
        [data-testid="stAlert"] { border-radius: 14px !important; box-shadow: none !important; }

        .stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] button {
            min-height: 2.65rem !important;
            border-radius: 11px !important;
            border: 1px solid #D4D2CB !important;
            background: #FBFAF7 !important;
            color: var(--f-ink) !important;
            box-shadow: none !important;
            font-weight: 590 !important;
            transition: transform .16s ease, border-color .16s ease, background .16s ease !important;
        }
        .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-1px) !important;
            border-color: #A9B2D6 !important;
            background: #F2F4FA !important;
        }
        button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: var(--f-blue) !important;
            border-color: var(--f-blue) !important;
            color: #FFFFFF !important;
        }
        button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: #334FAF !important;
            border-color: #334FAF !important;
        }

        [data-baseweb="input"] > div, [data-baseweb="select"] > div, textarea {
            background: #FFFEFB !important;
            color: var(--f-ink) !important;
            border-color: #D5D4CD !important;
            border-radius: 11px !important;
        }
        [data-baseweb="input"] > div:focus-within, [data-baseweb="select"] > div:focus-within, textarea:focus {
            border-color: rgba(63,95,202,.6) !important;
            box-shadow: 0 0 0 3px rgba(63,95,202,.09) !important;
        }
        input, textarea { color: var(--f-ink) !important; }
        [data-baseweb="popover"], [data-baseweb="menu"] { color: var(--f-ink) !important; }
        [data-testid="stSegmentedControl"] {
            background: #E9E6DE !important;
            border: 1px solid #D8D5CC !important;
            border-radius: 12px !important;
            padding: 3px !important;
        }
        [data-testid="stSegmentedControl"] button { border-radius: 9px !important; }
        [data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom: 1px solid var(--f-line); }

        [data-testid="stDataFrame"] {
            border: 1px solid #D9D7D0 !important;
            border-radius: 14px !important;
            box-shadow: none !important;
            overflow: hidden;
        }
        [data-testid="stAltairChart"] {
            background: transparent !important;
            border: 0 !important;
            padding-top: .15rem !important;
        }
        [data-testid="stFileUploader"] section {
            background: #FBFAF7 !important;
            border: 1px dashed #C8C7C0 !important;
            border-radius: 16px !important;
        }
        [data-testid="stProgressBar"] > div { background: #E0DED7 !important; }
        [data-testid="stProgressBar"] > div > div { background: var(--f-blue) !important; }
        [data-testid="stToast"] { background: #FFFFFF !important; color: var(--f-ink) !important; border: 1px solid var(--f-line) !important; }

        ::selection { background: rgba(63,95,202,.18); color: var(--f-ink); }
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: #EEEAE2; }
        ::-webkit-scrollbar-thumb { background: #C9C6BE; border-radius: 99px; border: 2px solid #EEEAE2; }

        @keyframes f-rise-soft {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @supports (animation-timeline: scroll()) {
            .st-key-fyntra-site-header {
                animation: f-shell-compact linear both;
                animation-timeline: scroll(root);
                animation-range: 0 180px;
            }
            @keyframes f-shell-compact {
                from { transform: scale(1); }
                to { transform: scale(.985); }
            }
        }

        @media (max-width: 980px) {
            [data-testid="stMainBlockContainer"] { padding: .7rem 1rem 4rem !important; }
            .st-key-fyntra-site-header { position: sticky; top: .35rem; border-radius: 16px; }
            .st-key-fyntra-site-header [data-testid="stCaptionContainer"] { display: none; }
            .st-key-fyntra-site-header .stButton > button { font-size: .72rem !important; padding-left: .4rem !important; padding-right: .4rem !important; }
            .f-hero { padding-top: 2rem !important; }
            .f-hero h1 { font-size: clamp(2.7rem, 8vw, 4.7rem) !important; }
            .st-key-bento-balance { min-height: 250px; }
        }
        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] { padding: .45rem .65rem 3rem !important; }
            .st-key-fyntra-site-header { padding: .5rem !important; border-radius: 14px; }
            .st-key-fyntra-site-header [data-testid="stImage"] { max-width: 92px; }
            .st-key-fyntra-site-header .stButton > button { min-height: 2.2rem !important; font-size: .65rem !important; }
            .f-context-strip { overflow-x: auto; white-space: nowrap; }
            .f-hero { padding: 1.6rem 0 1.6rem !important; }
            .f-hero h1 { font-size: clamp(2.35rem, 12vw, 3.8rem) !important; }
            .st-key-bento-balance,
            .st-key-bento-month,
            .st-key-bento-pulse,
            .st-key-bento-motion,
            .st-key-bento-budget,
            .st-key-bento-spending,
            .st-key-bento-position,
            .st-key-bento-activity,
            .st-key-bento-horizon,
            .st-key-transaction-summary,
            .st-key-transaction-ledger,
            .st-key-budget-summary,
            .st-key-budget-pressure,
            .st-key-budget-planner { padding: 1rem !important; border-radius: 16px; }
        }
        @media (prefers-reduced-motion: reduce) {
            html { scroll-behavior: auto; }
            *, *::before, *::after { animation: none !important; transition: none !important; }
        }
        </style>
        """
    )
