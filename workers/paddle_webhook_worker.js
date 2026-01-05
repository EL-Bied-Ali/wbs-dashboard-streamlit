export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === "/health") {
      return jsonResponse({ ok: true, status: "ready" });
    }

    if (path === "/account" && request.method === "GET") {
      const tokenOk = requireToken(request, env);
      if (!tokenOk.ok) {
        return jsonResponse({ ok: false, error: tokenOk.error }, 401);
      }
      const email = (url.searchParams.get("email") || "").trim().toLowerCase();
      const accountId = (url.searchParams.get("account_id") || "").trim();
      if (!email && !accountId) {
        return jsonResponse({ ok: false, error: "missing_identifier" }, 400);
      }
      const key = email ? accountKey(email) : accountIdKey(accountId);
      const record = await env.BILLING_KV.get(key, { type: "json" });
      if (!record) {
        return jsonResponse({ ok: false, error: "not_found" }, 404);
      }
      return jsonResponse({ ok: true, account: record });
    }

    if (path === "/transactions" && request.method === "GET") {
      const tokenOk = requireToken(request, env);
      if (!tokenOk.ok) {
        return jsonResponse({ ok: false, error: tokenOk.error }, 401);
      }
      const email = (url.searchParams.get("email") || "").trim().toLowerCase();
      const accountId = (url.searchParams.get("account_id") || "").trim();
      if (!email && !accountId) {
        return jsonResponse({ ok: false, error: "missing_identifier" }, 400);
      }
      const key = email ? accountKey(email) : accountIdKey(accountId);
      const record = await env.BILLING_KV.get(key, { type: "json" });
      if (!record) {
        return jsonResponse({ ok: true, transactions: [] });
      }
      const customerId = toStringOrNull(record.paddle_customer_id);
      if (!customerId) {
        return jsonResponse({ ok: true, transactions: [] });
      }
      const limitParam = parseInt(url.searchParams.get("limit") || "5", 10);
      const limit = Math.min(Math.max(1, Number.isNaN(limitParam) ? 5 : limitParam), 20);
      const apiToken = env.PADDLE_API_TOKEN || "";
      if (!apiToken) {
        return jsonResponse({ ok: false, error: "missing_paddle_token" }, 500);
      }
      const envName = String(env.PADDLE_ENV || "sandbox").toLowerCase();
      const base = envName === "production" ? "https://api.paddle.com" : "https://sandbox-api.paddle.com";
      const query = new URLSearchParams({ customer_id: customerId, per_page: String(limit) });
      const apiUrl = `${base}/transactions?${query.toString()}`;
      const apiResp = await fetch(apiUrl, {
        headers: {
          Authorization: `Bearer ${apiToken}`,
          Accept: "application/json",
        },
      });
      if (!apiResp.ok) {
        const body = await apiResp.text();
        return jsonResponse({ ok: false, error: "paddle_api_error", detail: body }, apiResp.status);
      }
      const payload = await apiResp.json();
      const transactions = Array.isArray(payload?.data) ? payload.data : [];
      return jsonResponse({ ok: true, transactions });
    }

    if (path === "/portal" && request.method === "POST") {
      const tokenOk = requireToken(request, env);
      if (!tokenOk.ok) {
        return jsonResponse({ ok: false, error: tokenOk.error }, 401);
      }
      let payload;
      try {
        payload = await request.json();
      } catch (err) {
        return jsonResponse({ ok: false, error: "invalid_json" }, 400);
      }
      const email = toStringOrNull(payload?.email)?.toLowerCase();
      const accountId = toStringOrNull(payload?.account_id);
      const returnUrl = toStringOrNull(payload?.return_url);
      if (!email && !accountId) {
        return jsonResponse({ ok: false, error: "missing_identifier" }, 400);
      }
      const key = email ? accountKey(email) : accountIdKey(accountId);
      const record = await env.BILLING_KV.get(key, { type: "json" });
      if (!record) {
        return jsonResponse({ ok: false, error: "not_found" }, 404);
      }
      const customerId = toStringOrNull(record.paddle_customer_id);
      if (!customerId) {
        return jsonResponse({ ok: false, error: "missing_customer" }, 404);
      }
      const apiToken = env.PADDLE_API_TOKEN || "";
      if (!apiToken) {
        return jsonResponse({ ok: false, error: "missing_paddle_token" }, 500);
      }
      const envName = String(env.PADDLE_ENV || "sandbox").toLowerCase();
      const base = envName === "production" ? "https://api.paddle.com" : "https://sandbox-api.paddle.com";
      const body = {};
      if (returnUrl) {
        body.return_url = returnUrl;
      }
      const apiResp = await fetch(`${base}/customers/${customerId}/portal-sessions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiToken}`,
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify(body),
      });
      if (!apiResp.ok) {
        const detail = await apiResp.text();
        return jsonResponse({ ok: false, error: "paddle_api_error", detail }, apiResp.status);
      }
      const data = await apiResp.json();
      const url =
        data?.data?.url
        || data?.data?.urls?.general?.overview
        || data?.data?.urls?.overview;
      if (!url) {
        return jsonResponse({ ok: false, error: "missing_portal_url", detail: data }, 500);
      }
      return jsonResponse({ ok: true, url });
    }

    if (path === "/webhook/paddle" && request.method === "POST") {
    const bodyBuffer = await request.arrayBuffer();
    const body = new TextDecoder().decode(bodyBuffer);
    const secret = env.PADDLE_WEBHOOK_SECRET || "";
    const signature = request.headers.get("Paddle-Signature") || "";
    if (secret) {
      const valid = await verifySignature(body, signature, secret);
      if (!valid) {
        return jsonResponse({ ok: false, error: "invalid_signature" }, 401);
      }
    }

      let payload;
      try {
        payload = JSON.parse(body || "{}");
      } catch (err) {
        return jsonResponse({ ok: false, error: "invalid_json" }, 400);
      }

      const data = payload.data || {};
      const custom = data.custom_data || {};
      const accountId = toStringOrNull(custom.account_id);
      const email =
        toStringOrNull(custom.email)
        || toStringOrNull((data.customer || {}).email)
        || toStringOrNull(data.customer_email);

      const planUpdate = planUpdateFromPayload(payload);
      const fallbackStatus = inferStatusFromEvent(payload.event_type || payload.alert_name || "");
      const planStatus = planUpdate.plan_status || fallbackStatus;
      const record = {
        account_id: accountId,
        email: email ? email.toLowerCase() : null,
        plan_status: planStatus,
        trial_end: planUpdate.trial_end,
        plan_end: planUpdate.plan_end,
        paddle_customer_id: toStringOrNull(data.customer_id || (data.customer || {}).id),
        paddle_subscription_id: toStringOrNull(data.id || data.subscription_id),
        last_event: payload.event_type || payload.alert_name || "unknown",
        updated_at: nowIso(),
      };

      if (email) {
        await env.BILLING_KV.put(accountKey(email.toLowerCase()), JSON.stringify(record));
      }
      if (accountId) {
        await env.BILLING_KV.put(accountIdKey(accountId), JSON.stringify(record));
      }

      return jsonResponse({ ok: true });
    }

    return jsonResponse({ ok: false, error: "not_found" }, 404);
  },
};

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

function requireToken(request, env) {
  const token = env.BILLING_API_TOKEN || "";
  if (!token) {
    return { ok: true };
  }
  const header = request.headers.get("Authorization") || "";
  const parts = header.split(" ");
  const value = parts.length === 2 ? parts[1].trim() : "";
  if (!value || value !== token) {
    return { ok: false, error: "unauthorized" };
  }
  return { ok: true };
}

function accountKey(email) {
  return `account:${email}`;
}

function accountIdKey(accountId) {
  return `account_id:${accountId}`;
}

function toStringOrNull(value) {
  if (value === undefined || value === null) {
    return null;
  }
  const raw = String(value).trim();
  return raw ? raw : null;
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function parseIso(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function planUpdateFromPayload(payload) {
  const data = payload.data || {};
  const status = String(data.status || data.subscription_status || "").toLowerCase();
  const period = data.current_billing_period || {};
  const planEnd = parseIso(period.ends_at || data.next_billed_at);
  const trialEnd = parseIso(data.trial_ends_at || data.trial_end);
  if (status === "active") {
    return { plan_status: "active", trial_end: null, plan_end: planEnd };
  }
  if (status === "trialing") {
    return { plan_status: "trialing", trial_end: trialEnd, plan_end: null };
  }
  if (["canceled", "paused", "past_due", "unpaid"].includes(status)) {
    return { plan_status: "active", trial_end: null, plan_end: planEnd || nowIso() };
  }
  return { plan_status: null, trial_end: null, plan_end: null };
}

function inferStatusFromEvent(eventType) {
  const normalized = String(eventType || "").toLowerCase();
  if (normalized.includes("subscription.activated")) return "active";
  if (normalized.includes("subscription.updated")) return "active";
  if (normalized.includes("transaction.completed")) return "active";
  if (normalized.includes("subscription.trialing")) return "trialing";
  return null;
}

async function verifySignature(body, header, secret) {
  if (!header) return false;
  const parts = parseSignature(header);
  const ts = parts.ts || parts.t;
  const sig = parts.h1 || parts.v1;
  if (!ts || !sig) return false;
  const payload = `${ts}:${body}`;
  const expectedHex = await hmacSha256Hex(secret, payload);
  const expectedB64 = await hmacSha256Base64(secret, payload);
  const normalizedSig = String(sig).trim();
  if (normalizedSig.length === expectedHex.length) {
    return timingSafeEqual(expectedHex, normalizedSig.toLowerCase());
  }
  if (normalizedSig.length === expectedB64.length) {
    return timingSafeEqual(expectedB64, normalizedSig);
  }
  return timingSafeEqual(expectedHex, normalizedSig.toLowerCase())
    || timingSafeEqual(expectedB64, normalizedSig);
}

function parseSignature(header) {
  const parts = {};
  header.replace(/,/g, ";").split(";").forEach((chunk) => {
    const [key, value] = chunk.trim().split("=", 2);
    if (!key || value === undefined) return;
    parts[key.trim()] = value.trim();
  });
  return parts;
}

async function hmacSha256Hex(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return bufferToHex(signature);
}

async function hmacSha256Base64(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return bufferToBase64(signature);
}

function bufferToHex(buffer) {
  const bytes = new Uint8Array(buffer);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function bufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i += 1) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}
