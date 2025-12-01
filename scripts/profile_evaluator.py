import cProfile
import pstats
import io
from datetime import datetime, timezone

from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext
from core import evaluator


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


def profile_run(iterations: int = 5000):
    tup = make_sample_tuple()
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

    # Use compiled rules and the fast path for profiling
    compiled = evaluator.compile_rules(rules)
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(iterations):
        evaluator.evaluate_compiled(tup, compiled)
    pr.disable()

    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(30)
    print(s.getvalue())


if __name__ == '__main__':
    print('Profiling evaluator.evaluate...')
    profile_run(5000)
