from core import org_service


class _FakeResult:
    def __init__(self, record):
        self._record = record

    def single(self):
        return self._record


class _FakeSession:
    def __init__(self, record):
        self._record = record

    def run(self, *args, **kwargs):
        return _FakeResult(self._record)


class _FakeSessionCtx:
    def __init__(self, record):
        self._session = _FakeSession(record)

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeDriver:
    def __init__(self, record):
        self._record = record

    def session(self):
        return _FakeSessionCtx(self._record)


class _FakeManager:
    def __init__(self, record):
        self.driver = _FakeDriver(record)


def test_org_lookup_uses_neo4j_manager_and_returns_expected_keys():
    # Prepare a fake graph record matching what _org_lookup_neo4j expects
    fake_record = {
        'sender': {'id': 'u1', 'name': 'Alice', 'manager_id': 'm1', 'security_clearance': 'low'},
        'sender_dept': {'id': 'd1', 'name': 'Dept A'},
        'recipient': {'id': 'u2', 'name': 'Bob', 'manager_id': None, 'security_clearance': 'low'},
        'recipient_dept': {'id': 'd2', 'name': 'Dept B'},
        'shared_projects': ['proj-x']
    }

    fake_mgr = _FakeManager(fake_record)

    # Register fake manager
    org_service.set_neo4j_manager(fake_mgr)

    try:
        ctx = org_service.org_lookup('u1', 'u2')
        assert isinstance(ctx, dict)
        # basic sanity checks
        assert ctx.get('sender_department') == 'Dept A'
        assert ctx.get('recipient_department') == 'Dept B'
        assert 'shared_projects' in ctx and ctx['shared_projects'] == ['proj-x']
    finally:
        # Reset manager to avoid side-effects
        org_service.set_neo4j_manager(None)
