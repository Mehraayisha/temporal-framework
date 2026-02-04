"""Run a quick smoke test that starts a TemporalPolicyEngine with Team B
integration enabled and confirms enrichment fields are attached.

This script expects Team B API to be reachable at http://localhost:8000 by default.
Set `TEAM_B_API` and `TEAM_B_INTEGRATION=true` in the environment if needed.
"""
from __future__ import annotations

import os
import pprint
from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext
from core.policy_engine import TemporalPolicyEngine


def main():
    os.environ.setdefault("TEAM_B_API", "http://localhost:8000")
    os.environ.setdefault("TEAM_B_INTEGRATION", "true")

    engine = TemporalPolicyEngine()

    tc = TemporalContext.mock(business_hours=True)
    tc.user_id = "alice@techflow.example"

    request = EnhancedContextualIntegrityTuple(
        data_type="employee_record",
        data_subject="bob@techflow.example",
        data_sender=tc.user_id,
        data_recipient="hr_team",
        transmission_principle="business_need",
        temporal_context=tc,
    )

    print("Evaluating request (this will attempt to enrich from Team B)...")
    decision = engine.evaluate_temporal_access(request)

    print("Decision summary:")
    pprint.pprint({
        "decision": decision.get("decision"),
        "reasons": decision.get("reasons"),
        "org_context_user_present": hasattr(request.temporal_context, "org_context_user"),
        "org_context_subject_present": hasattr(request.temporal_context, "org_context_subject"),
    })

    if hasattr(request.temporal_context, "org_context_user"):
        print("Org context for user:")
        pprint.pprint(request.temporal_context.org_context_user)


if __name__ == "__main__":
    main()
