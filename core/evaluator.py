# core/evaluator.py
from datetime import datetime
from typing import Any, Dict, List
from core.tuples import EnhancedContextualIntegrityTuple
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

def _in_time_window(now: datetime, window: Dict[str, Any]):
    if not window:
        return True
    start = window.get("start")
    end = window.get("end")
    if start:
        start_dt = datetime.fromisoformat(start)
        if now < start_dt:
            return False
    if end:
        end_dt = datetime.fromisoformat(end)
        if now > end_dt:
            return False
    return True

def evaluate(request_tuple: EnhancedContextualIntegrityTuple, rules=None, neo4j_manager=None, graphiti_manager=None) -> Dict[str, Any]:
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
        return {"action": rule.get("action", "BLOCK"), "matched_rule_id": rule.get("id"), "reasons": ["matched rule"]}
    # default
    return {"action": "BLOCK", "matched_rule_id": None, "reasons": ["no rule matched"]}
