from __future__ import annotations

import html
import json
import os
import time
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st
import streamlit.components.v1 as components

from auth_google import _get_logo_data_uri, require_login
from billing_store import (
    access_status,
    create_portal_session,
    fetch_remote_transactions,
    force_sync_account_from_remote,
    get_account_by_email,
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
    host = st.get_option("server.address") or "localhost"
    port = st.get_option("server.port") or 8501
    return f"http://{host}:{port}"


def _portal_return_url() -> str | None:
    raw = _get_secret("BILLING_PORTAL_RETURN_URL")
    if not raw:
        return None
    candidate = raw.strip()
    if not candidate:
        return None
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None
    if parsed.scheme != "https":
        return None
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1"}:
        return None
    return candidate


def _get_portal_link(
    email: str,
    account_id: int | None,
    ttl_seconds: int = 300,
) -> tuple[str | None, str | None]:
    cache = st.session_state.get("billing_portal_cache", {})
    now = time.time()
    cached_email = cache.get("email")
    cached_at = cache.get("created_at", 0)
    cached_url = cache.get("url")
    cached_error = cache.get("error")
    if cached_email == email and (now - cached_at) < ttl_seconds:
        return cached_url, cached_error
    url, error = create_portal_session(
        email,
        account_id=account_id,
        return_url=_portal_return_url(),
    )
    st.session_state["billing_portal_cache"] = {
        "email": email,
        "created_at": now,
        "url": url,
        "error": error,
    }
    return url, error


def _rerun() -> None:
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()


def _get_query_params() -> dict:
    try:
        return st.query_params  # type: ignore[attr-defined]
    except AttributeError:
        return st.experimental_get_query_params()


def _query_value(params: dict, key: str) -> str | None:
    val = params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    return val


def _format_tx_date(value: str | None) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    return dt.strftime("%b %d, %Y")


def _format_tx_amount(amount: str | int | None, currency: str | None) -> str:
    if amount is None:
        return "-"
    try:
        raw = int(amount)
    except (TypeError, ValueError):
        return "-"
    value = raw / 100
    label = currency or ""
    return f"{value:,.2f} {label}".strip()


def _tx_status_label(status: str | None) -> tuple[str, str]:
    normalized = (status or "").lower()
    if normalized in {"paid", "completed", "billed"}:
        return "Paid", "paid"
    if normalized in {"canceled", "payment_failed", "past_due", "revised"}:
        return "Action needed", "issue"
    if normalized in {"ready", "created", "updated", "draft"}:
        return "Pending", "pending"
    return "Pending", "pending"


def _paddle_overlay_widget_html(
    token: str,
    env: str,
    price_id: str,
    email: str,
    name: str,
    success_url: str,
    custom_data: dict[str, str],
    button_label: str,
) -> str:
    # NOTE: Streamlit components render inside a sandboxed iframe. Paddle's SDK
    # expects to append its script to document.head, which can be undefined in
    # that iframe. Loading paddle.js in the parent window and calling
    # Checkout.open on the parent avoids the appendChild error we hit before.
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
    return f"""
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
    gap: 10px;
  }}
  .checkout-btn {{
    width: 100%;
    padding: 12px 18px;
    border-radius: 999px;
    border: 1px solid rgba(148,163,184,0.25);
    background: linear-gradient(120deg, #6dd5ed, #b47cff);
    color: #0b0f18;
    font-weight: 700;
    font-size: 14px;
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
</style>
<div class="checkout-wrap">
  <button id="paddle-checkout-btn" class="checkout-btn">{html.escape(button_label)}</button>
  <div id="paddle-checkout-status" class="checkout-status">Ready to launch checkout.</div>
</div>
<script>
(() => {{
  const cfg = {payload_json};
  const statusEl = document.getElementById("paddle-checkout-status");
  const btn = document.getElementById("paddle-checkout-btn");
  let paddleReady = false;

  const showStatus = (message, tone = "#9aa7c0") => {{
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.style.color = tone;
  }};
  const fail = (message) => showStatus(message, "#f87171");

  const getHostWindow = () => {{
    try {{
      if (window.parent && window.parent.document) {{
        return window.parent;
      }}
    }} catch (err) {{}}
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
        return false;
      }}
      paddleReady = true;
      showStatus("Ready. Click to start checkout.");
      return true;
    }} catch (err) {{
      fail("Paddle init failed. " + (err?.message || "Unknown error."));
      return false;
    }}
  }};

  const waitForPaddle = () => {{
    if (initPaddle()) {{
      return;
    }}
    showStatus("Loading Paddle...");
    setTimeout(waitForPaddle, 150);
  }};

  const loadPaddle = () => {{
    if (!ensureHostDom()) {{
      fail("Checkout failed to initialize.");
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
  }};

  const openCheckout = () => {{
    if (!paddleReady) {{
      showStatus("Checkout is still loading. Try again in a moment.", "#fbbf24");
      return;
    }}
    try {{
      host.Paddle.Checkout.open({{
        items: [{{ priceId: cfg.price_id, quantity: 1 }}],
        customer: cfg.customer,
        customData: cfg.custom_data,
        settings: {{
          displayMode: "overlay",
          theme: "dark",
          successUrl: cfg.success_url
        }}
      }});
      showStatus("Checkout opened. Complete payment to activate your plan.");
    }} catch (err) {{
      fail("Checkout failed to open. " + (err?.message || "Unknown error."));
    }}
  }};

  if (btn) {{
    btn.addEventListener("click", () => {{
      btn.disabled = true;
      openCheckout();
      setTimeout(() => {{
        btn.disabled = false;
      }}, 1200);
    }});
  }}

  loadPaddle();
}})();
</script>
"""


def _paddle_checkout_html(
    token: str,
    env: str,
    price_id: str,
    email: str,
    name: str,
    success_url: str,
    custom_data: dict[str, str],
    display_mode: str = "overlay",
    frame_target: str | None = None,
    frame_initial_height: int = 680,
) -> str:
    if display_mode == "inline" and not frame_target:
        raise ValueError("frame_target required for inline checkout")
    payload = {
        "token": token,
        "env": env,
        "price_id": price_id,
        "customer": {"email": email, "name": name},
        "custom_data": custom_data,
        "success_url": success_url,
        "display_mode": display_mode,
        "frame_target": frame_target,
        "frame_initial_height": frame_initial_height,
    }
    payload_json = json.dumps(payload)
    target_html = ""
    status_id = "paddle-checkout-status"
    if display_mode == "inline":
        target_html = (
            f'<div id="{frame_target}" style="min-height:{frame_initial_height}px;"></div>'
            f'<div id="{status_id}" style="margin-top:10px;color:#9aa7c0;font-size:12px;">'
            "Loading checkout..."
            "</div>"
        )
    return f"""
{target_html}
<script>
(() => {{
  const cfg = {payload_json};
  const statusEl = document.getElementById("{status_id}");
  const showStatus = (message, tone = "#9aa7c0") => {{
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.style.color = tone;
  }};
  const fail = (message) => showStatus(message, "#f87171");

  const loadPaddle = () => {{
    if (!window.Paddle) {{
      fail("Paddle failed to load. Check your network connection.");
      return;
    }}
    if (cfg.env === "sandbox") {{
      window.Paddle.Environment.set("sandbox");
    }} else {{
      window.Paddle.Environment.set("production");
    }}
    try {{
      if (window.Paddle.Initialize) {{
        window.Paddle.Initialize({{ token: cfg.token }});
      }} else if (window.Paddle.Setup) {{
        window.Paddle.Setup({{ token: cfg.token }});
      }} else {{
        fail("Paddle initialization API not available.");
        return;
      }}
      window.Paddle.Checkout.open({{
        items: [{{ priceId: cfg.price_id, quantity: 1 }}],
        customer: cfg.customer,
        customData: cfg.custom_data,
        settings: {{
          displayMode: cfg.display_mode,
          frameTarget: cfg.frame_target || undefined,
          frameInitialHeight: cfg.frame_initial_height || undefined,
          frameStyle: cfg.display_mode === "inline" ? "width: 100%; min-height: 640px; border: 0;" : undefined,
          theme: "dark",
          successUrl: cfg.success_url
        }}
      }});
      showStatus("Checkout loaded. Complete payment to activate your plan.");
    }} catch (err) {{
      fail("Checkout failed to open. " + (err?.message || "Unknown error."));
    }}
  }};

  const existing = document.querySelector("script[data-paddle]");
  if (existing && window.Paddle) {{
    loadPaddle();
  }} else {{
    const script = document.createElement("script");
    script.src = "https://cdn.paddle.com/paddle/v2/paddle.js";
    script.dataset.paddle = "true";
    script.onload = loadPaddle;
    script.onerror = () => fail("Paddle script blocked or unavailable.");
    const target = document.head || document.body || document.documentElement;
    if (!target) {{
      fail("Checkout failed to initialize (no script target).");
      return;
    }}
    target.appendChild(script);
  }}
}})();
</script>
"""


def _paddle_checkout_widget_html(
    token: str,
    env: str,
    price_id: str,
    email: str,
    name: str,
    success_url: str,
    custom_data: dict[str, str],
    button_label: str,
    display_mode: str = "overlay",
    frame_target: str | None = None,
    frame_initial_height: int = 680,
) -> str:
    if display_mode == "inline" and not frame_target:
        raise ValueError("frame_target required for inline checkout")
    payload = {
        "token": token,
        "env": env,
        "price_id": price_id,
        "customer": {"email": email, "name": name},
        "custom_data": custom_data,
        "success_url": success_url,
        "display_mode": display_mode,
        "frame_target": frame_target,
        "frame_initial_height": frame_initial_height,
        "button_label": button_label,
    }
    payload_json = json.dumps(payload)
    target_html = ""
    if display_mode == "inline":
        target_html = f'<div id="{frame_target}" style="min-height:{frame_initial_height}px;"></div>'
    return f"""
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
  .checkout-actions {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .checkout-btn {{
    width: 100%;
    padding: 12px 18px;
    border-radius: 999px;
    border: 1px solid rgba(148,163,184,0.25);
    background: linear-gradient(120deg, #6dd5ed, #b47cff);
    color: #0b0f18;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    box-shadow: 0 16px 36px rgba(109,213,237,.35);
  }}
  .checkout-btn:disabled {{
    opacity: 0.6;
    cursor: not-allowed;
  }}
  .checkout-debug-toggle {{
    background: transparent;
    border: 1px dashed rgba(148,163,184,0.3);
    color: #9aa7c0;
    font-size: 11px;
    padding: 6px 10px;
    border-radius: 10px;
    cursor: pointer;
  }}
  .checkout-status {{
    font-size: 12px;
    color: #9aa7c0;
  }}
  .checkout-debug {{
    background: rgba(12,17,32,0.9);
    border: 1px solid rgba(148,163,184,0.25);
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 11px;
    color: #cbd5f5;
    max-height: 180px;
    overflow: auto;
    display: none;
    white-space: pre-wrap;
  }}
</style>
<div class="checkout-wrap">
  <div class="checkout-actions">
    <button id="paddle-checkout-btn" class="checkout-btn">{html.escape(button_label)}</button>
    <button id="paddle-debug-toggle" class="checkout-debug-toggle" type="button">Show debug log</button>
  </div>
  <div id="paddle-checkout-status" class="checkout-status">Checkout is ready.</div>
  <pre id="paddle-debug" class="checkout-debug"></pre>
  {target_html}
</div>
<script>
(() => {{
  const cfg = {payload_json};
  const statusEl = document.getElementById("paddle-checkout-status");
  const btn = document.getElementById("paddle-checkout-btn");
  const debugEl = document.getElementById("paddle-debug");
  const debugToggle = document.getElementById("paddle-debug-toggle");
  let paddleReady = false;

  const showStatus = (message, tone = "#9aa7c0") => {{
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.style.color = tone;
  }};
  const log = (message) => {{
    if (!debugEl) return;
    const stamp = new Date().toISOString();
    debugEl.textContent += `${{stamp}} ${{message}}\\n`;
  }};
  const fail = (message) => {{
    showStatus(message, "#f87171");
    log(`ERROR: ${{message}}`);
  }};

  if (debugToggle && debugEl) {{
    debugToggle.addEventListener("click", () => {{
      const isHidden = debugEl.style.display === "none";
      debugEl.style.display = isHidden ? "block" : "none";
      debugToggle.textContent = isHidden ? "Hide debug log" : "Show debug log";
    }});
  }}

  window.addEventListener("message", (event) => {{
    if (!event) return;
    if (typeof event.origin === "string" && event.origin.includes("paddle")) {{
      try {{
        const payload = JSON.stringify(event.data);
        log(`Paddle message: ${{payload.slice(0, 500)}}`);
      }} catch (err) {{
        log("Paddle message received (unserializable).");
      }}
    }}
  }});

  const ensureDom = () => {{
    if (!document.documentElement) {{
      log("DOM not ready yet.");
      return false;
    }}
    if (!document.head) {{
      const head = document.createElement("head");
      document.documentElement.insertBefore(head, document.documentElement.firstChild);
      log("Injected <head>.");
    }}
    if (!document.body) {{
      const body = document.createElement("body");
      document.documentElement.appendChild(body);
      log("Injected <body>.");
    }}
    return true;
  }};

  const ensureTarget = () => {{
    if (cfg.display_mode !== "inline" || !cfg.frame_target) {{
      return true;
    }}
    if (!ensureDom()) {{
      return false;
    }}
    let target = document.getElementById(cfg.frame_target);
    if (!target && document.body) {{
      target = document.createElement("div");
      target.id = cfg.frame_target;
      target.style.minHeight = `${{cfg.frame_initial_height || 640}}px`;
      document.body.appendChild(target);
      log(`Created target div #${{cfg.frame_target}}`);
    }}
    return Boolean(target);
  }};

  const initPaddle = () => {{
    if (!window.Paddle) {{
      fail("Paddle failed to load. Check your network connection.");
      return;
    }}
    if (cfg.env === "sandbox") {{
      window.Paddle.Environment.set("sandbox");
    }} else {{
      window.Paddle.Environment.set("production");
    }}
    try {{
      if (window.Paddle.Initialize) {{
        window.Paddle.Initialize({{ token: cfg.token }});
      }} else if (window.Paddle.Setup) {{
        window.Paddle.Setup({{ token: cfg.token }});
      }} else {{
        fail("Paddle initialization API not available.");
        return;
      }}
      paddleReady = true;
      log("Paddle initialized.");
      showStatus("Ready. Click the button to launch checkout.");
    }} catch (err) {{
      fail("Paddle init failed. " + (err?.message || "Unknown error."));
    }}
  }};

  const ensurePaddle = () => {{
    const existing = document.querySelector("script[data-paddle]");
    if (existing && window.Paddle) {{
      log("Paddle script already loaded.");
      initPaddle();
      return;
    }}
    const script = document.createElement("script");
    script.src = "https://cdn.paddle.com/paddle/v2/paddle.js";
    script.dataset.paddle = "true";
    script.onload = initPaddle;
    script.onerror = () => fail("Paddle script blocked or unavailable.");
    const target = document.head || document.body || document.documentElement;
    if (!target) {{
      fail("Checkout failed to initialize (no script target).");
      return;
    }}
    target.appendChild(script);
    log("Appended Paddle script tag.");
    showStatus("Loading Paddle...");
  }};

  const openInlineCheckout = () => {{
    const handleEvent = (evt) => {{
      const name = evt?.name || evt?.type || "checkout_event";
      const message = evt?.data?.error?.message || evt?.data?.message || "";
      const lowerName = String(name).toLowerCase();
      if (lowerName.includes("error")) {{
        fail(`Checkout error: ${{name}} ${{message}}`.trim());
        return;
      }}
      showStatus(`Checkout event: ${{name}} ${{message}}`.trim());
      log(`Event: ${{name}} ${{message}}`.trim());
      if (
        lowerName.includes("completed")
        || lowerName.includes("success")
        || lowerName.includes("activated")
      ) {{
        window.top.location.href = cfg.success_url;
      }}
    }};
    log("Opening inline checkout...");
    window.Paddle.Checkout.open({{
      items: [{{ priceId: cfg.price_id, quantity: 1 }}],
      customer: cfg.customer,
      customData: cfg.custom_data,
      eventCallback: handleEvent,
      settings: {{
        displayMode: "inline",
        frameTarget: cfg.frame_target || undefined,
        frameInitialHeight: cfg.frame_initial_height || undefined,
        frameStyle: "width: 100%; min-height: 640px; border: 0;",
        theme: "dark",
        successUrl: cfg.success_url,
        eventCallback: handleEvent
      }}
    }});
  }};

  const openOverlayCheckout = () => {{
    const handleEvent = (evt) => {{
      const name = evt?.name || evt?.type || "checkout_event";
      const message = evt?.data?.error?.message || evt?.data?.message || "";
      const lowerName = String(name).toLowerCase();
      if (lowerName.includes("error")) {{
        fail(`Checkout error: ${{name}} ${{message}}`.trim());
        return;
      }}
      showStatus(`Checkout event: ${{name}} ${{message}}`.trim());
      log(`Event: ${{name}} ${{message}}`.trim());
      if (
        lowerName.includes("completed")
        || lowerName.includes("success")
        || lowerName.includes("activated")
      ) {{
        window.top.location.href = cfg.success_url;
      }}
    }};
    log("Opening overlay checkout...");
    window.Paddle.Checkout.open({{
      items: [{{ priceId: cfg.price_id, quantity: 1 }}],
      customer: cfg.customer,
      customData: cfg.custom_data,
      eventCallback: handleEvent,
      settings: {{
        displayMode: "overlay",
        theme: "dark",
        successUrl: cfg.success_url,
        eventCallback: handleEvent
      }}
    }});
  }};

  const openCheckout = () => {{
    if (!paddleReady) {{
      showStatus("Checkout is still loading. Try again in a moment.", "#fbbf24");
      return;
    }}
    try {{
      if (cfg.display_mode === "inline") {{
        const targetOk = ensureTarget();
        if (!targetOk) {{
          fail("Checkout target unavailable. Retrying with overlay.");
          openOverlayCheckout();
          showStatus("Overlay checkout opened. Complete payment to activate your plan.");
          return;
        }}
        openInlineCheckout();
        showStatus("Checkout opened. Complete payment to activate your plan.");
      }} else {{
        openOverlayCheckout();
        showStatus("Overlay checkout opened. Complete payment to activate your plan.");
      }}
    }} catch (err) {{
      const message = err?.message || "Unknown error.";
      if (cfg.display_mode === "inline") {{
        showStatus("Inline checkout failed. Trying overlay...", "#fbbf24");
        try {{
          openOverlayCheckout();
          showStatus("Overlay checkout opened. Complete payment to activate your plan.");
          return;
        }} catch (overlayErr) {{
          fail("Checkout failed to open. " + (overlayErr?.message || message));
          return;
        }}
      }}
      fail("Checkout failed to open. " + message);
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

  ensureDom();
  ensureTarget();
  ensurePaddle();
  log(`Config env=${{cfg.env}} price=${{cfg.price_id}} success=${{cfg.success_url}}`);
}})();
</script>
"""


st.set_page_config(
    page_title="ChronoPlan Billing",
    page_icon="CP",
    layout="wide",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
  --bg: #06060d;
  --bg-2: #0b0f1f;
  --card: rgba(17, 23, 40, 0.88);
  --card-border: rgba(148, 163, 184, 0.18);
  --text: #e5e7eb;
  --muted: #9aa7c0;
  --accent: #6dd5ed;
  --accent-2: #b47cff;
  --success: #22c55e;
  --warning: #fbbf24;
  --danger: #f87171;
}

html, body {
  background: var(--bg);
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  background:
    radial-gradient(1200px 600px at 10% -20%, rgba(79,70,229,.28), transparent 65%),
    radial-gradient(900px 600px at 90% 15%, rgba(109,40,217,.28), transparent 60%),
    radial-gradient(700px 500px at 20% 110%, rgba(14,165,233,.22), transparent 60%);
  pointer-events: none;
  z-index: 0;
}

body::after {
  content: "";
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px);
  background-size: 140px 140px;
  opacity: 0.1;
  pointer-events: none;
  z-index: 0;
}

.stApp {
  background: transparent;
  color: var(--text);
  font-family: "Space Grotesk", sans-serif;
}

header, [data-testid="stToolbar"] {
  background: transparent !important;
}

section[data-testid="stSidebar"],
[data-testid="stSidebarNav"],
[data-testid="collapsedControl"] {
  display: none !important;
}

.block-container {
  max-width: 1200px;
  padding: 42px 28px 96px;
}

.billing-top {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 36px;
}

.brand-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.back-link,
.back-link:link,
.back-link:visited,
.back-link:active {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted) !important;
  text-decoration: none !important;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid transparent;
}

.back-link:hover {
  color: var(--text) !important;
  background: rgba(15,23,42,0.45);
  border-color: rgba(148,163,184,0.2);
  text-decoration: none !important;
}

div.st-key-billing_back_btn .stButton button {
  background: transparent;
  border: 1px solid transparent;
  color: var(--muted);
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

div.st-key-billing_back_btn .stButton button:hover {
  color: var(--text);
  background: rgba(15,23,42,0.45);
  border-color: rgba(148,163,184,0.2);
}

.brand {
  display: flex;
  align-items: center;
  gap: 16px;
}

.brand-logo {
  height: 84px;
  width: auto;
  display: block;
}

.brand-name {
  font-family: "Fraunces", serif;
  font-size: 28px;
  margin: 0 0 4px;
}

.brand-sub {
  font-size: 12px;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.2em;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.account-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.6);
}

.account-avatar {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.35);
  object-fit: cover;
}

.account-avatar.fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(109,213,237,0.12);
  font-weight: 700;
  color: var(--text);
}

.account-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.account-name {
  font-size: 13px;
  font-weight: 600;
}

.account-email {
  font-size: 11px;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.status-pill {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.5);
  color: var(--text);
}

.status-pill.premium {
  border-color: rgba(34,197,94,0.35);
  background: rgba(34,197,94,0.12);
  color: var(--success);
}

.status-pill.trial {
  border-color: rgba(251,191,36,0.35);
  background: rgba(251,191,36,0.12);
  color: var(--warning);
}

.status-pill.locked {
  border-color: rgba(248,113,113,0.35);
  background: rgba(248,113,113,0.12);
  color: var(--danger);
}

.history-card {
  margin-top: 18px;
  padding: 20px 22px;
  border-radius: 18px;
  border: 1px solid rgba(148,163,184,0.2);
  background: rgba(13, 18, 32, 0.9);
  box-shadow: 0 16px 32px rgba(0,0,0,0.25);
}

.history-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--muted);
  margin-bottom: 8px;
}

.history-sub {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 10px;
}

.history-empty {
  font-size: 13px;
  color: var(--text);
  opacity: 0.85;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
  max-height: 240px;
  overflow-y: auto;
  padding-right: 6px;
}

.history-list::-webkit-scrollbar {
  width: 6px;
}

.history-list::-webkit-scrollbar-thumb {
  background: rgba(148,163,184,0.35);
  border-radius: 999px;
}

.history-list::-webkit-scrollbar-track {
  background: rgba(15,23,42,0.4);
  border-radius: 999px;
}

.history-row {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(148,163,184,0.15);
  background: rgba(15,23,42,0.45);
}

.history-left {
  min-width: 0;
}

.history-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.history-meta {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}

.history-right {
  text-align: right;
}

.history-amount {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

.history-status {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  border: 1px solid rgba(148,163,184,0.2);
}

.history-status.paid {
  border-color: rgba(34,197,94,0.4);
  color: var(--success);
  background: rgba(34,197,94,0.12);
}

.history-status.pending {
  border-color: rgba(251,191,36,0.4);
  color: var(--warning);
  background: rgba(251,191,36,0.12);
}

.history-status.issue {
  border-color: rgba(248,113,113,0.4);
  color: var(--danger);
  background: rgba(248,113,113,0.12);
}

.banner {
  position: relative;
  z-index: 1;
  padding: 12px 16px;
  border-radius: 14px;
  border: 1px solid rgba(148,163,184,0.2);
  margin-bottom: 20px;
  background: rgba(15,23,42,0.6);
  color: var(--text);
  font-size: 13px;
}

.banner.success {
  border-color: rgba(34,197,94,0.35);
  background: rgba(34,197,94,0.14);
  color: #bbf7d0;
}

  .banner.info {
    border-color: rgba(148,163,184,0.35);
  }
  .banner-sub {
    margin-top: 6px;
    font-size: 12px;
    color: var(--muted);
  }

.billing-card {
  position: relative;
  z-index: 1;
  padding: 28px 30px;
  border-radius: 22px;
  border: 1px solid rgba(148,163,184,0.2);
  background: linear-gradient(130deg, rgba(26, 34, 55, 0.85), rgba(12, 17, 32, 0.9));
  box-shadow: 0 20px 45px rgba(0,0,0,0.35);
}

.hero-title {
  font-family: "Fraunces", serif;
  font-size: clamp(30px, 5vw, 46px);
  margin: 0 0 12px;
}

.hero-sub {
  font-size: 15px;
  color: var(--muted);
  max-width: 520px;
}

.hero-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 22px;
}

.metric-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--muted);
  margin-bottom: 6px;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-sub {
  font-size: 12px;
  color: var(--muted);
}

.hero-warning {
  margin-top: 18px;
  padding: 12px 16px;
  border-radius: 14px;
  border: 1px solid rgba(248,113,113,0.35);
  background: rgba(248,113,113,0.12);
  color: #fecaca;
  font-size: 13px;
}

.feature-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.feature-chip {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.55);
  font-size: 12px;
  color: var(--text);
}

div.st-key-billing_checkout_card {
  padding: 26px 26px 22px;
  border-radius: 22px;
  border: 1px solid rgba(148,163,184,0.2);
  background: linear-gradient(160deg, rgba(22, 29, 50, 0.92), rgba(10, 15, 32, 0.95));
  box-shadow: 0 20px 45px rgba(0,0,0,0.35);
}

.checkout-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: var(--muted);
  margin-bottom: 12px;
}

.checkout-price {
  font-size: 34px;
  font-weight: 700;
  margin: 6px 0;
}

.checkout-sub {
  font-size: 13px;
  color: var(--muted);
}

.checkout-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.checkout-subtitle {
  font-size: 14px;
  font-weight: 600;
  margin-top: 6px;
  color: var(--text);
}

.checkout-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.checkout-price-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 10px;
}

.checkout-period {
  font-size: 14px;
  color: var(--muted);
  font-weight: 600;
}

.checkout-divider {
  height: 1px;
  margin: 14px 0;
  background: rgba(148,163,184,0.2);
}

.checkout-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 8px;
}

.checkout-meta-label {
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
}

.checkout-meta-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-top: 4px;
}

.checkout-meta {
  margin-top: 12px;
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--muted);
}

.checkout-meta strong {
  color: var(--text);
  font-weight: 600;
}

.checkout-badge {
  margin-top: 10px;
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(34,197,94,0.35);
  background: rgba(34,197,94,0.12);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--success);
}

.env-pill {
  margin-top: 10px;
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--muted);
}

.checkout-status .env-pill {
  margin-top: 0;
}

div.st-key-billing_currency .stRadio [role="radiogroup"] {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  margin-bottom: 12px;
}

div.st-key-billing_currency .stRadio [data-baseweb="radio"] {
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.28);
  background: rgba(15,23,42,0.6);
  padding: 6px 12px;
}

div.st-key-billing_currency .stRadio [data-baseweb="radio"] > div:first-child {
  display: none;
}

div.st-key-billing_currency .stRadio [data-baseweb="radio"]:has(input:checked) {
  border-color: rgba(109,213,237,0.6);
  background: rgba(109,213,237,0.15);
}

div.st-key-billing_currency .stRadio [data-testid="stMarkdownContainer"] p {
  font-size: 12px;
  font-weight: 600;
  margin: 0;
}

div.st-key-billing_checkout .stButton button {
  width: 100%;
  padding: 12px 18px;
  border-radius: 999px;
  border: 1px solid rgba(148,163,184,0.25);
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: #0b0f18;
  font-weight: 700;
  font-size: 14px;
  box-shadow: 0 16px 36px rgba(109,213,237,.35);
}

div.st-key-billing_checkout .stButton button:hover {
  border-color: rgba(109,213,237,0.6);
}

.checkout-note {
  margin-top: 10px;
  font-size: 12px;
  color: var(--muted);
}

.portal-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 12px;
  padding: 10px 16px;
  border-radius: 999px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  border: 1px solid rgba(148,163,184,0.25);
  background: rgba(15,23,42,0.6);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.portal-button.primary {
  border: 1px solid rgba(109,213,237,0.6);
  background: linear-gradient(120deg, var(--accent), var(--accent-2));
  color: #0b0f18;
  box-shadow: 0 16px 36px rgba(109,213,237,.35);
}

.portal-button.full {
  width: 100%;
}

.portal-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(15,23,42,0.35);
}

@media (max-width: 900px) {
  .billing-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .top-actions {
    flex-direction: column;
    align-items: flex-start;
    width: 100%;
  }
}
</style>
""",
    unsafe_allow_html=True,
)

user = require_login()
if not user:
    st.stop()

is_admin = _is_admin_user(user)

params = _get_query_params()
checkout_state = _query_value(params, "checkout")
checkout_returned = st.session_state.get("checkout_returned", False)
if checkout_state == "success" or checkout_returned:
    force_sync_account_from_remote(user.get("email", ""))
    st.session_state["billing_poll_until"] = time.time() + 90

account = get_account_by_email(user.get("email", ""))
plan_state = access_status(account)
plan_status = (plan_state.get("status") or "trialing").lower()
trial_end = plan_state.get("trial_end")
days_left = plan_state.get("days_left")
plan_end = plan_state.get("plan_end")
poll_until = st.session_state.get("billing_poll_until", 0)
if plan_status == "active":
    st.session_state.pop("billing_poll_until", None)

should_poll = False
is_locked = not plan_state.get("allowed", True)

user_name = user.get("name") or user.get("email") or "User"
user_email = user.get("email") or ""
user_picture = user.get("picture") or ""
initial = (user_name.strip()[:1] or "?").upper()

account_id = account.get("id") if account else None
transactions = fetch_remote_transactions(user_email, account_id=account_id, limit=20)

if st.session_state.get("billing_portal_email") != user_email:
    st.session_state["billing_portal_email"] = user_email
    st.session_state["billing_portal_url"] = None
    st.session_state["billing_portal_error"] = None

portal_url = st.session_state.get("billing_portal_url")
portal_error = st.session_state.get("billing_portal_error")

plan_label = "Premium"
plan_class = "premium"
status_headline = "Premium active"
status_sub = "Uploads and dashboards unlocked."
next_label = "Renews on"
next_value = "TBD"

if plan_status == "active":
    if is_locked:
        plan_label = "Premium ended"
        plan_class = "locked"
        status_headline = "Premium ended"
        status_sub = "Renew to restore uploads and dashboards."
        next_label = "Ended"
        if plan_end:
            next_value = plan_end.strftime("%b %d, %Y")
    elif plan_end:
        next_value = plan_end.strftime("%b %d, %Y")
elif plan_status == "trialing":
    if is_locked:
        plan_label = "Trial ended"
        plan_class = "locked"
        status_headline = "Trial ended"
        status_sub = "Start a subscription to unlock uploads and dashboards."
        next_label = "Ended"
        if trial_end:
            next_value = trial_end.strftime("%b %d, %Y")
    else:
        plan_label = "Trial"
        plan_class = "trial"
        status_headline = "Trial active"
        status_sub = "Full access during your trial."
        next_label = "Trial ends"
        if trial_end:
            next_value = trial_end.strftime("%b %d, %Y")
        elif days_left is not None:
            next_value = f"{days_left} days left"
else:
    plan_label = "Subscription required"
    plan_class = "locked"
    status_headline = "Subscription required"
    status_sub = "Start a subscription to unlock uploads and dashboards."
    next_label = "Status"
    next_value = "Locked"

if is_locked and plan_status == "active":
    cta_label = "Renew subscription"
elif plan_status == "active":
    cta_label = "Manage subscription"
else:
    cta_label = "Start subscription"

client_token = _get_secret("PADDLE_CLIENT_TOKEN")
paddle_env = (_get_secret("PADDLE_ENV") or "sandbox").lower()
price_eur = _get_secret("PADDLE_PRICE_EUR")
price_mad = _get_secret("PADDLE_PRICE_MAD")

currency_options: list[str] = []
if price_eur:
    currency_options.append("EUR")
if price_mad:
    currency_options.append("MAD")
if not currency_options:
    currency_options = ["EUR"]

currency_choice = st.session_state.get("billing_currency", currency_options[0])
if currency_choice not in currency_options:
    currency_choice = currency_options[0]
    st.session_state["billing_currency"] = currency_choice

price_id = price_eur if currency_choice == "EUR" else price_mad
price_amount = "20" if currency_choice == "EUR" else "199"
price_label = f"{price_amount} {currency_choice} / month"
checkout_ready = bool(client_token and price_id)

custom_data: dict[str, str] = {"email": user_email}
if account:
    if account.get("id") is not None:
        custom_data["account_id"] = str(account.get("id"))
    if account.get("referral_code"):
        custom_data["referral_code"] = str(account.get("referral_code"))
    if account.get("referrer_code"):
        custom_data["referrer_code"] = str(account.get("referrer_code"))

logo_uri = _get_logo_data_uri()
logo_html = f'<img class="brand-logo" src="{logo_uri}" alt="ChronoPlan logo" />' if logo_uri else ""
avatar_html = (
    f'<img class="account-avatar" src="{html.escape(user_picture)}" alt="avatar" />'
    if user_picture
    else f'<div class="account-avatar fallback">{html.escape(initial)}</div>'
)

top_html = f"""
<div class="billing-top">
  <div class="brand-block">
    <div class="brand">
      {logo_html}
      <div>
        <div class="brand-name">ChronoPlan</div>
        <div class="brand-sub">Billing</div>
      </div>
    </div>
  </div>
  <div class="top-actions">
    <div class="account-chip">
      {avatar_html}
      <div class="account-meta">
        <div class="account-name">{html.escape(user_name)}</div>
        <div class="account-email">{html.escape(user_email)}</div>
      </div>
      <div class="status-pill {plan_class}">{html.escape(plan_label)}</div>
    </div>
  </div>
</div>
"""

with st.container(key="billing_back_btn"):
    if st.button("<- Back to projects", key="billing_back_projects"):
        st.switch_page("pages/0_Projects.py")

st.markdown(top_html, unsafe_allow_html=True)

if checkout_state == "success":
    if plan_status == "active" and not is_locked:
        st.markdown(
            "<div class=\"banner success\">Subscription active. Thanks for supporting ChronoPlan.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class=\"banner success\">Checkout completed. Paddle usually confirms within a few seconds. "
            "If your status still shows trial, refresh this page to see Premium.</div>",
            unsafe_allow_html=True,
        )
elif checkout_state == "cancel":
    st.markdown(
        '<div class="banner info">Checkout canceled. You can try again anytime.</div>',
        unsafe_allow_html=True,
    )
else:
    checkout_returned = st.session_state.pop("checkout_returned", False)
    checkout_txn = st.session_state.pop("checkout_txn", None)
    if checkout_returned:
        txn_line = f"<div class='banner-sub'>Transaction: {html.escape(checkout_txn)}</div>" if checkout_txn else ""
        st.markdown(
            "<div class='banner success'>Checkout submitted. Waiting for Paddle confirmation."
            f"{txn_line}</div>",
            unsafe_allow_html=True,
        )

poll_until = st.session_state.get("billing_poll_until", 0)
poll_remaining = int(poll_until - time.time()) if poll_until else 0
if poll_remaining > 0 and plan_status != "active":
    st.markdown(
        f"<div class='banner info'>Waiting for Paddle confirmation. "
        f"Auto-refreshing for the next {poll_remaining} seconds.</div>",
        unsafe_allow_html=True,
    )
    force_sync_account_from_remote(user.get("email", ""))
    time.sleep(2)
    _rerun()

hero_html = f"""
<div class="billing-card">
  <div class="hero-title">Keep your dashboards live.</div>
  <div class="hero-sub">Manage your plan, renewal date, and access in one place.</div>
  <div class="hero-badges">
    <div class="status-pill {plan_class}">{html.escape(plan_label)}</div>
    <div class="status-pill {'locked' if is_locked else plan_class}">{'Locked' if is_locked else 'Active'}</div>
    <div class="status-pill">Monthly plan</div>
  </div>
  <div class="hero-metrics">
    <div>
      <div class="metric-label">Status</div>
      <div class="metric-value">{html.escape(status_headline)}</div>
      <div class="metric-sub">{html.escape(status_sub)}</div>
    </div>
    <div>
      <div class="metric-label">{html.escape(next_label)}</div>
      <div class="metric-value">{html.escape(next_value)}</div>
      <div class="metric-sub">Billing cycle</div>
    </div>
    <div>
      <div class="metric-label">Account</div>
      <div class="metric-value">{html.escape(user_email) if user_email else 'Signed in'}</div>
      <div class="metric-sub">{html.escape(user_name)}</div>
    </div>
  </div>
  <div class="feature-row">
    <div class="feature-chip">Unlimited dashboards</div>
    <div class="feature-chip">Priority uploads</div>
    <div class="feature-chip">Shared reporting</div>
    <div class="feature-chip">Referral credits</div>
  </div>
  {f'<div class="hero-warning">{html.escape(status_sub)}</div>' if is_locked else ''}
</div>
"""

col_left, col_right = st.columns([1.35, 0.75], gap="large")
with col_left:
    st.markdown(hero_html, unsafe_allow_html=True)

with col_right:
    with st.container(key="billing_checkout_card"):
        is_active = plan_status == "active" and not is_locked
        sandbox_html = '<span class="env-pill">Sandbox mode</span>' if paddle_env == "sandbox" and is_admin else ""
        if is_active:
            st.markdown(
                f"""
                <div class="checkout-header">
                  <div>
                    <div class="checkout-title">Current plan</div>
                    <div class="checkout-subtitle">ChronoPlan Premium</div>
                  </div>
                  <div class="checkout-status">
                    <span class="status-pill premium">Active</span>
                    {sandbox_html}
                  </div>
                </div>
                <div class="checkout-price-row">
                  <div class="checkout-price">{html.escape(price_amount)} {html.escape(currency_choice)}</div>
                  <div class="checkout-period">/ month</div>
                </div>
                <div class="checkout-sub">Manage billing and payment details.</div>
                <div class="checkout-divider"></div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="checkout-title">Checkout</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="checkout-price">{html.escape(price_label)}</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="checkout-sub">Taxes shown at checkout. Monthly billing.</div>',
                unsafe_allow_html=True,
            )
            if sandbox_html:
                st.markdown(sandbox_html, unsafe_allow_html=True)
        if len(currency_options) > 1:
            with st.container(key="billing_currency"):
                st.radio(
                    "Billing currency",
                    currency_options,
                    key="billing_currency",
                    index=currency_options.index(currency_choice),
                    horizontal=True,
                    label_visibility="collapsed",
                    format_func=lambda x: "EUR 20 / month" if x == "EUR" else "MAD 199 / month",
                )
        show_checkout = not is_active
        if not checkout_ready:
            st.markdown(
                "<div class='checkout-note'>Set PADDLE_CLIENT_TOKEN and a price ID in .streamlit/secrets.toml.</div>",
                unsafe_allow_html=True,
            )
        elif show_checkout:
            with st.container(key="billing_checkout"):
                components.html(
                    _paddle_overlay_widget_html(
                        token=client_token,
                        env=paddle_env,
                        price_id=price_id,
                        email=user.get("email", ""),
                        name=user.get("name", "") or user.get("email", ""),
                        success_url=f"{_base_url()}/Billing?checkout=success",
                        custom_data=custom_data,
                        button_label=cta_label,
                    ),
                    height=200,
                )
                if is_admin and st.button("Open admin checkout page", key="billing_admin_checkout"):
                    st.switch_page("pages/5_Checkout.py")
            st.markdown(
                "<div class='checkout-note'>Checkout opens in an overlay.</div>",
                unsafe_allow_html=True,
            )
        else:
            portal_url, portal_error = _get_portal_link(user_email, account_id)
            renew_value = plan_end.strftime("%b %d, %Y") if plan_end else "Monthly"
            st.markdown(
                f"""
                <div class="checkout-meta-grid">
                  <div>
                    <div class="checkout-meta-label">Renews on</div>
                    <div class="checkout-meta-value">{html.escape(renew_value)}</div>
                  </div>
                  <div>
                    <div class="checkout-meta-label">Billing cycle</div>
                    <div class="checkout-meta-value">Monthly</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if portal_url:
                st.markdown(
                    f'<a class="portal-button primary full" href="{html.escape(portal_url)}" target="_self">Manage subscription</a>',
                    unsafe_allow_html=True,
                )
            elif portal_error:
                st.markdown(
                    f"<div class='checkout-note'>Portal error: {html.escape(portal_error)}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div class='checkout-note'>Subscription active. Billing portal is loading.</div>",
                    unsafe_allow_html=True,
                )

    history_paid_rows: list[str] = []
    history_other_rows: list[str] = []
    for tx in transactions:
        status_raw = (tx.get("status") or "").lower()
        status_label, status_class = _tx_status_label(status_raw)
        details = tx.get("details") if isinstance(tx.get("details"), dict) else {}
        totals = details.get("totals") if isinstance(details.get("totals"), dict) else {}
        amount = totals.get("total") or totals.get("grand_total") or totals.get("subtotal")
        currency = totals.get("currency_code") or tx.get("currency_code")
        billed_at = tx.get("billed_at") or tx.get("created_at")
        date_label = _format_tx_date(billed_at if isinstance(billed_at, str) else None)
        tx_id = str(tx.get("id") or "").strip()
        tx_label = f"Txn {tx_id[-8:]}" if tx_id else "Transaction"
        items = details.get("line_items") if isinstance(details.get("line_items"), list) else []
        product_name = "Subscription payment"
        if items:
            product = items[0].get("product") if isinstance(items[0], dict) else {}
            name = product.get("name") if isinstance(product, dict) else None
            if isinstance(name, str) and name.strip():
                product_name = name.strip()
        row_html = (
            "<div class=\"history-row\">"
            "<div class=\"history-left\">"
            f"<div class=\"history-name\">{html.escape(product_name)}</div>"
            f"<div class=\"history-meta\">{html.escape(date_label)} - {html.escape(tx_label)}</div>"
            "</div>"
            "<div class=\"history-right\">"
            f"<div class=\"history-amount\">{html.escape(_format_tx_amount(amount, currency))}</div>"
            f"<div class=\"history-status {html.escape(status_class)}\">{html.escape(status_label)}</div>"
            "</div>"
            "</div>"
        )
        if status_raw in {"paid", "completed", "billed"}:
            history_paid_rows.append(row_html)
        else:
            history_other_rows.append(row_html)

    history_sub = "Invoices and receipts appear after your first payment."
    history_body = ""
    if history_paid_rows:
        history_body = f'<div class="history-list">{"".join(history_paid_rows)}</div>'
        history_sub = "Showing latest paid invoices (max 20)."
    elif history_other_rows:
        history_body = f'<div class="history-list">{"".join(history_other_rows)}</div>'
        history_sub = "No paid invoices yet. Pending checkouts shown below."
    else:
        history_body = '<div class="history-empty">No invoices yet.</div>'

    history_html = (
        "<div class=\"history-card\">"
        "<div class=\"history-title\">Billing history</div>"
        f"<div class=\"history-sub\">{html.escape(history_sub)}</div>"
        f"{history_body}"
        "</div>"
    )
    st.markdown(history_html, unsafe_allow_html=True)
