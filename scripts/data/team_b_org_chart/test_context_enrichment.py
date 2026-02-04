"""
Test script for Employee Context Enrichment API

This demonstrates the new get_employee_context() endpoint that Team C
will use to enrich requests before sending to Team A's temporal engine.
"""

import asyncio
import json
from api.privacy_api import get_employee_context, check_access


async def test_employee_context_enrichment():
    """Test the new employee context enrichment API"""
    
    print("="*80)
    print("EMPLOYEE CONTEXT ENRICHMENT API TEST")
    print("="*80)
    print()
    
    # Test 1: Get CEO context (highest level)
    print("Test 1: CEO Context (Sarah Chen)")
    print("-" * 80)
    
    ceo_context = await get_employee_context("sarah.chen@techflow.com")
    
    if ceo_context:
        print(f"✓ Employee Found: {ceo_context['name']}")
        print(f"  Title: {ceo_context['title']}")
        print(f"  Department: {ceo_context['department']}")
        print(f"  Team: {ceo_context['team']}")
        print(f"  Security Clearance: {ceo_context['security_clearance']}")
        print(f"  Hierarchy Level: {ceo_context['hierarchy_level']}")
        print(f"  Is Manager: {ceo_context['is_manager']}")
        print(f"  Is Executive: {ceo_context['is_executive']}")
        print(f"  Is CEO: {ceo_context['is_ceo']}")
        print(f"  Direct Reports: {len(ceo_context['direct_reports'])} people")
        
        if ceo_context['direct_reports']:
            print(f"    - " + "\n    - ".join([
                f"{r['name']} ({r['title']})" 
                for r in ceo_context['direct_reports'][:3]
            ]))
        
        print(f"  Reports To: {ceo_context['reports_to']}")
        print(f"  Projects: {len(ceo_context['projects'])}")
        print(f"  Working Hours: {ceo_context['working_hours']['start']} - {ceo_context['working_hours']['end']} ({ceo_context['working_hours']['timezone']})")
        print(f"  Location: {ceo_context['location']}")
    else:
        print("✗ Employee not found!")
    
    print()
    
    # Test 2: Get engineering manager context
    print("Test 2: Engineering Manager Context (Marcus Johnson)")
    print("-" * 80)
    
    manager_context = await get_employee_context("marcus.johnson@techflow.com")
    
    if manager_context:
        print(f"✓ Employee Found: {manager_context['name']}")
        print(f"  Title: {manager_context['title']}")
        print(f"  Department: {manager_context['department']}")
        print(f"  Security Clearance: {manager_context['security_clearance']}")
        print(f"  Hierarchy Level: {manager_context['hierarchy_level']}")
        print(f"  Is Manager: {manager_context['is_manager']}")
        print(f"  Is Executive: {manager_context['is_executive']}")
        
        if manager_context['reports_to']:
            print(f"  Reports To: {manager_context['reports_to']['name']} ({manager_context['reports_to']['title']})")
        
        print(f"  Direct Reports: {len(manager_context['direct_reports'])} people")
        print(f"  Projects: {len(manager_context['projects'])}")
        
        if manager_context['projects']:
            print(f"    Active Projects:")
            for proj in manager_context['projects']:
                print(f"    - {proj['name']} (Status: {proj['status']})")
    else:
        print("✗ Employee not found!")
    
    print()
    
    # Test 3: Get individual contributor context
    print("Test 3: Individual Contributor Context (Alice Cooper)")
    print("-" * 80)
    
    ic_context = await get_employee_context("alice.cooper@techflow.com")
    
    if ic_context:
        print(f"✓ Employee Found: {ic_context['name']}")
        print(f"  Title: {ic_context['title']}")
        print(f"  Department: {ic_context['department']}")
        print(f"  Team: {ic_context['team']}")
        print(f"  Security Clearance: {ic_context['security_clearance']}")
        print(f"  Hierarchy Level: {ic_context['hierarchy_level']}")
        print(f"  Is Manager: {ic_context['is_manager']}")
        print(f"  Employment Type: {ic_context['employment_type']}")
        
        if ic_context['reports_to']:
            print(f"  Reports To: {ic_context['reports_to']['name']} ({ic_context['reports_to']['title']})")
        
        print(f"  Direct Reports: {len(ic_context['direct_reports'])}")
        print(f"  Projects: {len(ic_context['projects'])}")
    else:
        print("✗ Employee not found!")
    
    print()
    
    # Test 4: Contractor context
    print("Test 4: Contractor Context (Lisa Kumar)")
    print("-" * 80)
    
    contractor_context = await get_employee_context("lisa.kumar@techflow.com")
    
    if contractor_context:
        print(f"✓ Employee Found: {contractor_context['name']}")
        print(f"  Title: {contractor_context['title']}")
        print(f"  Employment Type: {contractor_context['employment_type']}")
        print(f"  Security Clearance: {contractor_context['security_clearance']}")
        print(f"  Contract End Date: {contractor_context['contract_end_date']}")
        print(f"  Is Active: {contractor_context['is_active']}")
    else:
        print("✗ Employee not found!")
    
    print()
    
    # Test 5: Non-existent employee
    print("Test 5: Non-Existent Employee")
    print("-" * 80)
    
    fake_context = await get_employee_context("fake.person@techflow.com")
    
    if fake_context is None:
        print("✓ Correctly returned None for non-existent employee")
    else:
        print("✗ Should have returned None!")
    
    print()
    
    # Test 6: Integration Example - Team C enrichment flow
    print("Test 6: Team C Integration Example")
    print("-" * 80)
    print("Simulating Team C enriching a request for Team A...")
    print()
    
    # Team C receives this request
    team_c_request = {
        "data_field": "patient_heart_rate",
        "requester_email": "sarah.chen@techflow.com",
        "urgency_level": "critical",
        "context": "emergency_access"
    }
    
    print(f"Team C Receives:")
    print(json.dumps(team_c_request, indent=2))
    print()
    
    # Team C calls your enrichment API
    context = await get_employee_context(team_c_request["requester_email"])
    
    if context:
        print(f"Team B Enrichment Returns:")
        enriched_data = {
            "requester_name": context["name"],
            "requester_title": context["title"],
            "requester_department": context["department"],
            "requester_clearance": context["security_clearance"],
            "requester_hierarchy": context["hierarchy_level"],
            "is_executive": context["is_executive"],
            "is_ceo": context["is_ceo"]
        }
        print(json.dumps(enriched_data, indent=2))
        print()
        
        # Team C can now use this to build Team A's temporal tuple
        print(f"Team C builds temporal tuple for Team A:")
        temporal_mapping = {
            "data_recipient": context["title"],  # "CEO & Co-Founder"
            "temporal_role": "oncall_critical" if team_c_request["urgency_level"] == "critical" else "user",
            "employee_clearance": context["security_clearance"],
            "department": context["department"],
            "is_executive": context["is_executive"]
        }
        print(json.dumps(temporal_mapping, indent=2))
    
    print()
    print("="*80)
    print("TEST COMPLETE")
    print("="*80)


async def test_access_check_integration():
    """Test the check_access convenience function"""
    
    print()
    print("="*80)
    print("ACCESS CHECK INTEGRATION TEST")
    print("="*80)
    print()
    
    # Test access check with enrichment
    print("Test: CEO accessing confidential resource")
    print("-" * 80)
    
    result = await check_access(
        employee_email="sarah.chen@techflow.com",
        resource_id="RES-EXEC-001",
        resource_classification="confidential"
    )
    
    print(f"Access Granted: {result['access_granted']}")
    print(f"Reason: {result['reason']}")
    print(f"Policy Matched: {result['policy_matched']}")
    print(f"Confidence: {result.get('confidence', 'N/A')}")
    
    if result.get('employee_context'):
        ctx = result['employee_context']
        print(f"Employee: {ctx['name']} ({ctx['title']})")
        print(f"Clearance: {ctx['security_clearance']}")
    
    print()
    print("="*80)


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_employee_context_enrichment())
    asyncio.run(test_access_check_integration())
