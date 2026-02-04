# Temporal Framework — Architecture & Potential Overview

## Purpose & Outcomes
- Problem: Static 5‑tuple access over‑blocks and cannot reflect emergencies or temporary authority.
- PRD Goal: Add “when” — time window, situation, and temporal role — to reduce inappropriate denials and prevent permanent escalation.
- Outcome: A context‑aware, time‑bounded, auditable, and resilient 6‑tuple access framework.

## Capabilities at a Glance
- TemporalContext: time windows, situations (EMERGENCY/AUDIT/NORMAL), temporal roles (on‑call/acting), auto‑expiry.
- Org Intelligence: Graphiti or Team B HTTP for reporting, departments, shared projects, temporal roles.
- Policy Evaluation: ALLOW/BLOCK with reasons and confidence; YAML rules for fallback.
- Safety & Resilience: caching, rate‑limit awareness, retries/backoff, failure tracking + alerts, ALLOW_WITH_AUDIT fallback.
- Audit & Metrics: structured audit logs; optional Prometheus metrics.

## System Diagram (Conceptual)
```
Client Request
	│
	▼
Temporal Enricher (Graphiti calls: reporting, department, projects, temporal roles)
	│
	▼
6‑Tuple Policy Engine (rules + risk + audit)
	│
	▼
Decision: ALLOW / BLOCK (+ audit)
```
- Enricher: caches results (TTL ~120s) to reduce load.
- External Org Service: clean HTTP boundary; no code embedding.
- Resilience: minimal fallback context when Graphiti fails; alerts if failure rate >5% in 5 minutes.

## Integrations & Data Flow
- Graphiti / Team B: environment‑driven base URLs/tokens; staging/production friendly.
- Neo4j (optional): persist contexts, relationships; support knowledge graph enrichment.
- YAML Fallback: local mock data/rules for deterministic demos and tests.

## Security & Compliance Signals
- Least Privilege: outside business hours without temporal role → BLOCK.
- Emergency Authorization: requires authorization ID for `emergency_override`.
- Auto‑Expiry: windows enforce decay; revert to BLOCK without manual revocation.
- Explainability: matched rule + reasons + confidence; audit sampling configurable.

## Resilience & Observability
- Cache: hit/miss/eviction stats; tune TTL (60–180s).
- Failure Tracker: rolling 5‑minute window; alerts and fallback on elevated failures.
- Retries/Backoff: handle timeouts and transient errors gracefully.
- Metrics: optional Prometheus exposure for runtime visibility.

## Extensibility & Roadmap
- Domains: healthcare (ER/ICU), finance (trading windows), HR (acting titles), security (incidents).
- Temporal Roles: deeper delegation chains, role overlap handling, seniority/risk scoring.
- Policies: richer DSL, scenario libraries (emergency/audit/maintenance), simulation tooling.
- Ops: governance reporting, admin UI (later), async search where needed.

## Demo Script
- 5‑tuple would BLOCK (narrative): after‑hours, no emergency, no temporal role.
- Emergency scenario → ALLOW: ER doctor, EMERGENCY situation, time‑bounded window.
- Non‑emergency audit/on‑call: allowed inside window; denied outside.
- Auto‑expiry: access reverts to BLOCK when the window ends.

## Proof Points
- PRD met: temporal intelligence reduces inappropriate denials.
- No zombie permissions: automatic revocation via time windows.
- Production‑safe: resilient integrations, auditability, clear microservice boundaries.
