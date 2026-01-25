# WBS Dashboard (Streamlit)

Streamlit dashboards to explore project progress data with S-curves, KPIs, and WBS details. The repo hosts the main dashboard plus a small WBS extractor UI.

## Apps
- Main dashboard: `streamlit run app.py` (uses bundled demo data; upload your Excel file to drive live charts).
- WBS extractor UI: `streamlit run wbs_app/wbs_app.py` (kept separate so it can have its own layout/theme).
- Quick smoke test: `streamlit run test_app.py` to confirm Streamlit/pandas/plotly install.

## Getting started
1) Use Python 3.12 (see `runtime.txt`).
2) Create a virtual env and install deps:
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```
3) Run one of the apps above.

## Data and settings
- Upload an Excel progress file when prompted; column mappings live in `data.py` (`MAPPINGS` dict).
- If you deploy the dashboard alongside the WBS UI, set `WBS_URL` (env var or Streamlit secret) so the cross-link points to the right host/port. The app defaults to `http://localhost:8502` when running locally.

## Auth (Streamlit OIDC)
This app uses Streamlit's OIDC login (`st.login`, `st.user`). Configure secrets (or Streamlit Cloud secrets) like:
```
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "set-a-long-random-string"
client_id = "..."
client_secret = "..."
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```
Notes:
- The redirect URI must match exactly in Google Console, including `/oauth2callback`.
- For Streamlit Cloud, use `https://your-app.streamlit.app/oauth2callback`.
- `cookie_secret` must stay stable across restarts or all sessions are invalidated.
- Optional: set `DEV_BYPASS=1` (env var or secret) to allow local bypass for dev-only testing.

## Repo notes
- `.gitignore` excludes virtualenvs, caches, Excel exports, and large videos so the repo stays light.
- Everything else can be committed normally; keep the two apps independent so each retains its theme.

## Paddle webhooks (billing sync)
To keep `plan_status`/`plan_end` in sync after checkout, run the lightweight webhook server:

```bash
python scripts/paddle_webhook_server.py
```

Configure secrets (env vars or `.streamlit/secrets.toml`):
```
PADDLE_WEBHOOK_SECRET = "your-webhook-secret"
PADDLE_WEBHOOK_PORT = "8001"
PADDLE_WEBHOOK_PATH = "/webhook/paddle"
```

Then set the webhook URL in Paddle to:
```
http://YOUR_HOST:8001/webhook/paddle
```

The handler maps Paddle subscription events to:
- `plan_status = active|trialing`
- `plan_end` from the current billing period end date

## R2 backups (artifacts)
The app can create daily backups of billing and project artifacts in Cloudflare R2.

Setup:
1) Create an R2 bucket in your Cloudflare account (e.g. `chronoplan-backups`).
2) Create an R2 API token with read/write access to that bucket.
3) Set these secrets (Streamlit secrets or env vars):
   - `R2_ACCOUNT_ID`
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_BUCKET`
   - `R2_ENDPOINT` (optional; defaults to `<account_id>.r2.cloudflarestorage.com`)
   - `R2_BACKUP_KEEP` (optional; defaults to 14)
   - `ENABLE_R2_BACKUPS` (optional; default 0)

Behavior:
- The Router page triggers a lazy daily backup if the last backup is older than 24h.
- Admins can trigger a manual backup from the Billing page (Admin billing diagnostics).
