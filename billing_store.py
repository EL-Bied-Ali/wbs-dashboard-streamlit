from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DB_ENV = "BILLING_DB_PATH"
DEFAULT_DB_PATH = Path("artifacts") / "billing.sqlite"
REMOTE_SYNC_TTL_SECONDS = 60
_REMOTE_SYNC_CACHE: dict[str, float] = {}
BILLING_LOGGER = logging.getLogger("billing_store")


def _debug_enabled() -> bool:
    return os.environ.get("BILLING_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}


def _ensure_logger() -> None:
    if not BILLING_LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [billing_store] %(levelname)s: %(message)s")
        )
        BILLING_LOGGER.addHandler(handler)
    BILLING_LOGGER.setLevel(logging.DEBUG if _debug_enabled() else logging.INFO)


def _log(level: int, message: str) -> None:
    _ensure_logger()
    BILLING_LOGGER.log(level, message)


def _log_info(message: str, *, force: bool = False) -> None:
    if force or _debug_enabled():
        _log(logging.INFO, message)


def _db_path() -> Path:
    raw = os.environ.get(DB_ENV)
    if raw:
        return Path(raw)
    return DEFAULT_DB_PATH


def get_billing_db_path() -> Path:
    return _db_path()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _trial_end(start: datetime) -> datetime:
    return start + timedelta(days=15)


def _get_secret(key: str) -> str:
    value = os.environ.get(key, "")
    if not value:
        try:
            import streamlit as st

            value = st.secrets.get(key, "")
        except Exception:
            value = ""
    return value


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _conn() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                country TEXT,
                referral_code TEXT UNIQUE,
                referrer_code TEXT,
                trial_start TEXT,
                trial_end TEXT,
                plan_status TEXT NOT NULL,
                plan_end TEXT,
                plan_updated_at TEXT,
                paddle_customer_id TEXT,
                paddle_subscription_id TEXT
            );
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(accounts)").fetchall()}
        if "plan_end" not in columns:
            conn.execute("ALTER TABLE accounts ADD COLUMN plan_end TEXT")
        if "plan_updated_at" not in columns:
            conn.execute("ALTER TABLE accounts ADD COLUMN plan_updated_at TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_account_id INTEGER NOT NULL,
                referee_account_id INTEGER NOT NULL,
                referral_code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                activated_at TEXT,
                reward_months INTEGER NOT NULL DEFAULT 0,
                UNIQUE(referrer_account_id, referee_account_id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                provider TEXT NOT NULL DEFAULT 'paddle',
                provider_subscription_id TEXT,
                status TEXT NOT NULL,
                plan_code TEXT,
                price_code TEXT,
                currency TEXT,
                started_at TEXT,
                current_period_end TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS credits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                months INTEGER NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata TEXT
            );
            """
        )


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _generate_referral_code() -> str:
    return f"ref_{secrets.token_hex(4)}"


def _get_account_by_email_local(email: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE email = ?",
            (email,),
        ).fetchone()
    return _row_to_dict(row)


def _remote_sync_allowed(email: str) -> bool:
    if not email:
        return False
    now = time.time()
    last = _REMOTE_SYNC_CACHE.get(email)
    if last is None:
        return True
    return (now - last) >= REMOTE_SYNC_TTL_SECONDS


def _fetch_remote_account(email: str) -> dict[str, Any] | None:
    base_url = _get_secret("BILLING_API_URL")
    if not base_url:
        _log(logging.WARNING, "fetch_remote_account missing BILLING_API_URL")
        return None
    token = _get_secret("BILLING_API_TOKEN")
    url = f"{base_url.rstrip('/')}/account?{urlencode({'email': email})}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=6) as response:
            status = getattr(response, "status", None)
            body = response.read().decode("utf-8")
        body_preview = body if len(body) <= 2000 else f"{body[:2000]}...(truncated)"
        _log(
            logging.DEBUG,
            f"fetch_remote_account url={url} status={status} "
            f"token_present={bool(token)} body={body_preview}",
        )
        payload = json.loads(body or "{}")
    except HTTPError as err:
        detail = ""
        try:
            detail = err.read().decode("utf-8")
        except Exception:
            detail = ""
        detail_preview = detail if len(detail) <= 2000 else f"{detail[:2000]}...(truncated)"
        _log(
            logging.WARNING,
            f"fetch_remote_account http_error status={err.code} "
            f"token_present={bool(token)} body={detail_preview}",
        )
        return None
    except URLError as err:
        _log(logging.WARNING, f"fetch_remote_account url_error reason={getattr(err, 'reason', None)}")
        return None
    except Exception as err:
        _log(logging.WARNING, f"fetch_remote_account error={err}")
        return None
    if not isinstance(payload, dict) or not payload.get("ok"):
        _log(logging.WARNING, f"fetch_remote_account invalid_payload payload={payload}")
        return None
    account = payload.get("account")
    return account if isinstance(account, dict) else None


def fetch_remote_transactions(
    email: str,
    account_id: int | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    email = (email or "").strip().lower()
    account_id_value = str(account_id) if account_id else ""
    base_url = _get_secret("BILLING_API_URL")
    if not base_url:
        return []
    if not email and not account_id_value:
        return []
    token = _get_secret("BILLING_API_TOKEN")
    params: dict[str, str] = {}
    if email:
        params["email"] = email
    elif account_id_value:
        params["account_id"] = account_id_value
    if limit:
        params["limit"] = str(limit)
    url = f"{base_url.rstrip('/')}/transactions?{urlencode(params)}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=8) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body or "{}")
    except Exception:
        return []
    if not isinstance(payload, dict) or not payload.get("ok"):
        return []
    transactions = payload.get("transactions")
    if not isinstance(transactions, list):
        return []
    return [tx for tx in transactions if isinstance(tx, dict)]


def create_portal_session(
    email: str,
    account_id: int | None = None,
    return_url: str | None = None,
) -> tuple[str | None, str | None]:
    email = (email or "").strip().lower()
    account_id_value = str(account_id) if account_id else ""
    base_url = _get_secret("BILLING_API_URL")
    if not base_url:
        return None, "Missing billing API URL."
    if not email and not account_id_value:
        return None, "Missing account identifier."
    token = _get_secret("BILLING_API_TOKEN")
    payload: dict[str, str] = {}
    if email:
        payload["email"] = email
    elif account_id_value:
        payload["account_id"] = account_id_value
    if return_url:
        payload["return_url"] = return_url
    url = f"{base_url.rstrip('/')}/portal"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urlopen(req, timeout=8) as response:
            body = response.read().decode("utf-8")
            result = json.loads(body or "{}")
    except HTTPError as err:
        detail = ""
        try:
            detail = err.read().decode("utf-8")
        except Exception:
            detail = ""
        message = f"Billing service error ({err.code})."
        if detail:
            message = f"{message} {detail}"
        return None, message
    except URLError as err:
        reason = getattr(err, "reason", None)
        if reason:
            return None, f"Billing service unreachable: {reason}"
        return None, "Unable to reach the billing service."
    except Exception:
        return None, "Unable to reach the billing service."
    if not isinstance(result, dict) or not result.get("ok"):
        error = "Billing portal unavailable."
        if isinstance(result, dict):
            detail = result.get("error")
            if isinstance(detail, str) and detail.strip():
                error = detail.strip()
        return None, error
    portal_url = result.get("url")
    if isinstance(portal_url, str) and portal_url.strip():
        return portal_url, None
    return None, "Missing billing portal link."


def sync_account_from_remote(email: str, force: bool = False) -> bool:
    email_raw = email
    email = (email or "").strip().lower()
    _log_info(
        f"sync_account_from_remote email_raw={email_raw!r} normalized={email!r} "
        f"force={force} db_path={_db_path()}",
        force=force,
    )
    if not _remote_sync_allowed(email):
        _log_info(f"sync_account_from_remote skip_ttl email={email!r}", force=force)
        return False
    _REMOTE_SYNC_CACHE[email] = time.time()
    local = _get_account_by_email_local(email)
    if not local:
        _log_info(f"sync_account_from_remote local_missing email={email!r}", force=force)
        return False
    remote = _fetch_remote_account(email)
    if not remote:
        _log_info(f"sync_account_from_remote remote_missing email={email!r}", force=force)
        return False
    remote_updated_at = _parse_iso(remote.get("updated_at") if isinstance(remote.get("updated_at"), str) else None)
    local_updated_at = _parse_iso(local.get("plan_updated_at") if isinstance(local.get("plan_updated_at"), str) else None)
    _log_info(
        f"sync_account_from_remote updated_at remote={remote_updated_at} local={local_updated_at} "
        f"force={force}",
        force=force,
    )
    if not force and remote_updated_at and local_updated_at and local_updated_at >= remote_updated_at:
        _log_info("sync_account_from_remote skip_up_to_date", force=force)
        return False
    plan_status = (remote.get("plan_status") or "").strip().lower()
    if plan_status in {"active", "trialing"}:
        _log_info(
            "sync_account_from_remote update_account_plan "
            f"status={plan_status!r} trial_end={remote.get('trial_end')!r} "
            f"plan_end={remote.get('plan_end')!r} plan_updated_at={remote_updated_at}",
            force=force,
        )
        updated = update_account_plan(
            email,
            plan_status,
            trial_end=remote.get("trial_end"),
            plan_end=remote.get("plan_end"),
            plan_updated_at=remote_updated_at,
        )
        _log_info(f"sync_account_from_remote update_account_plan ok={updated}", force=force)
    else:
        _log_info(f"sync_account_from_remote skip_update_plan status={plan_status!r}", force=force)
    customer_id = remote.get("paddle_customer_id")
    subscription_id = remote.get("paddle_subscription_id")
    if customer_id or subscription_id:
        account_id = local.get("id")
        if account_id:
            _log_info(
                "sync_account_from_remote update_paddle_ids "
                f"account_id={account_id} customer_id_present={bool(customer_id)} "
                f"subscription_id_present={bool(subscription_id)}",
                force=force,
            )
            updated = update_paddle_ids(int(account_id), customer_id, subscription_id)
            _log_info(f"sync_account_from_remote update_paddle_ids ok={updated}", force=force)
    else:
        _log_info("sync_account_from_remote skip_update_paddle_ids missing_ids", force=force)
    return True


def force_sync_account_from_remote(email: str) -> bool:
    email_raw = email
    email = (email or "").strip().lower()
    _log_info(
        f"force_sync_account_from_remote email_raw={email_raw!r} normalized={email!r} db_path={_db_path()}",
        force=True,
    )
    if not email:
        return False
    _REMOTE_SYNC_CACHE.pop(email, None)
    return sync_account_from_remote(email, force=True)


def get_account_by_email(email: str) -> dict[str, Any] | None:
    sync_account_from_remote(email)
    account = _get_account_by_email_local(email)
    if account:
        _log_info(
            "get_account_by_email "
            f"email={email!r} plan_status={account.get('plan_status')!r} "
            f"plan_end={account.get('plan_end')!r} plan_updated_at={account.get('plan_updated_at')!r} "
            f"db_path={_db_path()}",
        )
    else:
        _log_info(f"get_account_by_email email={email!r} not_found db_path={_db_path()}")
    return account


def get_account_by_id(account_id: int) -> dict[str, Any] | None:
    if not account_id:
        return None
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
    return _row_to_dict(row)


def get_account_by_referral_code(code: str) -> dict[str, Any] | None:
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE referral_code = ?",
            (code,),
        ).fetchone()
    return _row_to_dict(row)


def record_referral(referrer_account_id: int, referee_account_id: int, referral_code: str) -> bool:
    init_db()
    with _conn() as conn:
        try:
            conn.execute(
                """
                INSERT INTO referrals (
                    referrer_account_id,
                    referee_account_id,
                    referral_code,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    referrer_account_id,
                    referee_account_id,
                    referral_code,
                    _iso(_utc_now()),
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def ensure_account(user: dict[str, Any], referrer_code: str | None = None) -> dict[str, Any] | None:
    email = (user or {}).get("email")
    if not email:
        return None
    init_db()
    now = _utc_now()
    now_iso = _iso(now)
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE email = ?",
            (email,),
        ).fetchone()
        if row:
            referral_code = row["referral_code"]
            if not referral_code:
                referral_code = _generate_referral_code()
                conn.execute(
                    "UPDATE accounts SET referral_code = ? WHERE email = ?",
                    (referral_code, email),
                )
            conn.execute(
                "UPDATE accounts SET last_seen = ?, name = COALESCE(?, name) WHERE email = ?",
                (now_iso, user.get("name"), email),
            )
            refreshed = conn.execute(
                "SELECT * FROM accounts WHERE email = ?",
                (email,),
            ).fetchone()
            return _row_to_dict(refreshed)

        referral_code = _generate_referral_code()
        trial_start = now
        trial_end = _trial_end(trial_start)
        conn.execute(
            """
            INSERT INTO accounts (
                email, name, created_at, last_seen,
                referral_code, referrer_code,
                trial_start, trial_end, plan_status, plan_updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                email,
                user.get("name"),
                now_iso,
                now_iso,
                referral_code,
                referrer_code,
                _iso(trial_start),
                _iso(trial_end),
                "trialing",
                now_iso,
            ),
        )
        account = conn.execute(
            "SELECT * FROM accounts WHERE email = ?",
            (email,),
        ).fetchone()
    account_dict = _row_to_dict(account)
    if account_dict and referrer_code:
        referrer = get_account_by_referral_code(referrer_code)
        if referrer and referrer.get("id") != account_dict.get("id"):
            record_referral(int(referrer["id"]), int(account_dict["id"]), referrer_code)
            record_event(
                int(account_dict["id"]),
                "referral_signup",
                {"referrer_account_id": referrer.get("id"), "referral_code": referrer_code},
            )
    if account_dict:
        record_event(int(account_dict["id"]), "signup", {"referrer_code": referrer_code})
    return account_dict


def list_accounts(limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM accounts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_referrals(limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT referrals.*, a.email AS referrer_email, b.email AS referee_email
            FROM referrals
            JOIN accounts a ON referrals.referrer_account_id = a.id
            JOIN accounts b ON referrals.referee_account_id = b.id
            ORDER BY referrals.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_events(limit: int = 200) -> list[dict[str, Any]]:
    init_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def record_event(account_id: int | None, event_type: str, metadata: dict[str, Any] | None = None) -> None:
    init_db()
    payload = json.dumps(metadata or {})
    with _conn() as conn:
        conn.execute(
            "INSERT INTO events (account_id, event_type, created_at, metadata) VALUES (?, ?, ?, ?)",
            (account_id, event_type, _iso(_utc_now()), payload),
        )


def access_status(account: dict[str, Any] | None) -> dict[str, Any]:
    if account and _debug_enabled():
        _log(
            logging.DEBUG,
            "access_status input "
            f"email={account.get('email')!r} plan_status={account.get('plan_status')!r} "
            f"trial_end={account.get('trial_end')!r} plan_end={account.get('plan_end')!r}",
        )
    if not account:
        return {
            "allowed": True,
            "status": "unknown",
            "trial_end": None,
            "days_left": None,
            "plan_end": None,
        }
    status = (account.get("plan_status") or "trialing").lower()
    trial_end_raw = account.get("trial_end")
    trial_end = _parse_iso(trial_end_raw if isinstance(trial_end_raw, str) else None)
    plan_end_raw = account.get("plan_end")
    plan_end = _parse_iso(plan_end_raw if isinstance(plan_end_raw, str) else None)
    now = _utc_now()
    allowed = False
    if status == "active":
        if plan_end is None:
            allowed = True
        else:
            allowed = plan_end >= now
    elif status == "trialing":
        if trial_end is None:
            allowed = True
        else:
            allowed = trial_end >= now
    days_left = None
    if trial_end is not None:
        delta = trial_end - now
        days_left = max(0, int(delta.total_seconds() // 86400))
    return {
        "allowed": allowed,
        "status": status,
        "trial_end": trial_end,
        "days_left": days_left,
        "plan_end": plan_end,
    }


def _normalize_plan_values(
    normalized_status: str,
    trial_end: datetime | str | None,
    plan_end: datetime | str | None,
) -> tuple[str | None, str | None]:
    if normalized_status == "active":
        trial_end_value = None
        if plan_end is None:
            plan_end_value = _iso(_utc_now() + timedelta(days=30))
        elif isinstance(plan_end, datetime):
            plan_end_value = _iso(plan_end)
        elif isinstance(plan_end, str):
            plan_end_value = plan_end.strip() or None
        else:
            plan_end_value = None
    else:
        plan_end_value = None
        if isinstance(trial_end, datetime):
            trial_end_value = _iso(trial_end)
        elif isinstance(trial_end, str):
            trial_end_value = trial_end.strip() or None
        else:
            trial_end_value = None
    return trial_end_value, plan_end_value


def update_account_plan(
    email: str,
    plan_status: str,
    trial_end: datetime | str | None = None,
    plan_end: datetime | str | None = None,
    plan_updated_at: datetime | str | None = None,
) -> bool:
    email = (email or "").strip()
    if not email:
        return False
    normalized_status = (plan_status or "").strip().lower()
    if normalized_status not in {"active", "trialing"}:
        return False
    trial_end_value, plan_end_value = _normalize_plan_values(
        normalized_status,
        trial_end,
        plan_end,
    )
    if isinstance(plan_updated_at, datetime):
        plan_updated_at_value = _iso(plan_updated_at)
    elif isinstance(plan_updated_at, str):
        plan_updated_at_value = plan_updated_at.strip() or None
    else:
        plan_updated_at_value = _iso(_utc_now())
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, plan_status, trial_end, plan_end, plan_updated_at FROM accounts WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            _log(logging.WARNING, f"update_account_plan email_not_found email={email!r}")
            return False
        _log_info(
            "update_account_plan before "
            f"email={email!r} status={row['plan_status']!r} trial_end={row['trial_end']!r} "
            f"plan_end={row['plan_end']!r} plan_updated_at={row['plan_updated_at']!r} "
            f"db_path={_db_path()}",
        )
        conn.execute(
            "UPDATE accounts SET plan_status = ?, trial_end = ?, plan_end = ?, plan_updated_at = ? WHERE email = ?",
            (normalized_status, trial_end_value, plan_end_value, plan_updated_at_value, email),
        )
        updated = conn.execute(
            "SELECT plan_status, trial_end, plan_end, plan_updated_at FROM accounts WHERE email = ?",
            (email,),
        ).fetchone()
        if updated:
            _log_info(
                "update_account_plan after "
                f"email={email!r} status={updated['plan_status']!r} "
                f"trial_end={updated['trial_end']!r} plan_end={updated['plan_end']!r} "
                f"plan_updated_at={updated['plan_updated_at']!r}",
            )
    return True


def update_account_plan_by_id(
    account_id: int,
    plan_status: str,
    trial_end: datetime | str | None = None,
    plan_end: datetime | str | None = None,
    plan_updated_at: datetime | str | None = None,
) -> bool:
    if not account_id:
        return False
    normalized_status = (plan_status or "").strip().lower()
    if normalized_status not in {"active", "trialing"}:
        return False
    trial_end_value, plan_end_value = _normalize_plan_values(
        normalized_status,
        trial_end,
        plan_end,
    )
    if isinstance(plan_updated_at, datetime):
        plan_updated_at_value = _iso(plan_updated_at)
    elif isinstance(plan_updated_at, str):
        plan_updated_at_value = plan_updated_at.strip() or None
    else:
        plan_updated_at_value = _iso(_utc_now())
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE accounts SET plan_status = ?, trial_end = ?, plan_end = ?, plan_updated_at = ? WHERE id = ?",
            (normalized_status, trial_end_value, plan_end_value, plan_updated_at_value, account_id),
        )
    return True


def update_paddle_ids(
    account_id: int,
    customer_id: str | None = None,
    subscription_id: str | None = None,
) -> bool:
    if not account_id:
        return False
    customer_id = (customer_id or "").strip() or None
    subscription_id = (subscription_id or "").strip() or None
    if customer_id is None and subscription_id is None:
        return False
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id, paddle_customer_id, paddle_subscription_id FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if not row:
            _log(logging.WARNING, f"update_paddle_ids account_id_not_found id={account_id}")
            return False
        _log_info(
            "update_paddle_ids before "
            f"id={account_id} customer_id={row['paddle_customer_id']!r} "
            f"subscription_id={row['paddle_subscription_id']!r} db_path={_db_path()}",
        )
        conn.execute(
            """
            UPDATE accounts
            SET paddle_customer_id = COALESCE(?, paddle_customer_id),
                paddle_subscription_id = COALESCE(?, paddle_subscription_id)
            WHERE id = ?
            """,
            (customer_id, subscription_id, account_id),
        )
        updated = conn.execute(
            "SELECT paddle_customer_id, paddle_subscription_id FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if updated:
            _log_info(
                "update_paddle_ids after "
                f"id={account_id} customer_id={updated['paddle_customer_id']!r} "
                f"subscription_id={updated['paddle_subscription_id']!r}",
            )
    return True


def delete_account_by_email(email: str) -> bool:
    email = (email or "").strip()
    if not email:
        return False
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM accounts WHERE email = ?",
            (email,),
        ).fetchone()
        if not row:
            return False
        account_id = row["id"]
        conn.execute(
            "DELETE FROM referrals WHERE referrer_account_id = ? OR referee_account_id = ?",
            (account_id, account_id),
        )
        conn.execute(
            "DELETE FROM subscriptions WHERE account_id = ?",
            (account_id,),
        )
        conn.execute(
            "DELETE FROM credits WHERE account_id = ?",
            (account_id,),
        )
        conn.execute(
            "DELETE FROM events WHERE account_id = ?",
            (account_id,),
        )
        conn.execute(
            "DELETE FROM accounts WHERE id = ?",
            (account_id,),
        )
    return True
