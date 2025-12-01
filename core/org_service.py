"""Org service: ingestion, TTL cache, and lookup API for Team B exports.

Clean, single-file implementation that prefers a Neo4j manager when registered
and falls back to an in-memory normalized export cache.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging

from core.org_importer import normalize_export, SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS
from core import audit

logger = logging.getLogger(__name__)

# In-memory store
_STORE: Dict[str, Dict[str, Any]] = {
    "users": {},
    "departments": {},
    "projects": {}
}

_CACHE_META: Dict[str, Any] = {
    "loaded_at": None,
    "ttl_seconds": 300
}

# Optional Neo4j manager (set with `set_neo4j_manager`).
_NEO4J_MANAGER = None


def set_neo4j_manager(manager) -> None:
    """Register a Neo4j manager instance for graph-backed lookups.

    The manager should expose a `.driver` attribute compatible with the
    official neo4j driver (i.e. driver.session()).
    """
    global _NEO4J_MANAGER
    _NEO4J_MANAGER = manager


def ingest_normalized(normalized: Dict[str, Any], ttl_seconds: int = 300) -> None:
    """Ingest the normalized payload produced by `normalize_export` into store."""
    _STORE['users'] = normalized.get('users', {})
    _STORE['departments'] = normalized.get('departments', {})
    _STORE['projects'] = normalized.get('projects', {})
    _CACHE_META['loaded_at'] = datetime.now(timezone.utc)
    _CACHE_META['ttl_seconds'] = ttl_seconds


def load_export(users: List[Dict[str, Any]],
                departments: List[Dict[str, Any]],
                projects: List[Dict[str, Any]],
                ttl_seconds: int = 300,
                name_to_id_override: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Normalize and ingest a raw Team B export (users, departments, projects).

    Returns the normalization result (errors/warnings/normalized) for logging.
    """
    norm = normalize_export(users, departments, projects, name_to_id_override=name_to_id_override)
    ingest_normalized(norm['normalized'], ttl_seconds=ttl_seconds)
    return norm


def cache_expired() -> bool:
    loaded = _CACHE_META.get('loaded_at')
    if not loaded:
        return True
    return (datetime.now(timezone.utc) - loaded).total_seconds() > _CACHE_META.get('ttl_seconds', 300)


def _find_shared_projects(sender: Dict[str, Any], recipient: Dict[str, Any]) -> List[str]:
    shared = []
    for pid, proj in _STORE['projects'].items():
        members = proj.get('team_member_ids', [])
        # members may contain names if unresolved
        if sender.get('id') in members or sender.get('name') in members:
            if recipient.get('id') in members or recipient.get('name') in members:
                shared.append(pid)
    return shared


def _org_lookup_neo4j(sender_id: str, recipient_id: str) -> Dict[str, Any]:
    """Attempt to resolve org context from Neo4j using the registered manager.

    Returns a dict with the expected keys or raises RuntimeError on failure.
    """
    if not _NEO4J_MANAGER:
        raise RuntimeError("Neo4j manager not configured")

    driver = _NEO4J_MANAGER.driver
    with driver.session() as session:
        # Defensive: return a single record with sender/recipient/dept/shared_projects
        query = (
            "MATCH (s:User {id: $sender_id}) OPTIONAL MATCH (s)-[:MEMBER_OF]->(sd:Department) "
            "OPTIONAL MATCH (r:User {id: $recipient_id}) OPTIONAL MATCH (r)-[:MEMBER_OF]->(rd:Department) "
            "OPTIONAL MATCH (s)-[:MEMBER_OF]->(sp:Project)<-[:MEMBER_OF]-(r) "
            "RETURN s {.*} as sender, sd {.*} as sender_dept, r {.*} as recipient, rd {.*} as recipient_dept, collect(DISTINCT sp.id) as shared_projects"
        )
        result = session.run(query, sender_id=sender_id, recipient_id=recipient_id)
        record = result.single()
        if not record:
            # try looser name-based lookup
            query2 = (
                "MATCH (s:User) WHERE s.name = $sender_name OPTIONAL MATCH (s)-[:MEMBER_OF]->(sd:Department) "
                "MATCH (r:User) WHERE r.name = $recipient_name OPTIONAL MATCH (r)-[:MEMBER_OF]->(rd:Department) "
                "OPTIONAL MATCH (s)-[:MEMBER_OF]->(sp:Project)<-[:MEMBER_OF]-(r) "
                "RETURN s {.*} as sender, sd {.*} as sender_dept, r {.*} as recipient, rd {.*} as recipient_dept, collect(DISTINCT sp.id) as shared_projects"
            )
            result2 = session.run(query2, sender_name=sender_id, recipient_name=recipient_id)
            record = result2.single()

        if not record:
            raise RuntimeError('No graph data found for provided ids')

        sender = record.get('sender') or {}
        recipient = record.get('recipient') or {}
        sender_dept = record.get('sender_dept') or {}
        recipient_dept = record.get('recipient_dept') or {}
        shared_projects = record.get('shared_projects') or []

        # determine relationship
        relationship = 'peer'
        if sender.get('manager_id') == recipient.get('id'):
            relationship = 'subordinate'
        elif recipient.get('manager_id') == sender.get('id'):
            relationship = 'manager'

        org_distance = 2
        if relationship in ('manager', 'subordinate'):
            org_distance = 1
        elif sender_dept and recipient_dept and sender_dept.get('id') == recipient_dept.get('id'):
            org_distance = 1

        return {
            'sender_department': sender_dept.get('name') if sender_dept else None,
            'recipient_department': recipient_dept.get('name') if recipient_dept else None,
            'relationship_type': relationship,
            'organizational_distance': org_distance,
            'sender_clearance': sender.get('security_clearance'),
            'recipient_clearance': recipient.get('security_clearance'),
            'emergency_authorizations': sender.get('emergency_authorizations', []),
            'shared_projects': shared_projects
        }


def org_lookup(sender_id: str, recipient_id: str) -> Optional[Dict[str, Any]]:
    """Return organizational context for sender->recipient.

    Prefer graph-backed lookup when a Neo4j manager is configured; fall back to
    the in-memory normalized export store.
    """
    # prefer graph
    if _NEO4J_MANAGER:
        try:
            # record an attempted graph lookup
            try:
                audit.increment_metric('org_graph_lookups')
            except Exception:
                pass
            return _org_lookup_neo4j(sender_id, recipient_id)
        except Exception as e:
            logger.debug(f"Neo4j lookup failed, falling back to cache: {e}")

    if cache_expired():
        try:
            audit.increment_metric('org_cache_misses')
        except Exception:
            pass
        raise RuntimeError('Org cache expired; reload from Team B export')

    users = _STORE['users']
    sender = users.get(sender_id)
    recipient = users.get(recipient_id)
    if not sender or not recipient:
        # try name-based
        for uid, u in users.items():
            if u.get('name') == sender_id:
                sender = u
            if u.get('name') == recipient_id:
                recipient = u
    if not sender or not recipient:
        try:
            audit.increment_metric('org_cache_misses')
        except Exception:
            pass
        return None

    # cache hit
    try:
        audit.increment_metric('org_cache_hits')
    except Exception:
        pass

    depts = _STORE['departments']
    sender_dept = depts.get(sender.get('department_id')) or next((d for d in depts.values() if d.get('name') == sender.get('department')), None)
    recipient_dept = depts.get(recipient.get('department_id')) or next((d for d in depts.values() if d.get('name') == recipient.get('department')), None)

    relationship = 'peer'
    if sender.get('manager_id') == recipient.get('id'):
        relationship = 'subordinate'
    elif recipient.get('manager_id') == sender.get('id'):
        relationship = 'manager'

    shared_projects = _find_shared_projects(sender, recipient)

    return {
        'sender_department': sender_dept.get('name') if sender_dept else None,
        'recipient_department': recipient_dept.get('name') if recipient_dept else None,
        'relationship_type': relationship,
        'organizational_distance': 1 if relationship in ('manager', 'subordinate') or (sender_dept and recipient_dept and sender_dept.get('id') == recipient_dept.get('id')) else 2,
        'sender_clearance': sender.get('security_clearance'),
        'recipient_clearance': recipient.get('security_clearance'),
        'emergency_authorizations': sender.get('emergency_authorizations', []),
        'shared_projects': shared_projects
    }


if __name__ == '__main__':
    # Quick demo using the SAMPLE_* payload from org_importer
    print('Loading sample Team B export into org_service...')
    norm = load_export(SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS, ttl_seconds=300)
    print('\nNormalization warnings:')
    for w in norm.get('warnings', []):
        print(' -', w)

    print('\nStore loaded. Running sample lookups:')

    # Example 1: emp-001 -> emp-001 (self)
    ctx = org_lookup('emp-001', 'emp-001')
    print('\nLookup emp-001 -> emp-001:')
    print(ctx)

    # Example 2: lookup where recipient not present
    try:
        ctx2 = org_lookup('emp-001', 'nonexistent-user')
        print('\nLookup emp-001 -> nonexistent-user:')
        print(ctx2)
    except Exception as exc:
        print('Error during lookup:', exc)
