#!/usr/bin/env python3
"""
Temporal Role Permission Inheritance Demo

This demonstrates the enhanced temporal role inheritance system that handles:
- Emergency oncall roles (oncall_low through oncall_critical)
- Acting roles (acting_manager, acting_supervisor, acting_department_head)
- Incident response roles (incident_responder, security_incident_lead)
- Comprehensive inheritance validation and risk assessment
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext


def create_emergency_oncall_example() -> EnhancedContextualIntegrityTuple:
    """Create example with emergency oncall role inheritance"""
    
    # Emergency context - critical system outage
    temporal_ctx = TemporalContext(
        timestamp=datetime.now(timezone.utc),
        timezone="UTC",
        business_hours=False,  # Outside business hours
        emergency_override=True,
        situation="EMERGENCY",
        temporal_role="oncall_critical",
        role_start_time=datetime.now(timezone.utc),
# role_duration calculated from valid_until timestamp
        emergency_context={"incident_id": "INC-2024-001", "severity": "P1", "affected_systems": ["payment_gateway", "user_database"]},
        organizational_context={"department": "engineering", "team": "platform", "escalation_level": "critical"},
        
        # NEW: Inheritance fields for oncall role
        base_role="engineer",  # Base role in organization
        inherited_permissions={"read_system_logs", "restart_services", "access_monitoring", "emergency_database_access"},
        permission_inheritance_chain=["engineer", "oncall_medium", "oncall_critical"],  # Escalation path
        temporal_role_valid_until=datetime.now(timezone.utc) + timedelta(hours=4),
        authorization_source="pagerduty_escalation_policy",
        emergency_authorization_id="PD-ESC-2024-001-CRITICAL"
    )
    
    return EnhancedContextualIntegrityTuple(
        data_type="system_logs",
        data_subject="payment_gateway_service",
        data_sender="monitoring_system", 
        data_recipient="oncall_engineer_john_doe",
        transmission_principle="emergency_system_access",
        temporal_context=temporal_ctx,
        
        # Enhanced attributes
        node_id="tuple_emergency_001",
        request_id="req_incident_001", 
        session_id="session_emergency_001",
        correlation_id="corr_p1_incident_001",
        data_classification="confidential",
        audit_required=True,
        compliance_tags=["SOX"],
        risk_level="CRITICAL",  # Will be validated against calculated risk
        decision_confidence=0.95
    )


def create_acting_manager_example() -> EnhancedContextualIntegrityTuple:
    """Create example with acting manager role inheritance"""
    
    temporal_ctx = TemporalContext(
        timestamp=datetime.now(timezone.utc),
        timezone="America/New_York", 
        business_hours=True,
        emergency_override=False,
        situation="NORMAL",
        temporal_role="acting_manager",
        role_start_time=datetime.now(timezone.utc) - timedelta(days=2),  # Started 2 days ago
# role_duration calculated from valid_until timestamp
        emergency_context=None,
        organizational_context={"department": "sales", "team": "enterprise", "manager_on_leave": "jane_smith"},
        
        # NEW: Inheritance fields for acting manager
        base_role="senior_sales_rep",
        inherited_permissions={"approve_deals", "access_team_metrics", "manage_team_calendar", "review_performance"},
        permission_inheritance_chain=["sales_rep", "senior_sales_rep", "acting_manager"],
        temporal_role_valid_until=datetime.now(timezone.utc) + timedelta(days=5),  # 5 more days
        authorization_source="hr_temporary_assignment",
        emergency_authorization_id=None  # Not an emergency role
    )
    
    return EnhancedContextualIntegrityTuple(
        data_type="team_performance_data",
        data_subject="enterprise_sales_team",
        data_sender="crm_system",
        data_recipient="acting_manager_bob_jones",
        transmission_principle="management_oversight",
        temporal_context=temporal_ctx,
        
        node_id="tuple_acting_mgr_001",
        request_id="req_team_review_001",
        session_id="session_mgmt_001", 
        correlation_id="corr_weekly_review_001",
        data_classification="internal",
        audit_required=True,
        compliance_tags=["SOX"],
        risk_level="MEDIUM",
        decision_confidence=0.88
    )


def create_incident_responder_example() -> EnhancedContextualIntegrityTuple:
    """Create example with security incident responder role"""
    
    temporal_ctx = TemporalContext(
        timestamp=datetime.now(timezone.utc),
        timezone="UTC",
        business_hours=True,
        emergency_override=True,  # Security incident
        situation="INCIDENT", 
        temporal_role="security_incident_lead",
        role_start_time=datetime.now(timezone.utc) - timedelta(minutes=30),
# role_duration calculated from valid_until timestamp
        emergency_context={
            "incident_type": "data_breach_investigation",
            "severity": "high", 
            "affected_users": 1250,
            "breach_vector": "compromised_api_key"
        },
        organizational_context={
            "department": "security",
            "incident_commander": "alice_security_lead",
            "legal_notification_required": True
        },
        
        # NEW: Inheritance fields for incident lead
        base_role="security_analyst", 
        inherited_permissions={
            "access_audit_logs", "query_user_data", "forensic_data_collection", 
            "coordinate_incident_response", "external_communication_authority"
        },
        permission_inheritance_chain=["security_analyst", "incident_responder", "security_incident_lead"],
        temporal_role_valid_until=datetime.now(timezone.utc) + timedelta(hours=7, minutes=30),
        authorization_source="security_incident_escalation_policy",
        emergency_authorization_id="SEC-INC-2024-003-BREACH"
    )
    
    return EnhancedContextualIntegrityTuple(
        data_type="user_audit_logs",
        data_subject="compromised_user_accounts", 
        data_sender="audit_system",
        data_recipient="security_incident_lead_alice",
        transmission_principle="security_investigation",
        temporal_context=temporal_ctx,
        
        node_id="tuple_sec_incident_001",
        request_id="req_breach_investigation_001",
        session_id="session_security_001",
        correlation_id="corr_breach_forensics_001", 
        data_classification="restricted",
        audit_required=True,
        compliance_tags=["GDPR"],
        risk_level="HIGH",
        decision_confidence=0.92
    )


def demonstrate_inheritance_validation(tuple_obj: EnhancedContextualIntegrityTuple, scenario_name: str):
    """Demonstrate comprehensive inheritance validation"""
    
    print(f"\n{'='*60}")
    print(f"TEMPORAL ROLE INHERITANCE DEMO: {scenario_name}")
    print(f"{'='*60}")
    
    # Basic tuple information
    print(f"\n📋 BASIC TUPLE INFO:")
    print(f"   Data Type: {tuple_obj.data_type}")
    print(f"   Transmission Principle: {tuple_obj.transmission_principle}")
    print(f"   Risk Level: {tuple_obj.risk_level}")
    
    # Temporal context and inheritance
    tc = tuple_obj.temporal_context
    print(f"\n🔄 TEMPORAL ROLE INHERITANCE:")
    print(f"   Base Role: {tc.base_role}")
    print(f"   Current Temporal Role: {tc.temporal_role}")
    print(f"   Inheritance Chain: {' → '.join(tc.permission_inheritance_chain or [])}")
    print(f"   Authorization Source: {tc.authorization_source}")
    if tc.emergency_authorization_id:
        print(f"   Emergency Auth ID: {tc.emergency_authorization_id}")
    
    # Inherited permissions
    print(f"\n🔑 INHERITED PERMISSIONS:")
    if tc.inherited_permissions:
        for perm in sorted(tc.inherited_permissions):
            print(f"   ✓ {perm}")
    else:
        print(f"   (No inherited permissions)")
    
    # Validation results
    print(f"\n✅ INHERITANCE VALIDATION:")
    validation = tuple_obj.validate_temporal_role_inheritance()
    print(f"   Overall Valid: {validation['is_valid']}")
    
    if validation['validation_errors']:
        print(f"   ❌ Validation Errors:")
        for error in validation['validation_errors']:
            print(f"      • {error}")
    
    if validation['warnings']:
        print(f"   ⚠️  Warnings:")
        for warning in validation['warnings']:
            print(f"      • {warning}")
    
    # Risk assessment
    print(f"\n⚡ RISK ASSESSMENT:")
    risk_indicators = tuple_obj._count_risk_indicators()
    temporal_risk = tuple_obj._calculate_temporal_role_risk_indicators()
    expected_risk = tuple_obj._calculate_expected_risk_level(risk_indicators)
    
    print(f"   Total Risk Indicators: {risk_indicators}")
    print(f"   Temporal Role Risk: +{temporal_risk}")
    print(f"   Expected Risk Level: {expected_risk}")
    print(f"   Declared Risk Level: {tuple_obj.risk_level}")
    
    # Authorization checks
    print(f"\n🛡️  AUTHORIZATION VALIDATION:")
    print(f"   Properly Authorized: {tuple_obj._is_temporal_role_properly_authorized()}")
    print(f"   Exceeds Scope: {tuple_obj._temporal_role_exceeds_scope()}")
    
    # Time validity
    if tc.temporal_role_valid_until:
        time_remaining = tc.temporal_role_valid_until - datetime.now(timezone.utc)
        print(f"   Time Remaining: {time_remaining}")
        print(f"   Role Expired: {time_remaining.total_seconds() <= 0}")
    
    # Enhanced audit trail sample
    print(f"\n📊 AUDIT TRAIL SAMPLE:")
    audit_trail = tuple_obj.get_enhanced_audit_trail()
    inheritance_details = audit_trail['temporal_summary']['inheritance_details']
    
    if inheritance_details['inheritance_active']:
        print(f"   Inheritance Active: Yes")
        print(f"   Validation Status: {inheritance_details['validation_status']['status']}")
        print(f"   Risk Adjustment: +{inheritance_details['risk_adjustment']}")
    else:
        print(f"   Inheritance Active: No")


def main():
    """Run comprehensive temporal role inheritance demonstration"""
    
    print("🚀 TEMPORAL ROLE PERMISSION INHERITANCE SYSTEM DEMO")
    print("=" * 80)
    print("This demo showcases the enhanced temporal role inheritance system")
    print("with comprehensive validation, risk assessment, and audit capabilities.")
    
    # Demo scenarios
    scenarios = [
        (create_emergency_oncall_example(), "Emergency Oncall Critical Response"),
        (create_acting_manager_example(), "Acting Manager Temporary Assignment"), 
        (create_incident_responder_example(), "Security Incident Response Lead")
    ]
    
    # Run each scenario
    for tuple_obj, scenario_name in scenarios:
        try:
            demonstrate_inheritance_validation(tuple_obj, scenario_name)
        except Exception as e:
            print(f"\n❌ Error in scenario '{scenario_name}': {e}")
    
    print(f"\n{'='*80}")
    print("✅ TEMPORAL ROLE INHERITANCE DEMO COMPLETE")
    print("Key capabilities demonstrated:")
    print("  • Emergency oncall role escalation with inheritance chains")
    print("  • Acting role temporary permission elevation")  
    print("  • Incident response role specialized access")
    print("  • Comprehensive validation and authorization checking")
    print("  • Risk assessment with temporal role factors")
    print("  • Enhanced audit trail with inheritance details")
    print("  • Integration points for Team B (PolicyEvaluationEngine) and Team C (Ontology)")


if __name__ == "__main__":
    main()