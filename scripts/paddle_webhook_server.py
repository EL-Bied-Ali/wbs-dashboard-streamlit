from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from billing_store import (
    get_account_by_email,
    get_account_by_id,
    record_event,
    update_account_plan_by_id,
    update_paddle_ids,
)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_signature(header: str) -> dict[str, str]:
    parts: dict[str, str] = {}
    for chunk in header.replace(",", ";").split(";"):
        if "=" not in chunk:
            continue
        key, value = chunk.strip().split("=", 1)
        parts[key.strip()] = value.strip()
    return parts


def _verify_signature(body: bytes, header: str, secret: str) -> bool:
    if not secret:
        return True
    if not header:
        return False
    parts = _parse_signature(header)
    ts = parts.get("ts") or parts.get("t")
    sig = parts.get("h1") or parts.get("v1")
    if not ts or not sig:
        return False
    signed = f"{ts}:{body.decode('utf-8')}".encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, sig)


def _extract_account(payload: dict[str, Any]) -> dict[str, Any] | None:
    data = payload.get("data") or {}
    custom = data.get("custom_data") or {}
    account_id = custom.get("account_id")
    email = custom.get("email")
    if account_id:
        try:
            account_id = int(account_id)
        except (TypeError, ValueError):
            account_id = None
    if account_id:
        return get_account_by_id(account_id)
    if not email:
        customer = data.get("customer") or {}
        email = customer.get("email") or data.get("customer_email")
    if email:
        return get_account_by_email(str(email))
    return None


def _plan_update_from_payload(payload: dict[str, Any]) -> tuple[str | None, datetime | None, datetime | None]:
    data = payload.get("data") or {}
    status = (data.get("status") or "").lower()
    period = data.get("current_billing_period") or {}
    plan_end = _parse_iso(period.get("ends_at") or data.get("next_billed_at"))
    trial_end = _parse_iso(data.get("trial_ends_at") or data.get("trial_end"))
    if status == "active":
        return "active", None, plan_end
    if status == "trialing":
        return "trialing", trial_end, None
    if status in {"canceled", "paused", "past_due", "unpaid"}:
        if plan_end is None:
            plan_end = _utc_now()
        return "active", None, plan_end
    return None, None, None


class PaddleWebhookHandler(BaseHTTPRequestHandler):
    webhook_secret = ""
    webhook_path = "/webhook/paddle"

    def _send_json(self, code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlparse(self.path).path != self.webhook_path:
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        self._send_json(200, {"ok": True, "status": "ready"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != self.webhook_path:
            self._send_json(404, {"ok": False, "error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length or 0)
        signature = self.headers.get("Paddle-Signature", "")
        if not _verify_signature(body, signature, self.webhook_secret):
            self._send_json(401, {"ok": False, "error": "invalid_signature"})
            return
        try:
            payload = json.loads(body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "invalid_json"})
            return

        event_type = payload.get("event_type") or payload.get("alert_name") or "unknown"
        account = _extract_account(payload)
        account_id = account.get("id") if account else None

        data = payload.get("data") or {}
        customer = data.get("customer") or {}
        customer_id = data.get("customer_id") or customer.get("id")
        subscription_id = data.get("id") or data.get("subscription_id")

        if account_id:
            update_paddle_ids(account_id, customer_id, subscription_id)

        plan_status, trial_end, plan_end = _plan_update_from_payload(payload)
        if account_id and plan_status:
            update_account_plan_by_id(
                int(account_id),
                plan_status,
                trial_end=trial_end,
                plan_end=plan_end,
            )

        record_event(
            int(account_id) if account_id else None,
            event_type,
            {
                "status": data.get("status"),
                "subscription_id": subscription_id,
                "customer_id": customer_id,
            },
        )
        self._send_json(200, {"ok": True})

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("PADDLE_WEBHOOK_PORT", "8001")))
    parser.add_argument("--path", default=os.environ.get("PADDLE_WEBHOOK_PATH", "/webhook/paddle"))
    parser.add_argument("--secret", default=os.environ.get("PADDLE_WEBHOOK_SECRET", ""))
    args = parser.parse_args()

    PaddleWebhookHandler.webhook_secret = args.secret
    PaddleWebhookHandler.webhook_path = args.path
    server = HTTPServer(("0.0.0.0", args.port), PaddleWebhookHandler)
    print(f"Paddle webhook server listening on http://0.0.0.0:{args.port}{args.path}")
    server.serve_forever()


if __name__ == "__main__":
    main()
