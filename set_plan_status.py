#!/usr/bin/env python3
"""
Helper to set plan status in billing.sqlite for testing.
Usage:
  python set_plan_status.py --email user@example.com --status trialing --trial-end "2025-01-01T00:00:00Z"
  python set_plan_status.py --email user@example.com --status active --plan-end "2026-12-31T23:59:59Z"
  python set_plan_status.py --email user@example.com --status trialing --days-left 2
"""

import argparse
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Set plan status for testing")
    parser.add_argument("--email", required=True, help="Email of account to update")
    parser.add_argument("--status", choices=["trialing", "active"], default="trialing", help="Plan status")
    parser.add_argument("--trial-end", help="ISO format trial end date (ex: 2025-01-01T00:00:00Z)")
    parser.add_argument("--plan-end", help="ISO format plan end date (ex: 2026-12-31T23:59:59Z)")
    parser.add_argument("--days-left", type=int, help="Set trial to expire in N days")
    
    args = parser.parse_args()
    
    db_path = Path("artifacts") / "billing.sqlite"
    if not db_path.exists():
        print(f"Error: {db_path} not found. Please login first to create the account.")
        return 1
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Build update values
    trial_end = args.trial_end
    plan_end = args.plan_end
    
    if args.days_left is not None:
        expiry = datetime.now(timezone.utc) + timedelta(days=args.days_left)
        trial_end = expiry.isoformat().replace("+00:00", "Z")
        print(f"[*] Setting trial to expire in {args.days_left} day(s): {trial_end}")
    
    # Update account
    cursor.execute(
        "UPDATE accounts SET plan_status = ?, trial_end = ?, plan_end = ? WHERE email = ?",
        (args.status, trial_end, plan_end, args.email)
    )
    conn.commit()
    
    # Verify
    cursor.execute("SELECT id, email, plan_status, trial_end, plan_end FROM accounts WHERE email = ?", (args.email,))
    row = cursor.fetchone()
    
    if row:
        print(f"[+] Updated account {args.email}")
        print(f"    Status: {row[2]}")
        print(f"    Trial end: {row[3]}")
        print(f"    Plan end: {row[4]}")
        result = 0
    else:
        print(f"[!] Account {args.email} not found")
        result = 1
    
    conn.close()
    return result

if __name__ == "__main__":
    exit(main())
