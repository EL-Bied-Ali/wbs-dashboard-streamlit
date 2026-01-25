from __future__ import annotations

import json
import logging
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DB_ENV = "BILLING_DB_PATH"
DEFAULT_DB_PATH = Path("artifacts") / "billing.sqlite"
SQLITE_TIMEOUT_SECONDS = 10.0
SQLITE_BUSY_TIMEOUT_MS = 10_000
SQLITE_WRITE_RETRIES = 8
SQLITE_RETRY_BASE_SLEEP = 0.03
SQLITE_RETRY_MAX_SLEEP = 0.35
REMOTE_SYNC_TTL_SECONDS = 60
_REMOTE_SYNC_CACHE: dict[str, float] = {}
BILLING_LOGGER = logging.getLogger("billing_store")
_DB_SCHEMA_LOCK = threading.Lock()
_DB_SCHEMA_READY = False
_META_REFERRAL_FLAG = "referrals_referee_email_backfilled"


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


def _is_locked_error(exc: Exception) -> bool:
    if not isinstance(exc, sqlite3.OperationalError):
        return False
    msg = str(exc).lower()
    return "database is locked" in msg or "locked" in msg


def _sleep_backoff(attempt: int) -> None:
    jitter = (time.time() % 0.01)
    delay = min(SQLITE_RETRY_MAX_SLEEP, SQLITE_RETRY_BASE_SLEEP * (2**attempt)) + jitter
    time.sleep(delay)


def _with_write_retry(fn):
    last_exc: Exception | None = None
    for attempt in range(SQLITE_WRITE_RETRIES):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if _is_locked_error(exc) and attempt < SQLITE_WRITE_RETRIES - 1:
                _sleep_backoff(attempt)
                continue
            raise
    raise last_exc if last_exc else RuntimeError("sqlite retry failed")


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
    conn = sqlite3.connect(
        path,
        timeout=SQLITE_TIMEOUT_SECONDS,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS};")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
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
    if "paddle_subscription_uid" not in columns:
        conn.execute("ALTER TABLE accounts ADD COLUMN paddle_subscription_uid TEXT")
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
    ref_cols = {row["name"] for row in conn.execute("PRAGMA table_info(referrals)").fetchall()}
    if "referee_email" not in ref_cols:
        conn.execute("ALTER TABLE referrals ADD COLUMN referee_email TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    flag = conn.execute(
        "SELECT 1 FROM meta WHERE key = ? LIMIT 1",
        (_META_REFERRAL_FLAG,),
    ).fetchone()
    if flag is None:
        conn.execute(
            """
            UPDATE referrals
            SET referee_email = (
                SELECT lower(email) FROM accounts WHERE accounts.id = referrals.referee_account_id
            )
            WHERE referee_email IS NULL
            """
        )
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            (_META_REFERRAL_FLAG, "1"),
        )
    try:
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_referrals_referrer_referee_email
            ON referrals(referrer_account_id, referee_email)
            """
        )
    except sqlite3.IntegrityError as err:
        _log(
            logging.WARNING,
            "ensure_schema unique index failed (possible duplicate referee_email):" f" {err}",
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


def ensure_db_ready() -> None:
    global _DB_SCHEMA_READY
    if _DB_SCHEMA_READY:
        return
    with _DB_SCHEMA_LOCK:
        if _DB_SCHEMA_READY:
            return

        def _do() -> None:
            with _conn() as conn:
                conn.execute("BEGIN IMMEDIATE;")
                ensure_schema(conn)
                conn.commit()

        _with_write_retry(_do)
        _DB_SCHEMA_READY = True


def init_db() -> None:
    ensure_db_ready()

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


def get_account_by_email_local(email: str) -> dict[str, Any] | None:
    return _get_account_by_email_local(email)


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
            status = getattr(response, "status", None)
            body = response.read().decode("utf-8")
        body_preview = body if len(body) <= 2000 else f"{body[:2000]}...(truncated)"
        _log(
            logging.DEBUG,
            f"fetch_remote_transactions url={url} status={status} "
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
            f"fetch_remote_transactions http_error status={err.code} "
            f"token_present={bool(token)} body={detail_preview}",
        )
        return []
    except URLError as err:
        _log(logging.WARNING, f"fetch_remote_transactions url_error reason={getattr(err, 'reason', None)}")
        return []
    except Exception as err:
        _log(logging.WARNING, f"fetch_remote_transactions error={err}")
        return []
    if not isinstance(payload, dict) or not payload.get("ok"):
        _log(logging.WARNING, f"fetch_remote_transactions invalid_payload payload={payload}")
        return []
    transactions = payload.get("transactions")
    if not isinstance(transactions, list):
        return []
    return [tx for tx in transactions if isinstance(tx, dict)]


def apply_months_from_remote_transactions(
    email: str,
    account_id: int,
    *,
    limit: int = 20,
    force: bool = False,
) -> int:
    """
    Fetch remote transactions and grant +1 month for each paid subscription transaction.
    Idempotent via credits.source = paddle_invoice:<invoice_id>.
    Returns number of months granted.
    """
    email = (email or "").strip().lower()
    if not email or not account_id:
        return 0

    txs = fetch_remote_transactions(email, account_id=account_id, limit=limit)
    if not txs:
        return 0

    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT paddle_subscription_uid FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
    local_sub_id = (row["paddle_subscription_uid"] or "").strip() if row else ""
    expected_account_id = str(account_id)

    if _debug_enabled():
        sample_tx: dict[str, Any] | None = None
        for candidate in txs:
            if not isinstance(candidate, dict):
                continue
            custom_candidate = candidate.get("custom_data") or {}
            candidate_account = str(custom_candidate.get("account_id") or "").strip()
            if candidate_account == expected_account_id:
                sample_tx = candidate
                break
        sample_tx = sample_tx or (txs[0] if isinstance(txs[0], dict) else None)
        if sample_tx:
            _log_info(
                "TX_SAMPLE=" + json.dumps(sample_tx, ensure_ascii=False)[:2000],
                force=force,
            )

    granted = 0
    for tx in txs:
        if not isinstance(tx, dict):
            continue

        tx_key = tx.get("invoice_id") or tx.get("id")
        if not tx_key:
            continue
        tx_id_str = str(tx_key).strip()
        if not tx_id_str:
            continue

        status = (tx.get("status") or tx.get("state") or "").strip().lower()
        if status not in {"completed", "paid", "succeeded", "success"}:
            continue

        tx_type = (tx.get("type") or tx.get("event_type") or tx.get("kind") or "").strip().lower()
        custom_data = tx.get("custom_data") or {}
        tx_account_id = str(custom_data.get("account_id") or "").strip()
        if tx_account_id and tx_account_id != expected_account_id:
            if _debug_enabled():
                _log_info(
                    f"skip_tx account_mismatch expected={expected_account_id} got={tx_account_id} invoice={tx_id_str}",
                    force=force,
                )
            continue
        tx_sub_id = (tx.get("subscription_id") or "").strip()
        if local_sub_id and tx_sub_id and tx_sub_id != local_sub_id:
            if _debug_enabled():
                _log_info(
                    f"skip_tx sub_mismatch local={local_sub_id} tx={tx_sub_id} invoice={tx_id_str}",
                    force=force,
                )
            continue
        if _debug_enabled() and tx_account_id == expected_account_id:
            _log_info(
                f"matching_tx subs local={local_sub_id or '<empty>'} tx={tx_sub_id or '<empty>'}",
                force=force,
            )
        billing_period = tx.get("billing_period") or {}
        period_end = None
        if isinstance(billing_period, dict):
            period_end = billing_period.get("ends_at") or billing_period.get("end_at")
        if not period_end:
            period_end = tx.get("billing_period_ends_at")
        source = f"paddle_invoice:{tx_id_str}"
        ok = grant_month_until(account_id, source=source, period_end_iso=period_end)
        if ok:
            granted += 1
            record_event(
                account_id,
                "paddle_month_applied",
                {"source": source, "tx_id": tx_id_str, "status": status, "tx_type": tx_type},
            )
            if _debug_enabled():
                _log_info(
                    f"paddle_month_applied source={source} status={status!r} tx_type={tx_type!r}",
                    force=force,
                )
    if _debug_enabled() and granted == 0 and txs:
        sample = txs[0]
        _log_info(f"apply_months_from_remote_transactions no grant sample_keys={list(sample.keys())}", force=force)
    return granted


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
    remote = _fetch_remote_account(email)
    if not remote:
        _log_info(f"sync_account_from_remote remote_missing email={email!r}", force=force)
        return False
    local = _get_account_by_email_local(email)
    if not local:
        _log_info(f"sync_account_from_remote local_missing email={email!r} creating stub", force=force)
        ensure_account({"email": email, "name": remote.get("name") if isinstance(remote, dict) else None})
        local = _get_account_by_email_local(email)
        if not local:
            _log_info(f"sync_account_from_remote local_create_failed email={email!r}", force=force)
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
    local_status_before = (local.get("plan_status") or "").strip().lower()
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
        if plan_status == "active" and local_status_before != "active":
            account_id = local.get("id")
            if account_id:
                if activate_referral_reward(int(account_id), reason="remote_sync_activation"):
                    _log_info(f"activate_referral_reward triggered for account_id={account_id}", force=force)
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
            subscription_uid = (remote.get("paddle_subscription_uid") or "").strip()
            local_subscription_uid = (local.get("paddle_subscription_uid") or "").strip()
            if subscription_uid:
                if subscription_uid != local_subscription_uid:
                    _log_info(
                        f"sync_account_from_remote update_paddle_subscription_uid "
                        f"account_id={account_id} uid_present=True uid={subscription_uid}",
                        force=force,
                    )
                    update_paddle_subscription_uid(int(account_id), subscription_uid)
                else:
                    _log_info(
                        f"sync_account_from_remote update_paddle_subscription_uid "
                        f"account_id={account_id} uid_present=True uid={subscription_uid} already_synced",
                        force=force,
                    )
            else:
                _log_info(
                    f"sync_account_from_remote update_paddle_subscription_uid "
                    f"account_id={account_id} uid_present=False local_uid={local_subscription_uid or '<empty>'}",
                    force=force,
                )
    else:
        _log_info("sync_account_from_remote skip_update_paddle_ids missing_ids", force=force)
    refreshed = _get_account_by_email_local(email)
    if refreshed and (refreshed.get("plan_status") or "").strip().lower() == "active":
        acc_id = refreshed.get("id")
        if acc_id:
            months = apply_months_from_remote_transactions(email, int(acc_id), limit=20, force=force)
            if months:
                _log_info(f"apply_months_from_remote_transactions granted={months} account_id={acc_id}", force=force)
            elif grant_bonus_month(int(acc_id), source="paddle_activation_fallback"):
                _log_info(
                    f"paddle_activation_fallback granted account_id={acc_id}",
                    force=force,
                )
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


def record_referral(
    referrer_account_id: int,
    referee_account_id: int,
    referral_code: str,
    referee_email: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> bool:
    init_db()

    referee_email_norm = (referee_email or "").strip().lower()
    if not referee_email_norm:
        return False

    def _insert(c: sqlite3.Connection) -> bool:
        existing = c.execute(
            """
            SELECT 1 FROM referrals
            WHERE referrer_account_id = ? AND referee_email = ?
            LIMIT 1
            """,
            (referrer_account_id, referee_email_norm),
        ).fetchone()
        if existing is not None:
            return False
        try:
            c.execute(
                """
                INSERT INTO referrals (
                    referrer_account_id,
                    referee_account_id,
                    referee_email,
                    referral_code,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    referrer_account_id,
                    referee_account_id,
                    referee_email_norm,
                    referral_code,
                    _iso(_utc_now()),
                ),
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def _do():
        if conn is not None:
            return _insert(conn)
        with _conn() as local:
            local.execute("BEGIN IMMEDIATE;")
            ok = _insert(local)
            local.commit()
            return ok

    return bool(_with_write_retry(_do))


def ensure_account(user: dict[str, Any], referrer_code: str | None = None) -> dict[str, Any] | None:
    email = (user or {}).get("email")
    if not email:
        return None
    init_db()
    now = _utc_now()
    now_iso = _iso(now)
    def _do():
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT * FROM accounts WHERE email = ?",
                (email,),
            ).fetchone()
            print(
                "[BILLING] ensure_account: existing=",
                bool(row),
                "email=",
                email,
                "referrer_code_arg=",
                referrer_code,
            )
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
                conn.commit()
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
            if account:
                print("[BILLING] ensure_account: created id=", account["id"], "email=", email)
            account_dict = _row_to_dict(account)
            if account_dict and referrer_code:
                referrer_row = conn.execute(
                    "SELECT * FROM accounts WHERE referral_code = ?",
                    (referrer_code,),
                ).fetchone()
                referrer = _row_to_dict(referrer_row)
                if referrer and referrer.get("id") != account_dict.get("id"):
                    record_referral(
                        int(referrer["id"]),
                        int(account_dict["id"]),
                        referrer_code,
                        referee_email=email,
                        conn=conn,
                    )
                    record_event(
                        int(account_dict["id"]),
                        "referral_signup",
                        {"referrer_account_id": referrer.get("id"), "referral_code": referrer_code},
                        conn=conn,
                    )
            if account_dict:
                record_event(int(account_dict["id"]), "signup", {"referrer_code": referrer_code}, conn=conn)
            conn.commit()
            return account_dict

    return _with_write_retry(_do)


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
            SELECT referrals.*,
                   a.email AS referrer_email,
                   COALESCE(b.email, referrals.referee_email) AS referee_email
            FROM referrals
            JOIN accounts a ON referrals.referrer_account_id = a.id
            LEFT JOIN accounts b ON referrals.referee_account_id = b.id
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


def record_event(
    account_id: int | None,
    event_type: str,
    metadata: dict[str, Any] | None = None,
    *,
    conn: sqlite3.Connection | None = None,
) -> None:
    init_db()
    payload = json.dumps(metadata or {})

    def _do():
        if conn is not None:
            conn.execute(
                "INSERT INTO events (account_id, event_type, created_at, metadata) VALUES (?, ?, ?, ?)",
                (account_id, event_type, _iso(_utc_now()), payload),
            )
            return None
        with _conn() as local:
            local.execute("BEGIN IMMEDIATE;")
            local.execute(
                "INSERT INTO events (account_id, event_type, created_at, metadata) VALUES (?, ?, ?, ?)",
                (account_id, event_type, _iso(_utc_now()), payload),
            )
        return None

    _with_write_retry(_do)


def has_credit_source(account_id: int, source: str) -> bool:
    if not account_id:
        return False
    init_db()
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM credits WHERE account_id = ? AND source = ? LIMIT 1",
            (account_id, source),
        ).fetchone()
    return row is not None


def grant_bonus_month(account_id: int, *, source: str = "first_paid_subscription") -> bool:
    if not account_id:
        return False
    init_db()
    now = _utc_now()
    now_iso = _iso(now)
    def _do() -> tuple[bool, datetime | None]:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")

            already = conn.execute(
                "SELECT 1 FROM credits WHERE account_id = ? AND source = ? LIMIT 1",
                (account_id, source),
            ).fetchone()
            if already is not None:
                if _debug_enabled():
                    _log_info(
                        f"grant_bonus_month skip_existing_credit account_id={account_id} source={source}",
                        force=True,
                    )
                return False, None

            account_row = conn.execute(
                "SELECT plan_end FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if not account_row:
                return False, None

            plan_end_raw = account_row["plan_end"]
            plan_end_dt = _parse_iso(plan_end_raw if isinstance(plan_end_raw, str) else None)
            base = plan_end_dt if plan_end_dt and plan_end_dt > now else now
            new_end_local = base + timedelta(days=30)

            conn.execute(
                "UPDATE accounts SET plan_end = ?, plan_updated_at = ? WHERE id = ?",
                (_iso(new_end_local), now_iso, account_id),
            )
            conn.execute(
                "INSERT INTO credits (account_id, months, source, created_at) VALUES (?, ?, ?, ?)",
                (account_id, 1, source, now_iso),
            )
            return True, new_end_local

    ok, new_end = _with_write_retry(_do)
    if not ok or new_end is None:
        return False
    record_event(
        account_id,
        "bonus_granted",
        {"source": source, "months": 1, "new_plan_end": _iso(new_end)},
    )
    return True


def grant_month_until(
    account_id: int,
    *,
    source: str,
    period_end_iso: str | None = None,
) -> bool:
    if not account_id:
        return False
    period_end_dt = _parse_iso(period_end_iso if isinstance(period_end_iso, str) else None)
    init_db()
    now = _utc_now()
    now_iso = _iso(now)

    def _do() -> tuple[bool, datetime | None]:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            already = conn.execute(
                "SELECT 1 FROM credits WHERE account_id = ? AND source = ? LIMIT 1",
                (account_id, source),
            ).fetchone()
            if already is not None:
                if _debug_enabled():
                    _log_info(
                        f"grant_month_until skip_existing_credit account_id={account_id} source={source}",
                        force=True,
                    )
                return False, None

            account_row = conn.execute(
                "SELECT plan_end FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if not account_row:
                return False, None

            plan_end_raw = account_row["plan_end"]
            plan_end_dt = _parse_iso(plan_end_raw if isinstance(plan_end_raw, str) else None)
            base = plan_end_dt if plan_end_dt and plan_end_dt > now else now
            if period_end_dt and period_end_dt > base:
                new_end = period_end_dt
            else:
                new_end = base + timedelta(days=30)

            conn.execute(
                "UPDATE accounts SET plan_end = ?, plan_updated_at = ? WHERE id = ?",
                (_iso(new_end), now_iso, account_id),
            )
            conn.execute(
                "INSERT INTO credits (account_id, months, source, created_at) VALUES (?, ?, ?, ?)",
                (account_id, 1, source, now_iso),
            )
            return True, new_end

    ok, new_end = _with_write_retry(_do)
    if not ok or new_end is None:
        return False
    record_event(
        account_id,
        "bonus_granted",
        {"source": source, "months": 1, "new_plan_end": _iso(new_end)},
    )
    return True


def activate_referral_reward(referee_account_id: int, *, reason: str = "first_paid_subscription") -> bool:
    """
    If a referral exists for referee_account_id and is not activated yet,
    grant +1 month to referee and referrer, then mark referral as activated.
    Idempotent via referrals.activated_at and credits.source.
    """
    if not referee_account_id:
        return False
    init_db()
    now = _utc_now()
    now_iso = _iso(now)

    def _extend_one_month_in_tx(conn: sqlite3.Connection, account_id: int, source: str) -> bool:
        already = conn.execute(
            "SELECT 1 FROM credits WHERE account_id = ? AND source = ? LIMIT 1",
            (account_id, source),
        ).fetchone()
        if already is not None:
            row = conn.execute(
                "SELECT plan_status, plan_end FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if row:
                plan_end_dt = _parse_iso(row["plan_end"] if isinstance(row["plan_end"], str) else None)
                if plan_end_dt and plan_end_dt > now:
                    conn.execute(
                        "UPDATE accounts SET plan_status = ?, trial_end = ?, plan_updated_at = ? WHERE id = ?",
                        ("active", None, now_iso, account_id),
                    )
            return True
        row = conn.execute(
            "SELECT plan_end FROM accounts WHERE id = ?",
            (account_id,),
        ).fetchone()
        if not row:
            return False
        plan_end_raw = row["plan_end"]
        plan_end_dt = _parse_iso(plan_end_raw if isinstance(plan_end_raw, str) else None)
        base = plan_end_dt if plan_end_dt and plan_end_dt > now else now
        new_end_local = base + timedelta(days=30)
        conn.execute(
            "UPDATE accounts SET plan_status = ?, trial_end = ?, plan_end = ?, plan_updated_at = ? WHERE id = ?",
            ("active", None, _iso(new_end_local), now_iso, account_id),
        )
        conn.execute(
            "INSERT INTO credits (account_id, months, source, created_at) VALUES (?, ?, ?, ?)",
            (account_id, 1, source, now_iso),
        )
        return True

    def _do() -> tuple[bool, int, int, int]:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            referee_email_row = conn.execute(
                "SELECT lower(email) AS email FROM accounts WHERE id = ?",
                (referee_account_id,),
            ).fetchone()
            if not referee_email_row:
                return False, 0, 0, 0
            referee_email = referee_email_row["email"]
            ref = conn.execute(
                """
                SELECT id, referrer_account_id, activated_at, reward_months
                FROM referrals
                WHERE referee_email = ?
                LIMIT 1
                """,
                (referee_email,),
            ).fetchone()
            if not ref:
                return False, 0, 0, 0
            if ref["activated_at"]:
                return False, int(ref["id"]), int(ref["referrer_account_id"]), int(ref["reward_months"] or 0)

            referral_id = int(ref["id"])
            referrer_id = int(ref["referrer_account_id"])
            source_referee = f"referral_bonus_referee:{referral_id}"
            source_referrer = f"referral_bonus_referrer:{referral_id}"
            ok_referee = _extend_one_month_in_tx(conn, referee_account_id, source_referee)
            ok_referrer = _extend_one_month_in_tx(conn, referrer_id, source_referrer)
            if ok_referee or ok_referrer:
                conn.execute(
                    """
                    UPDATE referrals
                    SET activated_at = ?, reward_months = reward_months + 1
                    WHERE id = ? AND activated_at IS NULL
                    """,
                    (now_iso, referral_id),
                )
                return True, referral_id, referrer_id, 1
            return False, referral_id, referrer_id, int(ref["reward_months"] or 0)

    ok, referral_id, referrer_id, reward_months = _with_write_retry(_do)
    if ok and referral_id and referrer_id:
        record_event(referee_account_id, "referral_reward_granted", {"referral_id": referral_id, "role": "referee", "reason": reason})
        record_event(referrer_id, "referral_reward_granted", {"referral_id": referral_id, "role": "referrer", "reason": reason})
        record_event(referee_account_id, "referral_activated", {"referral_id": referral_id, "referrer_account_id": referrer_id})
        return True
    return False


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
    status_raw = (account.get("plan_status") or "trialing").lower()
    trial_end_raw = account.get("trial_end")
    trial_end = _parse_iso(trial_end_raw if isinstance(trial_end_raw, str) else None)
    plan_end_raw = account.get("plan_end")
    plan_end = _parse_iso(plan_end_raw if isinstance(plan_end_raw, str) else None)
    now = _utc_now()

    plan_allowed = plan_end is not None and plan_end >= now
    trial_allowed = False
    if status_raw == "trialing":
        trial_allowed = True if trial_end is None else (trial_end >= now)

    allowed = plan_allowed or trial_allowed
    status = "active" if plan_allowed else status_raw

    days_left = None
    if status_raw == "trialing" and trial_end is not None:
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
            plan_end_value = None
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


def _retain_plan_end_for_active(
    current_plan_end: str | None,
    incoming_plan_end: str | None,
    normalized_status: str,
) -> str | None:
    final = incoming_plan_end
    if normalized_status == "active":
        current_dt = _parse_iso(current_plan_end if isinstance(current_plan_end, str) else None)
        incoming_dt = _parse_iso(incoming_plan_end if isinstance(incoming_plan_end, str) else None)
        if incoming_dt is None and current_dt is not None:
            final = current_plan_end
        elif incoming_dt is not None and current_dt is not None and current_dt > incoming_dt:
            final = current_plan_end
    return final


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
    def _do() -> bool:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
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
            final_plan_end_value = _retain_plan_end_for_active(row["plan_end"], plan_end_value, normalized_status)
            conn.execute(
                "UPDATE accounts SET plan_status = ?, trial_end = ?, plan_end = ?, plan_updated_at = ? WHERE email = ?",
                (normalized_status, trial_end_value, final_plan_end_value, plan_updated_at_value, email),
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

    return bool(_with_write_retry(_do))


def recompute_plan_end_from_credits(account_id: int) -> bool:
    if not account_id:
        return False
    init_db()
    now = _utc_now()
    now_iso = _iso(now)

    def _do() -> bool:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT COALESCE(SUM(months), 0) AS m FROM credits WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            months = int(row["m"] or 0) if row else 0
            if months <= 0:
                return False
            acc = conn.execute(
                "SELECT plan_end FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            current_end = _parse_iso(acc["plan_end"] if acc and isinstance(acc["plan_end"], str) else None)
            computed_end = now + timedelta(days=30 * months)
            final_end = computed_end
            if current_end and current_end > final_end:
                final_end = current_end
            conn.execute(
                "UPDATE accounts SET plan_end = ?, plan_updated_at = ? WHERE id = ?",
                (_iso(final_end), now_iso, account_id),
            )
            return True

    return bool(_with_write_retry(_do))


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
    def _do() -> bool:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT id, plan_end FROM accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            if not row:
                return False
            conn.execute(
                "UPDATE accounts SET plan_status = ?, trial_end = ?, plan_end = ?, plan_updated_at = ? WHERE id = ?",
                (
                    normalized_status,
                    trial_end_value,
                    _retain_plan_end_for_active(row["plan_end"], plan_end_value, normalized_status),
                    plan_updated_at_value,
                    account_id,
                ),
            )
            return True

    return bool(_with_write_retry(_do))


def update_paddle_subscription_uid(
    account_id: int,
    subscription_uid: str | None,
) -> bool:
    if not account_id:
        return False
    subscription_uid = (subscription_uid or "").strip() or None
    if subscription_uid is None:
        return False
    init_db()

    def _do() -> bool:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute(
                "UPDATE accounts SET paddle_subscription_uid = COALESCE(?, paddle_subscription_uid) WHERE id = ?",
                (subscription_uid, account_id),
            )
            return True

    return bool(_with_write_retry(_do))


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
    def _do() -> bool:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
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

    return bool(_with_write_retry(_do))


def delete_account_by_email(email: str) -> bool:
    email = (email or "").strip()
    if not email:
        return False
    init_db()
    def _do() -> bool:
        with _conn() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            row = conn.execute(
                "SELECT id FROM accounts WHERE email = ?",
                (email,),
            ).fetchone()
            if not row:
                return False
            account_id = row["id"]
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

    return bool(_with_write_retry(_do))
