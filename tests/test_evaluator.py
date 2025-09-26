# tests/test_evaluator.py
from datetime import datetime, timezone, timedelta
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple
from core.evaluator import evaluate

def make_tc(now, emergency=False):
    return TemporalContext(
        timestamp=now,
        timezone="UTC",
        business_hours=not emergency,
        emergency_override=emergency,
        access_window=None,
        data_freshness_seconds=None,
        situation="EMERGENCY" if emergency else "NORMAL",
        temporal_role=None,
        event_correlation=None
    )

def test_evaluator_no_match_blocks():
    now = datetime.now(timezone.utc)
    tc = make_tc(now, emergency=False)
    req = EnhancedContextualIntegrityTuple("unknown","s","a","b","tp", tc)
    res = evaluate(req, rules=[])  # no rules
    assert res["action"] == "BLOCK"

def test_evaluator_emergency_allows():
    now = datetime.now(timezone.utc)
    tc = make_tc(now, emergency=True)
    req = EnhancedContextualIntegrityTuple("financial","s","x","oncall-team","tp", tc)
    # rule matching inline
    rules = [{
        "id":"EMRG-TEST",
        "action":"ALLOW",
        "tuples":{"data_type":"financial","data_sender":"*","data_recipient":"oncall-team","transmission_principle":"*"},
        "temporal_context":{"situation":"EMERGENCY","require_emergency_override":True}
    }]
    res = evaluate(req, rules=rules)
    assert res["action"] == "ALLOW" and res["matched_rule_id"] == "EMRG-TEST"

def test_evaluator_time_window_blocks_when_outside():
    now = datetime.now(timezone.utc)
    tc = make_tc(now, emergency=False)
    req = EnhancedContextualIntegrityTuple("hr","s","a","b","tp", tc)
    rules = [{
        "id":"TW-1",
        "action":"ALLOW",
        "tuples":{"data_type":"hr"},
        "temporal_context":{"access_window":{"start":"2000-01-01T00:00:00+00:00","end":"2000-01-01T01:00:00+00:00"}}
    }]
    res = evaluate(req, rules=rules)
    assert res["action"] == "BLOCK"
