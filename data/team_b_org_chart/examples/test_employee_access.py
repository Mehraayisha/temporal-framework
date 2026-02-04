"""
Test the new employee-to-employee access endpoint
This will show REAL ALLOW/DENY decisions based on organizational relationships!
"""

import asyncio
import httpx


BASE_URL = "http://localhost:8000"


async def test_employee_access_checks():
    """Test various employee-to-employee access scenarios"""
    
    async with httpx.AsyncClient() as client:
        print("\n" + "="*80)
        print("TESTING EMPLOYEE-TO-EMPLOYEE ACCESS CHECKS")
        print("="*80 + "\n")
        
        # Test 1: Manager accessing team member's PTO calendar (should ALLOW)
        print("Test 1: Manager (Priya) accessing team member's (Emily) PTO calendar")
        print("-" * 80)
        response = await client.post(
            f"{BASE_URL}/api/v1/check-employee-access",
            params={
                "requester_email": "priya.patel@techflow.com",  # Engineering Manager
                "target_email": "emily.zhang@techflow.com",      # Senior Backend Developer (reports to Priya)
                "resource_type": "pto_calendar"
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Access Granted: {data['access_granted']}")
            print(f"📋 Reason: {data['reason']}")
            print(f"👤 Requester: {data['requester']['name']} ({data['requester']['title']})")
            print(f"🎯 Target: {data['target']['name']} ({data['target']['title']})")
            print(f"📦 Resource Type: {data['resource_type']}")
            if 'relationship_context' in data:
                print(f"🔗 Context: {data['relationship_context']}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        # Test 2: Peer accessing peer's salary info (should DENY)
        print("Test 2: Peer (Emily) accessing another peer's (Michael) salary info")
        print("-" * 80)
        response = await client.post(
            f"{BASE_URL}/api/v1/check-employee-access",
            params={
                "requester_email": "emily.zhang@techflow.com",   # Senior Backend Developer
                "target_email": "michael.rodriguez@techflow.com", # Senior Frontend Developer
                "resource_type": "salary_info"
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"🚫 Access Granted: {data['access_granted']}")
            print(f"📋 Reason: {data['reason']}")
            print(f"👤 Requester: {data['requester']['name']} ({data['requester']['title']})")
            print(f"🎯 Target: {data['target']['name']} ({data['target']['title']})")
            print(f"📦 Resource Type: {data['resource_type']}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        # Test 3: Manager accessing team member's code repository (should ALLOW)
        print("Test 3: Manager (Priya) accessing team member's (Emily) code repository")
        print("-" * 80)
        response = await client.post(
            f"{BASE_URL}/api/v1/check-employee-access",
            params={
                "requester_email": "priya.patel@techflow.com",
                "target_email": "emily.zhang@techflow.com",
                "resource_type": "code_repository"
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Access Granted: {data['access_granted']}")
            print(f"📋 Reason: {data['reason']}")
            print(f"👤 Requester: {data['requester']['name']} ({data['requester']['title']})")
            print(f"🎯 Target: {data['target']['name']} ({data['target']['title']})")
            print(f"📦 Resource Type: {data['resource_type']}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        # Test 4: Team member accessing team member's data (same team, should have some access)
        print("Test 4: Team member (Emily) accessing teammate's (Michael) project docs")
        print("-" * 80)
        response = await client.post(
            f"{BASE_URL}/api/v1/check-employee-access",
            params={
                "requester_email": "emily.zhang@techflow.com",
                "target_email": "michael.rodriguez@techflow.com",
                "resource_type": "project_docs"
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            result_icon = "✅" if data['access_granted'] else "🚫"
            print(f"{result_icon} Access Granted: {data['access_granted']}")
            print(f"📋 Reason: {data['reason']}")
            print(f"👤 Requester: {data['requester']['name']} ({data['requester']['title']})")
            print(f"🎯 Target: {data['target']['name']} ({data['target']['title']})")
            print(f"📦 Resource Type: {data['resource_type']}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        # Test 5: Department member accessing department docs (should ALLOW based on dept)
        print("Test 5: Department member accessing department colleague's dept docs")
        print("-" * 80)
        response = await client.post(
            f"{BASE_URL}/api/v1/check-employee-access",
            params={
                "requester_email": "priya.patel@techflow.com",   # Engineering dept
                "target_email": "michael.rodriguez@techflow.com", # Engineering dept
                "resource_type": "department_docs"
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            result_icon = "✅" if data['access_granted'] else "🚫"
            print(f"{result_icon} Access Granted: {data['access_granted']}")
            print(f"📋 Reason: {data['reason']}")
            print(f"👤 Requester: {data['requester']['name']} ({data['requester']['title']})")
            print(f"🎯 Target: {data['target']['name']} ({data['target']['title']})")
            print(f"📦 Resource Type: {data['resource_type']}")
        else:
            print(f"❌ Error: {response.text}")
        print()
        
        print("="*80)
        print("🎉 EMPLOYEE ACCESS TESTS COMPLETE!")
        print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_employee_access_checks())
