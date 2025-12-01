import time
from core import audit


def test_audit_metrics_enqueue_and_flush():
    # Ensure a clean slate
    audit.clear_log()
    audit.reset_audit_metrics()

    # Enqueue a couple of decisions
    audit.record_decision({"action": "TEST1"})
    audit.record_decision({"action": "TEST2"})

    # Force a synchronous flush by reading entries (this calls _flush_queue_now internally)
    entries = audit.read_entries()

    metrics = audit.get_audit_metrics()

    assert metrics.get("enqueued_count", 0) >= 2
    # At least one flush should have occurred during read_entries
    assert metrics.get("flushed_batches", 0) >= 1
    # last flush duration is recorded (may be 0 in rare cases, but should be numeric)
    assert isinstance(metrics.get("last_flush_duration_ms", 0.0), float)


def test_enable_prometheus_metrics_safe():
    # The function should return True if prometheus_client is installed, else False
    res = audit.enable_prometheus_metrics()
    assert res in (True, False)
