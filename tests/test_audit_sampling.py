import core.audit as audit


def test_audit_sampling_off_and_on():
    # reset metrics
    audit.reset_audit_metrics()
    audit.set_audit_enabled(True)

    # sample rate 0.0 should drop all events
    audit.set_audit_sample_rate(0.0)
    audit.record_decision({"action": "TEST_OFF"})
    m = audit.get_audit_metrics()
    assert m["enqueued_count"] == 0

    # sample rate 1.0 should enqueue events
    audit.reset_audit_metrics()
    audit.set_audit_sample_rate(1.0)
    audit.record_decision({"action": "TEST_ON"})
    m2 = audit.get_audit_metrics()
    assert m2["enqueued_count"] >= 1

    # cleanup
    audit.set_audit_sample_rate(1.0)
    audit.set_audit_enabled(True)
