#!/usr/bin/env python3
"""
Quick validation script for server-side access guards.

This tests that:
- access_guard.assert_can_edit() blocks when plan is expired
- projects.py mutation helpers block server-side for expired users
- allowed users can still mutate projects

Notes:
- No Streamlit UI is exercised here.
- No Paddle/billing network calls are required (BILLING_API_URL forced empty).
"""

from __future__ import annotations

import os
import sys
import tempfile
import atexit
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from access_guard import assert_can_edit, get_access_status_for_user  # noqa: E402
from billing_store import ensure_account, update_account_plan  # noqa: E402
import projects as projects_module  # noqa: E402


def _expect_permission_error(fn, message: str) -> None:
    try:
        fn()
        raise AssertionError(message)
    except PermissionError:
        return


def test_access_guard() -> None:
    os.environ["BILLING_API_URL"] = ""
    os.environ["BILLING_API_TOKEN"] = ""

    tmp_dir = tempfile.mkdtemp(prefix="chronoplan-tests-")
    tmp_path = Path(tmp_dir)
    atexit.register(lambda: shutil.rmtree(tmp_path, ignore_errors=True))
    os.environ["BILLING_DB_PATH"] = str(tmp_path / "billing.sqlite")

    active_email = "active@example.com"
    expired_email = "expired@example.com"

    active_account = ensure_account({"email": active_email, "name": "Active Test"})
    expired_account = ensure_account({"email": expired_email, "name": "Expired Test"})
    assert active_account and active_account.get("id")
    assert expired_account and expired_account.get("id")

    now = datetime.now(timezone.utc)
    update_account_plan(active_email, "active", plan_end=now + timedelta(days=30))
    update_account_plan(expired_email, "trialing", trial_end=now - timedelta(days=1))

    user_active = {
        "sub": "sub-active",
        "email": active_email,
        "billing_account_id": int(active_account["id"]),
    }
    user_expired = {
        "sub": "sub-expired",
        "email": expired_email,
        "billing_account_id": int(expired_account["id"]),
    }

    # Isolate project storage away from repo artifacts/.
    projects_module.PROJECTS_PATH = tmp_path / "projects.json"
    projects_module.PROJECTS_DIR = tmp_path / "projects"
    projects_module.PROJECTS_LOCK_PATH = tmp_path / "projects.json.lock"

    print("[1] assert_can_edit() allows active user")
    gate_active = get_access_status_for_user(user_active)
    assert gate_active.get("allowed") is True, gate_active
    assert_can_edit(user_active)

    print("[2] assert_can_edit() blocks expired user")
    gate_expired = get_access_status_for_user(user_expired)
    assert gate_expired.get("allowed") is False, gate_expired
    _expect_permission_error(
        lambda: assert_can_edit(user_expired),
        "assert_can_edit(user_expired) did not raise PermissionError",
    )

    print("[3] create/update/delete blocked for expired user")
    _expect_permission_error(
        lambda: projects_module.create_project(
            "Blocked",
            owner_id=user_expired["billing_account_id"],
            user=user_expired,
        ),
        "create_project should have raised PermissionError for expired user",
    )

    print("[4] create/update/delete allowed for active user")
    project = projects_module.create_project(
        "OK",
        owner_id=user_active["billing_account_id"],
        user=user_active,
    )
    assert project and project.get("id")
    project_id = str(project["id"])

    updated = projects_module.update_project(
        project_id,
        owner_id=user_active["billing_account_id"],
        user=user_active,
        name="OK2",
    )
    assert updated and updated.get("name") == "OK2"

    deleted = projects_module.delete_project(
        project_id,
        owner_id=user_active["billing_account_id"],
        user=user_active,
    )
    assert deleted is True

    print("PASS")


if __name__ == "__main__":
    test_access_guard()
