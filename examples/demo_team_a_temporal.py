#!/usr/bin/env python
"""
Team A: Temporal Dimension Enhancement Demo
-------------------------------------------
Shows the 6-tuple temporal engine making decisions for PRD rules:
- EMRG-001 / MED-EMRG-001 (Emergency override)
- FIN-001 (Earnings embargo pre/post release)
- GDPR-001 (72h breach notification window)
- TEMP-001 (Acting role permissions)
"""

import sys
from datetime import datetime, timezone

# Ensure repo root on path
from pathlib import Path
repo_root = str(Path(__file__).parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext
from core.policy_engine import TemporalPolicyEngine


def run_case(name: str, tuple_obj: EnhancedContextualIntegrityTuple):
    engine = TemporalPolicyEngine()
    decision = engine.evaluate_temporal_access(tuple_obj)
    print(f"\n=== {name} ===")
    print(f"Decision: {decision['decision']}")
    if decision.get('policy_matched'):
        print(f"Matched Policy: {decision['policy_matched']}")
    if decision.get('reasons'):
        print("Reasons:")
        for r in decision['reasons']:
            print(f"  - {r}")
    if decision.get('expires_at'):
        print(f"Expires At: {decision['expires_at']}")
    if decision.get('risk_level'):
        print(f"Risk Level: {decision['risk_level']}")
    if decision.get('confidence_score') is not None:
        print(f"Confidence: {decision['confidence_score']}")
    return decision


def scenario_emergency_medical():
    tc = TemporalContext(
        timestamp=datetime(2025, 1, 5, 2, 0, 0, tzinfo=timezone.utc),
        timezone="UTC",
        business_hours=False,
        emergency_override=True,
        emergency_authorization_id="AUTH-EMRG-001-20250105",
        situation="EMERGENCY",
        temporal_role="oncall_critical",
    )
    req = EnhancedContextualIntegrityTuple(
        data_type="medical_record",
        data_subject="patient-5847",
        data_sender="emergency_physician",
        data_recipient="patient_care_team",
        transmission_principle="clinical_care",
        temporal_context=tc,
        data_classification="restricted",
    )
    return run_case("EMRG-001: Emergency Medical Override", req)


def scenario_fin_embargo_block():
    tc = TemporalContext(
        timestamp=datetime(2025, 1, 6, 12, 0, 0, tzinfo=timezone.utc),
        timezone="UTC",
        business_hours=True,
        emergency_override=False,
        situation="NORMAL",
        temporal_role="user",
    )
    req = EnhancedContextualIntegrityTuple(
        data_type="earnings_data",
        data_subject="company-q4",
        data_sender="finance-analyst",
        data_recipient="investor_relations",
        transmission_principle="embargoed_earnings",
        temporal_context=tc,
        data_classification="confidential",
    )
    return run_case("FIN-001: Embargo (BLOCK before release)", req)


def scenario_fin_after_release_allow():
    tc = TemporalContext(
        timestamp=datetime(2025, 1, 9, 9, 0, 0, tzinfo=timezone.utc),
        timezone="UTC",
        business_hours=True,
        emergency_override=False,
        situation="NORMAL",
        temporal_role="user",
    )
    req = EnhancedContextualIntegrityTuple(
        data_type="earnings_data",
        data_subject="company-q4",
        data_sender="finance-analyst",
        data_recipient="investor_relations",
        transmission_principle="post_release",
        temporal_context=tc,
        data_classification="confidential",
    )
    return run_case("FIN-001: Post-release (ALLOW_WITH_AUDIT)", req)


def scenario_gdpr_expedite():
    tc = TemporalContext(
        timestamp=datetime(2025, 1, 6, 10, 0, 0, tzinfo=timezone.utc),
        timezone="UTC",
        business_hours=True,
        emergency_override=False,
        situation="INCIDENT",
        temporal_role="incident_responder",
        data_freshness_seconds=3600,  # within 72h window
    )
    req = EnhancedContextualIntegrityTuple(
        data_type="breach_details",
        data_subject="incident-4242",
        data_sender="soc-analyst",
        data_recipient="regulator",
        transmission_principle="regulatory_requirement",
        temporal_context=tc,
        data_classification="confidential",
    )
    return run_case("GDPR-001: 72h breach notification (EXPEDITE)", req)


def scenario_temp_acting_role():
    tc = TemporalContext(
        timestamp=datetime(2024, 12, 15, 10, 0, 0, tzinfo=timezone.utc),
        timezone="UTC",
        business_hours=True,
        emergency_override=False,
        situation="NORMAL",
        temporal_role="acting_manager",
    )
    req = EnhancedContextualIntegrityTuple(
        data_type="project_data",
        data_subject="project-nova",
        data_sender="acting-manager-anna",
        data_recipient="engineering_team",
        transmission_principle="project_work",
        temporal_context=tc,
        data_classification="internal",
    )
    return run_case("TEMP-001: Acting role inherits permissions", req)


def main():
    print("\nTEAM A TEMPORAL FRAMEWORK DEMO (6-TUPLE)")
    decisions = [
        scenario_emergency_medical(),
        scenario_fin_embargo_block(),
        scenario_fin_after_release_allow(),
        scenario_gdpr_expedite(),
        scenario_temp_acting_role(),
    ]
    allow_like = [d for d in decisions if d.get('decision') in ("ALLOW", "ALLOW_WITH_AUDIT", "EXPEDITE", "INHERIT_PERMISSIONS")]
    print("\nSUMMARY:")
    print(f"  Scenarios run: {len(decisions)}")
    print(f"  Allow-ish decisions: {len(allow_like)}")
    print(f"  Decisions: {[d.get('decision') for d in decisions]}")


if __name__ == "__main__":
    main()
