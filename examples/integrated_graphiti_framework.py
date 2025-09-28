#!/usr/bin/env python3
"""
Comprehensive example of the Temporal Framework with Graphiti Knowledge Graph integration.

This example demonstrates:
1. Setting up Graphiti connection to company Neo4j infrastructure
2. Creating and storing temporal contexts with knowledge graph relationships
3. Policy evaluation using Graphiti-backed rules
4. Team-isolated data management for the LLM Security team

Usage:
    python examples/integrated_graphiti_framework.py

Environment variables required:
    GRAPHITI_NEO4J_URI=bolt://ssh.phorena.com:57687
    NEO4J_USER=llm_security
    NEO4J_PASSWORD=your_password_here
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext, TimeWindow
from core.enricher import enrich_temporal_context
from core.evaluator import evaluate, load_rules
from core.policy_engine import TemporalPolicyEngine
from core.graphiti_manager import TemporalGraphitiManager, GraphitiConfig

def setup_graphiti_manager():
    """Set up Graphiti connection to company Neo4j infrastructure."""
    config = GraphitiConfig(
        neo4j_uri=os.getenv("GRAPHITI_NEO4J_URI", "bolt://ssh.phorena.com:57687"),
        neo4j_user=os.getenv("NEO4J_USER", "llm_security"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "your_password_here"),
        team_namespace="llm_security"
    )
    
    return TemporalGraphitiManager(config)

def demo_basic_graphiti_operations(graphiti_manager):
    """Demonstrate basic Graphiti knowledge graph operations."""
    print("🧠 Basic Graphiti Knowledge Graph Operations")
    print("=" * 50)
    
    # Create a service entity
    service_id = graphiti_manager.create_entity(
        entity_type="Service",
        properties={
            "name": "payment-processor",
            "criticality": "high",
            "owner": "payments-team",
            "oncall": ["alice@company.com", "bob@company.com"],
            "timezone": "America/New_York"
        }
    )
    print(f"✅ Created service entity: {service_id}")
    
    # Create a user entity
    user_id = graphiti_manager.create_entity(
        entity_type="User",
        properties={
            "username": "alice",
            "role": "senior_engineer",
            "department": "engineering",
            "access_level": "elevated"
        }
    )
    print(f"✅ Created user entity: {user_id}")
    
    # Create relationship between user and service
    rel_id = graphiti_manager.create_relationship(
        source_id=user_id,
        target_id=service_id,
        relationship_type="HAS_ACCESS_TO",
        properties={
            "granted_at": datetime.now(timezone.utc).isoformat(),
            "access_level": "read_write",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
    )
    print(f"✅ Created relationship: {rel_id}")
    
    # Search for entities
    services = graphiti_manager.search_entities(
        entity_type="Service",
        filters={"criticality": "high"}
    )
    print(f"✅ Found {len(services)} high-criticality services")
    
    return service_id, user_id

def demo_temporal_context_with_graphiti(graphiti_manager):
    """Demonstrate temporal context creation and Graphiti storage."""
    print("\n⏰ Temporal Context with Graphiti Storage")
    print("=" * 50)
    
    # Create temporal context
    context = TemporalContext(
        service_name="ml-training-pipeline",
        situation="incident_response",
        business_hours=False,
        incident_active=True,
        emergency_override=True,
        time_window=TimeWindow(
            start=datetime.now(timezone.utc) - timedelta(hours=1),
            end=datetime.now(timezone.utc) + timedelta(hours=4)
        )
    )
    
    print(f"📝 Created temporal context: {context.context_id}")
    print(f"   Service: {context.service_name}")
    print(f"   Situation: {context.situation}")
    print(f"   Emergency Override: {context.emergency_override}")
    
    # Save to Graphiti knowledge graph
    try:
        saved_id = context.save_to_graphiti(graphiti_manager)
        print(f"✅ Saved to Graphiti with ID: {saved_id}")
        
        # Retrieve from Graphiti
        retrieved_contexts = TemporalContext.find_by_service_graphiti(
            graphiti_manager, 
            "ml-training-pipeline"
        )
        print(f"✅ Retrieved {len(retrieved_contexts)} contexts for service")
        
    except Exception as e:
        print(f"❌ Error with Graphiti operations: {e}")
    
    return context

def demo_policy_evaluation_with_graphiti(graphiti_manager):
    """Demonstrate policy evaluation using Graphiti-backed rules."""
    print("\n🛡️  Policy Evaluation with Graphiti Rules")
    print("=" * 50)
    
    # First, let's create a sample rule in Graphiti
    rule_id = graphiti_manager.create_entity(
        entity_type="PolicyRule",
        properties={
            "rule_id": "emergency_ml_access",
            "action": "ALLOW",
            "data_type": "model_data",
            "data_sender": "ml_engineer",
            "data_recipient": "training_service",
            "transmission_principle": "emergency_override",
            "situation": "incident_response",
            "require_emergency_override": True,
            "access_window": None,
            "priority": 10,
            "team": "llm_security"
        }
    )
    print(f"✅ Created policy rule in Graphiti: {rule_id}")
    
    # Create a 6-tuple request
    request = EnhancedContextualIntegrityTuple(
        data_type="model_data",
        data_sender="ml_engineer",
        data_recipient="training_service",
        transmission_principle="emergency_override",
        temporal_context=TemporalContext(
            service_name="ml-training-pipeline",
            situation="incident_response",
            business_hours=False,
            incident_active=True,
            emergency_override=True
        )
    )
    
    print(f"📋 Evaluating request:")
    print(f"   Data: {request.data_type} from {request.data_sender} to {request.data_recipient}")
    print(f"   Principle: {request.transmission_principle}")
    print(f"   Context: {request.temporal_context.situation}")
    
    # Evaluate using Graphiti-backed rules
    try:
        result = evaluate(request, graphiti_manager=graphiti_manager)
        print(f"✅ Policy decision: {result['action']}")
        print(f"   Matched rule: {result.get('matched_rule_id', 'None')}")
        print(f"   Reasons: {', '.join(result.get('reasons', []))}")
        
    except Exception as e:
        print(f"❌ Error evaluating policy: {e}")
        # Fallback to YAML-based evaluation
        result = evaluate(request)
        print(f"🔄 Fallback decision: {result['action']}")

def demo_enrichment_with_graphiti(graphiti_manager):
    """Demonstrate context enrichment with Graphiti auto-save."""
    print("\n🔍 Context Enrichment with Graphiti Auto-save")
    print("=" * 50)
    
    # Create base temporal context
    base_context = TemporalContext(
        service_name="auth-service",
        situation="maintenance_window",
        business_hours=False
    )
    
    print(f"📝 Base context: {base_context.service_name} - {base_context.situation}")
    
    # Enrich with Graphiti auto-save
    try:
        enriched_context = enrich_temporal_context(
            base_context,
            graphiti_manager=graphiti_manager
        )
        
        print(f"✅ Enriched context: {enriched_context.context_id}")
        print(f"   Business hours: {enriched_context.business_hours}")
        print(f"   Incident active: {enriched_context.incident_active}")
        print(f"   Auto-saved to Graphiti knowledge graph")
        
    except Exception as e:
        print(f"❌ Error during enrichment: {e}")

def demo_comprehensive_policy_engine(graphiti_manager):
    """Demonstrate comprehensive policy engine with Graphiti integration."""
    print("\n🏛️  Comprehensive Policy Engine with Graphiti")
    print("=" * 50)
    
    # Create policy engine with Graphiti support
    policy_engine = TemporalPolicyEngine(graphiti_manager=graphiti_manager)
    print("✅ Initialized policy engine with Graphiti support")
    
    # Create a complex request
    request = EnhancedContextualIntegrityTuple(
        data_type="financial_data",
        data_sender="data_scientist",
        data_recipient="analytics_service", 
        transmission_principle="research_analysis",
        temporal_context=TemporalContext(
            service_name="fraud-detection",
            situation="business_hours",
            business_hours=True,
            incident_active=False,
            emergency_override=False
        )
    )
    
    print(f"📋 Complex request evaluation:")
    print(f"   Financial data analysis during business hours")
    print(f"   Service: {request.temporal_context.service_name}")
    
    try:
        # Evaluate with full policy engine
        result = policy_engine.evaluate_temporal_access(request)
        
        print(f"✅ Policy engine decision: {result['decision']}")
        print(f"   Confidence: {result['confidence_score']:.2f}")
        print(f"   Risk level: {result['risk_level']}")
        print(f"   Reasons: {', '.join(result['reasons'])}")
        
        if result.get('expires_at'):
            print(f"   Expires: {result['expires_at']}")
            
    except Exception as e:
        print(f"❌ Error in policy engine: {e}")

def main():
    """Main demonstration function."""
    print("🚀 Temporal Framework with Graphiti Knowledge Graph Integration")
    print("=" * 70)
    print("Connecting to company Neo4j infrastructure via Graphiti...")
    
    # Check environment variables
    required_vars = ["GRAPHITI_NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Please set these variables to connect to the company Neo4j instance.")
        print("   Using demo mode with mock data...")
        
        # In production, you would exit here
        # For demo purposes, we'll continue with limited functionality
        graphiti_manager = None
    else:
        try:
            graphiti_manager = setup_graphiti_manager()
            print("✅ Connected to Graphiti knowledge graph successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to Graphiti: {e}")
            print("   Continuing with YAML fallback mode...")
            graphiti_manager = None
    
    if graphiti_manager:
        # Run all Graphiti demonstrations
        demo_basic_graphiti_operations(graphiti_manager)
        demo_temporal_context_with_graphiti(graphiti_manager)
        demo_policy_evaluation_with_graphiti(graphiti_manager)
        demo_enrichment_with_graphiti(graphiti_manager)
        demo_comprehensive_policy_engine(graphiti_manager)
        
        print("\n🎉 All Graphiti knowledge graph demonstrations completed!")
        print("   The temporal framework is now fully integrated with your")
        print("   company's Neo4j infrastructure via Graphiti abstraction.")
    else:
        print("\n⚠️ Running in fallback mode without Graphiti integration.")
        print("   Set up the required environment variables to enable")
        print("   Graphiti knowledge graph functionality.")

if __name__ == "__main__":
    main()