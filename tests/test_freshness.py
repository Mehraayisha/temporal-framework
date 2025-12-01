import pytest
from datetime import datetime, timezone, timedelta
from core.tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple
from core.evaluator import evaluate


def make_tuple_with_context(age_seconds: int, freshness_seconds: int):
    now = datetime.now(timezone.utc)
    tc = TemporalContext.mock(now=now - timedelta(seconds=age_seconds), business_hours=True)
    tc.data_freshness_seconds = freshness_seconds
    eci = EnhancedContextualIntegrityTuple(
        data_type='test',
        data_subject='subj',
        data_sender='alice',
        data_recipient='bob',
        transmission_principle='standard',
        temporal_context=tc
    )
    return eci


def test_fresh_context_allows_evaluation(monkeypatch):
    # Create a fresh context (age < freshness)
    eci = make_tuple_with_context(age_seconds=10, freshness_seconds=60)

    # No rules -> default BLOCK, but no RuntimeError
    res = evaluate(eci, rules=[])
    assert isinstance(res, dict)


def test_stale_context_raises():
    # context older than freshness -> should raise RuntimeError
    eci = make_tuple_with_context(age_seconds=3600, freshness_seconds=300)
    with pytest.raises(RuntimeError):
        evaluate(eci, rules=[])
