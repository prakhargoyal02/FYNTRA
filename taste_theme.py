"""Template-driven FYNTRA visual layer.

Presentation only. The supplied landing/admin templates inform hierarchy, color,
spacing and responsive behavior while FYNTRA keeps its Streamlit architecture.
"""
import streamlit as st


def apply_taste_layer():
    st.html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Host+Grotesk:wght@400;500;600;700&display=swap');

        :root {
            --f-canvas: #F3F0E9;
            --f-paper: #FFFDF8;
            --f-paper-2: #F8F5EE;
            --f-ink: #1A1E22;
            --f-ink-2: #343A3F;
            --f-muted: #6D7478;
            --f-line: #D9D7D0;
            --f-line-2: #C7C5BE;
            --f-ocean: #21435A;
            --f-blue: #2F6B8A;
            --f-blue-2: #527C9D;
            --f-sky: #DCEAF1;
            --f-sand: #E8DDCF;
            --f-sage: #DCE6DE;
            --f-rose: #EADBD6;
            --f-lilac: #E7E0EC;
            --f-positive: #327A5F;
            --f-negative: #C96C5A;
            --f-warning: #B8873D;
            --f-radius-xl: 34px;
            --f-radius-lg: 24px;
            --f-radius-md: 16px;
            --f-ease: cubic-bezier(.22,.78,.22,1);
            --f-shadow: 0 24px 70px rgba(38,45,51,.10);
        }

        html { background: var(--f-canvas); scroll-behavior: smooth; }
        body, .stApp, [data-testid="stAppViewContainer"] {
            font-family: "Host Grotesk", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
            color: var(--f-ink) !important;
        }
        .stApp {
            background:
                radial-gradient(900px 520px at 88% -14%, rgba(47,107,138,.11), transparent 66%),
                radial-gradient(700px 480px at 0% 52%, rgba(184,135,61,.055), transparent 72%),
                var(--f-canvas) !important;
        }
        [data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        [data-testid="stMainBlockContainer"] {
            max-width: 1500px !important;
            padding: .78rem 2rem 5rem !important;
        }
        [data-testid="stAppViewContainer"] > .main { overflow: visible !important; }

        h1, h2, h3, h4, p, label, button, input, textarea, select {
            font-family: "Host Grotesk", ui-sans-serif, system-ui, sans-serif !important;
        }
        h1, h2, h3 { color: var(--f-ink) !important; letter-spacing: -.045em !important; }
        h2 { font-size: clamp(1.75rem, 2.4vw, 2.7rem) !important; font-weight: 600 !important; }
        h3 { font-size: clamp(1.2rem, 1.7vw, 1.6rem) !important; font-weight: 600 !important; }
        p, label, [data-testid="stCaptionContainer"] p { color: var(--f-muted); }
        code, pre, .f-mono, .f-kicker, [data-testid="stMetricLabel"] p {
            font-family: "DM Mono", ui-monospace, monospace !important;
        }
        a { color: var(--f-blue) !important; }
        ::selection { background: #BFD6E2; color: var(--f-ink); }

        .st-key-fyntra-site-header {
            position: sticky;
            top: .55rem;
            z-index: 999;
            padding: .62rem .72rem !important;
            margin-bottom: .65rem;
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 999px;
            background: rgba(23,25,29,.97);
            box-shadow: 0 20px 54px rgba(32,39,45,.18);
            backdrop-filter: blur(18px);
            animation: f-shell-in .55s var(--f-ease) both;
        }
        .st-key-fyntra-site-header [data-testid="stCaptionContainer"] p {
            color: #9EA5AA !important;
            font-size: .54rem !important;
            letter-spacing: .11em !important;
            margin-top: -.22rem !important;
        }
        .st-key-fyntra-site-header .stButton > button,
        .st-key-fyntra-site-header [data-testid="stPopover"] > button {
            min-height: 2.55rem !important;
            border-radius: 999px !important;
            border: 1px solid transparent !important;
            background: transparent !important;
            color: #D5D9DC !important;
            box-shadow: none !important;
            font-size: .82rem !important;
            font-weight: 600 !important;
            padding: .45rem .78rem !important;
            transition: background .18s ease, color .18s ease, transform .18s ease !important;
        }
        .st-key-fyntra-site-header .stButton > button:hover,
        .st-key-fyntra-site-header [data-testid="stPopover"] > button:hover {
            background: rgba(255,255,255,.08) !important;
            color: #FFFFFF !important;
            transform: translateY(-1px);
        }
        .st-key-fyntra-site-header .stButton > button[kind="primary"] {
            background: #F7F3EA !important;
            color: #191D20 !important;
            border-color: #F7F3EA !important;
        }
        .f-context-strip {
            display: flex;
            align-items: center;
            gap: .55rem;
            padding: .28rem .3rem .75rem;
            color: #787C7B;
            font-family: "DM Mono", ui-monospace, monospace;
            font-size: .58rem;
            letter-spacing: .075em;
            text-transform: uppercase;
        }
        .f-context-strip span:not(:last-child)::after { content: " /"; color: #AAA8A2; }

        .f-hero {
            padding: 1.15rem 0 1.3rem !important;
            margin: 0 !important;
            min-height: 0 !important;
            overflow: visible !important;
            animation: f-rise .62s var(--f-ease) both !important;
        }
        .f-hero::before { display: none !important; }
        .f-kicker {
            color: currentColor !important;
            opacity: .68;
            font-size: .61rem !important;
            letter-spacing: .105em !important;
            margin-bottom: 1rem !important;
        }
        .f-kicker::before { width: 20px !important; background: currentColor !important; }
        .f-hero h1 {
            max-width: 980px !important;
            font-size: clamp(3.2rem, 6.5vw, 7.1rem) !important;
            line-height: .88 !important;
            font-weight: 600 !important;
            letter-spacing: -.073em !important;
            color: currentColor !important;
        }
        .f-hero p {
            max-width: 660px !important;
            margin-top: 1.1rem !important;
            color: currentColor !important;
            opacity: .76;
            font-size: clamp(1rem, 1.2vw, 1.16rem) !important;
            line-height: 1.55 !important;
        }
        .f-hero-rule {
            margin-top: 1.8rem !important;
            background: linear-gradient(90deg, currentColor, transparent 78%) !important;
            opacity: .22;
        }

        .st-key-overview-hero-stage,
        .st-key-transactions-hero-stage,
        .st-key-budgets-hero-stage,
        .st-key-analytics-hero-stage {
            border-radius: var(--f-radius-xl);
            padding: 1.15rem 2.15rem 1.65rem !important;
            margin: .25rem 0 1.1rem;
            overflow: hidden;
            box-shadow: var(--f-shadow);
            animation: f-rise .58s var(--f-ease) both;
        }
        .st-key-overview-hero-stage {
            background:
                radial-gradient(750px 360px at 86% 14%, rgba(124,186,210,.55), transparent 62%),
                linear-gradient(135deg, #1E3B50 0%, #245A77 54%, #5B9BB8 100%);
            color: #FBF8F1;
        }
        .st-key-transactions-hero-stage {
            background: linear-gradient(135deg, #EADBC8 0%, #F4EDE1 62%, #D9E7EC 100%);
            color: var(--f-ink);
        }
        .st-key-budgets-hero-stage {
            background: linear-gradient(135deg, #DCEAF1 0%, #E7EFEA 55%, #F2E8DA 100%);
            color: var(--f-ink);
        }
        .st-key-analytics-hero-stage {
            background:
                radial-gradient(620px 340px at 82% 10%, rgba(82,124,157,.35), transparent 64%),
                linear-gradient(135deg, #1B2025 0%, #25323B 62%, #314B5B 100%);
            color: #FAF7F0;
        }
        .st-key-overview-hero-stage h1,
        .st-key-overview-hero-stage h2,
        .st-key-overview-hero-stage h3,
        .st-key-analytics-hero-stage h1,
        .st-key-analytics-hero-stage h2,
        .st-key-analytics-hero-stage h3 { color: #FAF7F0 !important; }
        .st-key-overview-hero-stage [data-testid="stCaptionContainer"] p,
        .st-key-analytics-hero-stage [data-testid="stCaptionContainer"] p { color: rgba(250,247,240,.72) !important; }
        .st-key-overview-hero-stage [data-testid="stMetricValue"],
        .st-key-analytics-hero-stage [data-testid="stMetricValue"] { color: #FFFFFF !important; }
        .st-key-overview-hero-stage [data-testid="stMetricLabel"] p,
        .st-key-analytics-hero-stage [data-testid="stMetricLabel"] p { color: rgba(250,247,240,.65) !important; }

        [data-testid="stMetric"] {
            background: transparent !important;
            border: 0 !important;
            border-top: 1px solid var(--f-line) !important;
            border-radius: 0 !important;
            padding: .9rem .05rem 1rem !important;
            min-height: 96px !important;
            box-shadow: none !important;
        }
        [data-testid="stMetricLabel"] p {
            color: #747A7D !important;
            font-size: .60rem !important;
            letter-spacing: .075em !important;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: var(--f-ink) !important;
            font-size: clamp(1.65rem, 2.55vw, 2.8rem) !important;
            line-height: 1 !important;
            font-weight: 600 !important;
            letter-spacing: -.055em !important;
            font-variant-numeric: tabular-nums;
        }

        .st-key-overview-position-card,
        .st-key-overview-income-card,
        .st-key-overview-expense-card,
        .st-key-overview-cashflow-panel,
        .st-key-overview-budget-panel,
        .st-key-overview-category-panel,
        .st-key-overview-activity-panel,
        .st-key-overview-horizon-panel,
        .st-key-transactions-ledger-panel,
        .st-key-transactions-summary-panel,
        .st-key-budgets-summary-panel,
        .st-key-budgets-planner-panel,
        .st-key-budgets-category-panel,
        .st-key-analytics-cashflow-panel,
        .st-key-analytics-category-panel,
        .st-key-analytics-rhythm-panel,
        .st-key-analytics-fastread-panel,
        .st-key-analytics-position-panel,
        .st-key-analytics-projection-panel,
        .st-key-analytics-review-panel {
            border: 1px solid rgba(26,30,34,.07) !important;
            border-radius: var(--f-radius-lg) !important;
            padding: 1.3rem 1.45rem !important;
            overflow: hidden;
            box-shadow: 0 12px 36px rgba(38,45,51,.055);
            animation: f-rise .54s var(--f-ease) both;
        }
        .st-key-overview-position-card { background: #20262B !important; min-height: 300px; }
        .st-key-overview-position-card [data-testid="stMetric"] { border-top-color: rgba(255,255,255,.14) !important; }
        .st-key-overview-position-card [data-testid="stMetricValue"] { color: #FFFFFF !important; }
        .st-key-overview-position-card [data-testid="stMetricLabel"] p,
        .st-key-overview-position-card [data-testid="stCaptionContainer"] p { color: #ADB5BA !important; }
        .st-key-overview-position-card > div > div:first-child [data-testid="stMetricValue"] {
            font-size: clamp(4rem, 7vw, 7.6rem) !important;
            line-height: .84 !important;
            letter-spacing: -.075em !important;
        }
        .st-key-overview-income-card { background: var(--f-sage) !important; min-height: 300px; }
        .st-key-overview-expense-card { background: var(--f-rose) !important; min-height: 300px; }
        .st-key-overview-income-card [data-testid="stMetricValue"] { color: var(--f-positive) !important; }
        .st-key-overview-expense-card [data-testid="stMetricValue"] { color: var(--f-negative) !important; }
        .st-key-overview-cashflow-panel { background: var(--f-paper) !important; }
        .st-key-overview-budget-panel { background: var(--f-sand) !important; }
        .st-key-overview-category-panel { background: #F9F7F1 !important; }
        .st-key-overview-activity-panel { background: var(--f-paper) !important; }
        .st-key-overview-horizon-panel { background: var(--f-lilac) !important; }

        .st-key-transactions-ledger-panel { background: var(--f-paper) !important; }
        .st-key-transactions-summary-panel { background: var(--f-sky) !important; }
        .st-key-budgets-summary-panel { background: #213542 !important; color: #F9F6EF; }
        .st-key-budgets-summary-panel h3,
        .st-key-budgets-summary-panel [data-testid="stMetricValue"] { color: #FFFFFF !important; }
        .st-key-budgets-summary-panel [data-testid="stMetricLabel"] p,
        .st-key-budgets-summary-panel [data-testid="stCaptionContainer"] p { color: #B9C4CA !important; }
        .st-key-budgets-summary-panel [data-testid="stMetric"] { border-top-color: rgba(255,255,255,.14) !important; }
        .st-key-budgets-planner-panel { background: var(--f-sand) !important; }
        .st-key-budgets-category-panel { background: var(--f-paper) !important; }
        .st-key-analytics-cashflow-panel { background: var(--f-paper) !important; }
        .st-key-analytics-category-panel { background: #F9F4F0 !important; }
        .st-key-analytics-rhythm-panel { background: var(--f-sand) !important; }
        .st-key-analytics-fastread-panel { background: var(--f-sky) !important; }
        .st-key-analytics-position-panel { background: var(--f-paper) !important; }
        .st-key-analytics-projection-panel { background: var(--f-sage) !important; }
        .st-key-analytics-review-panel { background: var(--f-lilac) !important; }

        .f-section-head {
            margin: .4rem 0 1rem !important;
            padding-top: 0 !important;
            border-top: 0 !important;
        }
        .f-section-head h3 { color: var(--f-ink) !important; font-size: clamp(1.35rem, 1.9vw, 1.9rem) !important; font-weight: 600 !important; }
        .f-section-head p { color: #70777A !important; line-height: 1.5 !important; }
        .f-insight { border-left: 2px solid currentColor !important; padding-left: 1rem !important; }
        .f-insight strong { color: inherit !important; font-size: 1.22rem !important; font-weight: 600 !important; }
        .f-insight span { color: inherit !important; opacity: .72; }

        .f-row {
            padding: .92rem .1rem !important;
            border-bottom: 1px solid #E1DED7 !important;
            transition: background .18s ease, padding .18s ease, transform .18s ease !important;
        }
        .f-row:hover {
            background: #F3F0E9 !important;
            padding-left: .55rem !important;
            padding-right: .55rem !important;
            transform: translateX(2px) !important;
        }
        .f-row strong { color: var(--f-ink) !important; font-weight: 600 !important; }
        .f-row small { color: #7B8082 !important; }
        .f-amount { font-weight: 650 !important; }
        .f-positive { color: var(--f-positive) !important; }
        .f-negative { color: var(--f-negative) !important; }
        .f-neutral { color: var(--f-ink-2) !important; }

        .f-progress-card { border-bottom: 1px solid #E1DED7 !important; padding: 1rem 0 1.15rem !important; }
        .f-progress-name, .f-progress-value { color: var(--f-ink) !important; }
        .f-progress-track { background: #DDDAD3 !important; height: 6px !important; }
        .f-progress-fill { background: linear-gradient(90deg, var(--f-blue), #5A8FA8) !important; }
        .f-progress-caption { color: #73797B !important; }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--f-paper) !important;
            border: 1px solid rgba(26,30,34,.085) !important;
            border-radius: 20px !important;
            box-shadow: 0 9px 28px rgba(38,45,51,.045) !important;
        }
        [data-testid="stForm"], [data-testid="stExpander"] {
            background: var(--f-paper) !important;
            border: 1px solid rgba(26,30,34,.09) !important;
            border-radius: 18px !important;
            box-shadow: none !important;
        }
        [data-testid="stForm"] { padding: 1.1rem 1.1rem .45rem !important; }
        [data-testid="stExpander"] { overflow: hidden; }

        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stFormSubmitButton"] button {
            border-radius: 999px !important;
            min-height: 2.75rem !important;
            border: 1px solid #CBC9C2 !important;
            background: #FFFDF8 !important;
            color: var(--f-ink) !important;
            box-shadow: none !important;
            font-weight: 600 !important;
            transition: transform .18s ease, border-color .18s ease, background .18s ease, box-shadow .18s ease !important;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            transform: translateY(-1px);
            border-color: #9FA5A6 !important;
            box-shadow: 0 8px 20px rgba(38,45,51,.07) !important;
        }
        .stButton > button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: var(--f-blue) !important;
            border-color: var(--f-blue) !important;
            color: #FFFFFF !important;
        }
        .stButton > button:active { transform: translateY(0) scale(.985); }

        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-baseweb="textarea"] > div,
        [data-baseweb="base-input"] {
            background: #FFFDF8 !important;
            border-color: #CCCAC3 !important;
            border-radius: 13px !important;
            box-shadow: none !important;
        }
        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within {
            border-color: var(--f-blue) !important;
            box-shadow: 0 0 0 3px rgba(47,107,138,.10) !important;
        }
        [data-testid="stFileUploader"] section {
            background: #F8F5EE !important;
            border: 1px dashed #B9B7B0 !important;
            border-radius: 18px !important;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid #DDDAD3 !important;
            border-radius: 16px !important;
            overflow: hidden;
            background: #FFFDF8 !important;
        }
        [data-testid="stProgressBar"] > div > div { background: var(--f-blue) !important; }
        hr { border-color: #D9D7D0 !important; }

        [data-baseweb="popover"] > div {
            border-radius: 20px !important;
            border: 1px solid #D5D2CB !important;
            background: #FFFDF8 !important;
            box-shadow: 0 24px 70px rgba(27,33,38,.18) !important;
        }

        @keyframes f-shell-in {
            from { opacity: 0; transform: translateY(-10px) scale(.99); }
            to { opacity: 1; transform: none; }
        }
        @keyframes f-rise {
            from { opacity: 0; transform: translateY(14px); }
            to { opacity: 1; transform: none; }
        }

        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] { padding: .65rem 1rem 3.5rem !important; }
            .st-key-fyntra-site-header { border-radius: 22px; top: .35rem; padding: .5rem .55rem !important; }
            .st-key-fyntra-site-header [data-testid="stCaptionContainer"] { display: none !important; }
            .st-key-overview-hero-stage,
            .st-key-transactions-hero-stage,
            .st-key-budgets-hero-stage,
            .st-key-analytics-hero-stage {
                border-radius: 26px;
                padding: .8rem 1.2rem 1.15rem !important;
            }
            .f-hero h1 { font-size: clamp(2.8rem, 10vw, 4.8rem) !important; }
            .st-key-overview-position-card,
            .st-key-overview-income-card,
            .st-key-overview-expense-card { min-height: 0; }
        }

        @media (max-width: 640px) {
            [data-testid="stMainBlockContainer"] { padding: .45rem .72rem 3rem !important; }
            .st-key-fyntra-site-header { position: sticky; border-radius: 18px; }
            .st-key-fyntra-site-header .stButton > button,
            .st-key-fyntra-site-header [data-testid="stPopover"] > button {
                min-height: 2.2rem !important;
                padding: .32rem .5rem !important;
                font-size: .72rem !important;
            }
            .f-context-strip { overflow-x: auto; white-space: nowrap; }
            .f-hero { padding-top: .8rem !important; }
            .f-hero h1 { font-size: clamp(2.45rem, 13vw, 3.8rem) !important; line-height: .91 !important; }
            .f-hero p { font-size: .96rem !important; }
            .st-key-overview-hero-stage,
            .st-key-transactions-hero-stage,
            .st-key-budgets-hero-stage,
            .st-key-analytics-hero-stage { padding: .65rem .95rem 1rem !important; border-radius: 22px; }
            .st-key-overview-position-card,
            .st-key-overview-income-card,
            .st-key-overview-expense-card,
            .st-key-overview-cashflow-panel,
            .st-key-overview-budget-panel,
            .st-key-overview-category-panel,
            .st-key-overview-activity-panel,
            .st-key-overview-horizon-panel,
            .st-key-transactions-ledger-panel,
            .st-key-transactions-summary-panel,
            .st-key-budgets-summary-panel,
            .st-key-budgets-planner-panel,
            .st-key-budgets-category-panel,
            .st-key-analytics-cashflow-panel,
            .st-key-analytics-category-panel,
            .st-key-analytics-rhythm-panel,
            .st-key-analytics-fastread-panel,
            .st-key-analytics-position-panel,
            .st-key-analytics-projection-panel,
            .st-key-analytics-review-panel {
                border-radius: 18px !important;
                padding: 1rem !important;
            }
            [data-testid="stMetricValue"] { font-size: 2rem !important; }
            .st-key-overview-position-card > div > div:first-child [data-testid="stMetricValue"] { font-size: clamp(3.3rem, 16vw, 5.5rem) !important; }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                scroll-behavior: auto !important;
                animation-duration: .01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: .01ms !important;
            }
        }
        </style>
        """
    )
