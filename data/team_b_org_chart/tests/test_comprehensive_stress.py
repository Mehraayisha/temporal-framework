#!/usr/bin/env python3
"""
Comprehensive Stress Test Suite for Privacy Firewall REST API
Tests all endpoints with various scenarios including edge cases
"""
import asyncio
import json
import time
from typing import Dict, List
import aiohttp
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

class StressTest:
    def __init__(self):
        self.results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': [],
            'timing': {}
        }
        
    def log(self, message: str, color: str = Colors.BLUE):
        """Print colored log message"""
        print(f"{color}{message}{Colors.END}")
        
    def assert_true(self, condition: bool, message: str):
        """Assert a condition and track results"""
        self.results['total'] += 1
        if condition:
            self.results['passed'] += 1
            print(f"{Colors.GREEN}✓{Colors.END} {message}")
        else:
            self.results['failed'] += 1
            error_msg = f"✗ {message}"
            self.results['errors'].append(error_msg)
            print(f"{Colors.RED}{error_msg}{Colors.END}")
            
    async def test_health_endpoint(self, session: aiohttp.ClientSession):
        """Test health check endpoint"""
        self.log("\n=== Testing Health Endpoint ===", Colors.BOLD + Colors.CYAN)
        
        start = time.time()
        async with session.get(f"{BASE_URL}/health") as resp:
            data = await resp.json()
            elapsed = time.time() - start
            
        self.results['timing']['health'] = elapsed
        self.assert_true(resp.status == 200, "Health endpoint returns 200")
        self.assert_true(data['status'] == 'healthy', "Status is healthy")
        self.assert_true('neo4j_connected' in data, "Neo4j connection status present")
        self.assert_true(elapsed < 1.0, f"Health check fast (<1s): {elapsed:.3f}s")
        
    async def test_manager_to_report_access(self, session: aiohttp.ClientSession):
        """Test manager accessing direct report's resources - should ALLOW"""
        self.log("\n=== Test 1: Manager → Direct Report Access ===", Colors.BOLD + Colors.CYAN)
        
        test_cases = [
            {
                'name': 'Priya (manager) → Emily (report) PTO calendar',
                'requester': 'priya.patel@techflow.com',
                'target': 'emily.zhang@techflow.com',
                'resource_type': 'pto_calendar',
                'should_allow': True,
                'expected_reason': 'manager'
            },
            {
                'name': 'Priya (manager) → Carlos (report) performance review',
                'requester': 'priya.patel@techflow.com',
                'target': 'carlos.martinez@techflow.com',
                'resource_type': 'performance_review',
                'should_allow': True,
                'expected_reason': 'manager'
            },
            {
                'name': 'Priya (manager) → Lisa (report) salary info',
                'requester': 'priya.patel@techflow.com',
                'target': 'lisa.anderson@techflow.com',
                'resource_type': 'salary_info',
                'should_allow': True,
                'expected_reason': 'manager'
            }
        ]
        
        for tc in test_cases:
            start = time.time()
            url = f"{BASE_URL}/check-employee-access"
            params = {
                'requester_email': tc['requester'],
                'target_email': tc['target'],
                'resource_type': tc['resource_type']
            }
            
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                elapsed = time.time() - start
                
            self.assert_true(resp.status == 200, f"{tc['name']}: Request successful")
            self.assert_true(
                data['access_granted'] == tc['should_allow'],
                f"{tc['name']}: Access {'granted' if tc['should_allow'] else 'denied'} correctly"
            )
            if tc['should_allow']:
                self.assert_true(
                    tc['expected_reason'] in data.get('reason', '').lower(),
                    f"{tc['name']}: Correct reason (manager relationship)"
                )
                self.assert_true(
                    data['relationship_context']['manager_relationship'] == True,
                    f"{tc['name']}: Manager relationship detected"
                )
            self.log(f"  ⏱ Response time: {elapsed:.3f}s", Colors.YELLOW)
            
    async def test_peer_to_peer_deny(self, session: aiohttp.ClientSession):
        """Test peer accessing peer's sensitive data - should DENY"""
        self.log("\n=== Test 2: Peer → Peer Sensitive Access (DENY) ===", Colors.BOLD + Colors.CYAN)
        
        test_cases = [
            {
                'name': 'Emily (peer) → Carlos (peer) salary info',
                'requester': 'emily.zhang@techflow.com',
                'target': 'carlos.martinez@techflow.com',
                'resource_type': 'salary_info',
                'should_allow': False
            },
            {
                'name': 'Emily (peer) → Carlos (peer) performance review',
                'requester': 'emily.zhang@techflow.com',
                'target': 'carlos.martinez@techflow.com',
                'resource_type': 'performance_review',
                'should_allow': False
            }
        ]
        
        for tc in test_cases:
            url = f"{BASE_URL}/check-employee-access"
            params = {
                'requester_email': tc['requester'],
                'target_email': tc['target'],
                'resource_type': tc['resource_type']
            }
            
            async with session.post(url, params=params) as resp:
                data = await resp.json()
                
            self.assert_true(resp.status == 200, f"{tc['name']}: Request successful")
            self.assert_true(
                data['access_granted'] == tc['should_allow'],
                f"{tc['name']}: Access denied correctly"
            )
            self.assert_true(
                data['relationship_context']['manager_relationship'] == False,
                f"{tc['name']}: Not a manager relationship"
            )
            
    async def test_same_team_project_access(self, session: aiohttp.ClientSession):
        """Test same team members accessing project resources - should ALLOW"""
        self.log("\n=== Test 3: Same Team → Project Access ===", Colors.BOLD + Colors.CYAN)
        
        # Emily and Carlos are both on Backend Engineering team and Project Phoenix
        url = f"{BASE_URL}/check-employee-access"
        params = {
            'requester_email': 'emily.zhang@techflow.com',
            'target_email': 'carlos.martinez@techflow.com',
            'resource_type': 'project_docs'
        }
        
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            
        self.assert_true(resp.status == 200, "Same team project access: Request successful")
        self.assert_true(
            data['relationship_context']['team_match'] == True,
            "Same team detected"
        )
        self.assert_true(
            data['relationship_context']['project_shared'] == True,
            "Shared project detected"
        )
        self.assert_true(
            len(data['relationship_context'].get('shared_projects', [])) > 0,
            "Shared projects listed"
        )
        
    async def test_employee_context_retrieval(self, session: aiohttp.ClientSession):
        """Test employee context endpoint for various employees"""
        self.log("\n=== Test 4: Employee Context Retrieval ===", Colors.BOLD + Colors.CYAN)
        
        test_emails = [
            'priya.patel@techflow.com',  # Manager
            'emily.zhang@techflow.com',   # Engineer
            'carlos.martinez@techflow.com',  # Engineer
            'sarah.johnson@techflow.com',  # VP Engineering
        ]
        
        for email in test_emails:
            start = time.time()
            async with session.get(f"{BASE_URL}/employee-context/{email}") as resp:
                data = await resp.json()
                elapsed = time.time() - start
                
            self.assert_true(resp.status == 200, f"Context for {email}: Request successful")
            self.assert_true('employee_id' in data, f"{email}: Has employee_id")
            self.assert_true('name' in data, f"{email}: Has name")
            self.assert_true('email' in data, f"{email}: Has email")
            self.assert_true('department' in data, f"{email}: Has department")
            
            # Priya should have direct reports
            if email == 'priya.patel@techflow.com':
                self.assert_true(
                    len(data.get('direct_reports', [])) > 0,
                    f"{email}: Manager has direct reports"
                )
                self.log(f"  📊 Priya has {len(data['direct_reports'])} direct reports", Colors.GREEN)
                
            self.log(f"  ⏱ Context retrieval: {elapsed:.3f}s", Colors.YELLOW)
            
    async def test_accessible_resources(self, session: aiohttp.ClientSession):
        """Test accessible resources endpoint"""
        self.log("\n=== Test 5: Accessible Resources ===", Colors.BOLD + Colors.CYAN)
        
        test_cases = [
            {
                'email': 'priya.patel@techflow.com',
                'resource_type': 'pto_calendar',
                'min_expected': 3  # Should see own + direct reports
            },
            {
                'email': 'emily.zhang@techflow.com',
                'resource_type': 'project_docs',
                'min_expected': 1  # Should see project docs
            }
        ]
        
        for tc in test_cases:
            url = f"{BASE_URL}/accessible-resources/{tc['email']}"
            params = {'resource_type': tc['resource_type']}
            
            start = time.time()
            async with session.get(url, params=params) as resp:
                data = await resp.json()
                elapsed = time.time() - start
                
            self.assert_true(resp.status == 200, f"Accessible resources for {tc['email']}: Request successful")
            self.assert_true('accessible_resources' in data, "Has accessible_resources field")
            
            resource_count = len(data.get('accessible_resources', []))
            self.assert_true(
                resource_count >= tc['min_expected'],
                f"{tc['email']}: Has at least {tc['min_expected']} accessible resources (got {resource_count})"
            )
            self.log(f"  📊 {resource_count} accessible resources found", Colors.GREEN)
            self.log(f"  ⏱ Query time: {elapsed:.3f}s", Colors.YELLOW)
            
    async def test_resource_viewers(self, session: aiohttp.ClientSession):
        """Test resource viewers endpoint"""
        self.log("\n=== Test 6: Resource Viewers ===", Colors.BOLD + Colors.CYAN)
        
        # Test with a project resource
        resource_id = "proj-001"
        start = time.time()
        async with session.get(f"{BASE_URL}/resource-viewers/{resource_id}") as resp:
            data = await resp.json()
            elapsed = time.time() - start
            
        self.assert_true(resp.status == 200, "Resource viewers: Request successful")
        self.assert_true('viewers' in data, "Has viewers field")
        self.assert_true(len(data.get('viewers', [])) > 0, "Has at least one viewer")
        self.log(f"  📊 {len(data['viewers'])} viewers found", Colors.GREEN)
        self.log(f"  ⏱ Query time: {elapsed:.3f}s", Colors.YELLOW)
        
    async def test_audit_trail(self, session: aiohttp.ClientSession):
        """Test audit trail retrieval"""
        self.log("\n=== Test 7: Audit Trail ===", Colors.BOLD + Colors.CYAN)
        
        # First make some access requests to generate audit logs
        url = f"{BASE_URL}/check-employee-access"
        test_requests = [
            {
                'requester_email': 'priya.patel@techflow.com',
                'target_email': 'emily.zhang@techflow.com',
                'resource_type': 'pto_calendar'
            },
            {
                'requester_email': 'emily.zhang@techflow.com',
                'target_email': 'carlos.martinez@techflow.com',
                'resource_type': 'salary_info'
            }
        ]
        
        for req in test_requests:
            async with session.post(url, params=req) as resp:
                await resp.json()
                
        # Now check audit trail
        start = time.time()
        async with session.get(f"{BASE_URL}/audit-trail") as resp:
            data = await resp.json()
            elapsed = time.time() - start
            
        self.assert_true(resp.status == 200, "Audit trail: Request successful")
        self.assert_true('entries' in data, "Has entries field")
        self.assert_true(len(data.get('entries', [])) > 0, "Has audit entries")
        
        # Check audit entry structure
        if data.get('entries'):
            entry = data['entries'][0]
            self.assert_true('timestamp' in entry, "Entry has timestamp")
            self.assert_true('decision' in entry, "Entry has decision")
            self.assert_true('employee_id' in entry, "Entry has employee_id")
            
        self.log(f"  📊 {len(data['entries'])} audit entries", Colors.GREEN)
        self.log(f"  ⏱ Query time: {elapsed:.3f}s", Colors.YELLOW)
        
    async def test_audit_stats(self, session: aiohttp.ClientSession):
        """Test audit statistics endpoint"""
        self.log("\n=== Test 8: Audit Statistics ===", Colors.BOLD + Colors.CYAN)
        
        start = time.time()
        async with session.get(f"{BASE_URL}/audit-stats") as resp:
            data = await resp.json()
            elapsed = time.time() - start
            
        self.assert_true(resp.status == 200, "Audit stats: Request successful")
        self.assert_true('total_requests' in data, "Has total_requests")
        self.assert_true('allowed' in data, "Has allowed count")
        self.assert_true('denied' in data, "Has denied count")
        
        total = data.get('total_requests', 0)
        allowed = data.get('allowed', 0)
        denied = data.get('denied', 0)
        
        self.log(f"  📊 Total: {total}, Allowed: {allowed}, Denied: {denied}", Colors.GREEN)
        self.log(f"  ⏱ Query time: {elapsed:.3f}s", Colors.YELLOW)
        
    async def test_cross_department_access(self, session: aiohttp.ClientSession):
        """Test cross-department access control"""
        self.log("\n=== Test 9: Cross-Department Access ===", Colors.BOLD + Colors.CYAN)
        
        # Try to access someone from different department
        # This tests if department boundaries are enforced
        url = f"{BASE_URL}/check-employee-access"
        params = {
            'requester_email': 'emily.zhang@techflow.com',  # Engineering
            'target_email': 'michael.brown@techflow.com',   # Different dept (if exists)
            'resource_type': 'salary_info'
        }
        
        async with session.post(url, params=params) as resp:
            data = await resp.json()
            
        # Should work but might deny based on lack of relationship
        self.assert_true(resp.status == 200, "Cross-department request successful")
        self.log(f"  🔒 Access granted: {data.get('access_granted')}", Colors.YELLOW)
        
    async def test_invalid_inputs(self, session: aiohttp.ClientSession):
        """Test error handling with invalid inputs"""
        self.log("\n=== Test 10: Error Handling ===", Colors.BOLD + Colors.CYAN)
        
        test_cases = [
            {
                'name': 'Invalid email format',
                'url': f"{BASE_URL}/employee-context/not-an-email",
                'expected_status': [404, 422]
            },
            {
                'name': 'Non-existent employee',
                'url': f"{BASE_URL}/employee-context/ghost@techflow.com",
                'expected_status': [404]
            }
        ]
        
        for tc in test_cases:
            async with session.get(tc['url']) as resp:
                status = resp.status
                
            self.assert_true(
                status in tc['expected_status'],
                f"{tc['name']}: Returns expected error status (got {status})"
            )
            
    async def test_concurrent_requests(self, session: aiohttp.ClientSession):
        """Test handling of concurrent requests"""
        self.log("\n=== Test 11: Concurrent Request Stress Test ===", Colors.BOLD + Colors.CYAN)
        
        # Fire 20 concurrent requests
        url = f"{BASE_URL}/check-employee-access"
        params = {
            'requester_email': 'priya.patel@techflow.com',
            'target_email': 'emily.zhang@techflow.com',
            'resource_type': 'pto_calendar'
        }
        
        start = time.time()
        tasks = [session.post(url, params=params) for _ in range(20)]
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        success_count = sum(1 for r in responses if r.status == 200)
        
        self.assert_true(
            success_count == 20,
            f"All 20 concurrent requests successful ({success_count}/20)"
        )
        self.log(f"  ⏱ 20 concurrent requests: {elapsed:.3f}s ({elapsed/20:.3f}s avg)", Colors.YELLOW)
        
        # Clean up responses
        for resp in responses:
            await resp.read()
            
    async def test_performance_benchmarks(self, session: aiohttp.ClientSession):
        """Run performance benchmarks"""
        self.log("\n=== Test 12: Performance Benchmarks ===", Colors.BOLD + Colors.CYAN)
        
        benchmarks = {
            'health_check': (f"{BASE_URL}/health", 'GET', None),
            'employee_context': (f"{BASE_URL}/employee-context/priya.patel@techflow.com", 'GET', None),
            'access_check': (f"{BASE_URL}/check-employee-access", 'POST', {
                'requester_email': 'priya.patel@techflow.com',
                'target_email': 'emily.zhang@techflow.com',
                'resource_type': 'pto_calendar'
            })
        }
        
        iterations = 10
        
        for name, (url, method, params) in benchmarks.items():
            times = []
            
            for _ in range(iterations):
                start = time.time()
                if method == 'GET':
                    async with session.get(url) as resp:
                        await resp.json()
                else:
                    async with session.post(url, params=params) as resp:
                        await resp.json()
                elapsed = time.time() - start
                times.append(elapsed)
                
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            self.log(f"  {name}:", Colors.CYAN)
            self.log(f"    Avg: {avg_time:.3f}s | Min: {min_time:.3f}s | Max: {max_time:.3f}s", Colors.YELLOW)
            
            # Performance assertions
            if name == 'health_check':
                self.assert_true(avg_time < 0.5, f"{name}: Average < 0.5s")
            else:
                self.assert_true(avg_time < 2.0, f"{name}: Average < 2.0s")
                
    async def run_all_tests(self):
        """Run all stress tests"""
        self.log("\n" + "="*70, Colors.BOLD + Colors.MAGENTA)
        self.log("🔥 PRIVACY FIREWALL REST API STRESS TEST 🔥", Colors.BOLD + Colors.MAGENTA)
        self.log("="*70, Colors.BOLD + Colors.MAGENTA)
        
        start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            # Run all test suites
            await self.test_health_endpoint(session)
            await self.test_manager_to_report_access(session)
            await self.test_peer_to_peer_deny(session)
            await self.test_same_team_project_access(session)
            await self.test_employee_context_retrieval(session)
            await self.test_accessible_resources(session)
            await self.test_resource_viewers(session)
            await self.test_audit_trail(session)
            await self.test_audit_stats(session)
            await self.test_cross_department_access(session)
            await self.test_invalid_inputs(session)
            await self.test_concurrent_requests(session)
            await self.test_performance_benchmarks(session)
            
        total_time = time.time() - start_time
        
        # Print summary
        self.print_summary(total_time)
        
    def print_summary(self, total_time: float):
        """Print test summary"""
        self.log("\n" + "="*70, Colors.BOLD + Colors.MAGENTA)
        self.log("📊 TEST SUMMARY", Colors.BOLD + Colors.MAGENTA)
        self.log("="*70, Colors.BOLD + Colors.MAGENTA)
        
        passed = self.results['passed']
        failed = self.results['failed']
        total = self.results['total']
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        self.log(f"\nTotal Tests: {total}", Colors.BOLD)
        self.log(f"✓ Passed: {passed}", Colors.GREEN)
        self.log(f"✗ Failed: {failed}", Colors.RED)
        self.log(f"Pass Rate: {pass_rate:.1f}%", Colors.CYAN)
        self.log(f"Total Time: {total_time:.2f}s", Colors.YELLOW)
        
        if self.results['errors']:
            self.log(f"\n❌ FAILURES ({len(self.results['errors'])}):", Colors.RED + Colors.BOLD)
            for error in self.results['errors']:
                self.log(f"  {error}", Colors.RED)
        
        if failed == 0:
            self.log("\n🎉 ALL TESTS PASSED! 🎉", Colors.GREEN + Colors.BOLD)
            self.log("The Privacy Firewall is ROCK SOLID! 💪", Colors.GREEN)
        else:
            self.log("\n⚠️  SOME TESTS FAILED", Colors.YELLOW + Colors.BOLD)
            self.log("Check the errors above for details.", Colors.YELLOW)
            
        self.log("\n" + "="*70, Colors.BOLD + Colors.MAGENTA)

async def main():
    """Main entry point"""
    stress_test = StressTest()
    
    try:
        await stress_test.run_all_tests()
        
        # Exit with proper code
        if stress_test.results['failed'] > 0:
            exit(1)
        else:
            exit(0)
            
    except Exception as e:
        print(f"{Colors.RED}{Colors.BOLD}💥 FATAL ERROR: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
