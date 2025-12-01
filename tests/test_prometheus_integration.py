import sys
import types

from core import audit


def test_enable_prometheus_with_mocked_client():
    # Inject a fake prometheus_client module to simulate presence
    fake = types.ModuleType("prometheus_client")

    class Counter:
        def __init__(self, name, desc, registry=None):
            self.name = name
            self.desc = desc

    class Gauge:
        def __init__(self, name, desc, registry=None):
            self.name = name
            self.desc = desc

    class CollectorRegistry:
        pass

    fake.Counter = Counter
    fake.Gauge = Gauge
    fake.CollectorRegistry = CollectorRegistry

    original = sys.modules.get('prometheus_client')
    sys.modules['prometheus_client'] = fake

    try:
        # Should return True when the fake client is available
        res = audit.enable_prometheus_metrics()
        assert res is True
        # Re-enable with registry param (None) should also succeed
        res2 = audit.enable_prometheus_metrics(registry=None)
        assert res2 is True
    finally:
        # Restore original module if present
        if original is not None:
            sys.modules['prometheus_client'] = original
        else:
            del sys.modules['prometheus_client']
