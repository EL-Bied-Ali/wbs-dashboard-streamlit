from __future__ import annotations

import base64
import hashlib
import html
import json
import logging
import os
import secrets
import textwrap
import time
from urllib.parse import urlparse, urlunparse, unquote
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import streamlit as st
from streamlit.errors import StreamlitDuplicateElementKey
from authlib.integrations.requests_client import OAuth2Session
from authlib.integrations.base_client.errors import OAuthError
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from streamlit_cookies_manager import CookieManager
from streamlit import components

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
SCOPES = ["openid", "email", "profile"]

SESSION_KEY = "auth_user"
STATE_KEY = "oauth_state"
NONCE_KEY = "oauth_nonce"
STATE_COOKIE = "oauth_state"
NONCE_COOKIE = "oauth_nonce"
_USED_CODES: dict[str, float] = {}
_CODE_TTL_SECONDS = 300
_CODE_USERS: dict[str, tuple[float, dict[str, Any]]] = {}
_AUTH_LOG_PATH = Path(__file__).resolve().parent / "artifacts" / "auth_debug.log"
_SESSION_STORE_PATH = Path(__file__).resolve().parent / "artifacts" / "auth_sessions.json"
_SESSION_TTL_SECONDS = 7 * 24 * 3600


@lru_cache(maxsize=1)
def _get_logo_path() -> Path | None:
    root = Path(__file__).resolve().parent
    candidates = [
        root / "chronoplan_logo.png",
        root / "Wibis_logo.png",
        root / "wibis_logo.png",
        root / "logo.png",
        root / "logo.jpg",
        root / "logo.jpeg",
        root / "logo.svg",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


@lru_cache(maxsize=1)
def _get_logo_data_uri() -> str | None:
    path = _get_logo_path()
    if not path:
        return None
    ext = path.suffix.lower().lstrip(".")
    if ext == "png":
        mime = "image/png"
    elif ext in {"jpg", "jpeg"}:
        mime = "image/jpeg"
    elif ext == "svg":
        mime = "image/svg+xml"
    else:
        return None
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _get_custom_logo_dir() -> Path:
    root = Path(__file__).resolve().parent
    logo_dir = root / "assets" / "logos"
    logo_dir.mkdir(parents=True, exist_ok=True)
    return logo_dir


def _custom_logo_candidates(role: str) -> list[Path]:
    base = _get_custom_logo_dir() / f"{role}_logo"
    return [base.with_suffix(ext) for ext in (".png", ".jpg", ".jpeg", ".svg")]


def _find_custom_logo(role: str) -> Path | None:
    for path in _custom_logo_candidates(role):
        if path.exists():
            return path
    return None


def _custom_logo_data_uri(role: str) -> str | None:
    path = _find_custom_logo(role)
    if not path:
        return None
    ext = path.suffix.lower().lstrip(".")
    if ext == "png":
        mime = "image/png"
    elif ext in {"jpg", "jpeg"}:
        mime = "image/jpeg"
    elif ext == "svg":
        mime = "image/svg+xml"
    else:
        return None
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def brand_strip_html(variant: str = "page") -> str:
    company_logo = _custom_logo_data_uri("company")
    client_logo = _custom_logo_data_uri("client")
    if not company_logo and not client_logo:
        return ""
    items = []
    for label, src in (("Company", company_logo), ("Client", client_logo)):
        if not src:
            continue
        items.append(
            f'<div class="brand-pill" title="{html.escape(label)} logo">'
            f'<img src="{src}" alt="{html.escape(label)} logo" /></div>'
        )
    if not items:
        return ""
    safe_variant = html.escape(variant)
    return f'<div class="brand-strip brand-strip--{safe_variant}">{"".join(items)}</div>'



def _save_custom_logo(role: str, uploaded) -> None:
    if uploaded is None:
        return
    ext = Path(uploaded.name).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".svg"}:
        ext = ".png"
    for existing in _custom_logo_candidates(role):
        if existing.exists():
            existing.unlink()
    target = _get_custom_logo_dir() / f"{role}_logo{ext}"
    target.write_bytes(uploaded.getvalue())


def _remove_custom_logo(role: str) -> None:
    for path in _custom_logo_candidates(role):
        if path.exists():
            path.unlink()


def _get_setting(key: str, default: str | None = None) -> str | None:
    try:
        if key in st.secrets:
            return str(st.secrets[key])
    except FileNotFoundError:
        pass
    return os.environ.get(key, default)


def _require_setting(key: str) -> str:
    value = _get_setting(key)
    if value is not None:
        value = value.strip()
    if value:
        return value
    st.error(f"Missing required setting: {key}")
    st.stop()
    raise RuntimeError(f"Missing required setting: {key}")


def _int_setting(key: str, default: int) -> int:
    raw = _get_setting(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_query_params() -> dict[str, Any]:
    try:
        return st.query_params  # type: ignore[attr-defined]
    except AttributeError:
        return st.experimental_get_query_params()


def _query_value(params: dict[str, Any], key: str) -> str | None:
    val = params.get(key)
    if isinstance(val, list):
        return val[0] if val else None
    return val


def _bypass_user_from_env() -> dict[str, Any] | None:
    raw = (_get_setting("AUTH_BYPASS") or "").strip().lower()
    if raw not in {"1", "true", "yes"}:
        return None
    email = _get_setting("AUTH_BYPASS_EMAIL", "local@dev") or "local@dev"
    name = _get_setting("AUTH_BYPASS_NAME", "Local Dev") or "Local Dev"
    picture = _get_setting("AUTH_BYPASS_PICTURE", "") or ""
    return {"email": email, "name": name, "picture": picture, "bypass": True}


def _is_localhost_host(host: str | None) -> bool:
    if not host:
        return False
    base = host.split(":")[0].strip().lower()
    return base in {"localhost", "127.0.0.1", "::1"}


def _request_headers() -> dict[str, str]:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        req = getattr(ctx, "request", None) if ctx else None
        headers = getattr(req, "headers", None) if req else None
        if headers:
            return dict(headers)
    except Exception:
        pass
    return {}


def _request_scheme(host: str | None = None) -> str:
    headers = _request_headers()
    raw = headers.get("x-forwarded-proto") or headers.get("X-Forwarded-Proto")
    if raw:
        return raw.split(",")[0].strip().lower()
    if host is None:
        host = _request_host()
    return "http" if _is_localhost_host(host) else "https"


def _render_component_html(script: str, key: str) -> None:
    try:
        components.v1.html(script, height=0, key=key)
    except TypeError:
        components.v1.html(script, height=0)


def _inject_cookie_js(name: str, token: str, max_age: int, key: str = "auth_cookie_js") -> None:
    secure = _request_scheme(_request_host()) == "https"
    name_js = json.dumps(name)
    token_js = json.dumps(token)
    secure_js = "true" if secure else "false"
    script = f"""
    <script>
    (function() {{
      const name = {name_js};
      const value = encodeURIComponent({token_js});
      const maxAge = {max_age};
      const secure = {secure_js};
      let cookie = `${{name}}=${{value}}; path=/; max-age=${{maxAge}}; SameSite=Lax`;
      if (secure) cookie += "; Secure";
      document.cookie = cookie;
    }})();
    </script>
    """
    _render_component_html(script, key=key)


def _expire_cookie_js(name: str, key: str) -> None:
    _inject_cookie_js(name, "", 0, key=key)


def _redirect_js(url: str, key: str) -> None:
    target_js = json.dumps(url)
    script = f"""
    <script>
    (function() {{
      const target = {target_js};
      setTimeout(() => window.location.replace(target), 80);
    }})();
    </script>
    """
    _render_component_html(script, key=key)


def _parse_cookie_header(raw_cookie: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for part in raw_cookie.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        cookies[name.strip()] = value.strip()
    return cookies


def _cookie_header_values(raw_cookie: str, name: str) -> list[str]:
    values: list[str] = []
    for part in raw_cookie.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key.strip() == name:
            values.append(value.strip())
    return values


def _load_user_from_request_cookie(cfg: dict[str, Any]) -> dict[str, Any] | None:
    ignore_until = st.session_state.get("_logout_ignore_until")
    if isinstance(ignore_until, (int, float)):
        if time.time() < ignore_until:
            return None
        st.session_state.pop("_logout_ignore_until", None)
    tokens: list[tuple[str, str]] = []
    try:
        ctx = getattr(st, "context", None)
        cookies = getattr(ctx, "cookies", None) if ctx else None
        if cookies:
            raw_token = cookies.get(cfg["cookie_name"])
            if raw_token:
                tokens.append((str(raw_token), "context"))
    except Exception:
        pass

    headers = _request_headers()
    raw_cookie = headers.get("cookie") or headers.get("Cookie") or ""
    if raw_cookie:
        for value in _cookie_header_values(raw_cookie, cfg["cookie_name"]):
            if not any(value == token for token, _ in tokens):
                tokens.append((value, "header"))

    if not tokens:
        _debug_log("cookie_load tokens none")
        return None
    token_summary = ", ".join(
        f"{source}:{_token_fingerprint(token)}" for token, source in tokens
    )
    _debug_log(f"cookie_load tokens {token_summary}")
    serializer = _serializer(cfg["cookie_secret"])
    if len(tokens) > 1:
        _debug_log(f"cookie_load candidates={len(tokens)}")
    errors: list[str] = []
    for token, source in tokens:
        token = unquote(token)
        fp = _token_fingerprint(token)
        try:
            data = serializer.loads(token, max_age=cfg["cookie_ttl_seconds"])
        except SignatureExpired:
            errors.append(f"{source}:{fp}:expired")
            continue
        except BadSignature:
            errors.append(f"{source}:{fp}:bad_signature")
            continue
        except Exception as exc:
            errors.append(f"{source}:{fp}:{type(exc).__name__}")
            continue
        if isinstance(data, dict) and data.get("email"):
            _debug_log(f"cookie_load ok source={source} fp={fp}")
            return data
    if errors:
        st.session_state["_auth_cookie_last_error"] = errors[-1]
        _debug_log("cookie_load failed " + ";".join(errors))
    return None


def _request_host() -> str | None:
    try:
        headers = _request_headers()
        if headers:
            return (
                headers.get("x-forwarded-host")
                or headers.get("X-Forwarded-Host")
                or headers.get("host")
                or headers.get("Host")
            )
    except Exception:
        pass
    try:
        return st.get_option("server.address")
    except Exception:
        return None


def _normalize_redirect_uri(uri: str) -> str:
    parsed = urlparse(uri)
    if not parsed.scheme or not parsed.netloc:
        return uri
    path = parsed.path or "/"
    if path in {"", "/"}:
        path = "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _resolve_redirect_uri() -> str:
    configured = (_get_setting("AUTH_REDIRECT_URI", "http://localhost:8501") or "").strip()
    host = _request_host()
    if host:
        scheme = _request_scheme(host)
        return _normalize_redirect_uri(f"{scheme}://{host}")
    return _normalize_redirect_uri(configured or "http://localhost:8501/")


def _bypass_user_for_localhost() -> dict[str, Any] | None:
    raw = (_get_setting("AUTH_BYPASS_LOCALHOST") or "").strip().lower()
    if raw in {"1", "true", "yes"}:
        host_ok = True
    else:
        host = _request_host()
        host_ok = _is_localhost_host(host)
    if not host_ok:
        return None
    email = _get_setting("AUTH_LOCALHOST_EMAIL", "local@dev") or "local@dev"
    name = _get_setting("AUTH_LOCALHOST_NAME", "Local Dev") or "Local Dev"
    picture = _get_setting("AUTH_LOCALHOST_PICTURE", "") or ""
    return {"email": email, "name": name, "picture": picture, "bypass": True, "localhost": True}


def _clear_query_params() -> None:
    try:
        st.query_params.clear()  # type: ignore[attr-defined]
    except Exception:
        st.experimental_set_query_params()


def _rerun() -> None:
    try:
        st.rerun()  # type: ignore[attr-defined]
    except AttributeError:
        st.experimental_rerun()


def _get_cookie_manager(refresh: bool = False) -> CookieManager:
    run_id = None
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        ctx = get_script_run_ctx()
        run_id = getattr(ctx, "script_run_id", None)
    except Exception:
        run_id = None
    cached = st.session_state.get("_auth_cookie_manager")
    last_create_ts = st.session_state.get("_auth_cookie_manager_last_create_ts")
    if isinstance(cached, CookieManager):
        if not refresh:
            return cached
        try:
            if cached.ready():
                return cached
        except Exception:
            pass
        last_run_id = st.session_state.get("_auth_cookie_manager_run_id")
        if run_id is not None:
            if run_id == last_run_id:
                return cached
        else:
            if isinstance(last_create_ts, (int, float)) and time.time() - last_create_ts < 1.0:
                return cached
    cookies = CookieManager()
    st.session_state["_auth_cookie_manager"] = cookies
    st.session_state["_auth_cookie_manager_run_id"] = run_id
    st.session_state["_auth_cookie_manager_last_create_ts"] = time.time()
    return cookies


def _cookies_ready(cookies: CookieManager) -> bool:
    try:
        return cookies.ready()
    except Exception:
        return False


def _load_config() -> dict[str, Any]:
    return {
        "client_id": _require_setting("GOOGLE_CLIENT_ID"),
        "client_secret": _require_setting("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": _resolve_redirect_uri(),
        "cookie_secret": _require_setting("AUTH_COOKIE_SECRET"),
        "cookie_name": _get_setting("AUTH_COOKIE_NAME", "nabil_auth"),
        "cookie_ttl_seconds": max(1, _int_setting("AUTH_COOKIE_TTL_DAYS", 7)) * 86400,
    }


def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt="streamlit-google-oauth")


def _auth_log(message: str) -> None:
    try:
        _AUTH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with _AUTH_LOG_PATH.open("a", encoding="utf-8", errors="ignore") as handle:
            handle.write(f"{timestamp} {message}\n")
    except Exception:
        pass


AUTH_LOGGER = logging.getLogger("auth_google")


def _debug_enabled() -> bool:
    raw = (_get_setting("AUTH_DEBUG") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _ensure_logger() -> None:
    if not AUTH_LOGGER.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [auth_google] %(levelname)s: %(message)s")
        )
        AUTH_LOGGER.addHandler(handler)
    AUTH_LOGGER.setLevel(logging.DEBUG if _debug_enabled() else logging.INFO)


def _debug_log(message: str) -> None:
    _ensure_logger()
    AUTH_LOGGER.debug(message)
    _auth_log(message)


def _token_fingerprint(token: str) -> str:
    try:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:10]
    except Exception:
        return "unknown"


def _session_token_from_headers() -> str | None:
    headers = _request_headers()
    raw_cookie = headers.get("cookie") or headers.get("Cookie") or ""
    for value in _cookie_header_values(raw_cookie, "streamlit_session"):
        if value:
            return value
    return None


def _session_token() -> str | None:
    token = _session_token_from_headers()
    if token:
        return token
    token = st.session_state.get("_session_token")
    if isinstance(token, str) and token:
        return token
    return None


def _load_session_store() -> dict[str, tuple[float, dict[str, Any]]]:
    try:
        if _SESSION_STORE_PATH.exists():
            data = json.loads(_SESSION_STORE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {k: (v[0], v[1]) for k, v in data.items() if isinstance(v, list) and len(v) == 2}
    except Exception:
        pass
    return {}


def _save_session_store(store: dict[str, tuple[float, dict[str, Any]]]) -> None:
    try:
        _SESSION_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        serializable = {k: [v[0], v[1]] for k, v in store.items()}
        _SESSION_STORE_PATH.write_text(json.dumps(serializable), encoding="utf-8")
    except Exception:
        pass


def _session_store_cleanup(store: dict[str, tuple[float, dict[str, Any]]]) -> dict[str, tuple[float, dict[str, Any]]]:
    now = time.time()
    return {k: v for k, v in store.items() if now - v[0] <= _SESSION_TTL_SECONDS}


def _session_store_get(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    store = _session_store_cleanup(_load_session_store())
    entry = store.get(token)
    if entry and isinstance(entry, tuple) and len(entry) == 2:
        ts, user = entry
        if isinstance(user, dict):
            return user
    return None


def _session_store_set(token: str | None, user: dict[str, Any]) -> None:
    if not token or not isinstance(user, dict):
        return
    store = _session_store_cleanup(_load_session_store())
    store[token] = (time.time(), user)
    _save_session_store(store)


def _session_store_delete(token: str | None) -> None:
    if not token:
        return
    store = _session_store_cleanup(_load_session_store())
    if token in store:
        store.pop(token, None)
        _save_session_store(store)


def _is_code_used(code: str) -> bool:
    now = time.time()
    expired = [key for key, ts in _USED_CODES.items() if now - ts > _CODE_TTL_SECONDS]
    for key in expired:
        _USED_CODES.pop(key, None)
    return code in _USED_CODES


def _mark_code_used(code: str) -> None:
    _USED_CODES[code] = time.time()


def _cache_code_user(code: str, user: dict[str, Any]) -> None:
    _CODE_USERS[code] = (time.time(), user)


def _get_cached_code_user(code: str) -> dict[str, Any] | None:
    now = time.time()
    expired = [key for key, (ts, _) in _CODE_USERS.items() if now - ts > _CODE_TTL_SECONDS]
    for key in expired:
        _CODE_USERS.pop(key, None)
    cached = _CODE_USERS.get(code)
    if not cached:
        return None
    return cached[1]


def _state_serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt="streamlit-google-oauth-state")


def _decode_state(cfg: dict[str, Any], state: str | None, max_age_seconds: int = 900) -> dict[str, Any] | None:
    if not state:
        return None
    try:
        return _state_serializer(cfg["cookie_secret"]).loads(state, max_age=max_age_seconds)
    except Exception:
        return None


def _save_cookies(cookies: CookieManager) -> None:
    try:
        if not cookies.ready():
            return
    except Exception:
        return
    try:
        _debug_log("save_cookies start")
        cookies.save()
        _debug_log("save_cookies saved")
    except StreamlitDuplicateElementKey:
        # Avoid duplicate component key errors if save() is called twice in one run.
        return


def _ensure_auth_debug(cookies: CookieManager, cfg: dict[str, Any]) -> dict[str, Any]:
    debug = st.session_state.get("_auth_debug")
    if not isinstance(debug, dict):
        debug = {}
    try:
        cookies_ready = cookies.ready()
    except Exception:
        cookies_ready = False
    debug.update(
        {
            "cookie_name": cfg.get("cookie_name"),
            "cookie_ready": cookies_ready,
            "cookie_present": bool(cookies.get(cfg.get("cookie_name", ""))) if cookies_ready else False,
            "cookie_error": None,
        }
    )
    st.session_state["_auth_debug"] = debug
    _debug_log(
        f"auth_debug cookie_name={debug['cookie_name']} ready={debug['cookie_ready']} present={debug['cookie_present']}"
    )
    return debug


def _load_user_from_cookie(cookies: CookieManager, cfg: dict[str, Any]) -> dict[str, Any] | None:
    debug = _ensure_auth_debug(cookies, cfg)
    cookies_ready = bool(debug.get("cookie_ready"))
    _debug_log(
        f"cookie_load start ready={cookies_ready} present={debug.get('cookie_present')} error={debug.get('cookie_error')}"
    )
    if not cookies_ready:
        for attempt in range(8):
            time.sleep(0.25)
            try:
                if cookies.ready():
                    cookies_ready = True
                    debug["cookie_ready"] = True
                    _debug_log("cookie_load ready after wait")
                    break
            except Exception:
                pass
    if not cookies_ready:
        header_user = _load_user_from_request_cookie(cfg)
        if header_user:
            debug["cookie_error"] = None
            _auth_log("cookie_load header_ok")
            _debug_log("cookie_load header_ok fallback")
            return header_user
        debug["cookie_error"] = "not_ready"
        _auth_log("cookie_load not_ready")
        _debug_log("cookie_load not_ready")
        return None
    token = cookies.get(cfg["cookie_name"])
    if not token:
        debug["cookie_error"] = "missing"
        _auth_log("cookie_load missing")
        _debug_log("cookie_load missing")
        return None
    serializer = _serializer(cfg["cookie_secret"])
    try:
        data = serializer.loads(token, max_age=cfg["cookie_ttl_seconds"])
    except SignatureExpired:
        del cookies[cfg["cookie_name"]]
        _save_cookies(cookies)
        debug["cookie_error"] = "expired"
        _auth_log("cookie_load expired")
        _debug_log(f"cookie_load expired fp={_token_fingerprint(token)}")
        return None
    except BadSignature:
        del cookies[cfg["cookie_name"]]
        _save_cookies(cookies)
        debug["cookie_error"] = "bad_signature"
        _auth_log("cookie_load bad_signature")
        _debug_log(f"cookie_load bad_signature fp={_token_fingerprint(token)}")
        return None
    if isinstance(data, dict) and data.get("email"):
        debug["cookie_error"] = None
        _auth_log("cookie_load ok")
        _debug_log(f"cookie_load ok fp={_token_fingerprint(token)}")
        return data
    debug["cookie_error"] = "invalid_payload"
    _auth_log("cookie_load invalid_payload")
    _debug_log("cookie_load invalid_payload")
    return None


def _store_user_cookie(
    cookies: CookieManager,
    cfg: dict[str, Any],
    user: dict[str, Any],
    save: bool = True,
) -> None:
    serializer = _serializer(cfg["cookie_secret"])
    token = serializer.dumps(user)
    _debug_log("cookie_store attempt")
    try:
        if not cookies.ready():
            st.session_state["_pending_user_cookie"] = user
            st.session_state["_pending_user_cookie_token"] = token
            _auth_log("cookie_store pending (not ready)")
            _debug_log("cookie_store pending (not ready)")
            return
    except Exception:
        st.session_state["_pending_user_cookie"] = user
        st.session_state["_pending_user_cookie_token"] = token
        _auth_log("cookie_store pending (exception)")
        _debug_log("cookie_store pending (exception)")
        return
    cookies[cfg["cookie_name"]] = token
    if save:
        _save_cookies(cookies)
    _auth_log("cookie_store saved")
    _debug_log("cookie_store saved")


def _flush_pending_cookie(cookies: CookieManager, cfg: dict[str, Any]) -> None:
    _debug_log("flush_pending_cookie start")
    pending = st.session_state.get("_pending_user_cookie")
    if not isinstance(pending, dict):
        return
    try:
        if not cookies.ready():
            return
    except Exception:
        return
    serializer = _serializer(cfg["cookie_secret"])
    cookies[cfg["cookie_name"]] = serializer.dumps(pending)
    _save_cookies(cookies)
    st.session_state.pop("_pending_user_cookie", None)
    st.session_state.pop("_pending_user_cookie_token", None)
    _auth_log("cookie_store flushed")
    _debug_log("cookie_store flushed")


def _build_login_url(cfg: dict[str, Any], cookies: CookieManager) -> str:
    oauth = OAuth2Session(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scope=SCOPES,
        redirect_uri=cfg["redirect_uri"],
    )
    nonce = secrets.token_urlsafe(16)
    state_payload = {
        "nonce": nonce,
        "ts": int(time.time()),
        "redirect_uri": _normalize_redirect_uri(cfg["redirect_uri"]),
    }
    state = _state_serializer(cfg["cookie_secret"]).dumps(state_payload)
    url, returned_state = oauth.create_authorization_url(
        AUTHORIZATION_ENDPOINT,
        state=state,
        nonce=nonce,
        prompt="select_account",
    )
    _auth_log(f"auth_url redirect_uri={cfg['redirect_uri']} state={state[:16]}...")
    resolved_state = returned_state or state
    st.session_state[STATE_KEY] = resolved_state
    st.session_state[NONCE_KEY] = nonce
    try:
        if cookies.ready():
            cookies[STATE_COOKIE] = resolved_state
            cookies[NONCE_COOKIE] = nonce
            _save_cookies(cookies)
    except Exception:
        pass
    return url


def _exchange_code_for_user(
    cfg: dict[str, Any],
    code: str,
    state: str | None,
    cookies: CookieManager | None,
) -> dict[str, Any] | None:
    state_payload = _decode_state(cfg, state)
    expected_state = st.session_state.get(STATE_KEY)
    if not expected_state and cookies is not None:
        try:
            if cookies.ready():
                expected_state = cookies.get(STATE_COOKIE)
        except Exception:
            expected_state = None
    state_ok = bool(expected_state and state == expected_state)
    if not state_ok and state_payload:
        state_ok = True
    if not state_ok and _is_localhost_host(_request_host()):
        _auth_log("state mismatch ignored for localhost")
        state_ok = True
    if not state_ok:
        st.error("Invalid login state. Please try again.")
        return None

    redirect_uri = _normalize_redirect_uri(cfg["redirect_uri"])
    if isinstance(state_payload, dict):
        redirect_uri = _normalize_redirect_uri(state_payload.get("redirect_uri") or redirect_uri)

    _auth_log(f"exchange code={code[:12]}... redirect_uri={redirect_uri}")
    oauth = OAuth2Session(
        client_id=cfg["client_id"],
        client_secret=cfg["client_secret"],
        scope=SCOPES,
        redirect_uri=redirect_uri,
    )
    try:
        token = oauth.fetch_token(
            TOKEN_ENDPOINT,
            code=code,
            redirect_uri=redirect_uri,
        )
        _auth_log("token_fetch ok")
        try:
            _auth_log(f"token_keys={list(token.keys())} has_id_token={'id_token' in token}")
        except Exception as exc:
            _auth_log(f"token_keys error={exc}")
    except OAuthError as exc:
        detail = getattr(exc, "description", "") or getattr(exc, "error", "") or str(exc)
        _auth_log(f"exchange error={detail}")
        if "invalid_grant" in detail:
            st.session_state["_oauth_last_error"] = detail
            return None
        st.error(f"Login failed: {detail}. Check the redirect URI.")
        return None
    except Exception as exc:
        _auth_log(f"exchange exception={exc}")
        st.error(f"Login failed: {exc}")
        return None
    try:
        raw_id_token = token.get("id_token")
    except Exception as exc:
        _auth_log(f"token get id_token exception={exc}")
        st.error("Login failed: token parse error.")
        return None
    if not raw_id_token:
        _auth_log(f"missing id_token, token_keys={list(token.keys())}")
        try:
            userinfo = oauth.get("https://openidconnect.googleapis.com/v1/userinfo")
            if userinfo.status_code == 200:
                info = userinfo.json()
                _auth_log("userinfo ok")
                user = {
                    "sub": info.get("sub"),
                    "email": info.get("email"),
                    "email_verified": info.get("email_verified"),
                    "name": info.get("name") or info.get("given_name") or "",
                    "picture": info.get("picture") or "",
                }
                _cache_code_user(code, user)
                st.session_state[SESSION_KEY] = user
                return user
            _auth_log(f"userinfo status={userinfo.status_code}")
        except Exception as exc:
            _auth_log(f"userinfo exception={exc}")
        st.error("Login failed: missing id_token.")
        return None
    try:
        userinfo = oauth.get("https://openidconnect.googleapis.com/v1/userinfo")
        _auth_log(f"userinfo status={userinfo.status_code}")
        if userinfo.status_code == 200:
            info = userinfo.json()
            _auth_log("userinfo ok")
            user = {
                "sub": info.get("sub"),
                "email": info.get("email"),
                "email_verified": info.get("email_verified"),
                "name": info.get("name") or info.get("given_name") or "",
                "picture": info.get("picture") or "",
            }
            _cache_code_user(code, user)
            st.session_state[SESSION_KEY] = user
            return user
    except Exception as exc:
        _auth_log(f"userinfo exception={exc}")

    try:
        _auth_log("id_token verify start")
        idinfo = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            cfg["client_id"],
        )
    except Exception as exc:
        _auth_log(f"id_token verify exception={exc}")
        st.error("Login failed: invalid id_token.")
        return None
    if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        st.error("Login failed: invalid issuer.")
        _auth_log("id_token invalid issuer")
        return None

    expected_nonce = st.session_state.get(NONCE_KEY)
    if not expected_nonce and cookies is not None:
        try:
            if cookies.ready():
                expected_nonce = cookies.get(NONCE_COOKIE)
        except Exception:
            expected_nonce = None
    if not expected_nonce and state_payload:
        expected_nonce = state_payload.get("nonce")
    if expected_nonce and idinfo.get("nonce") != expected_nonce:
        st.error("Login failed: invalid nonce.")
        _auth_log("id_token invalid nonce")
        return None
    _auth_log("id_token ok")

    user = {
        "sub": idinfo.get("sub"),
        "email": idinfo.get("email"),
        "email_verified": idinfo.get("email_verified"),
        "name": idinfo.get("name") or idinfo.get("given_name") or "",
        "picture": idinfo.get("picture") or "",
    }
    _auth_log("user created")
    _cache_code_user(code, user)
    st.session_state[SESSION_KEY] = user
    return user


def _app_url() -> str:
    return (_get_setting("APP_URL", "/") or "/").strip()


def get_current_user(cookies: CookieManager | None = None) -> dict[str, Any] | None:
    cfg = _load_config()
    if cookies is None:
        cookies = _get_cookie_manager(refresh=True)
    _flush_pending_cookie(cookies, cfg)
    debug = _ensure_auth_debug(cookies, cfg)
    user = st.session_state.get(SESSION_KEY)
    if user:
        debug["cookie_error"] = None
        return user
    user = _load_user_from_cookie(cookies, cfg)
    if user:
        st.session_state[SESSION_KEY] = user
    return user


def _render_home_screen(
    auth_url: str,
    user: dict[str, Any] | None = None,
    app_url: str | None = None,
) -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        :root {
            --bg-1: #0b1026;
            --bg-2: #0e1a3a;
            --bg-3: #1a0f2f;
            --card: rgba(18, 26, 58, 0.82);
            --line: rgba(255, 255, 255, 0.08);
            --text: #f4f6ff;
            --muted: #b8c2e6;
            --accent: #40f0c7;
            --accent-2: #f5c055;
        }

        * { box-sizing: border-box; }
        section[data-testid="stSidebar"] { display: none !important; }

        [data-testid="stAppViewContainer"] {
            background:
              radial-gradient(1200px 600px at 10% 10%, rgba(64, 240, 199, 0.18), transparent 60%),
              radial-gradient(900px 500px at 90% 0%, rgba(245, 192, 85, 0.18), transparent 55%),
              radial-gradient(900px 500px at 80% 80%, rgba(122, 98, 255, 0.18), transparent 60%),
              linear-gradient(160deg, var(--bg-1), var(--bg-2) 55%, var(--bg-3));
        }

        [data-testid="stHeader"], [data-testid="stToolbar"], footer {
            visibility: hidden;
            height: 0;
        }

        .block-container { padding: 0; }

        .home-shell {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem 3.5rem;
            color: var(--text);
            font-family: "Space Grotesk", sans-serif;
        }

        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 3rem;
        }

        .topbar-right {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 0.75rem;
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.4px;
        }

        .brand-mark {
            width: 56px;
            height: 56px;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--accent), #3a7cff);
            box-shadow: 0 12px 24px rgba(64, 240, 199, 0.25);
            margin-left: 6px;
        }

        .brand-logo {
            width: 62px;
            height: 62px;
            border-radius: 14px;
            object-fit: contain;
            box-shadow: 0 12px 24px rgba(64, 240, 199, 0.22);
            margin-left: 6px;
        }

        .brand span { color: var(--accent); }

        .status-pill {
            padding: 0.35rem 0.9rem;
            border-radius: 999px;
            border: 1px solid var(--line);
            background: rgba(255, 255, 255, 0.04);
            color: var(--muted);
            font-size: 0.9rem;
        }

        .brand-strip {
            display: flex;
            gap: 0.6rem;
            align-items: center;
        }

        .brand-strip--hero .brand-pill {
            height: 252px;
            min-width: 252px;
            padding: 0.5rem 0.8rem;
            border-radius: 32px;
        }

        .brand-pill {
            height: 216px;
            min-width: 216px;
            padding: 0.5rem 0.8rem;
            border-radius: 28px;
            border: 1px solid var(--line);
            background: rgba(15, 23, 42, 0.6);
            box-shadow: 0 12px 24px rgba(8, 12, 32, 0.35);
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .brand-pill img {
            height: 100%;
            width: auto;
            object-fit: contain;
        }

        .hero {
            display: grid;
            grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
            gap: 2.5rem;
            align-items: center;
        }

        .hero h1 {
            font-family: "Fraunces", serif;
            font-size: clamp(2.5rem, 4vw, 4.2rem);
            margin: 0 0 1rem;
            line-height: 1.05;
        }

        .hero p {
            font-size: 1.1rem;
            color: var(--muted);
            margin-bottom: 2rem;
        }

        .cta-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 1rem;
        }

        .cta {
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            padding: 0.85rem 1.5rem;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--accent), #5ce8ff);
            color: #081225;
            font-weight: 700;
            text-decoration: none;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .cta:hover {
            transform: translateY(-2px);
            box-shadow: 0 16px 30px rgba(64, 240, 199, 0.3);
        }

        .cta.secondary {
            background: transparent;
            border: 1px solid var(--line);
            color: var(--text);
        }

        .cta-note {
            color: var(--muted);
            font-size: 0.95rem;
        }

        .hero-card {
            border-radius: 24px;
            padding: 1.8rem;
            background: var(--card);
            border: 1px solid var(--line);
            box-shadow: 0 24px 60px rgba(8, 12, 32, 0.5);
            position: relative;
            overflow: hidden;
        }

        .hero-card::before {
            content: "";
            position: absolute;
            inset: -40% 40% auto auto;
            width: 160px;
            height: 160px;
            background: radial-gradient(circle, rgba(245, 192, 85, 0.45), transparent 70%);
            filter: blur(0px);
            animation: float 9s ease-in-out infinite;
        }

        .kpi {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
            margin-top: 1.2rem;
        }

        .kpi-card {
            padding: 1rem;
            border-radius: 16px;
            border: 1px solid var(--line);
            background: rgba(10, 16, 38, 0.55);
        }

        .kpi-card h4 {
            margin: 0 0 0.4rem;
            font-weight: 600;
            color: var(--muted);
        }

        .kpi-card strong {
            font-size: 1.6rem;
            color: var(--accent-2);
        }

        .feature-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin-top: 3rem;
        }

        .feature {
            padding: 1.2rem 1.3rem;
            border-radius: 18px;
            border: 1px solid var(--line);
            background: rgba(12, 18, 40, 0.6);
        }

        .feature h3 {
            margin: 0 0 0.5rem;
            font-size: 1.1rem;
        }

        .feature p {
            margin: 0;
            color: var(--muted);
            font-size: 0.95rem;
        }

        .marquee {
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
            margin-top: 2rem;
            color: var(--muted);
            font-size: 0.95rem;
        }

        @keyframes float {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(-14px, 10px); }
        }

        @media (max-width: 980px) {
            .hero { grid-template-columns: 1fr; }
            .feature-grid { grid-template-columns: 1fr; }
            .topbar {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    auth_error = st.session_state.get("_oauth_last_error")
    if auth_error:
        st.error(f"Login failed: {auth_error}. Try again.")

    safe_url = html.escape(auth_url, quote=True)
    safe_app_url = html.escape(app_url or _app_url(), quote=True)
    auth_link_attrs = ""
    logo_uri = _get_logo_data_uri()
    logo_html = (
        f'<img class="brand-logo" src="{logo_uri}" alt="Chronoplan logo" />'
        if logo_uri
        else '<div class="brand-mark"></div>'
    )
    brand_strip = brand_strip_html("hero")
    signed_in_note = ""
    if user:
        name = user.get("name") or user.get("email") or "User"
        email = user.get("email") or ""
        signed_in_note = f"Signed in as {html.escape(name)}"
        if email and email not in signed_in_note:
            signed_in_note += f" ({html.escape(email)})"
        signed_in_note = f'<div class="cta-note">{signed_in_note}</div>'
    primary_cta = f'<a class="cta" href="{safe_app_url}">Open Project Progress</a>'
    secondary_cta = f'<a class="cta secondary" href="{safe_url}"{auth_link_attrs}>Switch account</a>'
    session_note = '<div class="cta-note">Session secured with signed cookies.</div>'
    if not user:
        primary_cta = f'<a class="cta" href="{safe_url}"{auth_link_attrs}>Continue with Google</a>'
        secondary_cta = ""
        signed_in_note = ""
        session_note = ""

    page_html = f"""
    <div class="home-shell">
      <div class="topbar">
        <div class="brand">
          {logo_html}
          <div>Project Progress <span>Studio</span></div>
        </div>
        <div class="topbar-right">
          <div class="status-pill">Secure access via Google OAuth</div>
          {brand_strip}
        </div>
      </div>

      <div class="hero">
        <div>
          <h1>Clarity for every milestone, in one place.</h1>
          <p>
            Track S-curves, KPIs, and WBS progress with a view that is simple,
            visual, and decision-ready. Upload your file, see the story.
          </p>
          <div class="cta-row">
            {primary_cta}
            {secondary_cta}
            {signed_in_note}
            {session_note}
          </div>
          <div class="marquee">
            <span>Weekly progress</span>
            <span>Earned value</span>
            <span>Schedule variance</span>
            <span>WBS drilldown</span>
          </div>
        </div>
        <div class="hero-card">
          <h3>Live project pulse</h3>
          <p>See early signals, reduce surprises, and keep stakeholders aligned.</p>
          <div class="kpi">
            <div class="kpi-card">
              <h4>Completion</h4>
              <strong>88%</strong>
            </div>
            <div class="kpi-card">
              <h4>Schedule</h4>
              <strong>+3.1%</strong>
            </div>
            <div class="kpi-card">
              <h4>Milestones</h4>
              <strong>24</strong>
            </div>
            <div class="kpi-card">
              <h4>Risk</h4>
              <strong>Low</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="feature-grid">
        <div class="feature">
          <h3>Instant narrative</h3>
          <p>Turn dense sheets into visuals that highlight what matters this week.</p>
        </div>
        <div class="feature">
          <h3>WBS focus</h3>
          <p>Zoom in by work package and compare planned vs actual outcomes.</p>
        </div>
        <div class="feature">
          <h3>Stakeholder ready</h3>
          <p>Clean visuals and exportable insights for reviews and reporting.</p>
        </div>
      </div>
    </div>
    """

    clean_html = textwrap.dedent(page_html).strip()
    clean_html = "\n".join(line.lstrip() for line in clean_html.splitlines())
    st.markdown(clean_html, unsafe_allow_html=True)


def _render_login_screen(auth_url: str) -> None:
    _render_home_screen(auth_url, user=None)


def require_login() -> dict[str, Any]:
    _auth_log("require_login start")
    bypass_user = _bypass_user_from_env()
    if bypass_user:
        st.session_state[SESSION_KEY] = bypass_user
        _auth_log("require_login bypass env")
        return bypass_user
    localhost_user = _bypass_user_for_localhost()
    if localhost_user:
        st.session_state[SESSION_KEY] = localhost_user
        _auth_log("require_login bypass localhost")
        return localhost_user

    session_token = _session_token()
    # Persist any existing session user into the store to make refreshes resilient.
    _existing = st.session_state.get(SESSION_KEY)
    if isinstance(_existing, dict) and _existing.get("email"):
        _session_store_set(session_token, _existing)
    store_user = _session_store_get(session_token)
    if store_user:
        st.session_state[SESSION_KEY] = store_user
        _auth_log("require_login session store user")
        return store_user

    if st.session_state.pop("_force_home", False):
        try:
            st.switch_page("pages/0_Home.py")  # type: ignore[attr-defined]
        except Exception:
            _rerun()
        st.stop()

    cfg = _load_config()
    params = _get_query_params()
    code = _query_value(params, "code")
    state = _query_value(params, "state")

    await_cookie = st.session_state.get("_await_auth_cookie")
    if isinstance(await_cookie, (int, float)):
        cookies = _get_cookie_manager(refresh=True)
        user = _load_user_from_request_cookie(cfg)
        if not user:
            user = _load_user_from_cookie(cookies, cfg) if _cookies_ready(cookies) else None
        if user:
            st.session_state[SESSION_KEY] = user
            st.session_state.pop("_await_auth_cookie", None)
            _auth_log("require_login awaited cookie user")
            return user
        if time.time() - await_cookie < 4:
            st.info("Finalizing sign-in...")
            time.sleep(0.25)
            _rerun()
        st.session_state.pop("_await_auth_cookie", None)

    inflight = st.session_state.get("_oauth_in_flight")
    if isinstance(inflight, (int, float)):
        if time.time() - inflight < 8:
            st.info("Completing sign-in...")
            st.stop()
        st.session_state.pop("_oauth_in_flight", None)

    user = st.session_state.get(SESSION_KEY)
    if user:
        if not _load_user_from_request_cookie(cfg):
            try:
                token = st.session_state.get("_pending_user_cookie_token")
                if not isinstance(token, str):
                    token = _serializer(cfg["cookie_secret"]).dumps(user)
                _inject_cookie_js(
                    cfg["cookie_name"],
                    token,
                    cfg["cookie_ttl_seconds"],
                    key="auth_cookie_js_session",
                )
                st.session_state.pop("_pending_user_cookie_token", None)
            except Exception as exc:
                _auth_log(f"cookie_js set failed={exc}")
        if isinstance(st.session_state.get("_pending_user_cookie"), dict):
            try:
                cookies = _get_cookie_manager(refresh=True)
                _flush_pending_cookie(cookies, cfg)
                _ensure_auth_debug(cookies, cfg)
            except Exception:
                pass
        _auth_log("require_login session user")
        return user

    if code:
        processed_code = st.session_state.get("_oauth_processed_code")
        cached_user = _get_cached_code_user(code)
        if cached_user and _is_localhost_host(_request_host()):
            st.session_state[SESSION_KEY] = cached_user
            _auth_log("require_login code cached user")
            return cached_user
        if st.session_state.get("_oauth_flow_handled") or processed_code == code or _is_code_used(code):
            _clear_query_params()
            user = _load_user_from_request_cookie(cfg)
            if user:
                st.session_state[SESSION_KEY] = user
                _auth_log("require_login code duplicate -> cookie user")
                return user
            _rerun()
        inflight = st.session_state.get("_oauth_in_flight")
        if isinstance(inflight, (int, float)) and time.time() - inflight < 8:
            st.info("Completing sign-in...")
            st.stop()
        st.session_state["_oauth_in_flight"] = time.time()
        st.session_state["_oauth_processed_code"] = code
        user = None
        try:
            _auth_log("require_login code exchange start")
            user = _exchange_code_for_user(cfg, code, state, None)
            st.session_state.pop(STATE_KEY, None)
            st.session_state.pop(NONCE_KEY, None)
            if user:
                _mark_code_used(code)
                st.session_state[SESSION_KEY] = user
                _session_store_set(session_token, user)
                try:
                    cookies = _get_cookie_manager(refresh=True)
                    _flush_pending_cookie(cookies, cfg)
                    _store_user_cookie(cookies, cfg, user, save=False)
                    _save_cookies(cookies)
                    _auth_log("require_login code user stored")
                except Exception as exc:
                    _auth_log(f"require_login cookie store failed={exc}")
                try:
                    token = _serializer(cfg["cookie_secret"]).dumps(user)
                    _inject_cookie_js(
                        cfg["cookie_name"],
                        token,
                        cfg["cookie_ttl_seconds"],
                        key="auth_cookie_js_code",
                    )
                except Exception as exc:
                    _auth_log(f"cookie_js set failed={exc}")
                st.session_state["_await_auth_cookie"] = time.time()
                try:
                    _clear_query_params()
                except Exception:
                    pass
                return user
        finally:
            st.session_state.pop("_oauth_in_flight", None)
        auth_url = _build_login_url(cfg, _get_cookie_manager(refresh=True))
        _render_login_screen(auth_url)
        _auth_log("require_login code failed -> login screen")
        st.stop()

    request_user = _load_user_from_request_cookie(cfg)
    if request_user:
        st.session_state[SESSION_KEY] = request_user
        _auth_log("require_login request cookie user")
        return request_user

    cookies = _get_cookie_manager(refresh=True)
    _flush_pending_cookie(cookies, cfg)
    _ensure_auth_debug(cookies, cfg)

    user = _load_user_from_cookie(cookies, cfg)
    if user:
        st.session_state[SESSION_KEY] = user
        _auth_log("require_login cookie user")
        _session_store_set(session_token, user)
        return user
    if not _cookies_ready(cookies):
        request_user = _load_user_from_request_cookie(cfg)
        if request_user:
            st.session_state[SESSION_KEY] = request_user
            _auth_log("require_login request cookie user (not ready manager)")
            return request_user
        session_user = st.session_state.get(SESSION_KEY)
        awaiting = st.session_state.get("_await_auth_cookie")
        has_pending = isinstance(awaiting, (int, float)) or isinstance(
            st.session_state.get("_pending_user_cookie"), dict
        )
        waits = st.session_state.get("_auth_cookie_waits", 0)
        if has_pending and waits < 10:
            st.session_state["_auth_cookie_waits"] = waits + 1
            if not isinstance(awaiting, (int, float)):
                st.session_state["_await_auth_cookie"] = time.time()
            st.info("Finalizing sign-in...")
            time.sleep(0.25)
            _rerun()
        st.session_state.pop("_await_auth_cookie", None)
        st.session_state.pop("_pending_user_cookie", None)
        st.session_state.pop("_pending_user_cookie_token", None)
        st.session_state.pop("_auth_cookie_waits", None)
        if isinstance(session_user, dict) and session_user.get("email"):
            _auth_log("require_login fallback to session user")
            _session_store_set(session_token, session_user)
            return session_user

    auth_url = _build_login_url(cfg, cookies)
    _render_login_screen(auth_url)
    _auth_log("require_login render login")
    st.stop()


def logout() -> None:
    cfg = _load_config()
    cookies = _get_cookie_manager()
    session_token = _session_token()
    if _cookies_ready(cookies):
        if cookies.get(cfg["cookie_name"]):
            del cookies[cfg["cookie_name"]]
        if cookies.get(STATE_COOKIE):
            del cookies[STATE_COOKIE]
        if cookies.get(NONCE_COOKIE):
            del cookies[NONCE_COOKIE]
        _save_cookies(cookies)
    else:
        _expire_cookie_js(cfg["cookie_name"], key="auth_cookie_js_logout")
        _expire_cookie_js(STATE_COOKIE, key="auth_cookie_js_logout_state")
        _expire_cookie_js(NONCE_COOKIE, key="auth_cookie_js_logout_nonce")
        _redirect_js("/Home", key="auth_cookie_js_logout_redirect")
        st.session_state["_logout_ignore_until"] = time.time() + 5
    st.session_state.pop(SESSION_KEY, None)
    st.session_state.pop(STATE_KEY, None)
    st.session_state.pop(NONCE_KEY, None)
    st.session_state["_force_home"] = True
    st.session_state.pop("_await_auth_cookie", None)
    st.session_state.pop("_auth_cookie_waits", None)
    st.session_state.pop("_pending_user_cookie", None)
    st.session_state.pop("_pending_user_cookie_token", None)
    _session_store_delete(session_token)
    _clear_query_params()
    st.stop()


def render_auth_sidebar(
    user: dict[str, Any] | None,
    show_logo: bool = True,
    show_branding: bool = True,
) -> None:
    if not user:
        return
    with st.sidebar:
        if show_logo:
            logo_uri = _get_logo_data_uri()
            if logo_uri:
                st.markdown(
                    f'<div style="margin: 10px 0 18px; display: flex; justify-content: center; align-items: center; width: 100%; padding-left: 12px;">'
                    f'<img src="{logo_uri}" alt="Chronoplan logo" '
                    f'style="width: 230px; max-width: 92%; height: auto; display: block; transform: translateX(6px);" />'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        name = user.get("name") or user.get("email") or "User"
        email = user.get("email")
        picture = user.get("picture")
        if picture:
            avatar_html = (
                f'<img class="auth-avatar" src="{html.escape(picture)}" alt="avatar" />'
            )
        else:
            initial = (name.strip()[:1] or "?").upper()
            avatar_html = (
                f'<div class="auth-avatar placeholder">{html.escape(initial)}</div>'
            )
        email_html = (
            f'<div class="auth-email">{html.escape(email)}</div>' if email else ""
        )
        with st.container(key="auth_card"):
            st.markdown(
                f"""
                <div class="auth-title">Account</div>
                <div class="auth-row">
                  {avatar_html}
                  <div class="auth-meta">
                    <div class="auth-name">{html.escape(name)}</div>
                    {email_html}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("\u23fb", key="auth_logout_btn", help="Sign out"):
                logout()
                return
        if show_branding:
            company_logo = _custom_logo_data_uri("company")
            client_logo = _custom_logo_data_uri("client")
            missing_roles: list[tuple[str, str]] = []
            if not company_logo:
                missing_roles.append(("company", "Company"))
            if not client_logo:
                missing_roles.append(("client", "Client"))
            if missing_roles:
                st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
                with st.container(key="brand_card"):
                    st.markdown(
                        '<div class="brand-title">Branding</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        '<div class="brand-note">To remove an existing logo, click the center of its logo tile.</div>',
                        unsafe_allow_html=True,
                    )
                    cols = st.columns(len(missing_roles), gap="small")
                    for col, (role, label) in zip(cols, missing_roles):
                        with col:
                            st.markdown(
                                f'<div class="brand-label">{html.escape(label)} logo</div>',
                                unsafe_allow_html=True,
                            )
                            uploaded = st.file_uploader(
                                f"Upload {label} logo",
                                type=["png", "jpg", "jpeg", "svg"],
                                key=f"logo_upload_{role}",
                                label_visibility="collapsed",
                            )
                            if uploaded is not None:
                                file_key = f"{uploaded.name}:{uploaded.size}"
                                state_key = f"_logo_upload_{role}_key"
                                if st.session_state.get(state_key) != file_key:
                                    _save_custom_logo(role, uploaded)
                                    st.session_state[state_key] = file_key
                                    _rerun()


def render_contact_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
        with st.container(key="contact_card"):
            st.markdown(
                """
                <div class="contact-title">Need help or feedback?</div>
                <div class="contact-note">
                  Reach the ChronoPlan developer on Discord.
                </div>
                <a class="contact-link" href="https://discord.gg/N7v8WwdRP8" target="_blank" rel="noopener noreferrer">
                  Join the ChronoPlan Discord
                </a>
                """,
                unsafe_allow_html=True,
            )
