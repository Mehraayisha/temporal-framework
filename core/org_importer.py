"""Simple Team B export validator + normalizer

This script validates the minimal schema Team B should provide, normalizes
human names to IDs where possible, and reports warnings for missing fields.

Run locally to check the sample payload and get a normalized JSON you can
feed into the local importer/cache.
"""
from typing import List, Dict, Any, Tuple, Optional
import json
from datetime import datetime


SAMPLE_USERS = [
    {
      "id": "emp-001",
      "name": "Sarah Chen",
      "email": "sarah.chen@techflow.com",
      "title": "CEO & Co-Founder",
      "department": "Executive",
      "team": "Executive Team",
      "reports_to": None,
      "skills": ["Leadership", "Strategy", "Business Development", "Fundraising"],
      "location": "San Francisco, CA",
      "timezone": "America/Los_Angeles",
      "phone": "+1-415-555-0001",
      "employee_type": "full_time",
      "security_clearance": "executive",
      "hire_date": "2018-03-15T09:00:00+00:00",
      "working_hours": {"start": "08:00", "end": "18:00"},
      "remote_eligible": False
    }
]

SAMPLE_DEPARTMENTS = [
    {
      "id": "dept-exec",
      "name": "Executive",
      "description": "C-suite and executive leadership team",
      "department_head": "Sarah Chen",
      "budget": 800000,
      "headCount": 4,
      "data_classification": "restricted",
      "office_location": "San Francisco, CA"
    }
]

SAMPLE_PROJECTS = [
    {
      "id": "proj-phoenix",
      "name": "Project Phoenix",
      "description": "AI-powered analytics dashboard for enterprise customers",
      "status": "active",
      "start_date": "2025-08-01T09:00:00+00:00",
      "end_date": "2025-12-31T17:00:00+00:00",
      "budget": 500000,
      "project_lead": "Priya Patel",
      "department": "Engineering",
      "data_classification": "confidential",
      "team_members": [
        "Priya Patel",
        "Emily Zhang",
        "Kevin Zhang",
        "David Kim",
        "Laura Bennett",
        "Sophie Martinez"
      ]
    }
]


def validate_export_schema(users: List[Dict[str, Any]],
                           departments: List[Dict[str, Any]],
                           projects: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    errors = []
    warnings = []

    # Basic checks
    if not isinstance(users, list):
        errors.append("users must be a list")
    if not isinstance(departments, list):
        errors.append("departments must be a list")
    if not isinstance(projects, list):
        errors.append("projects must be a list")

    # Check user fields
    for u in users:
        if 'id' not in u:
            errors.append("user missing 'id' field: %r" % (u.get('name') if isinstance(u, dict) else str(u)))
        if 'name' not in u:
            warnings.append(f"user {u.get('id','?')} missing name")
        if 'department' not in u:
            warnings.append(f"user {u.get('id','?')} missing department")

    # Check departments
    dept_names = {d.get('name'): d for d in departments}
    for d in departments:
        if 'id' not in d:
            errors.append("department missing 'id' field: %r" % d.get('name'))
        if 'data_classification' not in d:
            warnings.append(f"department {d.get('id','?')} missing data_classification")

    # Check projects
    for p in projects:
        if 'id' not in p:
            errors.append("project missing 'id' field: %r" % p.get('name'))
        if 'team_members' in p and not isinstance(p['team_members'], list):
            errors.append(f"project {p.get('id','?')} team_members must be a list")

    return errors, warnings


def build_name_to_id_map(users: List[Dict[str, Any]]) -> Dict[str, str]:
    m = {}
    for u in users:
        name = u.get('name')
        uid = u.get('id')
        if name and uid:
            m[name] = uid
    return m


def normalize_export(users: List[Dict[str, Any]],
                     departments: List[Dict[str, Any]],
                     projects: List[Dict[str, Any]],
                     name_to_id_override: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Normalize names to ids where possible and return normalized dict.
    This function is permissive: missing items will be reported but normalization
    will continue with best-effort mapping.
    """
    errors, warnings = validate_export_schema(users, departments, projects)
    result = {
        'errors': errors,
        'warnings': warnings,
        'normalized': {
            'users': {},
            'departments': {},
            'projects': {}
        }
    }

    # Start with auto-built mapping from users, allow an override map to be provided
    name_to_id = build_name_to_id_map(users)
    if name_to_id_override:
        # override or extend the mapping provided by Team B
        name_to_id.update(name_to_id_override)

    # Normalize departments: ensure department id exists; map department_head name->id
    for d in departments:
        dept_id = d.get('id') or d.get('name')
        dept_head_name = d.get('department_head')
        dept_head_id = name_to_id.get(dept_head_name) if dept_head_name else None
        normalized_dept = dict(d)
        normalized_dept['department_head_id'] = dept_head_id
        # keep both id and name
        result['normalized']['departments'][dept_id] = normalized_dept

    # Normalize users: ensure reports_to becomes manager_id (if name -> convert), attach dept_id
    for u in users:
        uid = u.get('id')
        normalized_user = dict(u)
        # reports_to may be name or id or None
        rpt = u.get('reports_to')
        if rpt is None:
            normalized_user['manager_id'] = None
        else:
            # prefer direct match in name_to_id, else assume it's already an id
            normalized_user['manager_id'] = name_to_id.get(rpt, rpt)
        # department: convert name -> department id (if exists)
        dept_name = u.get('department')
        if dept_name in result['normalized']['departments']:
            normalized_user['department_id'] = list(result['normalized']['departments'].keys())[list(result['normalized']['departments'].values()).index(result['normalized']['departments'][dept_name])] if False else None
            # above logic is intentionally skipped because departments keyed by id; do better:
        # try to find department by name
        found_dept_id = None
        for did, dd in result['normalized']['departments'].items():
            if dd.get('name') == dept_name or dd.get('id') == dept_name:
                found_dept_id = did
                break
        normalized_user['department_id'] = found_dept_id

        # normalize emergency authorizations if present
        if 'emergency_authorizations' not in normalized_user:
            # attempt to infer from security_clearance (best-effort)
            normalized_user['emergency_authorizations'] = []
        result['normalized']['users'][uid] = normalized_user

    # Normalize projects: convert team member names -> user_ids where possible
    for p in projects:
        pid = p.get('id')
        normalized_p = dict(p)
        member_ids = []
        for m in p.get('team_members', []):
            if m in name_to_id:
                member_ids.append(name_to_id[m])
            else:
                # not found; keep original name but add warning
                result['warnings'].append(f"project {pid} member '{m}' not present in users; leaving as name")
                member_ids.append(m)
        normalized_p['team_member_ids'] = member_ids
        # map project_lead name -> id if possible
        lead = p.get('project_lead')
        normalized_p['project_lead_id'] = name_to_id.get(lead, lead)
        result['normalized']['projects'][pid] = normalized_p

    # Post-normalization checks
    # ensure all manager_ids point to known users; warn otherwise
    for uid, u in result['normalized']['users'].items():
        mid = u.get('manager_id')
        if mid and mid not in result['normalized']['users']:
            result['warnings'].append(f"user {uid} manager_id '{mid}' not found among users")

    return result


if __name__ == '__main__':
    print("Team B export validator + normalizer running\n")
    norm = normalize_export(SAMPLE_USERS, SAMPLE_DEPARTMENTS, SAMPLE_PROJECTS)
    print("=== ERRORS ===")
    print(json.dumps(norm['errors'], indent=2))
    print('\n=== WARNINGS ===')
    print(json.dumps(norm['warnings'], indent=2))
    print('\n=== NORMALIZED OUTPUT ===')
    print(json.dumps(norm['normalized'], indent=2))
