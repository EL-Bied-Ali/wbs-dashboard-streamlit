# Paddle Webhook Worker (Cloudflare)

This worker receives Paddle webhooks, verifies the signature, and stores the
latest plan status in Cloudflare KV. The Streamlit app can then read the
status from the worker.

## 1) Create KV namespace
```
wrangler kv:namespace create BILLING_KV
```
Copy the `id` into your `wrangler.toml`.

## 2) Create wrangler.toml
Create `workers/wrangler.toml` with:
```
name = "chronoplan-billing"
main = "paddle_webhook_worker.js"
compatibility_date = "2024-01-01"

kv_namespaces = [
  { binding = "BILLING_KV", id = "YOUR_KV_NAMESPACE_ID" }
]
```

## 3) Set secrets
```
wrangler secret put PADDLE_WEBHOOK_SECRET
wrangler secret put BILLING_API_TOKEN
```

`BILLING_API_TOKEN` is used by the Streamlit app when it calls `/account`.

## 4) Deploy
```
wrangler deploy
```

You will get a URL like:
`https://chronoplan-billing.<your-account>.workers.dev`

## 5) Configure Paddle webhooks
Set the webhook URL to:
`https://chronoplan-billing.<your-account>.workers.dev/webhook/paddle`

Subscribe to:
- subscription.activated
- subscription.updated
- subscription.canceled
- transaction.completed

## 6) Configure Streamlit
Add to `.streamlit/secrets.toml`:
```
BILLING_API_URL = "https://chronoplan-billing.<your-account>.workers.dev"
BILLING_API_TOKEN = "YOUR_TOKEN"
```
