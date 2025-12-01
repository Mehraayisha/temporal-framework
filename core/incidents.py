"""Small incident registry to support runtime incident toggles for Team A/B demos.

This is intentionally lightweight: an in-memory manager with thread-safe
operations to register/clear incidents and query whether a service currently
has an active incident (which the enricher will consider to enable emergency
override semantics).
"""
from datetime import datetime, timezone
from threading import RLock
from typing import Dict, List, Optional

_lock = RLock()
# incidents keyed by incident_id -> dict with fields: service, status, created_at, metadata
_INCIDENTS: Dict[str, Dict] = {}


def add_incident(incident_id: str, service: str, status: str = "investigating", metadata: Optional[Dict] = None):
    """Register an incident. If the id already exists it will be updated.

    Args:
        incident_id: unique incident identifier
        service: service name the incident applies to
        status: e.g., 'investigating', 'resolved'
        metadata: optional additional info
    """
    with _lock:
        _INCIDENTS[incident_id] = {
            "incident_id": incident_id,
            "service": service,
            "status": status,
            "type": (metadata or {}).get("type") if isinstance(metadata, dict) else None,
            "severity": (metadata or {}).get("severity") if isinstance(metadata, dict) else None,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc)
        }


def clear_incident(incident_id: str):
    """Remove an incident by id."""
    with _lock:
        if incident_id in _INCIDENTS:
            del _INCIDENTS[incident_id]


def clear_all():
    """Remove all incidents (useful for tests)."""
    with _lock:
        _INCIDENTS.clear()


def list_incidents() -> List[Dict]:
    """Return a shallow copy of current incidents."""
    with _lock:
        return list(_INCIDENTS.values())


def active_incidents_for_service(service: str) -> List[Dict]:
    """Return active (non-resolved) incidents for a given service."""
    with _lock:
        return [i for i in _INCIDENTS.values() if i.get("service") == service and i.get("status") != "resolved"]


def is_emergency_for_service(service: str) -> bool:
    """Convenience check: True if any active incident affects the service."""
    return len(active_incidents_for_service(service)) > 0


def get_primary_incident_for_service(service: str) -> Optional[Dict]:
    """Return the most recent active incident for a service or None."""
    incidents = active_incidents_for_service(service)
    if not incidents:
        return None
    # Return the most recently created incident
    incidents.sort(key=lambda i: i.get("created_at") or datetime.min, reverse=True)
    return incidents[0]


def map_incident_type_to_role(incident: Dict) -> str:
    """Map incident dict to a temporal_role string.

    Rules:
      - If `metadata.role` exists, return it (explicit override)
      - If incident.type == 'security' -> 'security_incident_lead' when severity is 'critical' else 'incident_responder'
      - If incident.type == 'system' -> 'incident_responder'
      - If incident.type == 'clinical' -> 'incident_responder'
      - Default -> 'incident_responder'
    """
    if not incident:
        return "incident_responder"

    # Metadata role override
    meta = incident.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("role"):
        return meta.get("role")

    itype = (incident.get("type") or "").lower()
    severity = (incident.get("severity") or "").lower()

    if itype == "security":
        if severity == "critical":
            return "security_incident_lead"
        return "incident_responder"
    if itype in ("system", "clinical", "service"):
        return "incident_responder"

    return "incident_responder"


def get_incident_temporal_role_for_service(service: str) -> Optional[str]:
    """Return a temporal_role derived from the primary incident for the service, or None."""
    inc = get_primary_incident_for_service(service)
    if not inc:
        return None
    return map_incident_type_to_role(inc)
