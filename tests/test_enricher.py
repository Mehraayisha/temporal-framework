# tests/test_enricher.py
from datetime import datetime, timezone, timedelta
from core.enricher import enrich_temporal_context

def test_enricher_basic():
    now = datetime.now(timezone.utc)
    tc = enrich_temporal_context("billing", now=now)
    assert tc.timestamp == now
    assert isinstance(tc.business_hours, bool)
    assert tc.situation in ("NORMAL", "EMERGENCY")
