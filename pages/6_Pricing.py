from __future__ import annotations

import streamlit as st
from pathlib import Path


_icon_path = Path(__file__).resolve().parents[1] / "Chronoplan_ico.png"
st.set_page_config(
    page_title="ChronoPlan Pricing",
    page_icon=str(_icon_path) if _icon_path.exists() else "CP",
    layout="wide",
)
st.markdown("<style>[data-testid='stSidebarNav']{display:none !important;}</style>", unsafe_allow_html=True)


def _hero():
    st.markdown(
        """
        <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:16px;">
          <div style="font-size:14px;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;">Pricing</div>
          <div style="font-size:30px;font-weight:700;">Keep your dashboards live.</div>
          <div style="color:#94a3b8;">Start with trial access, upgrade to unlock uploads, dashboards, and support.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _plan_card(title, price, period, features, cta_label, cta_page, highlight=False):
    border = "#0ea5e9" if highlight else "rgba(148,163,184,0.25)"
    bg = "linear-gradient(120deg, #0ea5e9, #8b5cf6)" if highlight else "rgba(15,23,42,0.35)"
    text = "#0b0f18" if highlight else "#e2e8f0"
    st.markdown(
        f"""
        <div style="
            border:1px solid {border};
            border-radius:16px;
            padding:18px;
            background:{bg};
            color:{text};
            display:flex;
            flex-direction:column;
            gap:12px;
            box-shadow:0 12px 30px rgba(0,0,0,0.15);
        ">
          <div style="font-size:18px;font-weight:700;">{title}</div>
          <div style="font-size:26px;font-weight:800;">{price}<span style="font-size:13px;font-weight:500;"> {period}</span></div>
          <ul style="margin:0;padding-left:18px;color:{text};">
            {''.join([f'<li>{f}</li>' for f in features])}
          </ul>
          <div>
            <a href="{cta_page}" style="
                text-decoration:none;
                display:inline-block;
                padding:10px 14px;
                border-radius:10px;
                background:{'#f8fafc' if highlight else '#0ea5e9'};
                color:{'#0f172a' if highlight else '#0b1221'};
                font-weight:700;
            ">{cta_label}</a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.session_state["_current_page"] = "Pricing"
    _hero()
    col1, col2 = st.columns(2, gap="large")
    with col1:
        _plan_card(
            "Trial",
            "Free",
            "for 15 days",
            [
                "All features unlocked during trial",
                "Upload and view dashboards",
                "No credit card required",
            ],
            "Go to Billing",
            "pages/4_Billing.py",
            highlight=False,
        )
    with col2:
        _plan_card(
            "Premium",
            "€20",
            "per month",
            [
                "Unlimited dashboards & uploads",
                "Priority support",
                "Billing portal for invoices",
            ],
            "Start subscription",
            "pages/5_Checkout.py",
            highlight=True,
        )
    st.markdown("---")
    st.caption("Questions? Contact support at support@chronoplan.app")


if __name__ == "__main__":
    main()
