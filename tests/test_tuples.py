# tests/test_tuples.py
from datetime import datetime, timezone
from core.tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple

def test_tuple_serialize_roundtrip():
    now = datetime.now(timezone.utc)
    tw = TimeWindow(start=now, end=now)
    tc = TemporalContext(timestamp=now, timezone="UTC", business_hours=True,
                         emergency_override=False, access_window=tw,
                         data_freshness_seconds=60, situation="NORMAL",
                         temporal_role="oncall", event_correlation=None)
    ect = EnhancedContextualIntegrityTuple("hr","user1","svc-a","svc-b","tp", tc)
    d = ect.to_dict()
    restored = EnhancedContextualIntegrityTuple.from_dict(d)
    assert restored.data_type == ect.data_type
    assert restored.temporal_context.situation == "NORMAL"
