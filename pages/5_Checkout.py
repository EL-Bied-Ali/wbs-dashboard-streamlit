from __future__ import annotations

import html
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from auth_google import _get_logo_data_uri, require_login
from billing_store import access_status, get_account_by_email

_icon_path = Path(__file__).resolve().parents[1] / "Chronoplan_ico.png"
st.set_page_config(
    page_title="ChronoPlan Checkout",
    page_icon=str(_icon_path) if _icon_path.exists() else "CP",
    layout="wide",
)


def _get_secret(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        try:
            value = st.secrets.get(key, "")
        except Exception:
            value = ""
    return value


def _admin_emails() -> set[str]:
    emails = {"ali.el.bied9898@gmail.com"}
    raw = os.environ.get("ADMIN_EMAILS", "")
    if not raw:
        try:
            raw = st.secrets.get("ADMIN_EMAILS", "")
        except Exception:
            raw = ""
    if raw:
        emails.update({e.strip().lower() for e in raw.split(",") if e.strip()})
    return emails


def _is_admin_user(user: dict | None) -> bool:
    if not user:
        return False
    email = (user.get("email") or "").strip().lower()
    return bool(email) and email in _admin_emails()


def _base_url() -> str:
    raw = _get_secret("APP_URL")
    if raw:
        return raw.rstrip("/")
    # Fallback: local dev
    return "http://localhost:8501"


def _paddle_checkout_widget_html(
    token: str,
    env: str,
    price_id: str,
    email: str,
    name: str,
    success_url: str,
    custom_data: dict[str, str],
    button_label: str,
    is_admin: bool,
) -> str:
    # NOTE: Paddle's JS overlay needs a real document head/body. Streamlit
    # components run in a sandboxed iframe, so we load paddle.js in the parent
    # window to avoid the appendChild error we hit previously.
    payload = {
        "token": token,
        "env": env,
        "price_id": price_id,
        "customer": {"email": email, "name": name},
        "custom_data": custom_data,
        "success_url": success_url,
        "button_label": button_label,
    }
    payload_json = json.dumps(payload)
    debug_block = ""
    if is_admin:
        debug_block = """
    <div class="checkout-debug-title">Debug log</div>
    <pre id="paddle-debug" class="checkout-debug"></pre>
        """
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <style>
    body {{
      margin: 0;
      font-family: "Space Grotesk", sans-serif;
      background: transparent;
      color: #e5e7eb;
    }}
    .checkout-wrap {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .checkout-btn {{
      width: 100%;
      padding: 14px 18px;
      border-radius: 999px;
      border: 1px solid rgba(148,163,184,0.25);
      background: linear-gradient(120deg, #6dd5ed, #b47cff);
      color: #0b0f18;
      font-weight: 700;
      font-size: 15px;
      cursor: pointer;
      box-shadow: 0 16px 36px rgba(109,213,237,.35);
    }}
    .checkout-btn:disabled {{
      opacity: 0.6;
      cursor: not-allowed;
    }}
    .checkout-status {{
      font-size: 12px;
      color: #9aa7c0;
    }}
    .checkout-debug-title {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #7f8ea8;
      margin-top: 4px;
    }}
    .checkout-debug {{
      margin: 0;
      padding: 10px 12px;
      min-height: 120px;
      border-radius: 12px;
      border: 1px solid rgba(148,163,184,0.18);
      background: rgba(10, 14, 24, 0.85);
      color: #b7c3d9;
      font-size: 11px;
      line-height: 1.5;
      overflow: auto;
      white-space: pre-wrap;
    }}
  </style>
</head>
<body>
  <div class="checkout-wrap">
    <button id="paddle-checkout-btn" class="checkout-btn">{html.escape(button_label)}</button>
    <div id="paddle-checkout-status" class="checkout-status">Ready to launch checkout.</div>
    {debug_block}
  </div>
  <script>
  (() => {{
    if (!document.head) {{
      const head = document.createElement("head");
      document.documentElement.insertBefore(head, document.documentElement.firstChild);
    }}
    if (!document.body) {{
      const body = document.createElement("body");
      document.documentElement.appendChild(body);
    }}
  }})();
  </script>
  <script>
(() => {{
  const cfg = {payload_json};
  const statusEl = document.getElementById("paddle-checkout-status");
  const btn = document.getElementById("paddle-checkout-btn");
  const debugEl = document.getElementById("paddle-debug");
  let paddleReady = false;

  const showStatus = (message, tone = "#9aa7c0") => {{
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.style.color = tone;
  }};
  const fail = (message) => showStatus(message, "#f87171");
  const log = (message) => {{
    if (!debugEl) return;
    const now = new Date().toISOString();
    debugEl.textContent += now + " " + message + "\\n";
    debugEl.scrollTop = debugEl.scrollHeight;
  }};

  const getHostWindow = () => {{
    try {{
      if (window.parent && window.parent.document) {{
        return window.parent;
      }}
    }} catch (err) {{
      log("Host access blocked: " + (err?.message || err));
    }}
    return window;
  }};

  const host = getHostWindow();
  const hostDoc = host.document || document;

  const ensureHostDom = () => {{
    try {{
      if (!hostDoc.documentElement) {{
        return false;
      }}
      if (!hostDoc.head) {{
        const head = hostDoc.createElement("head");
        hostDoc.documentElement.insertBefore(head, hostDoc.documentElement.firstChild);
      }}
      if (!hostDoc.body) {{
        const body = hostDoc.createElement("body");
        hostDoc.documentElement.appendChild(body);
      }}
      return true;
    }} catch (err) {{
      log("Host DOM error: " + (err?.message || err));
      return false;
    }}
  }};

  const initPaddle = () => {{
    if (!host.Paddle) {{
      return false;
    }}
    if (cfg.env === "sandbox") {{
      host.Paddle.Environment.set("sandbox");
    }} else {{
      host.Paddle.Environment.set("production");
    }}
    try {{
      if (host.Paddle.Initialize) {{
        host.Paddle.Initialize({{ token: cfg.token }});
      }} else if (host.Paddle.Setup) {{
        host.Paddle.Setup({{ token: cfg.token }});
      }} else {{
        fail("Paddle initialization API not available.");
        log("Paddle init failed: missing API.");
        return false;
      }}
      paddleReady = true;
      showStatus("Ready. Click to start checkout.");
      log("Paddle initialized.");
      return true;
    }} catch (err) {{
      const message = err?.message || "Unknown error.";
      fail("Paddle init failed. " + message);
      log("Paddle init failed: " + message);
      return false;
    }}
  }};

  const waitForPaddle = () => {{
    if (initPaddle()) {{
      return;
    }}
    showStatus("Loading Paddle...");
    log("Waiting for Paddle...");
    setTimeout(waitForPaddle, 150);
  }};

  const loadPaddle = () => {{
    if (!ensureHostDom()) {{
      fail("Host DOM unavailable.");
      return;
    }}
    if (host.Paddle) {{
      initPaddle();
      return;
    }}
    const existing = hostDoc.querySelector("script[data-paddle]");
    if (existing) {{
      waitForPaddle();
      return;
    }}
    const script = hostDoc.createElement("script");
    script.src = "https://cdn.paddle.com/paddle/v2/paddle.js";
    script.dataset.paddle = "true";
    script.onload = initPaddle;
    script.onerror = () => fail("Paddle script blocked or unavailable.");
    const target = hostDoc.head || hostDoc.body || hostDoc.documentElement;
    if (!target) {{
      fail("Paddle script target missing.");
      return;
    }}
    target.appendChild(script);
    showStatus("Loading Paddle...");
    log("Appended Paddle script to host document.");
  }};

  const openCheckout = () => {{
    if (!paddleReady) {{
      showStatus("Checkout is still loading. Try again in a moment.", "#fbbf24");
      log("Checkout blocked: Paddle not ready.");
      return;
    }}
    try {{
      host.Paddle.Checkout.open({{
        items: [{{ priceId: cfg.price_id, quantity: 1 }}],
        customer: cfg.customer,
        customData: cfg.custom_data,
        eventCallback: (evt) => {{
          const name = evt?.name || evt?.type || "checkout_event";
          const message = evt?.data?.error?.message || evt?.data?.message || "";
          if (String(name).includes("error")) {{
            fail(`Checkout error: ${{name}} ${{message}}`.trim());
            log(`Checkout error: ${{name}} ${{message}}`.trim());
          }}
        }},
        settings: {{
          displayMode: "overlay",
          theme: "dark",
          successUrl: cfg.success_url
        }}
      }});
      showStatus("Checkout opened. Complete payment to activate your plan.");
      log("Checkout opened in overlay.");
    }} catch (err) {{
      const message = err?.message || "Unknown error.";
      fail("Checkout failed to open. " + message);
      log("Checkout failed: " + message);
    }}
  }};

  if (btn) {{
    btn.addEventListener("click", () => {{
      btn.disabled = true;
      log("Checkout button clicked.");
      openCheckout();
      setTimeout(() => {{
        btn.disabled = false;
      }}, 1200);
    }});
  }}

  log("Config env=" + cfg.env + " price=" + cfg.price_id + " success=" + cfg.success_url);
  log("Host window: " + (host === window ? "iframe" : "parent"));
  loadPaddle();
}})();
  </script>
</body>
</html>
"""


def _create_checkout_url(
    api_token: str,
    env: str,
    price_id: str,
    email: str,
    name: str,
    success_url: str,
    custom_data: dict[str, str],
    api_version: str | None = None,
) -> tuple[str, dict]:
    base = "https://api.paddle.com"
    if env == "sandbox":
        base = "https://sandbox-api.paddle.com"
    payload = {
        "items": [{"price_id": price_id, "quantity": 1}],
        "customer": {"email": email, "name": name},
        "custom_data": custom_data,
        "checkout": {"return_url": success_url},
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/transactions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            **({"Paddle-Version": api_version} if api_version else {}),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            status = resp.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        status = exc.code
    if status < 200 or status >= 300:
        raise RuntimeError(f"Paddle API error ({status}): {raw}")
    data = json.loads(raw)
    checkout = data.get("data", {}).get("checkout", {}) or {}
    url = checkout.get("url") or data.get("data", {}).get("checkout_url")
    if not url:
        raise RuntimeError("Paddle API did not return a checkout URL.")
    return url, data


def _render_checkout_link(
    api_token: str,
    env: str,
    price_id: str,
    email: str,
    name: str,
    success_url: str,
    custom_data: dict[str, str],
    key_prefix: str = "checkout",
) -> None:
    url_key = f"{key_prefix}_url"
    error_key = f"{key_prefix}_error"
    response_key = f"{key_prefix}_response"
    if url_key not in st.session_state:
        st.session_state[url_key] = ""
    if error_key not in st.session_state:
        st.session_state[error_key] = ""
    if response_key not in st.session_state:
        st.session_state[response_key] = None
    if st.button("Generate checkout link", key=f"{key_prefix}_generate"):
        try:
            api_version = _get_secret("PADDLE_API_VERSION") or None
            checkout_url, response = _create_checkout_url(
                api_token=api_token,
                env=env,
                price_id=price_id,
                email=email,
                name=name,
                success_url=success_url,
                custom_data=custom_data,
                api_version=api_version,
            )
            st.session_state[url_key] = checkout_url
            st.session_state[response_key] = response
            st.session_state[error_key] = ""
        except Exception as exc:
            st.session_state[error_key] = str(exc)
            st.session_state[url_key] = ""
            st.session_state[response_key] = None
    if st.session_state[error_key]:
        st.error(st.session_state[error_key])
    checkout_url = st.session_state[url_key]
    if checkout_url:
        app_host = urlparse(_base_url()).netloc
        parsed_checkout = urlparse(checkout_url)
        checkout_host = parsed_checkout.netloc
        if app_host and checkout_host and app_host == checkout_host:
            st.warning(
                "Your Paddle checkout link points to the same domain as the app. "
                "Update Paddle Checkout Settings -> Default payment link to use Paddle's hosted domain "
                "(or a dedicated subdomain like pay.yourdomain.com) so the payment form can load."
            )
        if checkout_host.endswith("paddle.com"):
            checkout_path = parsed_checkout.path
            if checkout_path in {"", "/"}:
                st.warning(
                    "Your Paddle checkout link has no path. In Paddle Checkout Settings, set the "
                    "Default payment link to include /checkout (for example "
                    "https://sandbox-checkout.paddle.com/checkout) so the payment page loads."
                )
        st.markdown(
            f'<a class="checkout-cta" href="{html.escape(checkout_url)}" target="_self">'
            "Open secure checkout</a>",
            unsafe_allow_html=True,
        )
        st.code(checkout_url)
        alt_links: list[str] = []
        if parsed_checkout.path == "/checkout" and parsed_checkout.query:
            alt_links.append(checkout_url.replace("/checkout?", "/checkout/?"))
        if parsed_checkout.path in {"", "/"} and parsed_checkout.query:
            alt_links.append(checkout_url.replace(parsed_checkout.path, "/checkout"))
        if "_ptxn=" in parsed_checkout.query:
            alt_links.append(checkout_url.replace("_ptxn=", "transaction_id="))
        if checkout_host == "sandbox-checkout.paddle.com":
            alt_links.append(checkout_url.replace("sandbox-checkout.paddle.com", "checkout.paddle.com"))
        elif checkout_host == "checkout.paddle.com":
            alt_links.append(checkout_url.replace("checkout.paddle.com", "sandbox-checkout.paddle.com"))
        if alt_links:
            unique_alts = list(dict.fromkeys(alt_links))
            with st.expander("Alternate checkout links (debug)"):
                for alt in unique_alts:
                    st.markdown(
                        f'<a class="checkout-cta" href="{html.escape(alt)}" target="_self">{alt}</a>',
                        unsafe_allow_html=True,
                    )
        if st.session_state[response_key]:
            with st.expander("Checkout response"):
                st.json(st.session_state[response_key])
        st.markdown(
            "<div class='checkout-sub'>You'll be redirected back to billing after payment.</div>",
            unsafe_allow_html=True,
        )


st.set_page_config(
    page_title="ChronoPlan Checkout",
    page_icon="CP",
    layout="wide",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg: #06060d;
  --card: rgba(17, 23, 40, 0.9);
  --card-border: rgba(148, 163, 184, 0.18);
  --text: #e5e7eb;
  --muted: #9aa7c0;
}

html, body {
  background: var(--bg);
}

.stApp {
  background: transparent;
  color: var(--text);
  font-family: "Space Grotesk", sans-serif;
}

section[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"] {
  display: none !important;
}

header, [data-testid="stToolbar"] {
  background: transparent !important;
}

.block-container {
  max-width: 900px;
  padding: 40px 24px 80px;
}

.checkout-shell {
  position: relative;
  z-index: 1;
  padding: 32px;
  border-radius: 24px;
  border: 1px solid var(--card-border);
  background: linear-gradient(130deg, rgba(26, 34, 55, 0.9), rgba(12, 17, 32, 0.95));
  box-shadow: 0 25px 50px rgba(0,0,0,0.4);
}

.checkout-heading {
  font-family: "Fraunces", serif;
  font-size: clamp(28px, 4vw, 40px);
  margin: 0 0 12px;
}

.checkout-sub {
  color: var(--muted);
  margin: 0 0 20px;
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
}

.brand-logo {
  height: 48px;
}

.back-link,
.back-link:link,
.back-link:visited {
  color: var(--muted);
  text-decoration: none;
  font-size: 12px;
  font-weight: 600;
}

.back-link:hover {
  color: var(--text);
}

div.st-key-checkout_back_btn .stButton button {
  background: transparent;
  border: 1px solid transparent;
  color: var(--muted);
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

div.st-key-checkout_back_btn .stButton button:hover {
  color: var(--text);
  background: rgba(15,23,42,0.45);
  border-color: rgba(148,163,184,0.2);
}
.checkout-cta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: linear-gradient(120deg, #6dd5ed, #b47cff);
  color: #0b0f18;
  font-weight: 700;
  font-size: 14px;
  text-decoration: none;
  box-shadow: 0 16px 36px rgba(109,213,237,.35);
}
.checkout-cta:hover {
  filter: brightness(1.04);
}
</style>
""",
    unsafe_allow_html=True,
)

user = require_login()
if not user:
    st.stop()
if not _is_admin_user(user):
    st.switch_page("pages/4_Billing.py")
    st.stop()

account = get_account_by_email(user.get("email", ""))
plan_state = access_status(account)
plan_status = (plan_state.get("status") or "trialing").lower()
is_locked = not plan_state.get("allowed", True)

logo_uri = _get_logo_data_uri()
logo_html = f'<img class="brand-logo" src="{logo_uri}" alt="ChronoPlan logo" />' if logo_uri else ""

with st.container(key="checkout_back_btn"):
    if st.button("<- Back to billing", key="checkout_back_billing"):
        st.switch_page("pages/4_Billing.py")

st.markdown(
    f"""
<div class="checkout-shell">
  <div class="brand-row">{logo_html}<div>ChronoPlan</div></div>
  <div class="checkout-heading">Complete your subscription</div>
  <div class="checkout-sub">You will be redirected back to billing after payment.</div>
</div>
""",
    unsafe_allow_html=True,
)

client_token = _get_secret("PADDLE_CLIENT_TOKEN")
paddle_env = (_get_secret("PADDLE_ENV") or "sandbox").lower()
price_id = _get_secret("PADDLE_PRICE_EUR" if paddle_env == "production" else "PADDLE_PRICE_EUR_SANDBOX")
if not price_id:
    price_id = _get_secret("PADDLE_PRICE_EUR")
paddle_api_token = _get_secret("PADDLE_API_TOKEN")
checkout_ready = bool(price_id)

custom_data: dict[str, str] = {"email": user.get("email", "")}
if account:
    if account.get("id") is not None:
        custom_data["account_id"] = str(account.get("id"))
    if account.get("referral_code"):
        custom_data["referral_code"] = str(account.get("referral_code"))
    if account.get("referrer_code"):
        custom_data["referrer_code"] = str(account.get("referrer_code"))

if plan_status == "active" and not is_locked:
    st.markdown(
        "<div class='checkout-sub'>Your subscription is active. Return to billing to manage details.</div>",
        unsafe_allow_html=True,
    )
else:
    success_url = f"{_base_url()}/Billing?checkout=success"
    if checkout_ready and client_token:
        components.html(
            _paddle_checkout_widget_html(
                token=client_token,
                env=paddle_env,
                price_id=price_id,
                email=user.get("email", ""),
                name=user.get("name", "") or user.get("email", ""),
                success_url=success_url,
                custom_data=custom_data,
                button_label="Start subscription",
                is_admin=_is_admin_user(user),
            ),
            height=320,
        )
        if paddle_api_token:
            with st.expander("Secure checkout link (fallback)"):
                _render_checkout_link(
                    api_token=paddle_api_token,
                    env=paddle_env,
                    price_id=price_id,
                    email=user.get("email", ""),
                    name=user.get("name", "") or user.get("email", ""),
                    success_url=success_url,
                    custom_data=custom_data,
                    key_prefix="checkout_fallback",
                )
    elif checkout_ready and paddle_api_token:
        _render_checkout_link(
            api_token=paddle_api_token,
            env=paddle_env,
            price_id=price_id,
            email=user.get("email", ""),
            name=user.get("name", "") or user.get("email", ""),
            success_url=success_url,
            custom_data=custom_data,
        )
    else:
        st.markdown(
            "<div class='checkout-sub'>Checkout is unavailable. Missing Paddle settings.</div>",
            unsafe_allow_html=True,
        )
