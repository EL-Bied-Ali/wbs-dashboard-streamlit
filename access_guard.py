"""
Access guard utilities for billing-based feature gating.
"""

from __future__ import annotations

from typing import Any
import streamlit as st

from billing_store import access_status, get_account_by_email


def get_access_status_for_user(user: dict | None) -> dict[str, Any]:
    """Get access status for the current user.
    
    Returns dict with keys: allowed, status, trial_end, days_left, plan_end
    """
    if not user:
        return {
            "allowed": False,
            "status": "unknown",
            "trial_end": None,
            "days_left": None,
            "plan_end": None,
            "can_edit": False,
        }
    email = user.get("email", "")
    account = get_account_by_email(email) if email else None
    gate = access_status(account)
    gate["can_edit"] = gate.get("allowed", True)  # Can edit only if plan allowed
    return gate


def check_access_or_redirect(user: dict | None, reason: str = "Your plan is expired.") -> dict[str, Any]:
    """Check if user has access. If not, show error and redirect to Projects.
    
    Returns access_status dict if allowed, otherwise redirects.
    """
    gate = get_access_status_for_user(user)
    if not gate.get("allowed"):
        st.error(f"{reason} Redirecting to projects...")
        st.session_state.pop("active_project_id", None)
        st.switch_page("pages/0_Projects.py")
        st.stop()
    return gate


def render_access_warning(gate: dict[str, Any]) -> None:
    """Render a warning banner if plan is expiring or expired."""
    if not gate:
        return
    
    status = gate.get("status", "unknown")
    days_left = gate.get("days_left")
    allowed = gate.get("allowed", True)
    
    if not allowed:
        st.error(
            "🔒 **Your plan is expired.** Projects are locked. "
            "[Upgrade now](/?upgrade=1)"
        )
    elif status == "trialing" and days_left is not None:
        if days_left <= 3:
            st.warning(
                f"⏰ **Your trial expires in {days_left} day(s).** "
                "[Upgrade now](/?upgrade=1)"
            )


def assert_can_edit(user: dict | None) -> None:
    """Raise PermissionError if user is not allowed to edit projects.
    
    This is a server-side guard that prevents mutations even if UI is bypassed.
    """
    gate = get_access_status_for_user(user)
    if not gate.get("allowed", True):
        raise PermissionError(
            "Plan expired: projects are locked. Upgrade your plan in Billing to continue."
        )
