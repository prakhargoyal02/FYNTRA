"""Dashboard-template visual system for FYNTRA."""
import streamlit as st


def apply_taste_layer():
    st.html(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Inter:wght@400;500;600;700&display=swap');

        :root {
          --canvas:#F5F7FB;
          --paper:#FFFFFF;
          --ink:#1D2433;
          --muted:#71798A;
          --line:#E6E9F0;
          --line-strong:#D8DDE8;
          --nav:#171A21;
          --blue:#4C6FFF;
          --blue-soft:#EEF2FF;
          --green:#2F8F68;
          --red:#D66A5E;
          --amber:#C58A32;
          --radius:14px;
          --shadow:0 8px 26px rgba(29,36,51,.06);
        }

        html{background:var(--canvas);scroll-behavior:smooth}
        body,.stApp,[data-testid="stAppViewContainer"]{font-family:"Inter",system-ui,sans-serif!important;color:var(--ink)!important}
        .stApp{background:var(--canvas)!important}
        [data-testid="stHeader"]{display:none!important}
        [data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important}
        [data-testid="stMainBlockContainer"]{max-width:1480px!important;padding:1rem 2rem 4rem!important}

        h1,h2,h3,h4,p,label{font-family:"Inter",system-ui,sans-serif!important}
        h1,h2,h3{color:var(--ink)!important;letter-spacing:-.035em!important}
        h2{font-size:1.55rem!important;font-weight:650!important}
        h3{font-size:1.08rem!important;font-weight:650!important}
        p,label,[data-testid="stCaptionContainer"] p{color:var(--muted)}
        code,pre,[data-testid="stMetricLabel"] p,.dk-page-head span{font-family:"DM Mono",monospace!important}
        a{color:var(--blue)!important}

        /* Landing-template influence is limited to the floating product header. */
        .st-key-fyntra-site-header{
          position:sticky;top:.7rem;z-index:999;
          padding:.55rem .65rem!important;margin:0 auto .8rem;
          border:1px solid rgba(255,255,255,.08);border-radius:999px;
          background:rgba(23,26,33,.97);box-shadow:0 14px 38px rgba(21,24,31,.16);
          backdrop-filter:blur(16px);max-width:1380px
        }
        .st-key-fyntra-site-header [data-testid="stCaptionContainer"] p{color:#8F96A6!important;font-size:.52rem!important;letter-spacing:.1em}
        .st-key-fyntra-site-header .stButton>button,
        .st-key-fyntra-site-header [data-testid="stPopover"]>button{
          min-height:2.3rem!important;border-radius:999px!important;border:1px solid transparent!important;
          background:transparent!important;color:#C6CBD5!important;box-shadow:none!important;
          font-size:.78rem!important;font-weight:600!important;padding:.35rem .7rem!important
        }
        .st-key-fyntra-site-header .stButton>button:hover,
        .st-key-fyntra-site-header [data-testid="stPopover"]>button:hover{background:#272B34!important;color:white!important}
        .st-key-fyntra-site-header .stButton>button[kind="primary"]{background:#FFFFFF!important;color:#171A21!important}
        .f-context-strip{display:flex;gap:.5rem;padding:.1rem .2rem .7rem;color:#89909E;font-family:"DM Mono",monospace;font-size:.56rem;letter-spacing:.07em;text-transform:uppercase}
        .f-context-strip span:not(:last-child)::after{content:" /";color:#B1B6C0}

        /* Compact admin page heading. */
        .dk-page-head{padding:1.25rem .1rem 1.35rem;border-bottom:1px solid var(--line);margin-bottom:1.1rem}
        .dk-page-head span{display:block;color:#8B92A0;font-size:.58rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:.45rem}
        .dk-page-head h1{margin:0;font-size:clamp(2rem,3.5vw,3.35rem);line-height:1;font-weight:680;letter-spacing:-.055em}
        .dk-page-head p{margin:.6rem 0 0;max-width:720px;font-size:.92rem;line-height:1.55;color:#777F8D}
        .f-hero{padding:1.25rem 0!important;margin:0!important}
        .f-hero h1{font-size:clamp(2rem,3.6vw,3.5rem)!important;line-height:1!important}
        .f-hero p{font-size:.92rem!important;max-width:700px!important}
        .f-hero::before,.f-hero-rule{display:none!important}

        /* DashboardKit-like cards. */
        [data-testid="stVerticalBlockBorderWrapper"]{background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:var(--radius)!important;box-shadow:var(--shadow)!important}
        .st-key-dk-balance-card,.st-key-dk-income-card,.st-key-dk-expense-card,
        .st-key-dk-cashflow-card,.st-key-dk-budget-card,.st-key-dk-category-card,
        .st-key-dk-activity-card,.st-key-dk-horizon-card,.st-key-dk-ledger-card,
        .st-key-dk-editor-card,.st-key-dk-budget-list,.st-key-dk-purchase-card,
        .st-key-dk-analytics-cashflow,.st-key-dk-analytics-summary,.st-key-dk-analytics-category,
        .st-key-dk-analytics-daily,.st-key-dk-analytics-position,.st-key-dk-analytics-projection,
        .st-key-dk-analytics-review{padding:1.1rem 1.2rem!important}
        .st-key-dk-balance-card{background:#1F2633!important;color:white!important}
        .st-key-dk-balance-card [data-testid="stMetricValue"]{color:white!important}
        .st-key-dk-balance-card [data-testid="stMetricLabel"] p,.st-key-dk-balance-card p{color:#AAB2C1!important}
        .st-key-dk-income-card{background:#F2F8F5!important;border-color:#DCEBE3!important}
        .st-key-dk-expense-card{background:#FFF5F2!important;border-color:#F3DDD7!important}
        .st-key-dk-budget-card{background:#F8F9FC!important}

        [data-testid="stMetric"]{background:transparent!important;border:0!important;padding:.55rem 0 .75rem!important;min-height:76px!important}
        [data-testid="stMetricLabel"] p{font-size:.58rem!important;letter-spacing:.08em;text-transform:uppercase;color:#8B92A0!important}
        [data-testid="stMetricValue"]{color:var(--ink)!important;font-size:clamp(1.55rem,2.25vw,2.45rem)!important;font-weight:650!important;letter-spacing:-.045em!important;font-variant-numeric:tabular-nums}
        .st-key-dk-balance-card>div>div:first-child [data-testid="stMetricValue"]{font-size:clamp(3rem,5.4vw,5.5rem)!important;line-height:.92!important}

        .f-section-head{margin:.2rem 0 .8rem!important;align-items:start!important}
        .f-section-head h3{font-size:1.02rem!important;font-weight:650!important;color:var(--ink)!important}
        .f-section-head p{font-size:.76rem!important;color:#89909C!important;max-width:460px!important}
        .f-row{padding:.78rem 0!important;border-bottom:1px solid #EEF0F4!important}
        .f-row:hover{background:#F8F9FC!important;padding-left:.45rem!important;padding-right:.45rem!important;transform:none!important}
        .f-row strong{color:var(--ink)!important;font-size:.86rem!important}.f-row small{color:#8A92A0!important}.f-amount{font-weight:650!important}
        .f-positive{color:var(--green)!important}.f-negative{color:var(--red)!important}.f-neutral{color:var(--ink)!important}
        .f-progress-card{padding:.9rem 0!important;border-bottom:1px solid #EEF0F4!important}.f-progress-track{height:6px!important;background:#ECEFF4!important}.f-progress-fill{background:var(--blue)!important}.f-progress-name,.f-progress-value{color:var(--ink)!important}.f-progress-caption{color:#8A92A0!important}

        [data-testid="stForm"],[data-testid="stExpander"]{background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:var(--radius)!important;box-shadow:none!important}
        [data-testid="stAlert"]{border-radius:12px!important}
        .stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button{
          min-height:2.5rem!important;border-radius:9px!important;border:1px solid var(--line-strong)!important;background:white!important;color:var(--ink)!important;box-shadow:none!important;font-weight:600!important
        }
        .stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stFormSubmitButton"] button:hover{border-color:#AEB7C7!important;background:#F8F9FC!important}
        button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:var(--blue)!important;border-color:var(--blue)!important;color:white!important}

        [data-baseweb="input"]>div,[data-baseweb="select"]>div,textarea{background:white!important;color:var(--ink)!important;border-color:#DCE0E8!important;border-radius:9px!important}
        [data-baseweb="input"]>div:focus-within,[data-baseweb="select"]>div:focus-within,textarea:focus{border-color:#8DA1FF!important;box-shadow:0 0 0 3px rgba(76,111,255,.10)!important}
        input,textarea{color:var(--ink)!important}
        [data-testid="stSegmentedControl"]{background:#ECEFF4!important;border:1px solid #E0E4EB!important;border-radius:10px!important;padding:3px!important}
        [data-testid="stSegmentedControl"] button{border-radius:7px!important}
        [data-testid="stDataFrame"]{border:1px solid var(--line)!important;border-radius:12px!important;overflow:hidden;background:white!important}
        [data-testid="stAltairChart"]{background:transparent!important;border:0!important}
        [data-testid="stFileUploader"] section{background:#FAFBFD!important;border:1px dashed #CDD3DF!important;border-radius:12px!important}
        [data-testid="stProgressBar"]>div{background:#ECEFF4!important}[data-testid="stProgressBar"]>div>div{background:var(--blue)!important}
        [data-testid="stToast"]{background:white!important;color:var(--ink)!important;border:1px solid var(--line)!important}

        ::selection{background:rgba(76,111,255,.18);color:var(--ink)}
        ::-webkit-scrollbar{width:9px;height:9px}::-webkit-scrollbar-track{background:#F2F4F7}::-webkit-scrollbar-thumb{background:#C8CDD6;border-radius:99px}

        @media(max-width:980px){[data-testid="stMainBlockContainer"]{padding:.8rem 1rem 3rem!important}.st-key-fyntra-site-header{top:.4rem;border-radius:18px;max-width:none}.dk-page-head h1{font-size:2.4rem}.st-key-fyntra-site-header [data-testid="stCaptionContainer"]{display:none}}
        @media(max-width:640px){[data-testid="stMainBlockContainer"]{padding:.5rem .65rem 2.5rem!important}.st-key-fyntra-site-header{border-radius:14px;padding:.45rem!important}.st-key-fyntra-site-header .stButton>button{font-size:.66rem!important;padding:.25rem .35rem!important}.dk-page-head{padding:.9rem 0 1rem}.dk-page-head h1{font-size:2rem}.f-context-strip{overflow-x:auto;white-space:nowrap}}
        @media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation:none!important;transition:none!important}}
        </style>
        """
    )
