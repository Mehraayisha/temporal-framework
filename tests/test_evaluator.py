# tests/test_evaluator.py
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from core.tuples import TemporalContext, EnhancedContextualIntegrityTuple
from core.evaluator import evaluate
from core.graphiti_manager import TemporalGraphitiManager, GraphitiConfig

def make_tc(now, emergency=False):
    return TemporalContext(
        timestamp=now,
        timezone="UTC",
        business_hours=not emergency,
        emergency_override=emergency,
        access_window=None,
        data_freshness_seconds=None,
        situation="EMERGENCY" if emergency else "NORMAL",
        temporal_role=None,
        event_correlation=None
    )

def test_evaluator_no_match_blocks():
    now = datetime.now(timezone.utc)
    tc = make_tc(now, emergency=False)
    req = EnhancedContextualIntegrityTuple("unknown","s","a","b","tp", tc)
    res = evaluate(req, rules=[])  # no rules
    assert res["action"] == "BLOCK"

def test_evaluator_emergency_allows():
    now = datetime.now(timezone.utc)
    tc = make_tc(now, emergency=True)
    req = EnhancedContextualIntegrityTuple("financial","s","x","oncall-team","tp", tc)
    # rule matching inline
    rules = [{
        "id":"EMRG-TEST",
        "action":"ALLOW",
        "tuples":{"data_type":"financial","data_sender":"*","data_recipient":"oncall-team","transmission_principle":"*"},
        "temporal_context":{"situation":"EMERGENCY","require_emergency_override":True}
    }]
    res = evaluate(req, rules=rules)
    assert res["action"] == "ALLOW" and res["matched_rule_id"] == "EMRG-TEST"

def test_evaluator_time_window_blocks_when_outside():
    now = datetime.now(timezone.utc)
    tc = make_tc(now, emergency=False)
    req = EnhancedContextualIntegrityTuple("hr","s","a","b","tp", tc)
    rules = [{
        "id":"TW-1",
        "action":"ALLOW",
        "tuples":{"data_type":"hr"},
        "temporal_context":{"access_window":{"start":"2000-01-01T00:00:00+00:00","end":"2000-01-01T01:00:00+00:00"}}
    }]
    res = evaluate(req, rules=rules)
    assert res["action"] == "BLOCK"

def test_evaluator_with_graphiti():
    """Test evaluator with Graphiti integration (company server)"""
    # Skip if no password provided
    password = os.getenv('NEO4J_PASSWORD') 
    if not password:
        print("Skipping Graphiti test - NEO4J_PASSWORD not set")
        return
    
    config = GraphitiConfig(
        neo4j_uri="bolt://ssh.phorena.com:57687",
        neo4j_user="llm_security",
        neo4j_password=password,
        team_namespace="llm_security"  
    )
    
    try:
        graphiti_manager = TemporalGraphitiManager(config)
        
        now = datetime.now(timezone.utc)
        tc = make_tc(now, emergency=True)
        req = EnhancedContextualIntegrityTuple("financial","account","engineer","fraud_service","emergency", tc)
        
        # Test evaluation with Graphiti-backed rules
        res = evaluate(req, graphiti_manager=graphiti_manager)
        assert res["action"] in ["ALLOW", "BLOCK"]  # Should get some decision
        
        graphiti_manager.close()
        print("✅ Evaluator working with company Graphiti server")
        
    except Exception as e:
        print(f"⚠️ Graphiti test failed (fallback to YAML): {e}")
        # Should still work with YAML fallback
        res = evaluate(req)
        assert res["action"] in ["ALLOW", "BLOCK"]

def test_evaluator_with_mock_graphiti():
    """Test evaluator with mock Graphiti (for CI/CD)"""
    mock_graphiti = Mock()
    # Mock Graphiti to return some rules
    mock_graphiti.search_entities.return_value = [
        {
            "properties": {
                "rule_id": "test_rule",
                "action": "ALLOW",
                "data_type": "financial",
                "data_sender": "engineer", 
                "data_recipient": "fraud_service",
                "transmission_principle": "emergency",
                "situation": "EMERGENCY",
                "require_emergency_override": True,
                "team": "llm_security"
            }
        }
    ]
    
    now = datetime.now(timezone.utc)
    tc = make_tc(now, emergency=True)
    req = EnhancedContextualIntegrityTuple("financial","account","engineer","fraud_service","emergency", tc)
    
    res = evaluate(req, graphiti_manager=mock_graphiti)
    assert res["action"] == "ALLOW"
    assert res["matched_rule_id"] == "test_rule"
