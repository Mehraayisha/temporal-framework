import pytest
from pydantic import ValidationError

from core.tuples import TemporalContext


def test_emergency_requires_authorization_id_missing():
    """Creating a TemporalContext with emergency_override=True and no auth id should fail."""
    with pytest.raises(ValidationError):
        # Direct construction triggers pydantic validation
        TemporalContext(emergency_override=True)


def test_emergency_with_authorization_id_passes():
    """TemporalContext with emergency_override=True and an auth id should succeed."""
    tc = TemporalContext(emergency_override=True, emergency_authorization_id="AUTH-123")
    assert tc.emergency_override is True
    assert tc.emergency_authorization_id == "AUTH-123"
