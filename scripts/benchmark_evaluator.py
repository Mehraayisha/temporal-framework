import time
from datetime import datetime, timezone

from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext
from core import evaluator, audit


def make_sample_tuple():
    now = datetime.now(timezone.utc)
    tc = TemporalContext.mock(now=now, business_hours=True, emergency_override=False, temporal_role=None)
    tup = EnhancedContextualIntegrityTuple(
        data_type="medical_record",
        data_subject="patient_x",
        data_sender="clinician_a",
        data_recipient="dept_b",
        transmission_principle="treatment",
        temporal_context=tc
    )
    return tup


def run_benchmark(iterations: int = 1000):
    tup = make_sample_tuple()

    # Prepare a minimal rule that will match quickly
    rules = [
        {
            "id": "r1",
            "action": "ALLOW",
            "tuples": {
                "data_type": "medical_record",
                "data_sender": "clinician_a",
                "data_recipient": "dept_b",
                "transmission_principle": "treatment"
            },
            "temporal_context": {}
        }
    ]

    # Disable auditing for this benchmark to measure hot-path baseline
    try:
        audit.set_audit_enabled(False)
    except Exception:
        pass

    # Compile rules once for the fast evaluation path
    compiled = evaluator.compile_rules(rules)

    # Warm-up
    for _ in range(5):
        evaluator.evaluate_compiled(tup, compiled)

    start = time.perf_counter()
    for i in range(iterations):
        evaluator.evaluate_compiled(tup, compiled)
    end = time.perf_counter()

    total = end - start
    per_call = total / iterations if iterations else float('inf')

    print(f"Benchmark: {iterations} iterations")
    print(f"Total time: {total:.6f}s")
    print(f"Per call: {per_call*1000:.3f} ms")


if __name__ == '__main__':
    run_benchmark(1000)
