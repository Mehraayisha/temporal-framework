from datetime import datetime, timezone

from core import incidents
from core.enricher import enrich_temporal_context


def test_security_critical_maps_to_security_incident_lead():
    incidents.clear_all()
    incidents.add_incident("s1", service="svcSec", status="investigating", metadata={"type": "security", "severity": "critical"})

    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = enrich_temporal_context("svcSec", now=now)

    assert tc.emergency_override is True
    assert tc.temporal_role == "security_incident_lead"


def test_meta_role_override_used_when_present():
    incidents.clear_all()
    incidents.add_incident("s2", service="svcX", status="investigating", metadata={"type": "system", "role": "acting_supervisor"})

    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = enrich_temporal_context("svcX", now=now)

    assert tc.emergency_override is True
    assert tc.temporal_role == "acting_supervisor"
