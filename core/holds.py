"""Simple legal-hold registry to support audit and preservation obligations.

Provides in-memory operations for test and demo purposes. Production systems
should integrate with an authoritative holds service.
"""
from datetime import datetime, timezone
from threading import RLock
from typing import Dict, List, Optional

_lock = RLock()
_HOLDS: Dict[str, Dict] = {}


def add_hold(hold_id: str, subject_type: str, subject_id: str, reason: Optional[str] = None):
    """Add or update a legal hold.

    subject_type: one of 'data_subject', 'service', 'project'
    subject_id: identifier for the subject under hold
    """
    with _lock:
        _HOLDS[hold_id] = {
            "hold_id": hold_id,
            "subject_type": subject_type,
            "subject_id": subject_id,
            "reason": reason or "",
            "created_at": datetime.now(timezone.utc),
            "active": True
        }


def clear_hold(hold_id: str):
    with _lock:
        if hold_id in _HOLDS:
            _HOLDS[hold_id]["active"] = False


def remove_hold(hold_id: str):
    with _lock:
        if hold_id in _HOLDS:
            del _HOLDS[hold_id]


def list_holds() -> List[Dict]:
    with _lock:
        return list(_HOLDS.values())


def is_on_hold(subject_type: str, subject_id: str) -> bool:
    """Return True if any active hold applies to the given subject."""
    with _lock:
        for h in _HOLDS.values():
            if not h.get("active", False):
                continue
            if h.get("subject_type") == subject_type and h.get("subject_id") == subject_id:
                return True
    return False
