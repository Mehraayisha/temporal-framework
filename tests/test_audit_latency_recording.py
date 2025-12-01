import time
from core import audit, evaluator
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple


def test_decision_latency_recorded_after_evaluate_compiled():
    # Reset metrics and log
    audit.clear_log()
    audit.reset_audit_metrics()

    # Create a minimal tuple
    tc = TemporalContext.mock()
    et = EnhancedContextualIntegrityTuple(
        data_type="public",
        data_subject="subj-1",
        data_sender="alice",
        data_recipient="bob",
        transmission_principle="default",
        temporal_context=tc,
    )

    # Use compiled path with empty rules (will result in BLOCK and record latency)
    res = evaluator.evaluate_compiled(et, compiled_rules=[])
    assert isinstance(res, dict)

    # Allow background writer/metrics to settle briefly
    time.sleep(0.01)

    agg = audit.get_aggregated_metrics()
    assert agg.get("decision_count", 0) >= 1
    assert agg.get("decision_total_ms", 0.0) >= 0.0
    # Average should be numeric
    assert isinstance(agg.get("decision_avg_ms"), float)
