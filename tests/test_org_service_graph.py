import pytest
from core.org_service import set_neo4j_manager, load_export, org_lookup
from core.org_importer import SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS


class FakeResult:
    def __init__(self, record):
        self._record = record

    def single(self):
        return self._record


class FakeSession:
    def __init__(self, behavior):
        # behavior can be a dict to return or an exception to raise
        self.behavior = behavior

    def run(self, *args, **kwargs):
        if isinstance(self.behavior, Exception):
            raise self.behavior
        return FakeResult(self.behavior)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeDriver:
    def __init__(self, behavior):
        self.behavior = behavior

    def session(self):
        return FakeSession(self.behavior)


class FakeManager:
    def __init__(self, behavior):
        self.driver = FakeDriver(behavior)


def test_org_lookup_uses_graph_when_available(tmp_path):
    # Arrange: load fallback cache
    load_export(SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS, ttl_seconds=300)

    # Graph will return a distinct sender_department so we can assert graph path used
    fake_graph_record = {
        'sender': {'id': 'emp-001', 'security_clearance': 'graph-clear'},
        'recipient': {'id': 'emp-001', 'security_clearance': 'graph-clear'},
        'sender_dept': {'id': 'dept-graph', 'name': 'GraphDept'},
        'recipient_dept': {'id': 'dept-graph', 'name': 'GraphDept'},
        'shared_projects': ['proj-graph']
    }

    fake_manager = FakeManager(fake_graph_record)
    set_neo4j_manager(fake_manager)

    # Act
    ctx = org_lookup('emp-001', 'emp-001')

    # Assert
    assert ctx is not None
    assert ctx['sender_department'] == 'GraphDept'
    assert ctx['shared_projects'] == ['proj-graph']


def test_org_lookup_falls_back_when_graph_fails(tmp_path):
    # Arrange: load fallback cache
    load_export(SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS, ttl_seconds=300)

    # Graph session will raise; org_lookup should fall back to cache
    fake_manager = FakeManager(Exception('graph down'))
    set_neo4j_manager(fake_manager)

    # Act
    ctx = org_lookup('emp-001', 'emp-001')

    # Assert: fallback should return department name from SAMPLE_DEPARTMENTS mapping
    assert ctx is not None
    assert ctx['sender_department'] is not None
    assert isinstance(ctx['shared_projects'], list)


def test_org_lookup_raises_when_cache_expired_and_no_graph(tmp_path):
    # Ensure no neo4j manager configured
    set_neo4j_manager(None)

    # Do not load cache; ensure it is considered expired
    # Clear the fallback cache metadata to simulate expired cache
    import core.org_service as osi
    osi._CACHE_META['loaded_at'] = None

    with pytest.raises(RuntimeError):
        org_lookup('emp-001', 'emp-001')
