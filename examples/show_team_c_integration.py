"""Show Team C integration demo.

Run with: .venv\Scripts\python.exe examples\show_team_c_integration.py

This script constructs a Team-C style 6-tuple, evaluates it with
TemporalPolicyEngine and prints the full decision JSON.
"""
import json
import os
import uuid
from datetime import datetime, timezone, timedelta

from pathlib import Path
import sys

# Ensure repo root is on sys.path when running this script directly
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple
from core.policy_engine import TemporalPolicyEngine
from adapters.team_c_adapter import get_adapter as get_team_c_adapter


def make_demo_tuple():
    now = datetime.now(timezone.utc)
    access_window = TimeWindow(
        start=now - timedelta(minutes=5),
        end=now + timedelta(hours=1),
        window_type="emergency",
        description="Demo emergency window"
    )

    tc = TemporalContext(
        situation="EMERGENCY",
        emergency_override=True,
        emergency_authorization_id=str(uuid.uuid4()),
        temporal_role="oncall_critical",
        access_window=access_window,
        timestamp=now,
        timezone="UTC",
        business_hours=False
    )

    t = EnhancedContextualIntegrityTuple(
        data_type="HealthData.VitalSigns",
        data_subject="patient_12345",
        data_sender="monitoring_system",
        data_recipient="emergency_team",
        transmission_principle="secure",
        temporal_context=tc
    )

    return t


def main():
    # Ensure Team B integration is disabled for this demo (Team C only)
    os.environ['TEAM_B_INTEGRATION'] = 'false'

    print("=== Team C Integration Demo  ===\n")
    print("Creating demo 6-tuple and evaluating with TemporalPolicyEngine...\n")

    demo_tuple = make_demo_tuple()

    # Run Team C enrichment (ontology classification)
    team_c = get_team_c_adapter()
    sem = team_c.classify_data(demo_tuple.data_type)

    # Keep semantic enrichment in a local variable (pydantic models may reject new fields)
    semantic_enrichment = sem

    # Also set the tuple's data_classification field to a useful value consumed elsewhere
    if sem.get("tags"):
        demo_tuple.data_classification = sem.get("tags")[0]
    elif sem.get("classes"):
        demo_tuple.data_classification = sem.get("classes")[0]

    # Instantiate engine with no Team B adapter to demonstrate Team C integration only
    engine = TemporalPolicyEngine(team_b_adapter=None)

    result = engine.evaluate_temporal_access(demo_tuple)

    print("=== Evaluation Result ===")
    print(json.dumps(result, default=str, indent=2))

    # Show whether Team B enrichment fields are present (if adapter attached)
    user_ctx = getattr(demo_tuple.temporal_context, 'org_context_user', None)
    subj_ctx = getattr(demo_tuple, 'org_context_subject', None) or getattr(demo_tuple.temporal_context, 'org_context_subject', None)

    print('\n=== Enrichment Fields (if any) ===')
    print('org_context_user present:', bool(user_ctx))
    print('org_context_subject present:', bool(subj_ctx))
    print('\n=== Team C Semantic Enrichment ===')
    print(json.dumps(semantic_enrichment, indent=2))


if __name__ == '__main__':
    main()
