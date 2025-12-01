from datetime import datetime, timezone

from core import holds
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple
from core.evaluator import evaluate
from core.policy_engine import TemporalPolicyEngine


def test_evaluator_blocks_when_data_subject_on_hold():
    holds.remove_hold("all") if "all" in [h.get("hold_id") for h in holds.list_holds()] else None
    holds.add_hold("h1", subject_type="data_subject", subject_id="patient_999", reason="litigation")

    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = TemporalContext.mock(now=now, emergency_override=False)
    req = EnhancedContextualIntegrityTuple(
        data_type="medical_record",
        data_subject="patient_999",
        data_sender="clinician_a",
        data_recipient="lab_b",
        transmission_principle="treatment",
        temporal_context=tc
    )

    res = evaluate(req, rules=[])
    assert res["action"] in ("DENY", "BLOCK") or res["action"] == "DENY"
    assert any("legal_hold" in r.lower() for r in res["reasons"]) or any("legal" in r.lower() for r in res["reasons"]) 


def test_policy_engine_denies_and_requires_audit_on_hold():
    holds.clear = None
    holds.add_hold("h2", subject_type="service", subject_id="svcX", reason="regulatory")

    engine = TemporalPolicyEngine()
    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = TemporalContext.mock(now=now, emergency_override=False, temporal_role="oncall_medium")
    # put service_id in temporal_context
    tc.service_id = "svcX"

    req = EnhancedContextualIntegrityTuple(
        data_type="internal_doc",
        data_subject="doc-1",
        data_sender="svcX",
        data_recipient="svcY",
        transmission_principle="maintenance",
        temporal_context=tc
    )

    res = engine.evaluate_temporal_access(req)
    assert res["decision"] == "DENY"
    assert res.get("audit_required", False) is True
