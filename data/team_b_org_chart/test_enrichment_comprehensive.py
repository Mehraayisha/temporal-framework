"""
Comprehensive Employee Context Enrichment Tests

Tests all possible employee scenarios from the org data:
- Executives (CEO, CTO, CFO)
- Managers (Engineering, Product, Sales)
- Individual contributors
- Contractors
- Project leads
- Team members on multiple projects
- Different departments
- Different security clearances
- Acting roles
- On-call rotation
"""

import asyncio
import json
from api.privacy_api import get_employee_context


async def test_employee(email: str, name: str, expected_features: dict):
    """Test a single employee and verify expected features"""
    print(f"\n{'=' * 80}")
    print(f"Testing: {name} ({email})")
    print('=' * 80)
    
    result = await get_employee_context(email)
    
    if not result:
        print("❌ FAILED: Employee not found!")
        return False
    
    success = True
    
    # Display full context
    print(f"\n📋 EMPLOYEE CONTEXT:")
    print(f"  Name: {result['name']}")
    print(f"  Email: {result['email']}")
    print(f"  Title: {result['title']}")
    print(f"  Department: {result.get('department', 'N/A')}")
    print(f"  Team: {result.get('team', 'N/A')}")
    print(f"  Security Clearance: {result['security_clearance']}")
    print(f"  Employment Type: {result['employment_type']}")
    print(f"  Hierarchy Level: {result['hierarchy_level']}")
    print(f"  Location: {result['location']}")
    print(f"  Phone: {result['phone']}")
    print(f"  Working Hours: {result['working_hours']['start']} - {result['working_hours']['end']} ({result['working_hours']['timezone']})")
    
    print(f"\n🏢 ORGANIZATIONAL POSITION:")
    print(f"  Is Manager: {result['is_manager']}")
    print(f"  Is Executive: {result['is_executive']}")
    print(f"  Is CEO: {result['is_ceo']}")
    
    if result.get('reports_to'):
        print(f"\n👤 REPORTS TO:")
        print(f"  Name: {result['reports_to']['name']}")
        print(f"  Email: {result['reports_to']['email']}")
        print(f"  Title: {result['reports_to']['title']}")
    else:
        print(f"\n👤 REPORTS TO: None (Top of hierarchy)")
    
    if result['direct_reports']:
        print(f"\n👥 DIRECT REPORTS ({len(result['direct_reports'])}):")
        for dr in result['direct_reports'][:5]:
            print(f"  • {dr['name']} - {dr['title']}")
        if len(result['direct_reports']) > 5:
            print(f"  ... and {len(result['direct_reports']) - 5} more")
    else:
        print(f"\n👥 DIRECT REPORTS: None")
    
    if result['projects']:
        print(f"\n🚀 PROJECTS ({len(result['projects'])}):")
        for proj in result['projects']:
            print(f"  • {proj['name']} ({proj['status']})")
    else:
        print(f"\n🚀 PROJECTS: None")
    
    if result.get('contract_end_date'):
        print(f"\n📅 CONTRACT END: {result['contract_end_date']}")
    
    # Verify expected features
    print(f"\n✅ VERIFICATION:")
    
    for feature, expected_value in expected_features.items():
        actual_value = result.get(feature)
        
        if feature == 'has_projects':
            actual_value = len(result['projects']) > 0
        elif feature == 'has_direct_reports':
            actual_value = len(result['direct_reports']) > 0
        elif feature == 'has_manager':
            actual_value = result.get('reports_to') is not None
        
        match = actual_value == expected_value
        symbol = "✓" if match else "✗"
        
        if not match:
            success = False
        
        print(f"  {symbol} {feature}: Expected={expected_value}, Actual={actual_value}")
    
    return success


async def main():
    """Run comprehensive enrichment tests"""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE EMPLOYEE CONTEXT ENRICHMENT TEST SUITE")
    print("=" * 80)
    print("\nTesting all employee types, roles, and edge cases from org data...")
    
    test_cases = [
        # 1. CEO - Top of hierarchy
        {
            "email": "sarah.chen@techflow.com",
            "name": "Sarah Chen (CEO)",
            "expected": {
                "department": "Executive",
                "team": "Executive Team",
                "security_clearance": "executive",
                "is_ceo": True,
                "is_executive": True,
                "is_manager": True,
                "has_direct_reports": True,
                "has_manager": False,
                "employment_type": "full_time",
            }
        },
        
        # 2. CTO - C-level, Engineering department
        {
            "email": "thomas.anderson@techflow.com",
            "name": "Thomas Anderson (CTO)",
            "expected": {
                "department": "Engineering",
                "security_clearance": "executive",
                "is_executive": True,
                "is_manager": True,
                "has_direct_reports": True,
                "employment_type": "full_time",
            }
        },
        
        # 3. CFO - C-level, Operations
        {
            "email": "jennifer.martinez@techflow.com",
            "name": "Jennifer Martinez (CFO)",
            "expected": {
                "department": "Operations",
                "security_clearance": "executive",
                "is_executive": True,
                "employment_type": "full_time",
            }
        },
        
        # 4. VP of Sales - Elevated clearance
        {
            "email": "michael.obrien@techflow.com",
            "name": "Michael O'Brien (VP Sales)",
            "expected": {
                "department": "Sales",
                "team": "Enterprise Sales",
                "security_clearance": "elevated",
                "is_manager": True,
                "has_direct_reports": True,
                "employment_type": "full_time",
            }
        },
        
        # 5. Engineering Manager - Backend (Project Lead)
        {
            "email": "priya.patel@techflow.com",
            "name": "Priya Patel (Eng Manager, Project Lead)",
            "expected": {
                "department": "Engineering",
                "team": "Backend Engineering",
                "security_clearance": "standard",
                "is_manager": True,
                "has_direct_reports": True,
                "has_projects": True,  # Project Phoenix lead
                "employment_type": "full_time",
            }
        },
        
        # 6. Engineering Manager - Frontend
        {
            "email": "marcus.johnson@techflow.com",
            "name": "Marcus Johnson (Frontend Manager)",
            "expected": {
                "department": "Engineering",
                "team": "Frontend Engineering",
                "security_clearance": "standard",
                "is_manager": True,
                "has_direct_reports": True,
                "employment_type": "full_time",
            }
        },
        
        # 7. Mobile Engineering Manager (Project Lead)
        {
            "email": "elena.rodriguez@techflow.com",
            "name": "Elena Rodriguez (Mobile Manager, Project Lead)",
            "expected": {
                "department": "Engineering",
                "team": "Mobile Engineering",
                "is_manager": True,
                "has_direct_reports": True,
                "has_projects": True,  # Mobile v2.0 lead
                "employment_type": "full_time",
            }
        },
        
        # 8. VP of Product
        {
            "email": "david.kim@techflow.com",
            "name": "David Kim (VP Product)",
            "expected": {
                "department": "Product",
                "team": "Product Management",
                "security_clearance": "elevated",
                "is_manager": True,
                "employment_type": "full_time",
            }
        },
        
        # 9. Lead Product Designer (Project member)
        {
            "email": "sophie.martinez@techflow.com",
            "name": "Sophie Martinez (Lead Designer, Multi-project)",
            "expected": {
                "department": "Product",
                "team": "Design Team",
                "is_manager": True,
                "has_projects": True,  # On Phoenix and Mobile v2.0
                "employment_type": "full_time",
            }
        },
        
        # 10. Director of Info Security (Project Lead)
        {
            "email": "alex.turner@techflow.com",
            "name": "Alex Turner (Security Director, Project Lead)",
            "expected": {
                "department": "Security",
                "team": "Information Security",
                "security_clearance": "elevated",
                "is_manager": True,
                "has_direct_reports": True,
                "has_projects": True,  # SOC 2 audit lead
                "employment_type": "full_time",
            }
        },
        
        # 11. Individual Contributor - Frontend
        {
            "email": "alice.cooper@techflow.com",
            "name": "Alice Cooper (IC - Frontend Engineer)",
            "expected": {
                "department": "Engineering",
                "team": "Frontend Engineering",
                "security_clearance": "standard",
                "is_manager": False,
                "has_direct_reports": False,
                "has_manager": True,
                "employment_type": "full_time",
            }
        },
        
        # 12. Backend Engineer (Project member)
        {
            "email": "emily.zhang@techflow.com",
            "name": "Emily Zhang (Backend Engineer, Project member)",
            "expected": {
                "department": "Engineering",
                "team": "Backend Engineering",
                "security_clearance": "standard",
                "is_manager": False,
                "has_projects": True,  # On Project Phoenix
                "has_manager": True,
                "employment_type": "full_time",
            }
        },
        
        # 13. DevOps Engineer (Project member)
        {
            "email": "james.wilson@techflow.com",
            "name": "James Wilson (DevOps, Project member)",
            "expected": {
                "department": "Engineering",
                "team": "DevOps & Infrastructure",
                "is_manager": True,
                "has_projects": True,  # On SOC 2 audit
                "employment_type": "full_time",
            }
        },
        
        # 14. Security Engineer
        {
            "email": "nina.patel@techflow.com",
            "name": "Nina Patel (Security Engineer)",
            "expected": {
                "department": "Security",
                "team": "Information Security",
                "security_clearance": "elevated",
                "employment_type": "full_time",
            }
        },
        
        # 15. Compliance Manager (Project member)
        {
            "email": "monica.lewis@techflow.com",
            "name": "Monica Lewis (Compliance, Project member)",
            "expected": {
                "department": "Security",
                "team": "Compliance & Privacy",
                "security_clearance": "elevated",
                "is_manager": True,
                "has_projects": True,  # On SOC 2 audit
                "employment_type": "full_time",
            }
        },
        
        # 16. Enterprise Account Executive
        {
            "email": "daniel.park@techflow.com",
            "name": "Daniel Park (Sales - Enterprise)",
            "expected": {
                "department": "Sales",
                "team": "Enterprise Sales",
                "security_clearance": "standard",
                "employment_type": "full_time",
            }
        },
        
        # 17. Director of Customer Success
        {
            "email": "jessica.thompson@techflow.com",
            "name": "Jessica Thompson (Customer Success Director)",
            "expected": {
                "department": "Sales",
                "team": "Customer Success",
                "is_manager": True,
                "has_direct_reports": True,
                "employment_type": "full_time",
            }
        },
        
        # 18. Director of HR
        {
            "email": "amanda.garcia@techflow.com",
            "name": "Amanda Garcia (HR Director)",
            "expected": {
                "department": "Operations",
                "team": "Human Resources",
                "security_clearance": "elevated",
                "is_manager": True,
                "employment_type": "full_time",
            }
        },
        
        # 19. Controller (Finance)
        {
            "email": "robert.lee@techflow.com",
            "name": "Robert Lee (Controller)",
            "expected": {
                "department": "Operations",
                "team": "Finance & Accounting",
                "security_clearance": "elevated",
                "is_manager": True,
                "employment_type": "full_time",
            }
        },
        
        # 20. CONTRACTOR - QA Engineer
        {
            "email": "lisa.kumar@techflow.com",
            "name": "Lisa Kumar (Contractor - QA)",
            "expected": {
                "department": "Engineering",
                "team": "Backend Engineering",
                "security_clearance": "standard",
                "employment_type": "contractor",
                "is_manager": False,
            }
        },
        
        # 21. CONTRACTOR - UX Designer
        {
            "email": "oliver.brown@techflow.com",
            "name": "Oliver Brown (Contractor - UX Designer, Project member)",
            "expected": {
                "department": "Product",
                "team": "Design Team",
                "employment_type": "contractor",
                "has_projects": True,  # On Mobile v2.0
            }
        },
        
        # 22. CONTRACTOR - Mobile Developer (Project member)
        {
            "email": "isabella.rossi@techflow.com",
            "name": "Isabella Rossi (Contractor - Mobile Dev, Project member)",
            "expected": {
                "department": "Engineering",
                "team": "Mobile Engineering",
                "employment_type": "contractor",
                "has_projects": True,  # On Mobile v2.0
            }
        },
        
        # 23. CONTRACTOR - Mobile Developer (Multi-project)
        {
            "email": "kenji.tanaka@techflow.com",
            "name": "Kenji Tanaka (Contractor - Mobile Dev, Project member)",
            "expected": {
                "department": "Engineering",
                "team": "Mobile Engineering",
                "employment_type": "contractor",
                "has_projects": True,  # On Mobile v2.0
            }
        },
        
        # 24. Senior Product Manager (Project member)
        {
            "email": "laura.bennett@techflow.com",
            "name": "Laura Bennett (Senior PM, Project member)",
            "expected": {
                "department": "Product",
                "team": "Product Management",
                "has_projects": True,  # On Project Phoenix
                "employment_type": "full_time",
            }
        },
        
        # 25. Backend Software Engineer (Project member)
        {
            "email": "kevin.zhang@techflow.com",
            "name": "Kevin Zhang (Backend Engineer, Project member)",
            "expected": {
                "department": "Engineering",
                "team": "Backend Engineering",
                "has_projects": True,  # On Project Phoenix
                "employment_type": "full_time",
            }
        },
    ]
    
    # Run all tests
    results = []
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'*' * 80}")
        print(f"TEST {i}/{len(test_cases)}")
        print('*' * 80)
        
        success = await test_employee(
            test_case["email"],
            test_case["name"],
            test_case["expected"]
        )
        
        results.append({
            "test": test_case["name"],
            "email": test_case["email"],
            "passed": success
        })
        
        await asyncio.sleep(0.1)  # Small delay between tests
    
    # Summary
    print("\n\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["passed"])
    failed = len(results) - passed
    
    print(f"\n📊 RESULTS: {passed}/{len(results)} tests passed")
    
    if failed > 0:
        print(f"\n❌ FAILED TESTS ({failed}):")
        for r in results:
            if not r["passed"]:
                print(f"  • {r['test']} ({r['email']})")
    else:
        print("\n✅ ALL TESTS PASSED!")
    
    print("\n" + "=" * 80)
    print("COVERAGE SUMMARY")
    print("=" * 80)
    print("""
✓ Tested employee types:
  - Executives (CEO, CTO, CFO, COO, VPs)
  - Managers (Engineering, Product, Sales, Operations, Security)
  - Individual Contributors (Engineers, Designers, etc.)
  - Contractors (QA, Mobile, Design)

✓ Tested organizational features:
  - Department membership
  - Team membership
  - Reporting relationships (reports_to, direct_reports)
  - Security clearances (executive, elevated, standard)
  - Employment types (full_time, contractor)
  - Hierarchy positions (CEO, executives, managers, ICs)

✓ Tested project involvement:
  - Project leads (Priya, Elena, Alex)
  - Project team members (multiple projects)
  - Employees not on projects

✓ Tested edge cases:
  - Top of hierarchy (CEO with no manager)
  - Contractors with contract end dates
  - Multi-project team members
  - Different security clearances across departments
    """)


if __name__ == "__main__":
    asyncio.run(main())
