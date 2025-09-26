# core/evaluator.py
from datetime import datetime
from typing import Any, Dict, List
from core.tuples import EnhancedContextualIntegrityTuple
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = ROOT / "mocks" / "rules.yaml"

def load_rules() -> List[Dict[str, Any]]:
    """Load rules from YAML file"""
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data.get("rules", [])

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

def evaluate(request_tuple: EnhancedContextualIntegrityTuple, rules=None) -> Dict[str, Any]:
    now = request_tuple.temporal_context.timestamp
    rules = rules if rules is not None else load_rules()
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
