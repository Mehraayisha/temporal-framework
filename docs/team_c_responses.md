## Team C → Team A: Answers to integration questions

Date: 2025-11-05

This document answers the four questions Team C asked about the integration format, validation behavior, response shape, and performance guidance.

---

## 1) Is this format correct?

Short answer: Yes — the `EnhancedContextualIntegrityTuple` + `TemporalContext` + `TimeWindow` structure you described is the expected input shape.

Details and recommended additions:

- Required fields: `data_subject`, `data_sender`, `data_recipient`, `data_type`, `transmission_principle`, and `temporal_context` (which itself must include `situation`, `temporal_role`, `emergency_override`, `access_window` with `start`/`end`, and `timestamp` timezone-aware).
- Recommended additional fields (for tracing and safe validation):
  - `request_id` (string, UUID) — required for correlation and debugging.
  - `correlation_id` (optional) — when the call is part of a larger workflow.
  - `emergency_authorization_id` (string) — required when `emergency_override == true` to assert an explicit authorization and to support audit.

Urgency mapping guidance (Team C mapping is acceptable, with a small tightening):

| urgency_level | temporal_role      | emergency_override |
|---------------:|:-------------------|:-------------------|
| low            | user               | False              |
| normal         | user               | False              |
| high           | oncall_high        | False unless explicit auth provided |
| critical       | oncall_critical    | True (but only if emergency_authorization_id present) |

Rationale: map `high` -> elevated role for evaluation, but do not grant automatic override (bypass) without an explicit `emergency_authorization_id`. Reserve automatic `emergency_override=True` for `critical` or when an explicit authorization is supplied.

---

## 2) What should Team C expect back? (response shape)

Minimal shape you showed is acceptable; we recommend the following fuller response for traceability and operational needs.

Recommended response JSON (fields explained):

```json
{
  "decision": "ALLOW",                       
  "decision_id": "uuid-v4",                 
  "evaluation_timestamp": "2025-11-05T14:00:00Z",
  "confidence": 0.75,                         
  "reasoning": "Matched policy: emergency_access_01",
  "policy_rule_matched": "emergency_access_01",
  "emergency_override": true,                 
  "urgency_level": "critical",
  "time_window_valid": true,
  "audit_required": true,
  "cache_ttl_seconds": 120,
  "details": null
}
```

Field notes:
- `decision`: "ALLOW" | "DENY".
- `decision_id`: UUID for correlation and logs.
- `evaluation_timestamp`: ISO8601 UTC timestamp of evaluation.
- `confidence`: float 0..1 indicating confidence in decision.
- `reasoning`: brief human-readable rationale.
- `policy_rule_matched`: optional id/name of policy used.
- `emergency_override`: boolean echoed back.
- `urgency_level`: echoed input mapping.
- `time_window_valid`: boolean result of time-window check.
- `audit_required`: whether the engine marked this for audit persistence.
- `cache_ttl_seconds`: present when the result used fallback cache (helps callers decide retry/backoff).
- `details`: optional structured explanation or null.

HTTP behavior and error shapes:
- Validation errors → HTTP 400 with structured body: `{"error":"validation_error","details":[{"field":"...","message":"..."}]}`.
- Internal failures → HTTP 500 with `error_id` for correlation: `{"error":"internal_error","error_id":"..."}`.

---

## 3) Validation errors — what to expect and how to handle them

Server-side validation rules we enforce (summary):

- All required top-level fields present.
- `temporal_context.timestamp` must be timezone-aware (ISO8601 with offset or Z). We use timezone-aware datetimes for all comparisons.
- `access_window.start` and `access_window.end` must be present when a window is supplied; `start <= now < end` semantics are used for validity checks.
- `situation` must be one of: `NORMAL`, `EMERGENCY`, `MAINTENANCE`, `INCIDENT`, `AUDIT`.
- `temporal_role` must be one of: `user`, `admin`, `system`, `emergency_responder`, `auditor`, `oncall_low`, `oncall_medium`, `oncall_high`, `oncall_critical`.

Special rule for `emergency_override`:
- If `emergency_override == true` then `emergency_authorization_id` must be present (and non-empty). If missing, we return HTTP 400 with a field-level validation error.

Malformed time window handling:
- If `start` or `end` are missing or not parseable/timezone-aware, the response is a validation error (HTTP 400) with details about the offending fields.
- The engine will NOT silently grant access on malformed windows. If you intentionally want emergency behavior despite malformed windows, include `emergency_authorization_id` and the engine will validate the authorization and may allow (subject to policy).

Cache / graph unavailable behavior:
- If organizational lookups require the graph and the graph is unavailable but a fallback cache exists and is unexpired, the engine will use the fallback and set `cache_ttl_seconds` in the response.
- If no data is available and the engine cannot safely evaluate, it will return either a conservative `DENY` with `audit_required: true` or an explicit error (configurable). Caller should retry after backoff.

Example validation error response:

```json
{
  "error": "validation_error",
  "details": [
    {"field": "temporal_context.timestamp", "message": "missing or not timezone-aware"},
    {"field": "temporal_context.emergency_authorization_id", "message": "required when emergency_override is true"}
  ]
}
```

---

## 4) Performance considerations & recommended client behavior

Expected latency and guidance:

- Demo/local optimized evaluator: sub-100ms for simple rules (no network lookups).
- Production latency depends on: graph lookups, audit sink mode (sync vs async), and whether fallback cache was used. For network-heavy evaluation expect higher tail latency.

Recommended client settings:

- Per-request timeout: 200 ms (recommended) — adjust up if your environment requires it.
- Retries: use exponential backoff for transient errors (5xx, graph-unavailable responses). Avoid retrying on validation (4xx) without changes.
- Batching: supported but keep batches small (≤ 50 tuples) to simplify tracing and auditing.

Operational best-practices:

- Include `request_id` in each payload to correlate logs and audits.
- When sending `emergency_override`, include `emergency_authorization_id` to prevent unnecessary rejections.
- If you rely on fallback cache, pay attention to `cache_ttl_seconds` and include a retry/backoff strategy when it expires.

Example client timeout + retry pseudocode (Python):

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=(500,502,503,504))
session.mount('https://', HTTPAdapter(max_retries=retries))

resp = session.post(url, json=payload, timeout=0.2)
if resp.status_code == 200:
    data = resp.json()
    # handle decision
else:
    # handle validation or server error
```

---

## Quick sample requests & responses (three scenarios)

1) Critical Emergency (ER Doctor) — expected `ALLOW` with override

Request (JSON):

```json
{
  "request_id": "req-123",
  "data_subject": "patient_heart_rate",
  "data_sender": "system",
  "data_recipient": "emergency_doctor",
  "data_type": "HealthData.VitalSigns",
  "transmission_principle": "secure",
  "temporal_context": {
    "situation": "EMERGENCY",
    "urgency_level": "critical",
    "temporal_role": "oncall_critical",
    "emergency_override": true,
    "emergency_authorization_id": "auth-789",
    "access_window": {"start": "2025-11-05T14:00:00Z", "end": "2025-11-05T15:00:00Z"},
    "timestamp": "2025-11-05T14:00:00Z",
    "timezone": "UTC"
  }
}
```

Response (JSON):

```json
{
  "decision": "ALLOW",
  "decision_id": "uuid-...",
  "evaluation_timestamp": "2025-11-05T14:00:00Z",
  "confidence": 0.8,
  "reasoning": "emergency override verified",
  "emergency_override": true,
  "urgency_level": "critical",
  "time_window_valid": true,
  "audit_required": true
}
```

2) Normal Business Hours (HR Manager) — expected evaluation without override

Request and expected `DENY`/`ALLOW` as per your policy; ensure `timestamp` is timezone-aware.

3) Low Priority Contractor — likely `DENY` due to insecure transmission or low privilege.

---


