#!/usr/bin/env python3
"""
Complete API Test Suite
Tests the full stack: API → Policy Engine → Graph Queries → Neo4j

This tests the RESOURCE-BASED access model with real employee data.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.privacy_api import PrivacyFirewallAPI


async def main():
    print("=" * 80)
    print("COMPLETE API STACK TEST - Resource-Based Access Control")
    print("=" * 80)
    print()
    
    # Initialize API
    print("Step 1: Initializing Privacy Firewall API...")
    try:
        api = PrivacyFirewallAPI()
        print("✓ API initialized successfully")
    except Exception as e:
        print(f"✗ FAILED to initialize API: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 80)
    print("TEST SUITE: Resource-Based Access Control")
    print("=" * 80)
    print()
    
    tests_passed = 0
    tests_failed = 0
    
    # TEST 1: CEO Universal Access
    print("TEST 1: CEO accessing Finance top_secret document")
    print("-" * 80)
    try:
        result = await api.check_resource_access(
            requester_id="Sarah Chen",
            resource_owner="Finance",
            resource_classification="top_secret",
            resource_type="financial_report",
            action="read"
        )
        
        print(f"  Requester: Sarah Chen (CEO)")
        print(f"  Resource: Finance top_secret financial_report")
        print(f"  Expected: ALLOW (CEO universal access)")
        print(f"  Actual: {'ALLOW' if result['allowed'] else 'DENY'}")
        print(f"  Reason: {result['reason']}")
        print(f"  Confidence: {result.get('confidence', 'N/A')}")
        
        if result['allowed']:
            print("  ✓ PASS")
            tests_passed += 1
        else:
            print("  ✗ FAIL")
            tests_failed += 1
            
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        tests_failed += 1
        import traceback
        traceback.print_exc()
    
    print()
    
    # TEST 2: Same Department Confidential
    print("TEST 2: Engineer accessing Engineering confidential document")
    print("-" * 80)
    try:
        result = await api.check_resource_access(
            requester_id="Alice Cooper",
            resource_owner="Engineering",
            resource_classification="confidential",
            resource_type="document",
            action="read"
        )
        
        print(f"  Requester: Alice Cooper (Engineer)")
        print(f"  Resource: Engineering confidential document")
        print(f"  Expected: ALLOW (same department)")
        print(f"  Actual: {'ALLOW' if result['allowed'] else 'DENY'}")
        print(f"  Reason: {result['reason']}")
        
        if result['allowed']:
            print("  ✓ PASS")
            tests_passed += 1
        else:
            print("  ✗ FAIL")
            tests_failed += 1
            
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        tests_failed += 1
    
    print()
    
    # TEST 3: Cross-Department Denial
    print("TEST 3: Engineer accessing Finance restricted financial report")
    print("-" * 80)
    try:
        result = await api.check_resource_access(
            requester_id="Alice Cooper",
            resource_owner="Finance",
            resource_classification="restricted",
            resource_type="financial_report",
            action="read"
        )
        
        print(f"  Requester: Alice Cooper (Engineer)")
        print(f"  Resource: Finance restricted financial_report")
        print(f"  Expected: DENY (cross-department, restricted)")
        print(f"  Actual: {'ALLOW' if result['allowed'] else 'DENY'}")
        print(f"  Reason: {result['reason']}")
        
        if not result['allowed']:
            print("  ✓ PASS")
            tests_passed += 1
        else:
            print("  ✗ FAIL")
            tests_failed += 1
            
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        tests_failed += 1
    
    print()
    
    # TEST 4: Public Resource Access
    print("TEST 4: Anyone accessing public resource")
    print("-" * 80)
    try:
        result = await api.check_resource_access(
            requester_id="Alice Cooper",
            resource_owner="Engineering",
            resource_classification="public",
            resource_type="document",
            action="read"
        )
        
        print(f"  Requester: Alice Cooper (Engineer)")
        print(f"  Resource: Engineering public document")
        print(f"  Expected: ALLOW (public resource)")
        print(f"  Actual: {'ALLOW' if result['allowed'] else 'DENY'}")
        print(f"  Reason: {result['reason']}")
        
        if result['allowed']:
            print("  ✓ PASS")
            tests_passed += 1
        else:
            print("  ✗ FAIL")
            tests_failed += 1
            
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        tests_failed += 1
    
    print()
    
    # TEST 5: Contractor Access Denial
    print("TEST 5: Contractor accessing confidential data")
    print("-" * 80)
    try:
        result = await api.check_resource_access(
            requester_id="Lisa Kumar",
            resource_owner="Engineering",
            resource_classification="confidential",
            resource_type="source_code",
            action="read"
        )
        
        print(f"  Requester: Lisa Kumar (Contractor)")
        print(f"  Resource: Engineering confidential source_code")
        print(f"  Expected: ALLOW or DENY (depends on policy)")
        print(f"  Actual: {'ALLOW' if result['allowed'] else 'DENY'}")
        print(f"  Reason: {result['reason']}")
        print(f"  Note: Contractors may have restricted access to confidential data")
        
        # Just report the result, no pass/fail
        print(f"  ℹ INFO: Result recorded")
            
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        tests_failed += 1
    
    print()
    
    # TEST 6: Insufficient Clearance
    print("TEST 6: Standard clearance trying to access secret data")
    print("-" * 80)
    try:
        result = await api.check_resource_access(
            requester_id="Maya Nguyen",
            resource_owner="Product",
            resource_classification="secret",
            resource_type="document",
            action="read"
        )
        
        print(f"  Requester: Maya Nguyen (Product Manager - standard clearance)")
        print(f"  Resource: Product secret document")
        print(f"  Expected: DENY (insufficient clearance)")
        print(f"  Actual: {'ALLOW' if result['allowed'] else 'DENY'}")
        print(f"  Reason: {result['reason']}")
        
        if not result['allowed']:
            print("  ✓ PASS")
            tests_passed += 1
        else:
            print("  ✗ FAIL")
            tests_failed += 1
            
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        tests_failed += 1
    
    print()
    print("=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    print(f"Total: {tests_passed + tests_failed}")
    print()
    
    if tests_failed == 0:
        print("✓ ALL TESTS PASSED!")
        return True
    else:
        print(f"✗ {tests_failed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
