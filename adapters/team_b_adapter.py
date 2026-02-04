"""Adapter to call Team B's org API without modifying their files.

This module is intentionally read-only with respect to the `privacy_firewall_integration/`
folder. It provides simple HTTP helpers that the Temporal evaluator can call to get
organizational context and to proxy check-access calls.

Configuration:
 - `TEAM_B_API` environment variable (default: `http://localhost:8000`)
"""
from __future__ import annotations

import os
import logging
from typing import Any, Dict, Optional

import requests

LOGGER = logging.getLogger(__name__)


def _base_url() -> str:
    return os.environ.get("TEAM_B_API", "http://localhost:8000")


def get_org_context(email: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Fetch organizational context for `email` from Team B's API.

    Returns the JSON response as a dict. Raises requests.HTTPError on failure.
    """
    url = f"{_base_url().rstrip('/')}/api/v1/employee-context/{email}"
    LOGGER.debug("Requesting TeamB org context: %s", url)
    try:
        resp = requests.get(url, timeout=timeout)
        LOGGER.debug("TeamB GET %s -> status=%s", url, resp.status_code)
        # Log response body at debug level (safe for non-sensitive org data)
        try:
            LOGGER.debug("TeamB response json: %s", resp.json())
        except Exception:
            LOGGER.debug("TeamB response text: %s", resp.text)

        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        LOGGER.exception("TeamB get_org_context failed for %s: %s", email, e)
        # Fallback: try to load a local copy of Team B package data if present
        try:
            from pathlib import Path
            import json

            local_paths = [
                Path("privacy_firewall_integration") / "data" / "org_data.json",
                Path("data") / "team_b_org_chart" / "data" / "org_data.json",
                Path("data") / "org_data.json",
            ]
            for p in local_paths:
                if p.exists():
                    LOGGER.debug("Attempting local fallback using %s", p)
                    raw = json.loads(p.read_text(encoding="utf-8"))
                    # Find employee by email
                    for emp in raw.get("employees", []):
                        if emp.get("email") == email:
                            LOGGER.debug("Found local employee record for %s", email)
                            return emp
        except Exception:
            LOGGER.debug("Local fallback failed or not available for %s", email)

        raise


def check_employee_access(requester_email: str, target_email: str, resource_type: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Proxy call to Team B's check-access API.

    Returns JSON result from Team B. This lets teams choose whether to combine
    their result with local policy evaluation.
    """
    url = f"{_base_url().rstrip('/')}/api/v1/check-employee-access"
    payload = {
        "requester_email": requester_email,
        "target_email": target_email,
        "resource_type": resource_type,
    }
    LOGGER.debug("Calling TeamB check-access: %s payload=%s", url, payload)
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        LOGGER.debug("TeamB POST %s payload=%s -> status=%s", url, payload, resp.status_code)
        try:
            LOGGER.debug("TeamB response json: %s", resp.json())
        except Exception:
            LOGGER.debug("TeamB response text: %s", resp.text)

        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        LOGGER.exception("TeamB check_employee_access failed: %s", e)
        raise


def health_check(timeout: float = 2.0) -> bool:
    """Quick health check for the Team B service.

    Returns True when `/api/v1/health` returns 200.
    """
    url = f"{_base_url().rstrip('/')}/api/v1/health"
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False
