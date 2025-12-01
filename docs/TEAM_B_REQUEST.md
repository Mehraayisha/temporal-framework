# Request to Team B: Org Data + Evaluation API

This document contains a short request you can send to Team B (Org Service / HR) to obtain the canonical data and the preferred evaluation API contract.

Purpose
-------
We need canonical IDs and emergency authorization information to reliably perform temporal role inheritance validation and to determine shared-project relationships. Ideally Team B will provide a runtime evaluation endpoint that accepts a small context and returns a decision; if not, a normalized export with canonical IDs and emergency_authorizations will work as a fallback.

Minimum data requested (canonical export)
----------------------------------------
- users: list of user objects with fields:
  - id (string, canonical user id e.g. emp-001)
  - name (string, display name)
  - department_id (string)
  - manager_id (string or null)
  - security_clearance (string)
  - emergency_authorizations (array of strings, e.g. ["oncall_read_emergency", "acting_manager"])

- departments: list of department objects with fields:
  - id (string, canonical dept id)
  - name (string)
  - department_head_id (string)

- projects: list of project objects with fields:
  - id (string)
  - name (string)
  - team_member_ids (array of canonical user ids)

Optional helpful fields
-----------------------
- user aliases or historical ids
- project role for each user (owner, contributor)
- timezone / business hours metadata

Evaluation API (preferred)
---------------------------
If Team B can expose a runtime evaluation endpoint (HTTP JSON), we ask for the following contract (small, fast, idempotent):

Request (POST /evaluate)
```
{
  "sender_id": "emp-001",
  "recipient_id": "emp-042",
  "temporal_role": "oncall_read_emergency",    // optional
  "situation": "EMERGENCY",                    // optional
  "service_id": "notifications",              // optional
  "timestamp": "2025-11-02T13:00:00Z"          // optional
}
```

Response
```
{
  "decision": "ALLOW" | "DENY" | "CONDITIONAL",
  "reasons": ["matched_oncall_policy", "department_match"],
  "matched_rule_id": "rule-123",
  "confidence": 0.92,
  "organization_context": {
     "sender_department": "Executive",
     "recipient_department": "Executive",
     "relationship_type": "manager",
     "shared_projects": ["proj-phoenix"]
  }
}
```

Notes
-----
- Prefer canonical IDs to avoid name ambiguity.
- If Team B cannot provide an eval endpoint, periodic exports (e.g., hourly) with canonical IDs and `emergency_authorizations` will be sufficient.
- We will accept CSV, JSON, or NDJSON. Provide the schema and a sample export.

Suggested email (short)
-----------------------
Subject: Request for canonical org export / eval API for Temporal Framework

Hi Team B,

We're integrating temporal role inheritance and emergency-auth checks into our privacy framework. To complete deterministic validation we need either:

1) A runtime evaluation API (preferred) with the contract described in the attached doc, or
2) A periodic canonical export (JSON/NDJSON) with users, departments, projects and `emergency_authorizations` per-user.

Could you provide either (1) or (2) and a small sample? Happy to help map fields if needed.

Thanks,
[Your name]

---

If you want, I can also produce a script that validates the export against our normalizer before ingestion.
