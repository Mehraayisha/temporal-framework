#!/usr/bin/env python3
"""
Team Onboarding Demo - Getting Started with Temporal Framework

This script provides a comprehensive walkthrough of the temporal framework
for new team members. It demonstrates core concepts, basic usage patterns,
and common scenarios you'll encounter in development.

Run this script to verify your development environment setup.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List

from core.tuples import TimeWindow, TemporalContext, EnhancedContextualIntegrityTuple
from core.policy_engine import TemporalPolicyEngine
from core.evaluator import TemporalEvaluator
from core.enricher import TemporalEnricher
from core.logging_config import setup_logging

# Configure logging for demo
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

def print_section(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step: str, description: str) -> None:
    """Print a formatted step description."""
    print(f"\n📋 {step}")
    print(f"   {description}")

def main():
    """
    Comprehensive demo walkthrough for team onboarding.
    
    This demo covers:
    1. Basic data model usage
    2. Temporal context creation  
    3. Policy evaluation
    4. Emergency scenarios
    5. Integration patterns
    """
    
    print_section("🚀 Temporal Framework - Team Onboarding Demo")
    
    print("""
Welcome to the Temporal Framework! This demo will walk you through
the key concepts and usage patterns you'll need for development.

The framework implements a 6-tuple contextual integrity model:
1. Data Type (what data is being accessed)
2. Data Subject (who the data is about) 
3. Data Sender (who is requesting access)
4. Data Recipient (who will receive the data)
5. Transmission Principle (why/how access is governed)
6. Temporal Context (when/where/situation context) ← Our enhancement!
    """)
    
    # Step 1: Basic TimeWindow Creation
    print_step("Step 1", "Creating Time Windows")
    
    # Business hours window
    business_start = datetime.now(timezone.utc).replace(hour=9, minute=0, second=0, microsecond=0)
    business_end = business_start.replace(hour=17)  # 5 PM
    
    business_window = TimeWindow(
        start=business_start,
        end=business_end,
        window_type="business_hours",
        description="Standard business operating hours (9 AM - 5 PM)"
    )
    
    print(f"   ✅ Created business window: {business_window.node_id}")
    print(f"      Time range: {business_window.start.strftime('%I:%M %p')} - {business_window.end.strftime('%I:%M %p')}")
    print(f"      Type: {business_window.window_type}")
    
    # Emergency window (24/7 access)
    emergency_window = TimeWindow(
        window_type="emergency",
        description="24/7 emergency access window"
        # Note: start/end are optional for 24/7 windows
    )
    
    print(f"   ✅ Created emergency window: {emergency_window.node_id}")
    print(f"      Type: {emergency_window.window_type} (24/7 access)")
    
    # Step 2: Temporal Context Creation
    print_step("Step 2", "Building Temporal Contexts")
    
    # Standard business context
    business_context = TemporalContext(
        service_id="medical_records_system",
        user_id="dr_johnson",
        location="clinic_station_3", 
        timezone="UTC",
        time_windows=[business_window],
        situation="NORMAL",
        temporal_role="physician"
    )
    
    print(f"   ✅ Created business context: {business_context.node_id}")
    print(f"      Service: {business_context.service_id}")
    print(f"      User: {business_context.user_id}")
    print(f"      Situation: {business_context.situation}")
    print(f"      Time windows: {len(business_context.time_windows)}")
    
    # Emergency context  
    emergency_context = TemporalContext(
        service_id="emergency_medical_system",
        user_id="dr_emergency_oncall",
        location="emergency_department_trauma_bay_1",
        timezone="UTC", 
        time_windows=[emergency_window],
        situation="EMERGENCY",
        emergency_override=True,
        temporal_role="emergency_physician"
    )
    
    print(f"   ✅ Created emergency context: {emergency_context.node_id}")
    print(f"      Service: {emergency_context.service_id}")
    print(f"      Location: {emergency_context.location}")
    print(f"      Emergency override: {emergency_context.emergency_override}")
    print(f"      Situation: {emergency_context.situation}")
    
    # Step 3: 6-Tuple Access Requests  
    print_step("Step 3", "Creating 6-Tuple Access Requests")
    
    # Standard business request
    business_request = EnhancedContextualIntegrityTuple(
        data_type="patient_medical_record",
        data_subject="patient_alice_smith_12345",
        data_sender="dr_johnson", 
        data_recipient="medical_records_system",
        transmission_principle="routine_patient_care",
        temporal_context=business_context,
        risk_level="MEDIUM",
        audit_required=False,
        compliance_tags=["HIPAA", "patient_care"]
    )
    
    print(f"   ✅ Created business request: {business_request.request_id}")
    print(f"      Data type: {business_request.data_type}")
    print(f"      Sender → Recipient: {business_request.data_sender} → {business_request.data_recipient}")
    print(f"      Risk level: {business_request.risk_level}")
    print(f"      Compliance: {', '.join(business_request.compliance_tags)}")
    
    # Emergency request
    emergency_request = EnhancedContextualIntegrityTuple(
        data_type="critical_patient_vitals",
        data_subject="trauma_patient_incoming_001",
        data_sender="paramedic_unit_7",
        data_recipient="emergency_trauma_team", 
        transmission_principle="life_safety_emergency_access",
        temporal_context=emergency_context,
        risk_level="HIGH",
        audit_required=True,
        compliance_tags=["HIPAA", "emergency_care", "life_safety"]
    )
    
    print(f"   ✅ Created emergency request: {emergency_request.request_id}")
    print(f"      Data type: {emergency_request.data_type}")
    print(f"      Sender → Recipient: {emergency_request.data_sender} → {emergency_request.data_recipient}")
    print(f"      Risk level: {emergency_request.risk_level}")
    print(f"      Audit required: {emergency_request.audit_required}")
    
    # Step 4: Policy Evaluation
    print_step("Step 4", "Evaluating Access Policies")
    
    # Initialize policy engine
    policy_engine = TemporalPolicyEngine()
    
    print(f"   📊 Initialized policy engine with {len(policy_engine.rules)} default rules")
    
    # Evaluate business request
    print(f"\n   🔍 Evaluating business request...")
    business_decision = policy_engine.evaluate_request(business_request)
    
    print(f"   📝 Business Decision:")
    print(f"      Allowed: {business_decision.allowed}")
    print(f"      Reason: {business_decision.reason}")
    print(f"      Confidence: {business_decision.confidence:.2f}")
    print(f"      Risk level: {business_decision.risk_level}")
    
    # Evaluate emergency request
    print(f"\n   🚨 Evaluating emergency request...")
    emergency_decision = policy_engine.evaluate_request(emergency_request)
    
    print(f"   📝 Emergency Decision:")
    print(f"      Allowed: {emergency_decision.allowed}")
    print(f"      Reason: {emergency_decision.reason}")
    print(f"      Confidence: {emergency_decision.confidence:.2f}")
    print(f"      Risk level: {emergency_decision.risk_level}")
    
    # Step 5: Advanced Features Demo
    print_step("Step 5", "Advanced Features Demonstration")
    
    # Context enrichment
    print(f"\n   🔧 Context Enrichment:")
    enricher = TemporalEnricher()
    
    print(f"      Original business context time windows: {len(business_context.time_windows)}")
    enriched_context = enricher.enrich_context(business_context)
    print(f"      Enriched context time windows: {len(enriched_context.time_windows)}")
    print(f"      Enrichment added related contexts and updated metadata")
    
    # Batch evaluation
    print(f"\n   📊 Batch Processing:")
    requests = [business_request, emergency_request]
    
    evaluator = TemporalEvaluator(policy_engine=policy_engine, enricher=enricher)
    
    print(f"      Processing {len(requests)} requests in batch...")
    batch_results = evaluator.evaluate_batch(requests)
    
    for i, result in enumerate(batch_results):
        print(f"      Request {i+1}: {result.decision.allowed} ({result.decision.reason})")
    
    # Step 6: Data Serialization
    print_step("Step 6", "Data Serialization & Integration")
    
    # JSON serialization (for APIs)
    print(f"\n   📤 JSON Serialization:")
    business_json = business_request.model_dump_json()
    print(f"      Business request JSON size: {len(business_json)} characters")
    
    # Round-trip test
    parsed_request = EnhancedContextualIntegrityTuple.model_validate_json(business_json)
    print(f"      ✅ JSON round-trip successful: {parsed_request.request_id == business_request.request_id}")
    
    # Dictionary format (for databases)
    print(f"\n   🗃️  Dictionary Format:")
    business_dict = business_request.model_dump(mode='json')
    print(f"      Business request dict keys: {len(business_dict)} fields")
    print(f"      Sample fields: {list(business_dict.keys())[:5]}...")
    
    # Step 7: Error Handling Demo
    print_step("Step 7", "Error Handling Patterns")
    
    try:
        # Invalid time window (end before start)
        invalid_window = TimeWindow(
            start=datetime.now(timezone.utc),
            end=datetime.now(timezone.utc) - timedelta(hours=1),  # Invalid!
            window_type="business_hours"
        )
    except ValueError as e:
        print(f"   ❌ Caught validation error: {e}")
        print(f"      ✅ Pydantic validation working correctly")
    
    try:
        # Invalid tuple (empty required field)
        invalid_tuple = EnhancedContextualIntegrityTuple(
            data_type="",  # Invalid! Required field can't be empty
            data_subject="patient_123",
            data_sender="doctor", 
            data_recipient="system",
            transmission_principle="access",
            temporal_context=business_context
        )
    except ValueError as e:
        print(f"   ❌ Caught validation error: {e}")
        print(f"      ✅ Field validation working correctly")
    
    # Step 8: Performance Insights
    print_step("Step 8", "Performance & Best Practices")
    
    import time
    
    # Measure evaluation performance
    start_time = time.time()
    for _ in range(100):
        policy_engine.evaluate_request(business_request)
    end_time = time.time()
    
    avg_time_ms = ((end_time - start_time) / 100) * 1000
    print(f"   ⚡ Policy evaluation performance:")
    print(f"      Average time per request: {avg_time_ms:.2f}ms")
    print(f"      Estimated throughput: {1000/avg_time_ms:.0f} requests/second")
    
    # Memory usage tip
    print(f"\n   💡 Performance Tips:")
    print(f"      - Use batch evaluation for multiple requests")
    print(f"      - Enable caching for repeated policy evaluations")
    print(f"      - Consider async operations for I/O-bound tasks")
    print(f"      - Monitor memory usage with large datasets")
    
    # Final Summary
    print_section("🎯 Demo Complete - Next Steps")
    
    print("""
Congratulations! You've successfully completed the temporal framework onboarding demo.

Key takeaways:
✅ Understand the 6-tuple model (5 traditional + temporal context)
✅ Know how to create TimeWindows and TemporalContexts  
✅ Can build and evaluate EnhancedContextualIntegrityTuples
✅ Familiar with policy evaluation and decision logic
✅ Understand error handling and validation patterns
✅ Ready for advanced features like graph integration

Next steps for development:
1. 📖 Read the full API documentation in docs/API_REFERENCE.md
2. 🧪 Explore the test suite in tests/ for usage patterns
3. 🔧 Set up Neo4j integration for production use
4. 🤝 Review CONTRIBUTING.md for development workflows
5. 💬 Join team discussions for questions and collaboration

Happy coding with the Temporal Framework! 🚀
    """)

if __name__ == "__main__":
    main()