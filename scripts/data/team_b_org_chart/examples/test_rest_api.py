#!/usr/bin/env python3
"""
Test REST API Endpoints

This script tests all the FastAPI endpoints using httpx async client.

Author: Aithel Christo Sunil
Date: November 6, 2025
"""

import asyncio
import sys
from pathlib import Path

import httpx

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://localhost:8000"

async def test_rest_api():
    """Test all REST API endpoints"""
    
    print("=" * 80)
    print("REST API ENDPOINT TESTS")
    print("=" * 80)
    print()
    
    async with httpx.AsyncClient() as client:
        
        # ====================================================================
        # Test 1: Health Check
        # ====================================================================
        print("Test 1: Health Check")
        print("-" * 80)
        try:
            response = await client.get(f"{BASE_URL}/api/v1/health")
            print(f"✓ Status Code: {response.status_code}")
            data = response.json()
            print(f"  Status: {data['status']}")
            print(f"  Version: {data['version']}")
            print(f"  Services: {data['services']}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 2: Get Employee Context
        # ====================================================================
        print("Test 2: Get Employee Context")
        print("-" * 80)
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/employee-context/priya.patel@techflow.com"
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Name: {data['name']}")
                print(f"  Title: {data['title']}")
                print(f"  Department: {data['department']}")
                print(f"  Team: {data['team']}")
                print(f"  Clearance: {data['security_clearance']}")
                print(f"  Is Manager: {data['is_manager']}")
                print(f"  Projects: {len(data['projects'])}")
            else:
                print(f"  Error: {response.text}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 3: Check Access - Manager with Correct Clearance
        # ====================================================================
        print("Test 3: Check Access - Manager (Should ALLOW)")
        print("-" * 80)
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/check-access",
                json={
                    "employee_email": "priya.patel@techflow.com",
                    "resource_id": "RES-BACKEND-001",
                    "classification": "confidential"
                }
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Access Granted: {data['access_granted']}")
                print(f"  Reason: {data['reason']}")
                print(f"  Policy: {data['policy_matched']}")
                if data.get('employee_context'):
                    print(f"  Employee: {data['employee_context'].get('name')}")
            else:
                print(f"  Error: {response.text}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 4: Check Access - Contractor (Should DENY)
        # ====================================================================
        print("Test 4: Check Access - Contractor with Low Clearance (Should DENY)")
        print("-" * 80)
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/check-access",
                json={
                    "employee_email": "lisa.kumar@techflow.com",
                    "resource_id": "RES-EXEC-001",
                    "classification": "top_secret"
                }
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Access Granted: {data['access_granted']}")
                print(f"  Reason: {data['reason']}")
                print(f"  Employee: {data['employee_context'].get('name')}")
            else:
                print(f"  Error: {response.text}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 5: Get Accessible Resources
        # ====================================================================
        print("Test 5: Get Accessible Resources")
        print("-" * 80)
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/accessible-resources/priya.patel@techflow.com"
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Employee: {data['employee_email']}")
                print(f"  Total Resources: {data['total_count']}")
                for resource in data['accessible_resources'][:3]:
                    print(f"    - {resource['resource_id']}: {resource['reason']}")
            else:
                print(f"  Error: {response.text}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 6: Get Audit Trail
        # ====================================================================
        print("Test 6: Get Audit Trail")
        print("-" * 80)
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/audit-trail",
                params={"limit": 5}
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Total Entries: {data['total_entries']}")
                print(f"  Filters: {data['filters_applied']}")
                for entry in data['entries'][:3]:
                    print(f"    - {entry['employee_email']} -> {entry['resource_id']}: {entry['decision']}")
            else:
                print(f"  Error: {response.text}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 7: Get Audit Statistics
        # ====================================================================
        print("Test 7: Get Audit Statistics")
        print("-" * 80)
        try:
            from datetime import date
            today = date.today()
            response = await client.get(
                f"{BASE_URL}/api/v1/audit-stats",
                params={
                    "start_date": today.isoformat(),
                    "end_date": today.isoformat()
                }
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Total Accesses: {data['total_accesses']}")
                print(f"  Allowed: {data['allowed']} ({data['success_rate']}%)")
                print(f"  Denied: {data['denied']}")
                print(f"  Errors: {data['errors']}")
                print(f"  Period: {data['period']['start_date']} to {data['period']['end_date']}")
            else:
                print(f"  Error: {response.text}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 8: Invalid Email Format
        # ====================================================================
        print("Test 8: Invalid Email Format (Should Return 422)")
        print("-" * 80)
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/check-access",
                json={
                    "employee_email": "invalid-email",
                    "resource_id": "RES-001",
                    "classification": "confidential"
                }
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 422:
                print("  ✓ Correctly rejected invalid email format")
            else:
                print(f"  Error: {response.text}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
        
        # ====================================================================
        # Test 9: Non-existent Employee
        # ====================================================================
        print("Test 9: Non-existent Employee (Should Return 404)")
        print("-" * 80)
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/employee-context/nonexistent@techflow.com"
            )
            print(f"✓ Status Code: {response.status_code}")
            if response.status_code == 404:
                print("  ✓ Correctly returned 404 for non-existent employee")
            else:
                print(f"  Response: {response.json()}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
    
    print("=" * 80)
    print("REST API TESTS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    print()
    print("Make sure the API is running first:")
    print("  python run_api.py")
    print()
    print("Then run this test script.")
    print()
    
    try:
        asyncio.run(test_rest_api())
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nTest suite failed: {e}")
        sys.exit(1)
