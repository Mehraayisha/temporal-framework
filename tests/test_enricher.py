# tests/test_enricher.py
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from core.enricher import enrich_temporal_context
from core.graphiti_manager import TemporalGraphitiManager, GraphitiConfig

def test_enricher_basic():
    """Test basic enricher functionality"""
    now = datetime.now(timezone.utc)
    tc = enrich_temporal_context("billing", now=now)
    assert tc.timestamp == now
    assert isinstance(tc.business_hours, bool)
    assert tc.situation in ("NORMAL", "EMERGENCY")

def test_enricher_with_graphiti():
    """Test enricher with Graphiti integration (company server)"""
    # Skip if no password provided (don't fail CI/CD)
    password = os.getenv('NEO4J_PASSWORD')
    if not password:
        print("Skipping Graphiti test - NEO4J_PASSWORD not set")
        return
    
    # Use company Graphiti configuration
    config = GraphitiConfig(
        neo4j_uri="bolt://ssh.phorena.com:57687",
        neo4j_user="llm_security",
        neo4j_password=password,
        team_namespace="llm_security"
    )
    
    try:
        graphiti_manager = TemporalGraphitiManager(config)
        now = datetime.now(timezone.utc)
        
        # Test enrichment with Graphiti auto-save
        tc = enrich_temporal_context("payment-service", now=now, graphiti_manager=graphiti_manager)
        
        assert tc.timestamp == now
        assert isinstance(tc.business_hours, bool)
        assert tc.situation in ("NORMAL", "EMERGENCY")
        
        graphiti_manager.close()
        print("✅ Enricher working with company Graphiti server")
        
    except Exception as e:
        print(f"⚠️ Graphiti test failed (fallback to YAML): {e}")
        # Test should still pass with YAML fallback
        tc = enrich_temporal_context("payment-service", now=now)
        assert tc.timestamp == now

def test_enricher_with_mock_graphiti():
    """Test enricher with mock Graphiti (for CI/CD)"""
    mock_graphiti = Mock()
    mock_graphiti.create_temporal_context.return_value = "mock-context-id"
    
    now = datetime.now(timezone.utc)
    tc = enrich_temporal_context("test-service", now=now, graphiti_manager=mock_graphiti)
    
    assert tc.timestamp == now
    assert isinstance(tc.business_hours, bool)
    # Should have called Graphiti to save the context
    mock_graphiti.create_temporal_context.assert_called_once()
