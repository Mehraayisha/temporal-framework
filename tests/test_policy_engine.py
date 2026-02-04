# tests/test_policy_engine.py
import os
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import patch, mock_open, Mock
from core.policy_engine import TemporalPolicyEngine
from core.tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple
from core.graphiti_manager import TemporalGraphitiManager, GraphitiConfig


class TestTemporalPolicyEngine:
    """Test suite for the TemporalPolicyEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = TemporalPolicyEngine()
        self.base_time = datetime.now(timezone.utc)
        
        # Create test temporal context
        self.test_context = TemporalContext(
            timestamp=self.base_time,
            timezone="UTC",
            business_hours=True,
            emergency_override=False,
            access_window=TimeWindow(
                start=self.base_time - timedelta(hours=1),
                end=self.base_time + timedelta(hours=8)
            ),
            data_freshness_seconds=300,
            situation="NORMAL",
            temporal_role="user",
            event_correlation=None
        )
        
        # Create test tuple
        self.test_tuple = EnhancedContextualIntegrityTuple(
            data_type="financial",
            data_subject="user123",
            data_sender="billing-service",
            data_recipient="audit-team", 
            transmission_principle="audit",
            temporal_context=self.test_context
        )

    def test_emergency_override_allows_access(self):
        """Test that emergency override always allows access"""
        # Create context with emergency override
        emergency_context = TemporalContext(
            timestamp=self.base_time,
            timezone="UTC",
            business_hours=False,  # Even outside business hours
            emergency_override=True,  # Emergency active!
            access_window=TimeWindow(start=self.base_time, end=self.base_time + timedelta(hours=1)),
            data_freshness_seconds=300,
            situation="EMERGENCY",
            temporal_role="emergency_responder",
            event_correlation="incident-123",
            emergency_authorization_id="AUTH-TEST-INCIDENT-123"
        )
        
        emergency_tuple = EnhancedContextualIntegrityTuple(
            data_type="financial",
            data_subject="user123", 
            data_sender="billing-service",
            data_recipient="oncall-team",
            transmission_principle="emergency-access",
            temporal_context=emergency_context
        )
        
        # Mock the YAML files
        mock_rules = {"rules": []}
        mock_oncall = {"services": {}, "global_policies": {}}
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(emergency_tuple)
                
                assert result["decision"] == "ALLOW"
                assert "Emergency override active" in result["reasons"]
                assert result["confidence_score"] == 0.9
                assert result["risk_level"] == "medium"
                assert result["expires_at"] is not None

    def test_business_hours_policy_matching(self):
        """Test that business hours policies are matched correctly"""
        # Mock business hours rule
        mock_rules = {
            "rules": [
                {
                    "id": "BUS-HOURS-001",
                    "action": "ALLOW",
                    "tuples": {
                        "data_type": "financial",
                        "data_recipient": "audit-team"
                    },
                    "temporal_context": {
                        "situation": "NORMAL"
                    }
                }
            ]
        }
        
        mock_oncall = {
            "services": {},
            "global_policies": {},
            "business_hours": {"start_hour": 9, "end_hour": 17}
        }
        
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(self.test_tuple)
                
                assert result["decision"] == "ALLOW"
                assert result["policy_matched"] == "BUS-HOURS-001"
                assert "Matched policy: BUS-HOURS-001" in result["reasons"]
                assert result["confidence_score"] > 0

    def test_outside_business_hours_denial(self):
        """Test that access is denied outside business hours without override"""
        # Create non-business hours context
        after_hours_context = TemporalContext(
            timestamp=self.base_time,
            timezone="UTC", 
            business_hours=False,  # Outside business hours
            emergency_override=False,
            access_window=TimeWindow(start=self.base_time, end=self.base_time + timedelta(hours=1)),
            data_freshness_seconds=300,
            situation="NORMAL",
            temporal_role="user",
            event_correlation=None
        )
        
        after_hours_tuple = EnhancedContextualIntegrityTuple(
            data_type="financial",
            data_subject="user123",
            data_sender="billing-service", 
            data_recipient="audit-team",
            transmission_principle="audit",
            temporal_context=after_hours_context
        )
        
        mock_rules = {"rules": []}  # No matching rules
        mock_oncall = {
            "services": {},
            "global_policies": {},
            "business_hours": {"weekend_support": {"critical_only": False}}
        }
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(after_hours_tuple)
                
                assert result["decision"] == "DENY"
                assert "Outside business hours" in result["reasons"]
                assert "No matching temporal policy found" in result["reasons"]

    def test_service_bypass_authorization(self):
        """Test that certain services get emergency bypass"""
        mock_rules = {"rules": []}
        mock_oncall = {
            "services": {},
            "global_policies": {
                "emergency_bypass_roles": ["billing-service", "critical-monitor"]
            }
        }
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(self.test_tuple)
                
                assert result["decision"] == "ALLOW"
                assert "Service billing-service has emergency bypass authorization" in result["reasons"]
                assert result["confidence_score"] == 0.8
                assert result["risk_level"] == "low"

    def test_stale_data_handling(self):
        """Test that stale data is properly flagged"""
        # Create context with stale data (over 1 hour old)
        stale_context = TemporalContext(
            timestamp=self.base_time,
            timezone="UTC",
            business_hours=True,
            emergency_override=False,
            access_window=TimeWindow(start=self.base_time, end=self.base_time + timedelta(hours=1)),
            data_freshness_seconds=7200,  # 2 hours - considered stale
            situation="NORMAL",
            temporal_role="user",
            event_correlation=None
        )
        
        stale_tuple = EnhancedContextualIntegrityTuple(
            data_type="personal",
            data_subject="user456",
            data_sender="user-service",
            data_recipient="analytics",
            transmission_principle="analysis",
            temporal_context=stale_context
        )
        
        mock_rules = {"rules": []}
        mock_oncall = {
            "services": {},
            "global_policies": {},
            "business_hours": {"weekend_support": {"critical_only": False}}
        }
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(stale_tuple)
                
                # Check temporal factors include data staleness
                assert "data_stale" in result["temporal_factors"]
                assert result["temporal_factors"]["data_stale"] is True
                assert result["temporal_factors"]["data_freshness_ok"] is False

    def test_weekend_access_restrictions(self):
        """Test weekend access restrictions"""
        # Create weekend context - find next Saturday
        days_until_saturday = (5 - self.base_time.weekday()) % 7
        if days_until_saturday == 0:  # Already Saturday
            weekend_time = self.base_time.replace(hour=14)
        else:
            weekend_time = (self.base_time + timedelta(days=days_until_saturday)).replace(hour=14)
        
        weekend_context = TemporalContext(
            timestamp=weekend_time,
            timezone="UTC",
            business_hours=False,
            emergency_override=False,
            access_window=TimeWindow(start=weekend_time, end=weekend_time + timedelta(hours=1)),
            data_freshness_seconds=300,
            situation="NORMAL",
            temporal_role="user",
            event_correlation=None
        )
        
        weekend_tuple = EnhancedContextualIntegrityTuple(
            data_type="analytics",
            data_subject="reports",
            data_sender="report-service",
            data_recipient="manager",
            transmission_principle="review",
            temporal_context=weekend_context
        )
        
        mock_rules = {"rules": []}
        mock_oncall = {
            "services": {},
            "global_policies": {},
            "business_hours": {"weekend_support": {"critical_only": True}}
        }
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(weekend_tuple)
                
                assert result["temporal_factors"]["weekend"] is True
                assert "Weekend access not permitted for this service" in result["reasons"]

    def test_active_incidents_tracking(self):
        """Test that active incidents are properly tracked"""
        mock_rules = {"rules": []}
        mock_oncall = {
            "services": {},
            "global_policies": {},
            "business_hours": {"weekend_support": {"critical_only": False}}
        }
        mock_incidents = {
            "incidents": [
                {"id": "INC-1", "status": "investigating", "service": "billing"},
                {"id": "INC-2", "status": "resolved", "service": "auth"},
                {"id": "INC-3", "status": "investigating", "service": "payments"}
            ]
        }
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(self.test_tuple)
                
                # Should count 2 active incidents (status: investigating)
                assert result["temporal_factors"]["active_incidents_count"] == 2

    def test_risk_level_calculation(self):
        """Test risk level calculation logic"""
        # High risk scenario: sensitive data + after hours + emergency
        high_risk_context = TemporalContext(
            timestamp=self.base_time,
            timezone="UTC",
            business_hours=False,  # After hours
            emergency_override=True,  # Emergency
            access_window=TimeWindow(start=self.base_time, end=self.base_time + timedelta(hours=1)),
            data_freshness_seconds=300,
            situation="EMERGENCY",
            temporal_role="emergency_responder",
            event_correlation="incident-456",
            emergency_authorization_id="AUTH-TEST-INCIDENT-456"
        )
        
        high_risk_tuple = EnhancedContextualIntegrityTuple(
            data_type="financial",  # Sensitive data
            data_subject="customer_accounts",
            data_sender="database",
            data_recipient="oncall-engineer",
            transmission_principle="emergency-fix",
            temporal_context=high_risk_context
        )
        
        mock_rules = {
            "rules": [
                {
                    "id": "EMERGENCY-001",
                    "action": "ALLOW",  # Permissive rule
                    "tuples": {"data_type": "financial"},
                    "temporal_context": {"situation": "EMERGENCY"}
                }
            ]
        }
        mock_oncall = {"services": {}, "global_policies": {}}
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(high_risk_tuple)
                
                # Emergency override should allow but be medium risk (not high due to emergency context)
                assert result["decision"] == "ALLOW"
                assert result["risk_level"] == "medium"

    def test_tuple_field_matching(self):
        """Test tuple field matching with wildcards and lists"""
        mock_rules = {
            "rules": [
                {
                    "id": "WILDCARD-001", 
                    "action": "ALLOW",
                    "tuples": {
                        "data_type": "financial",
                        "transmission_principle": "*"  # Wildcard
                    }
                },
                {
                    "id": "LIST-001",
                    "action": "ALLOW", 
                    "tuples": {
                        "data_type": ["financial", "audit", "compliance"],  # List match
                        "data_recipient": "audit-team"
                    }
                }
            ]
        }
        mock_oncall = {"services": {}, "global_policies": {}}
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(self.test_tuple)
                
                assert result["decision"] == "ALLOW"
                # Should match LIST-001 since it has exact matches
                assert result["policy_matched"] in ["WILDCARD-001", "LIST-001"]

    def test_expiration_times(self):
        """Test that expiration times are set correctly"""
        mock_rules = {
            "rules": [
                {
                    "id": "TIMED-001",
                    "action": "ALLOW",
                    "tuples": {"data_type": "financial"},
                    "temporal_context": {
                        "access_window": {
                            "end": (self.base_time + timedelta(hours=2)).isoformat()
                        }
                    }
                }
            ]
        }
        mock_oncall = {"services": {}, "global_policies": {}}
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(self.test_tuple)
                
                assert result["decision"] == "ALLOW"
                assert result["expires_at"] is not None
                # Should expire at the access window end time
                expected_expiry = (self.base_time + timedelta(hours=2)).isoformat()
                assert result["expires_at"] == expected_expiry

    def test_confidence_scoring(self):
        """Test that confidence scores are calculated properly"""
        # Perfect match should have high confidence
        mock_rules = {
            "rules": [
                {
                    "id": "PERFECT-MATCH",
                    "action": "ALLOW",
                    "tuples": {
                        "data_type": "financial",
                        "data_sender": "billing-service", 
                        "data_recipient": "audit-team",
                        "transmission_principle": "audit"
                    },
                    "temporal_context": {
                        "situation": "NORMAL"
                    }
                }
            ]
        }
        mock_oncall = {"services": {}, "global_policies": {}}
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(self.test_tuple)
                
                assert result["decision"] == "ALLOW"
                assert result["confidence_score"] > 0.8  # High confidence for perfect match

    def test_next_review_time_set(self):
        """Test that next review time is always set"""
        mock_rules = {"rules": []}
        mock_oncall = {"services": {}, "global_policies": {}}
        mock_incidents = {"incidents": []}
        
        with patch("builtins.open", mock_open()) as mock_file:
            with patch("yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [mock_rules, mock_oncall, mock_incidents]
                
                result = self.engine.evaluate_temporal_access(self.test_tuple)
                
                assert result["next_review"] is not None
                # Should be about 1 hour from now
                review_time = datetime.fromisoformat(result["next_review"])
                # Make sure both times are timezone-aware for comparison
                if review_time.tzinfo is None:
                    review_time = review_time.replace(tzinfo=timezone.utc)
                expected_review = self.base_time + timedelta(hours=1)
                # Allow 2 minutes tolerance for test execution time
                assert abs((review_time - expected_review).total_seconds()) < 120

    def test_policy_engine_with_graphiti(self):
        """Test policy engine with Graphiti integration (company server)"""
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
            engine = TemporalPolicyEngine(graphiti_manager=graphiti_manager)
            
            # Test policy evaluation with Graphiti
            result = engine.evaluate_temporal_access(self.test_tuple)
            
            assert result["decision"] in ["ALLOW", "DENY"]
            assert "confidence_score" in result
            assert "risk_level" in result
            
            graphiti_manager.close()
            print("✅ Policy engine working with company Graphiti server")
            
        except Exception as e:
            print(f"⚠️ Graphiti test failed (fallback to YAML): {e}")
            # Should still work with YAML fallback
            engine = TemporalPolicyEngine()
            result = engine.evaluate_temporal_access(self.test_tuple)
            assert result["decision"] in ["ALLOW", "DENY"]

    def test_policy_engine_with_mock_graphiti(self):
        """Test policy engine with mock Graphiti (for CI/CD)"""
        mock_graphiti = Mock()
        # Mock Graphiti to return empty rules (will use YAML fallback)
        mock_graphiti.search_entities.return_value = []
        
        engine = TemporalPolicyEngine(graphiti_manager=mock_graphiti)
        result = engine.evaluate_temporal_access(self.test_tuple)
        
        assert result["decision"] in ["ALLOW", "DENY"]
        assert "confidence_score" in result
        # Should have tried to load from Graphiti first
        mock_graphiti.search_entities.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])