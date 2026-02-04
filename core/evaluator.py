# core/evaluator.py
from datetime import datetime
import time
from typing import Any, Dict, List
from core.tuples import EnhancedContextualIntegrityTuple
from core import holds
from core import audit
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = ROOT / "mocks" / "rules.yaml"

def load_rules(neo4j_manager=None, graphiti_manager=None) -> List[Dict[str, Any]]:
    """Load rules from Graphiti (preferred), Neo4j, or YAML file (fallback)"""
    if graphiti_manager:
        try:
            return load_rules_from_graphiti(graphiti_manager)
        except Exception as e:
            print(f"Warning: Graphiti rule loading failed, using YAML fallback: {e}")
    elif neo4j_manager:
        try:
            return load_rules_from_neo4j(neo4j_manager)
        except Exception as e:
            print(f"Warning: Neo4j rule loading failed, using YAML fallback: {e}")
    
    # Fallback to YAML
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("rules", [])

def load_rules_from_neo4j(neo4j_manager) -> List[Dict[str, Any]]:
    """Load rules from Neo4j database"""
    with neo4j_manager.driver.session() as session:
        query = """
        MATCH (rule:PolicyRule {team: 'llm_security'})
        RETURN rule
        ORDER BY rule.priority DESC, rule.created_at ASC
        """
        
        rules = []
        for record in session.run(query):
            rule_data = dict(record["rule"])
            # Convert Neo4j format to evaluator format
            rules.append({
                "id": rule_data.get("rule_id"),
                "action": rule_data.get("action", "BLOCK"),
                "tuples": {
                    "data_type": rule_data.get("data_type"),
                    "data_sender": rule_data.get("data_sender"), 
                    "data_recipient": rule_data.get("data_recipient"),
                    "transmission_principle": rule_data.get("transmission_principle")
                },
                "temporal_context": {
                    "situation": rule_data.get("situation"),
                    "require_emergency_override": rule_data.get("require_emergency_override", False),
                    "access_window": rule_data.get("access_window")
                }
            })
        
        return rules

def load_rules_from_graphiti(graphiti_manager) -> List[Dict[str, Any]]:
    """Load rules from Graphiti knowledge graph"""
    try:
        # Search for policy rule entities
        rule_entities = graphiti_manager.search_entities(
            entity_type="PolicyRule",
            filters={"team": "llm_security"}
        )
        
        rules = []
        for entity in rule_entities:
            # Convert Graphiti entity to evaluator format
            props = entity.get("properties", {})
            rules.append({
                "id": props.get("rule_id"),
                "action": props.get("action", "BLOCK"),
                "tuples": {
                    "data_type": props.get("data_type"),
                    "data_sender": props.get("data_sender"), 
                    "data_recipient": props.get("data_recipient"),
                    "transmission_principle": props.get("transmission_principle")
                },
                "temporal_context": {
                    "situation": props.get("situation"),
                    "require_emergency_override": props.get("require_emergency_override", False),
                    "access_window": props.get("access_window")
                }
            })
        
        # Sort by priority and creation time
        rules.sort(key=lambda r: (r.get("priority", 100), r.get("created_at", "")))
        
        return rules
    except Exception as e:
        print(f"Error loading rules from Graphiti: {e}")
        raise

def _match_field(value: str, rule_val):
    # rule_val can be "*", a string, or a list
    if rule_val == "*" or rule_val is None:
        return True
    if isinstance(rule_val, list):
        return value in rule_val
    return value == rule_val


def _match_field_fast(value: str, rule_val):
    # Slightly faster matcher for compiled rules: avoid isinstance checks on hot path
    if rule_val is None or rule_val == "*":
        return True
    # rule_val may be a set for faster membership testing
    if isinstance(rule_val, set):
        return value in rule_val
    if isinstance(rule_val, list):
        return value in rule_val
    return value == rule_val


def compile_rules(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compile rules into a faster-invocation structure.

    - Converts access_window ISO strings into TimeWindow instances when possible.
    - Converts list matchers into sets for O(1) membership checks.
    """
    compiled = []
    try:
        from core.tuples import TimeWindow
    except Exception:
        TimeWindow = None

    for r in rules:
        tconf = r.get("temporal_context", {}) or {}
        aw = tconf.get("access_window")
        if aw and TimeWindow and not isinstance(aw, TimeWindow):
            # Accept dict with ISO strings
            try:
                aw = TimeWindow(start=aw.get("start"), end=aw.get("end"))
            except Exception:
                aw = None

        tuples = r.get("tuples", {}) or {}
        # convert list matchers to sets
        def maybe_set(v):
            if isinstance(v, list):
                return set(v)
            return v

        compiled.append({
            "id": r.get("id"),
            "action": r.get("action", "BLOCK"),
            "data_type": maybe_set(tuples.get("data_type")),
            "data_sender": maybe_set(tuples.get("data_sender")),
            "data_recipient": maybe_set(tuples.get("data_recipient")),
            "transmission_principle": maybe_set(tuples.get("transmission_principle")),
            "situation": tconf.get("situation"),
            "require_emergency_override": bool(tconf.get("require_emergency_override", False)),
            "access_window": aw,
        })
    return compiled


def evaluate_compiled(request_tuple: EnhancedContextualIntegrityTuple, compiled_rules: List[Dict[str, Any]], neo4j_manager=None, graphiti_manager=None) -> Dict[str, Any]:
    """Evaluate using pre-compiled rules for lower per-call overhead.

    This is a fast-path alternative to `evaluate` and avoids repeated parsing/lookup costs.
    """
    start = time.perf_counter()
    # Freshness check
    try:
        request_tuple.temporal_context.assert_fresh()
    except RuntimeError:
        raise

    subj = getattr(request_tuple, 'data_subject', None)
    svc = getattr(request_tuple.temporal_context, 'service_id', None)
    try:
        if subj and holds.is_on_hold('data_subject', subj):
            out = {"action": "DENY", "matched_rule_id": None, "reasons": ["legal_hold_active"]}
            try:
                audit.record_decision(out)
            except Exception:
                pass
            return out
        if svc and holds.is_on_hold('service', svc):
            out = {"action": "DENY", "matched_rule_id": None, "reasons": ["legal_hold_active"]}
            try:
                audit.record_decision(out)
            except Exception:
                pass
            return out
    except Exception:
        pass

    now = request_tuple.temporal_context.timestamp

    for r in compiled_rules:
        # fast field matching
        if not _match_field_fast(request_tuple.data_type, r.get("data_type")):
            continue
        if not _match_field_fast(request_tuple.data_sender, r.get("data_sender")):
            continue
        if not _match_field_fast(request_tuple.data_recipient, r.get("data_recipient")):
            continue

        # temporal checks
        if r.get("situation") and r.get("situation") != request_tuple.temporal_context.situation:
            continue
        if r.get("require_emergency_override") and not request_tuple.temporal_context.emergency_override:
            continue
        aw = r.get("access_window")
        if aw and not _in_time_window(now, aw):
            continue

        out = {"action": r.get("action", "BLOCK"), "matched_rule_id": r.get("id"), "reasons": ["matched rule"]}
        try:
            audit.record_decision(out)
        except Exception:
            pass
        finally:
            # record latency for the evaluation
            try:
                duration_ms = (time.perf_counter() - start) * 1000.0
                audit.record_decision_latency(duration_ms)
            except Exception:
                pass
        return out

    out = {"action": "BLOCK", "matched_rule_id": None, "reasons": ["no rule matched"]}
    try:
        audit.record_decision(out)
    except Exception:
        pass
    finally:
        try:
            duration_ms = (time.perf_counter() - start) * 1000.0
            audit.record_decision_latency(duration_ms)
        except Exception:
            pass
    return out

def _in_time_window(now: datetime, window: Dict[str, Any]):
    """Return True if 'now' falls within the window.

    Support window supplied as dict with ISO strings or as a TimeWindow instance.
    Semantics: start <= now < end when both are present. If start is None -> open start.
    If end is None -> open end.
    """
    if not window:
        return True

    # Accept TimeWindow object from core.tuples
    try:
        from core.tuples import TimeWindow
    except Exception:
        TimeWindow = None

    if TimeWindow and isinstance(window, TimeWindow):
        start_dt = window.start
        end_dt = window.end
    else:
        # Assume dict-like
        start = window.get("start")
        end = window.get("end")
        start_dt = datetime.fromisoformat(start) if start else None
        end_dt = datetime.fromisoformat(end) if end else None

    if start_dt and now < start_dt:
        return False
    if end_dt and not (now < end_dt):
        # enforce exclusive end
        return False
    return True

def evaluate(request_tuple: EnhancedContextualIntegrityTuple, rules=None, neo4j_manager=None, graphiti_manager=None) -> Dict[str, Any]:
    start = time.perf_counter()
    # Use current time to validate freshness (not the context timestamp)
    try:
        request_tuple.temporal_context.assert_fresh()
    except RuntimeError:
        # propagate the error to caller to signal a reload is required
        raise

    # Legal hold enforcement: block if a legal hold applies to the data subject or the service
    subj = getattr(request_tuple, 'data_subject', None)
    svc = getattr(request_tuple.temporal_context, 'service_id', None)
    try:
        if subj and holds.is_on_hold('data_subject', subj):
            out = {"action": "DENY", "matched_rule_id": None, "reasons": ["legal_hold_active"]}
            try:
                audit.record_decision(out)
            except Exception:
                pass
            return out
        if svc and holds.is_on_hold('service', svc):
            out = {"action": "DENY", "matched_rule_id": None, "reasons": ["legal_hold_active"]}
            try:
                audit.record_decision(out)
            except Exception:
                pass
            return out
    except Exception:
        # If holds system fails, don't change behavior (fail-open logging)
        pass
    now = request_tuple.temporal_context.timestamp
    rules = rules if rules is not None else load_rules(neo4j_manager, graphiti_manager)
    reasons = []

    for rule in rules:
        rtu = rule.get("tuples", {})
        # field matching
        if not _match_field(request_tuple.data_type, rtu.get("data_type", "*")):
            continue
        if not _match_field(request_tuple.data_sender, rtu.get("data_sender", "*")):
            continue
        if not _match_field(request_tuple.data_recipient, rtu.get("data_recipient", "*")):
            continue
        if not _match_field(request_tuple.transmission_principle, rtu.get("transmission_principle", "*")):
            continue
        # temporal checks
        tconf = rule.get("temporal_context", {})
        # situation check
        if tconf.get("situation"):
            if tconf["situation"] != request_tuple.temporal_context.situation:
                continue
        # require emergency override
        if tconf.get("require_emergency_override", False) and not request_tuple.temporal_context.emergency_override:
            continue
        # access_window check
        aw = tconf.get("access_window")
        if aw and not _in_time_window(now, aw):
            continue

        # matched
        out = {"action": rule.get("action", "BLOCK"), "matched_rule_id": rule.get("id"), "reasons": ["matched rule"]}
        try:
            audit.record_decision(out)
        except Exception:
            pass
        finally:
            try:
                duration_ms = (time.perf_counter() - start) * 1000.0
                audit.record_decision_latency(duration_ms)
            except Exception:
                pass
        return out
    # default
    out = {"action": "BLOCK", "matched_rule_id": None, "reasons": ["no rule matched"]}
    try:
        audit.record_decision(out)
    except Exception:
        pass
    finally:
        try:
            duration_ms = (time.perf_counter() - start) * 1000.0
            audit.record_decision_latency(duration_ms)
        except Exception:
            pass
    return out
