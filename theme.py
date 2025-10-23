import streamlit as st

CSS = """
<style>
/* === Fond général animé === */
body {
  background: radial-gradient(circle at 20% 20%, #0d1a2f, #060b14 80%);
  animation: bgShift 20s ease-in-out infinite alternate;
}
@keyframes bgShift {
  from { background-position: 0% 50%; }
  to   { background-position: 100% 50%; }
}

/* === Glow global et police === */
*{font-family: 'Segoe UI', Roboto, sans-serif;}
:root{
  --bg:#0b1220; --glass:#0f172a; --glass2:#0b1224; --line:#1f2a44;
  --text:#e5e7eb; --muted:#94a3b8; --ok:#22c55e; --bad:#ef4444; --accent:#60a5fa;
}

/* === Hero (N1) néon === */
.hero{
  position:relative;
  background:linear-gradient(145deg,rgba(17,28,50,.95),rgba(10,18,38,.95));
  border:1px solid rgba(96,165,250,.4);
  border-radius:18px;
  padding:22px 26px; margin:10px 0 18px;
  box-shadow:0 0 18px rgba(59,130,246,.25), inset 0 0 20px rgba(59,130,246,.15);
  animation: fadeSlideUp .6s ease, neonPulse 6s ease-in-out infinite;
}
@keyframes neonPulse {
  0%,100% { box-shadow:0 0 20px rgba(59,130,246,.25), inset 0 0 20px rgba(59,130,246,.15); }
  50% { box-shadow:0 0 40px rgba(96,165,250,.55), inset 0 0 28px rgba(59,130,246,.25); }
}
.hero .title{
  font-size:2.2rem; font-weight:800; color:#f0f7ff;
  text-shadow:0 0 22px rgba(96,165,250,.45);
}

/* === Section N2 === */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel){
  background:linear-gradient(180deg,#101a35,#0b1326);
  border-radius:14px; border:1px solid rgba(59,130,246,.35);
  box-shadow:0 0 14px rgba(59,130,246,.2) inset;
  padding:14px 16px; margin:10px 0 18px;
  animation: fadeSlideUp .6s ease .05s both;
}

/* === Table N3 en verre === */
.table-card{
  background:rgba(17,25,45,.65);
  backdrop-filter:blur(8px);
  border:1px solid rgba(96,165,250,.3);
  border-radius:14px; padding:12px; margin:10px 0;
  box-shadow:0 0 18px rgba(0,0,0,.25), inset 0 0 10px rgba(59,130,246,.15);
  animation: fadeSlideUp .6s ease .1s both;
}

/* === Barres dynamiques === */
@keyframes growBar { from{width:0} to{width:var(--to,0%)} }
.mfill.anim{animation:growBar .9s cubic-bezier(.25,.8,.25,1) both;}
.mbar::after{
  content:""; position:absolute; top:0; bottom:0; width:40%;
  background:linear-gradient(90deg, transparent, rgba(255,255,255,.18), transparent);
  animation: sheen 2.4s ease-in-out infinite;
}
@keyframes sheen{
  0%{transform:translateX(-100%);opacity:0}
  25%{opacity:.25}
  50%{opacity:.15}
  100%{transform:translateX(100%);opacity:0}
}

/* === Dot lumineux === */
.dot{
  width:10px; height:10px; border-radius:999px;
  background:radial-gradient(circle,#93c5fd 10%,#3b82f6 90%);
  box-shadow:0 0 12px #60a5fa; animation:pulseDot 2s ease-in-out infinite;
}
@keyframes pulseDot{0%,100%{transform:scale(1)}50%{transform:scale(1.3)}}

/* === Boutons futuristes === */
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton button{
  border-radius:10px;
  background:linear-gradient(145deg,#17233c,#0e182d);
  border:1px solid rgba(96,165,250,.6);
  color:#e5f0ff; font-weight:800; font-size:16px;
  box-shadow:0 0 14px rgba(59,130,246,.35);
  transition:all .25s ease;
}
div[data-testid="stVerticalBlock"]:has(.n2-block-sentinel) .stButton button:hover{
  transform:translateY(-2px) scale(1.06);
  box-shadow:0 0 20px rgba(125,211,252,.55);
  border-color:rgba(125,211,252,.9);
}

/* === Apparitions === */
@keyframes fadeSlideUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
</style>
"""

def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)
