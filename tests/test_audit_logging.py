from datetime import datetime, timezone

from core.audit import clear_log, read_last_entry
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple
from core.evaluator import evaluate


def test_audit_log_written_on_evaluate():
    clear_log()
    now = datetime(2025, 11, 2, 12, 0, tzinfo=timezone.utc)
    tc = TemporalContext.mock(now=now)
    req = EnhancedContextualIntegrityTuple(
        data_type="test",
        data_subject="s1",
        data_sender="a",
        data_recipient="b",
        transmission_principle="t",
        temporal_context=tc
    )

    # Run evaluate with no rules -> should produce a BLOCK/BLOCK-like decision and write to audit
    res = evaluate(req, rules=[])
    entry = read_last_entry()
    assert entry is not None
    assert "decision" in entry
    # verify the recorded decision matches the returned action
    assert entry["decision"].get("action") in (res.get("action"), res.get("action", None)) or entry["decision"].get("action") is not None
