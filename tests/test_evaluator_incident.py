from datetime import datetime, timezone

from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple
from core.evaluator import evaluate


def make_request_tuple(emergency: bool, now: datetime = None) -> EnhancedContextualIntegrityTuple:
    now = now or datetime.now(timezone.utc)
    tc = TemporalContext.mock(now=now, emergency_override=emergency, temporal_role=("incident_responder" if emergency else "oncall_medium"))
    tup = EnhancedContextualIntegrityTuple(
        data_type="medical_record",
        data_subject="patient_123",
        data_sender="clinician_a",
        data_recipient="lab_b",
        transmission_principle="treatment",
        temporal_context=tc
    )
    return tup


def test_evaluator_allows_when_emergency_override_and_rule_requires_it():
    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    req = make_request_tuple(True, now=now)

    rules = [
        {
            "id": "r_emergency_allow",
            "action": "ALLOW",
            "tuples": {
                "data_type": "medical_record",
                "data_sender": "*",
                "data_recipient": "*",
                "transmission_principle": "*"
            },
            "temporal_context": {
                "require_emergency_override": True
            }
        }
    ]

    res = evaluate(req, rules=rules)
    assert res["action"] == "ALLOW"
    assert res["matched_rule_id"] == "r_emergency_allow"


def test_evaluator_blocks_when_no_emergency_override_but_rule_requires_it():
    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    req = make_request_tuple(False, now=now)

    rules = [
        {
            "id": "r_emergency_allow",
            "action": "ALLOW",
            "tuples": {
                "data_type": "medical_record",
                "data_sender": "*",
                "data_recipient": "*",
                "transmission_principle": "*"
            },
            "temporal_context": {
                "require_emergency_override": True
            }
        }
    ]

    res = evaluate(req, rules=rules)
    assert res["action"] == "BLOCK"
    assert res["matched_rule_id"] is None
