"""Run enrichment test using a known-valid Team B email (sarah.chen@techflow.com).
This script requires Team B API reachable at TEAM_B_API or will use local fallback.
"""
from __future__ import annotations

import os
import pprint
import sys
from pathlib import Path

# Ensure repo root on sys.path for local imports
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext
from core.policy_engine import TemporalPolicyEngine


def main():
    os.environ.setdefault("TEAM_B_API", "http://127.0.0.1:8000")
    os.environ.setdefault("TEAM_B_INTEGRATION", "true")

    engine = TemporalPolicyEngine()
    print("Engine team_b_adapter present:", engine.team_b_adapter is not None)

    tc = TemporalContext.mock(business_hours=True)
    tc.user_id = "sarah.chen@techflow.com"

    request = EnhancedContextualIntegrityTuple(
        data_type="employee_record",
        data_subject="sarah.chen@techflow.com",
        data_sender=tc.user_id,
        data_recipient="hr_team",
        transmission_principle="business_need",
        temporal_context=tc,
    )

    print("Evaluating request (attempting to enrich from Team B or local fallback)...")
    decision = engine.evaluate_temporal_access(request)

    print("Decision summary:")
    pprint.pprint({
        "decision": decision.get("decision"),
        "reasons": decision.get("reasons"),
        "org_context_user_present": hasattr(request.temporal_context, "org_context_user"),
        "org_context_subject_present": hasattr(request.temporal_context, "org_context_subject"),
    })

    if hasattr(request.temporal_context, "org_context_user"):
        print("Org context for user (attached):")
        pprint.pprint(request.temporal_context.org_context_user)


if __name__ == "__main__":
    main()
