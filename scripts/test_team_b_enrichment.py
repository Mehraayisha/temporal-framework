"""Test script to confirm TemporalPolicyEngine enrichment from Team B API.

This script enables `TEAM_B_INTEGRATION`, waits for Team B health, then
constructs a small `EnhancedContextualIntegrityTuple` and calls
`TemporalPolicyEngine.evaluate_temporal_access` to verify enrichment attaches
`org_context_user` to the temporal context.
"""
import os
import time
import pprint

os.environ.setdefault("TEAM_B_API", "http://localhost:8000")
os.environ.setdefault("TEAM_B_INTEGRATION", "true")

from adapters.team_b_adapter import health_check
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple
from core.policy_engine import TemporalPolicyEngine


def wait_for_team_b(timeout: int = 30) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if health_check():
            return True
        time.sleep(1)
    return False


def main():
    print("Waiting for Team B API health...")
    if not wait_for_team_b(30):
        print("Team B API did not become healthy within timeout. Aborting test.")
        return 1

    # Choose an email expected to exist in Team B data; try to read sample
    sample_email = None
    try:
        import json
        with open('data/org_data.json','r',encoding='utf-8') as f:
            d = json.load(f)
            emps = d.get('employees') or []
            if emps:
                sample_email = emps[0].get('email')
    except Exception:
        sample_email = None

    if not sample_email:
        sample_email = os.environ.get('TEST_TEAM_B_EMAIL','alice@example.com')

    print(f"Using sample email: {sample_email}")

    tc = TemporalContext(service_id='test_service', user_id=sample_email, location='test', timezone='UTC')
    tpl = EnhancedContextualIntegrityTuple(
        data_type='employee_record',
        data_subject=sample_email,
        data_sender=sample_email,
        data_recipient='hr',
        transmission_principle='business_need',
        temporal_context=tc
    )

    engine = TemporalPolicyEngine()
    print('Evaluating tuple (this will trigger enrichment)...')
    result = engine.evaluate_temporal_access(tpl)

    print('\nDecision summary:')
    pprint.pprint(result)

    print('\nTemporalContext keys:')
    print(vars(tpl.temporal_context))

    has_org_user = hasattr(tpl.temporal_context, 'org_context_user')
    print(f"org_context_user attached: {has_org_user}")

    return 0 if has_org_user else 2


if __name__ == '__main__':
    raise SystemExit(main())
