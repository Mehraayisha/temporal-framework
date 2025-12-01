from datetime import datetime, timezone

from core.org_importer import SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS
from core.org_service import load_export, org_lookup
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple
from core.enricher import enrich_temporal_context
from core.evaluator import evaluate
from core.policy_engine import TemporalPolicyEngine


def test_e2e_smoke_flow():
    # Load the sample Team B export into the local cache
    load_export(SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS, ttl_seconds=60)

    # Create a base temporal context representing a late-night emergency
    now = datetime.now(timezone.utc)
    tc = TemporalContext.mock(now=now, business_hours=False, emergency_override=True, temporal_role=None)
    tc.service_id = "notifications"

    # Enrich temporal context (this uses enrich_temporal_context which may consult incidents/graph)
    enriched = enrich_temporal_context(tc.service_id)

    # Verify org lookup for the sample users (SAMPLE_USERS contains Sarah Chen -> emp-001)
    # Use the normalized names/ids: the sample users list uses 'emp-001' as id
    ctx = org_lookup('emp-001', 'emp-001')
    assert ctx is not None
    assert 'sender_department' in ctx

    # Build a 6-tuple request and run evaluation and policy engine
    req = EnhancedContextualIntegrityTuple(
        data_type="medical_record",
        data_subject="patient_x",
        data_sender="emp-001",
        data_recipient="dept-exec",
        transmission_principle="treatment",
        temporal_context=enriched
    )

    # Evaluate using the evaluator (no graph managers passed so YAML fallback rules will be used)
    res = evaluate(req, rules=[])
    assert 'action' in res

    # Run through the policy engine fast-path
    engine = TemporalPolicyEngine()
    pres = engine.evaluate_temporal_access(req)
    assert 'decision' in pres
    assert 'confidence_score' in pres
