"""Small reusable presentation pieces; all user text is HTML-escaped."""
from html import escape
from pathlib import Path
import math
import altair as alt
import streamlit as st

MINT = "#68E8B6"
GOLD = "#DCC58B"

def rupees(value,decimals=False):
    if value is None or not math.isfinite(float(value)):
        return "—"
    negative = float(value)<0
    text = f"{abs(float(value)):.2f}"
    whole,fraction = text.split(".")
    if len(whole)>3:
        end,head = whole[-3:],whole[:-3]
        groups = []
        while head:
            groups.insert(0,head[-2:])
            head = head[:-2]
        whole = ",".join(groups+[end])
    return ("−" if negative else "")+"₹"+whole+("."+fraction if decimals else "")

def style():
    st.html("""<style>
    .fyntra-brand{display:flex;align-items:center;gap:12px;font-size:24px;font-weight:800;letter-spacing:.14em;color:#f4f1e8}
    .fyntra-brand svg{flex-shrink:0}
    .f-kicker{color:#86aa9b;font-size:11px;letter-spacing:.18em;text-transform:uppercase;margin-bottom:10px}
    .f-hero{border:1px solid #355c4c;border-radius:20px;padding:26px 28px;background:linear-gradient(115deg,#18372a,#14231e 70%);position:relative;overflow:hidden}
    .f-hero::after{content:"";position:absolute;width:40%;height:220px;right:-5%;top:-25px;border:1px solid #69e7b530;transform:rotate(-30deg);border-radius:30%;pointer-events:none;animation:flow 16s ease-in-out infinite}
    .f-hero h2{font-size:clamp(24px,3vw,38px);font-weight:550;margin:0 0 8px;letter-spacing:-.04em}
    .f-hero p{color:#b2c6ba;margin:0;font-size:14px;max-width:620px}
    .f-pill{display:inline-block;border:1px solid #3c6251;border-radius:30px;padding:5px 10px;font-size:11px;color:#91e2bc;background:#163023}
    .f-row{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:13px 0;border-bottom:1px solid #26382f}
    .f-row:last-child{border-bottom:0}
    .f-row strong{font-size:14px;overflow-wrap:anywhere}
    .f-row small{display:block;color:#8eaa9b;font-size:11px;margin-top:4px}
    .f-amount{font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}
    .f-positive{color:#80dcb0}.f-negative{color:#eed4a9}
    .f-foot{font-size:11px;color:#789184;margin-top:24px;line-height:1.7}
    [data-testid="stMetricValue"]{font-variant-numeric:tabular-nums}
    @keyframes flow{50%{transform:rotate(-25deg) translateX(-10px)}}
    @media(prefers-reduced-motion:reduce){.f-hero::after{animation:none}}
    @media(max-width:640px){.f-hero{padding:20px}.f-row{gap:10px}.f-amount{font-size:14px}}
    </style>""")

def brand():
    st.image(str(Path(__file__).parent/"assets"/"wordmark.svg"),width=210)


def hero(title,subtitle,kicker="YOUR MONEY, WITH CLARITY"):
    st.html(f'<section class="f-hero"><div class="f-kicker">{escape(kicker)}</div><h2>{escape(title)}</h2><p>{escape(subtitle)}</p></section>')

def metrics(items):
    # Native columns stack at narrow widths instead of clipping number cards.
    for offset in range(0,len(items),4):
        batch=items[offset:offset+4]
        for column,(label,value,help_text) in zip(st.columns(len(batch)),batch):
            column.metric(label,value,border=True,help=help_text)


def rows(frame,limit=6):
    for r in frame.head(limit).to_dict("records"):
        kind=r.get("kind","expense")
        label=r.get("merchant") or r.get("name") or r.get("category","Transaction")
        on=str(r.get("date",""))[:10]
        subtitle=f"{r.get('category',kind)} · {on}"
        amount=rupees(r.get("amount",0))
        sign="+" if kind=="income" else ("↔ " if kind=="transfer" else "−")
        css="f-positive" if kind=="income" else "f-negative"
        st.html(f'<div class="f-row"><div><strong>{escape(str(label))}</strong><small>{escape(subtitle)}</small></div><span class="f-amount {css}">{sign}{escape(amount)}</span></div>')

def chart(data,x,y,kind="bar",color=MINT,height=260,title=None):
    if data.empty:
        st.caption("Your chart appears when you add records.")
        return
    c=alt.Chart(data)
    if kind=="line":
        c=c.mark_line(color=color,strokeWidth=2.5,point=True)
    elif kind=="area":
        c=c.mark_area(color=color,opacity=.22,line={"color":color,"strokeWidth":2})
    else:
        c=c.mark_bar(color=color,cornerRadiusTopLeft=4,cornerRadiusTopRight=4)
    c=c.encode(x=alt.X(x,title=None),y=alt.Y(y,title="₹",axis=alt.Axis(format="~s")),tooltip=[x,y]).properties(height=height)
    st.altair_chart(c,width="stretch",alt=title or "Financial data from your recorded ledger")

def progress_card(name,value,target,caption=""):
    pct=0 if target<=0 else min(1,max(0,value/target))
    with st.container(border=True):
        st.markdown("**"+str(name).replace("*","")+"**")
        st.metric("Progress",rupees(value),label_visibility="collapsed")
        st.progress(pct)
        st.caption(f"{pct*100:.0f}% of {rupees(target)} · {caption}")

