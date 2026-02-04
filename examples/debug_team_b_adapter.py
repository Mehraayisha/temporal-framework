"""Debug helper: pick a valid email from Team B's org_data.json and call the adapter.

Usage:
  python examples/debug_team_b_adapter.py

This prints the HTTP response (or error) returned by Team B's `employee-context` endpoint.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pprint

import sys
from pathlib import Path

# Ensure repo root is on sys.path so local packages (adapters) import reliably
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from adapters.team_b_adapter import get_org_context


def find_first_email_from_package() -> str | None:
    pkg = Path("privacy_firewall_integration") / "data" / "org_data.json"
    if not pkg.exists():
        pkg = Path("data") / "team_b_org_chart" / "data" / "org_data.json"
        if not pkg.exists():
            return None

    data = json.loads(pkg.read_text(encoding="utf-8"))
    employees = data.get("employees", [])
    if not employees:
        return None
    # Prefer an email field
    for e in employees:
        if e.get("email"):
            return e.get("email")
    # Fallback to first employee name-based email
    first = employees[0]
    return first.get("email") or None


def main():
    os.environ.setdefault("TEAM_B_API", "http://127.0.0.1:8000")
    email = find_first_email_from_package()
    if not email:
        print("No email found in Team B package org_data.json; please provide one.")
        return

    print(f"Using email: {email}")
    try:
        ctx = get_org_context(email)
        print("Adapter returned JSON:")
        pprint.pprint(ctx)
    except Exception as e:
        print("Adapter call failed:")
        print(repr(e))


if __name__ == "__main__":
    main()
