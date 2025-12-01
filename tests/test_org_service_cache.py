from datetime import datetime, timezone, timedelta

import pytest

from core import org_service
from core.org_importer import SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS


def test_org_lookup_works_after_load():
    # Load sample export with a generous TTL
    org_service.load_export(SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS, ttl_seconds=300)

    ctx = org_service.org_lookup('emp-001', 'emp-001')
    assert ctx is not None
    assert ctx.get('sender_department') == 'Executive'


def test_org_lookup_raises_when_cache_expired():
    # Load sample export with short TTL
    org_service.load_export(SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS, ttl_seconds=1)

    # Force loaded_at to a time in the past beyond TTL
    org_service._CACHE_META['loaded_at'] = datetime.now(timezone.utc) - timedelta(seconds=120)

    with pytest.raises(RuntimeError) as exc:
        org_service.org_lookup('emp-001', 'emp-001')

    assert 'Org cache expired' in str(exc.value)
