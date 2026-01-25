from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any

import streamlit as st

from billing_store import get_billing_db_path

_LOGGED_EVENTS: set[str] = set()
RUNTIME_LOGGER = logging.getLogger("runtime_checks")


def _ensure_logger() -> None:
    if not RUNTIME_LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [runtime_checks] %(levelname)s: %(message)s")
        )
        RUNTIME_LOGGER.addHandler(handler)
    RUNTIME_LOGGER.setLevel(logging.INFO)


def _log_once(key: str, level: int, message: str) -> None:
    if key in _LOGGED_EVENTS:
        return
    _ensure_logger()
    RUNTIME_LOGGER.log(level, message)
    _LOGGED_EVENTS.add(key)


def _get_secret(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        try:
            value = st.secrets.get(key, "")
        except Exception:
            value = ""
    return value


@st.cache_resource(show_spinner=False)
def validate_runtime_config(checkout_enabled: bool) -> dict[str, Any]:
    missing: list[str] = []
    keys = ["BILLING_API_URL", "BILLING_API_TOKEN", "APP_URL"]
    if checkout_enabled:
        keys.append("PADDLE_CLIENT_TOKEN")
    for key in keys:
        if not _get_secret(key):
            missing.append(key)
            _log_once(f"missing:{key}", logging.WARNING, f"Missing runtime config key: {key}")
    return {"missing": missing}


@st.cache_resource(show_spinner=False)
def check_billing_db_integrity() -> dict[str, Any]:
    path = get_billing_db_path()
    _log_once(f"db_path:{path}", logging.INFO, f"Billing DB path: {path}")
    duplicates: list[dict[str, Any]] = []
    if path.exists():
        with sqlite3.connect(path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT lower(email) AS email, COUNT(*) AS count
                FROM accounts
                GROUP BY lower(email)
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            duplicates = [dict(row) for row in rows]
    else:
        _log_once(f"db_missing:{path}", logging.INFO, f"Billing DB missing at {path}")
    if duplicates:
        _log_once("db_duplicates", logging.ERROR, f"Billing DB duplicate emails: {duplicates}")
    return {"db_path": str(path), "duplicates": duplicates}


def get_account_row(email: str | None) -> dict[str, Any] | None:
    normalized = (email or "").strip().lower()
    if not normalized:
        return None
    path = get_billing_db_path()
    if not path.exists():
        return None
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT id, email, plan_status, trial_end, plan_end, plan_updated_at,
                   paddle_customer_id, paddle_subscription_id
            FROM accounts
            WHERE lower(email) = ?
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()
    return dict(row) if row else None
