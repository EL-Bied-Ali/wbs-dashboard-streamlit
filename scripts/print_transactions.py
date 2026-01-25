import json
import os

from billing_store import fetch_remote_transactions


def main() -> None:
    email = os.environ.get("TX_EMAIL", "").strip().lower()
    if not email:
        raise SystemExit("Set TX_EMAIL env var.")
    limit = int(os.environ.get("TX_LIMIT", "3"))
    txs = fetch_remote_transactions(email, limit=limit)
    print(json.dumps(txs[:limit], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
