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

## Google auth
This app supports Google OAuth with a signed cookie session. Configure the following secrets or env vars:
```
GOOGLE_CLIENT_ID = "..."
GOOGLE_CLIENT_SECRET = "..."
AUTH_COOKIE_SECRET = "set-a-long-random-string"
AUTH_REDIRECT_URI = "http://localhost:8501"
AUTH_COOKIE_TTL_DAYS = "7"
```
Notes:
- Add your redirect URI(s) in the Google Console (local and Streamlit Cloud URLs).
- `AUTH_COOKIE_SECRET` must stay stable across restarts or all sessions are invalidated.

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
