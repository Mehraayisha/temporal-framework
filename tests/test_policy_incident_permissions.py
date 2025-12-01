from datetime import datetime, timezone

from core.policy_engine import TemporalPolicyEngine
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple


def test_apply_permissions_for_security_incident_lead():
    engine = TemporalPolicyEngine()
    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = TemporalContext.mock(now=now, emergency_override=True, temporal_role="security_incident_lead")
    req = EnhancedContextualIntegrityTuple(
        data_type="security_event",
        data_subject="sys-1",
        data_sender="sec_a",
        data_recipient="sec_ops",
        transmission_principle="investigation",
        temporal_context=tc
    )

    perms = engine.apply_temporal_role_permissions(req)

    assert "security_override" in perms
    assert "evidence_collection" in perms
    assert req.temporal_context.inherited_permissions == perms


def test_apply_permissions_for_incident_responder_fallback():
    engine = TemporalPolicyEngine()
    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = TemporalContext.mock(now=now, emergency_override=True, temporal_role="incident_responder")
    req = EnhancedContextualIntegrityTuple(
        data_type="log",
        data_subject="svc-1",
        data_sender="ops_a",
        data_recipient="forensics",
        transmission_principle="forensics",
        temporal_context=tc
    )

    perms = engine.apply_temporal_role_permissions(req)
    assert "incident_investigation" in perms
    assert "system_access_override" in perms
