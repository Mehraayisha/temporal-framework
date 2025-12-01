from datetime import datetime, timezone

from core import incidents
from core.enricher import enrich_temporal_context


def test_enrich_sets_emergency_override_when_incident_active():
    incidents.clear_all()
    incidents.add_incident("inc-1", service="svcX", status="investigating")

    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = enrich_temporal_context("svcX", now=now)

    assert tc.emergency_override is True
    assert tc.temporal_role == "incident_responder"


def test_enrich_reverts_after_clearing_incident():
    incidents.clear_all()

    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = enrich_temporal_context("svcX", now=now)

    assert tc.emergency_override is False
    assert tc.temporal_role.startswith("oncall_")
