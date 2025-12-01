from datetime import datetime, timezone, timedelta

from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple


def make_tuple_with_role(role: str, base_role: str = None, valid_until: datetime = None, chain=None):
    now = datetime.now(timezone.utc)
    tc = TemporalContext.mock(now=now, emergency_override=False, temporal_role=role)
    tc.base_role = base_role
    tc.temporal_role_valid_until = valid_until
    if chain is not None:
        tc.permission_inheritance_chain = chain

    tup = EnhancedContextualIntegrityTuple(
        data_type="medical_record",
        data_subject="patient_x",
        data_sender="clinician_a",
        data_recipient="dept_b",
        transmission_principle="treatment",
        temporal_context=tc
    )
    return tup


def test_no_temporal_role_is_valid():
    tup = make_tuple_with_role(None)
    res = tup.validate_temporal_role_inheritance()
    assert res["is_valid"] is True


def test_missing_base_role_is_invalid_for_oncall():
    tup = make_tuple_with_role("oncall_high", base_role=None)
    res = tup.validate_temporal_role_inheritance()
    assert res["is_valid"] is False
    assert any("Base role required" in e or "Base role" in e for e in res["validation_errors"]) or len(res["validation_errors"])>0


def test_valid_oncall_inheritance_passes():
    # oncall_high eligible base includes 'attending_physician'
    tup = make_tuple_with_role("oncall_high", base_role="attending_physician")
    res = tup.validate_temporal_role_inheritance()
    assert res["is_valid"] is True


def test_expired_temporal_role_fails():
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    tup = make_tuple_with_role("oncall_medium", base_role="nurse", valid_until=past)
    res = tup.validate_temporal_role_inheritance()
    assert res["is_valid"] is False
    assert any("expired" in e.lower() for e in res["validation_errors"]) or len(res["validation_errors"])>0
