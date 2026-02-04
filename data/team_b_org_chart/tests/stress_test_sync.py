#!/usr/bin/env python3
"""
Comprehensive Stress Test Suite for Privacy Firewall REST API
Synchronous version using requests library
"""
import requests
import time
import json
from typing import Dict, List
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

class Colors:
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
            'errors': []
        }
        
    def log(self, message: str, color: str = Colors.BLUE):
        print(f"{color}{message}{Colors.END}")
        
    def assert_true(self, condition: bool, message: str):
        self.results['total'] += 1
        if condition:
            self.results['passed'] += 1
            print(f"{Colors.GREEN}✓{Colors.END} {message}")
        else:
            self.results['failed'] += 1
            error_msg = f"✗ {message}"
            self.results['errors'].append(error_msg)
            print(f"{Colors.RED}{error_msg}{Colors.END}")
            
    def test_health_endpoint(self):
        """Test 1: Health check endpoint"""
        self.log("\n=== Test 1: Health Endpoint ===", Colors.BOLD + Colors.CYAN)
        
        start = time.time()
        resp = requests.get(f"{BASE_URL}/health")
        elapsed = time.time() - start
        data = resp.json()
        
        self.assert_true(resp.status_code == 200, "Health endpoint returns 200")
        self.assert_true(data['status'] == 'healthy', "Status is healthy")
        self.assert_true('neo4j_connected' in data, "Neo4j connection status present")
        self.log(f"  ⏱ Response time: {elapsed:.3f}s", Colors.YELLOW)
        
    def test_manager_to_report_access(self):
        """Test 2: Manager → Direct Report Access (ALLOW)"""
        self.log("\n=== Test 2: Manager → Direct Report Access ===", Colors.BOLD + Colors.CYAN)
        
        test_cases = [
            ('Priya → Emily PTO', 'priya.patel@techflow.com', 'emily.zhang@techflow.com', 'pto_calendar'),
            ('Priya → Carlos Performance', 'priya.patel@techflow.com', 'carlos.martinez@techflow.com', 'performance_review'),
            ('Priya → Lisa Salary', 'priya.patel@techflow.com', 'lisa.anderson@techflow.com', 'salary_info'),
        ]
        
        for name, requester, target, resource_type in test_cases:
            start = time.time()
            resp = requests.post(
                f"{BASE_URL}/check-employee-access",
                params={
                    'requester_email': requester,
                    'target_email': target,
                    'resource_type': resource_type
                }
            )
            elapsed = time.time() - start
            data = resp.json()
            
            self.assert_true(resp.status_code == 200, f"{name}: Request successful")
            self.assert_true(data['access_granted'] == True, f"{name}: Access GRANTED ✓")
            self.assert_true(
                data['relationship_context']['manager_relationship'] == True,
                f"{name}: Manager relationship detected"
            )
            self.log(f"  ⏱ {elapsed:.3f}s - Reason: {data.get('reason', 'N/A')}", Colors.YELLOW)
            
    def test_peer_to_peer_deny(self):
        """Test 3: Peer → Peer Sensitive Access (DENY)"""
        self.log("\n=== Test 3: Peer → Peer Sensitive Access (DENY) ===", Colors.BOLD + Colors.CYAN)
        
        test_cases = [
            ('Emily → Carlos Salary', 'emily.zhang@techflow.com', 'carlos.martinez@techflow.com', 'salary_info'),
            ('Emily → Carlos Performance', 'emily.zhang@techflow.com', 'carlos.martinez@techflow.com', 'performance_review'),
        ]
        
        for name, requester, target, resource_type in test_cases:
            resp = requests.post(
                f"{BASE_URL}/check-employee-access",
                params={
                    'requester_email': requester,
                    'target_email': target,
                    'resource_type': resource_type
                }
            )
            data = resp.json()
            
            self.assert_true(resp.status_code == 200, f"{name}: Request successful")
            self.assert_true(data['access_granted'] == False, f"{name}: Access DENIED ✓")
            self.log(f"  🔒 Correctly denied - Reason: {data.get('reason', 'N/A')}", Colors.YELLOW)
            
    def test_same_team_detection(self):
        """Test 4: Same Team Detection"""
        self.log("\n=== Test 4: Same Team Detection ===", Colors.BOLD + Colors.CYAN)
        
        resp = requests.post(
            f"{BASE_URL}/check-employee-access",
            params={
                'requester_email': 'emily.zhang@techflow.com',
                'target_email': 'carlos.martinez@techflow.com',
                'resource_type': 'project_docs'
            }
        )
        data = resp.json()
        
        self.assert_true(resp.status_code == 200, "Same team check: Request successful")
        self.assert_true(
            data['relationship_context']['team_match'] == True,
            "Same team detected (Backend Engineering)"
        )
        self.assert_true(
            data['relationship_context']['project_shared'] == True,
            "Shared project detected"
        )
        self.log(f"  📊 Shared projects: {data['relationship_context'].get('shared_projects', [])}", Colors.GREEN)
        
    def test_employee_context_retrieval(self):
        """Test 5: Employee Context Retrieval"""
        self.log("\n=== Test 5: Employee Context Retrieval ===", Colors.BOLD + Colors.CYAN)
        
        test_emails = [
            'priya.patel@techflow.com',
            'emily.zhang@techflow.com',
            'carlos.martinez@techflow.com',
        ]
        
        for email in test_emails:
            start = time.time()
            resp = requests.get(f"{BASE_URL}/employee-context/{email}")
            elapsed = time.time() - start
            data = resp.json()
            
            self.assert_true(resp.status_code == 200, f"Context for {email}: Successful")
            self.assert_true('employee_id' in data, f"{email}: Has employee_id")
            self.assert_true('name' in data, f"{email}: Has name")
            self.assert_true('department' in data, f"{email}: Has department")
            
            if email == 'priya.patel@techflow.com':
                reports_count = len(data.get('direct_reports', []))
                self.assert_true(reports_count > 0, f"Priya has {reports_count} direct reports")
                self.log(f"  📊 Direct reports: {reports_count}", Colors.GREEN)
                
            self.log(f"  ⏱ {elapsed:.3f}s", Colors.YELLOW)
            
    def test_accessible_resources(self):
        """Test 6: Accessible Resources Endpoint"""
        self.log("\n=== Test 6: Accessible Resources ===", Colors.BOLD + Colors.CYAN)
        
        start = time.time()
        resp = requests.get(
            f"{BASE_URL}/accessible-resources/priya.patel@techflow.com",
            params={'resource_type': 'pto_calendar'}
        )
        elapsed = time.time() - start
        data = resp.json()
        
        self.assert_true(resp.status_code == 200, "Accessible resources: Request successful")
        self.assert_true('accessible_resources' in data, "Has accessible_resources field")
        
        count = len(data.get('accessible_resources', []))
        self.assert_true(count >= 3, f"Priya can access {count} PTO calendars (self + reports)")
        self.log(f"  📊 {count} accessible resources", Colors.GREEN)
        self.log(f"  ⏱ {elapsed:.3f}s", Colors.YELLOW)
        
    def test_resource_viewers(self):
        """Test 7: Resource Viewers Endpoint"""
        self.log("\n=== Test 7: Resource Viewers ===", Colors.BOLD + Colors.CYAN)
        
        start = time.time()
        resp = requests.get(f"{BASE_URL}/resource-viewers/proj-001")
        elapsed = time.time() - start
        data = resp.json()
        
        self.assert_true(resp.status_code == 200, "Resource viewers: Request successful")
        self.assert_true('viewers' in data, "Has viewers field")
        
        count = len(data.get('viewers', []))
        self.log(f"  📊 {count} viewers found", Colors.GREEN)
        self.log(f"  ⏱ {elapsed:.3f}s", Colors.YELLOW)
        
    def test_audit_trail(self):
        """Test 8: Audit Trail"""
        self.log("\n=== Test 8: Audit Trail ===", Colors.BOLD + Colors.CYAN)
        
        # Generate some audit entries first
        requests.post(
            f"{BASE_URL}/check-employee-access",
            params={
                'requester_email': 'priya.patel@techflow.com',
                'target_email': 'emily.zhang@techflow.com',
                'resource_type': 'pto_calendar'
            }
        )
        
        start = time.time()
        resp = requests.get(f"{BASE_URL}/audit-trail")
        elapsed = time.time() - start
        data = resp.json()
        
        self.assert_true(resp.status_code == 200, "Audit trail: Request successful")
        self.assert_true('entries' in data, "Has entries field")
        
        count = len(data.get('entries', []))
        self.assert_true(count > 0, f"Has {count} audit entries")
        
        if data.get('entries'):
            entry = data['entries'][0]
            self.assert_true('timestamp' in entry, "Entry has timestamp")
            self.assert_true('decision' in entry, "Entry has decision")
            
        self.log(f"  📊 {count} audit entries", Colors.GREEN)
        self.log(f"  ⏱ {elapsed:.3f}s", Colors.YELLOW)
        
    def test_audit_stats(self):
        """Test 9: Audit Statistics"""
        self.log("\n=== Test 9: Audit Statistics ===", Colors.BOLD + Colors.CYAN)
        
        start = time.time()
        resp = requests.get(f"{BASE_URL}/audit-stats")
        elapsed = time.time() - start
        data = resp.json()
        
        self.assert_true(resp.status_code == 200, "Audit stats: Request successful")
        self.assert_true('total_requests' in data, "Has total_requests")
        self.assert_true('allowed' in data, "Has allowed count")
        self.assert_true('denied' in data, "Has denied count")
        
        total = data.get('total_requests', 0)
        allowed = data.get('allowed', 0)
        denied = data.get('denied', 0)
        
        self.log(f"  📊 Total: {total}, Allowed: {allowed}, Denied: {denied}", Colors.GREEN)
        self.log(f"  ⏱ {elapsed:.3f}s", Colors.YELLOW)
        
    def test_error_handling(self):
        """Test 10: Error Handling"""
        self.log("\n=== Test 10: Error Handling ===", Colors.BOLD + Colors.CYAN)
        
        # Non-existent employee
        resp = requests.get(f"{BASE_URL}/employee-context/ghost@techflow.com")
        self.assert_true(resp.status_code == 404, "Non-existent employee returns 404")
        
    def test_rapid_fire(self):
        """Test 11: Rapid Fire Requests"""
        self.log("\n=== Test 11: Rapid Fire (50 requests) ===", Colors.BOLD + Colors.CYAN)
        
        start = time.time()
        success_count = 0
        
        for i in range(50):
            resp = requests.post(
                f"{BASE_URL}/check-employee-access",
                params={
                    'requester_email': 'priya.patel@techflow.com',
                    'target_email': 'emily.zhang@techflow.com',
                    'resource_type': 'pto_calendar'
                }
            )
            if resp.status_code == 200:
                success_count += 1
                
        elapsed = time.time() - start
        
        self.assert_true(success_count == 50, f"All 50 requests successful ({success_count}/50)")
        self.log(f"  ⏱ 50 requests in {elapsed:.3f}s ({elapsed/50:.3f}s avg)", Colors.YELLOW)
        self.log(f"  🚀 Throughput: {50/elapsed:.1f} req/sec", Colors.GREEN)
        
    def test_performance_benchmarks(self):
        """Test 12: Performance Benchmarks"""
        self.log("\n=== Test 12: Performance Benchmarks (10 iterations) ===", Colors.BOLD + Colors.CYAN)
        
        benchmarks = {
            'Health Check': lambda: requests.get(f"{BASE_URL}/health"),
            'Employee Context': lambda: requests.get(f"{BASE_URL}/employee-context/priya.patel@techflow.com"),
            'Access Check': lambda: requests.post(
                f"{BASE_URL}/check-employee-access",
                params={
                    'requester_email': 'priya.patel@techflow.com',
                    'target_email': 'emily.zhang@techflow.com',
                    'resource_type': 'pto_calendar'
                }
            )
        }
        
        for name, func in benchmarks.items():
            times = []
            for _ in range(10):
                start = time.time()
                func()
                elapsed = time.time() - start
                times.append(elapsed)
                
            avg = sum(times) / len(times)
            min_t = min(times)
            max_t = max(times)
            
            self.log(f"  {name}:", Colors.CYAN)
            self.log(f"    Avg: {avg:.3f}s | Min: {min_t:.3f}s | Max: {max_t:.3f}s", Colors.YELLOW)
            
    def run_all_tests(self):
        """Run all stress tests"""
        self.log("\n" + "="*70, Colors.BOLD + Colors.MAGENTA)
        self.log("🔥 PRIVACY FIREWALL REST API STRESS TEST 🔥", Colors.BOLD + Colors.MAGENTA)
        self.log("="*70 + "\n", Colors.BOLD + Colors.MAGENTA)
        
        start_time = time.time()
        
        try:
            self.test_health_endpoint()
            self.test_manager_to_report_access()
            self.test_peer_to_peer_deny()
            self.test_same_team_detection()
            self.test_employee_context_retrieval()
            self.test_accessible_resources()
            self.test_resource_viewers()
            self.test_audit_trail()
            self.test_audit_stats()
            self.test_error_handling()
            self.test_rapid_fire()
            self.test_performance_benchmarks()
            
        except requests.exceptions.ConnectionError:
            self.log("\n❌ ERROR: Cannot connect to API server!", Colors.RED + Colors.BOLD)
            self.log("Make sure the server is running on http://localhost:8000", Colors.RED)
            return False
            
        total_time = time.time() - start_time
        self.print_summary(total_time)
        return self.results['failed'] == 0
        
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
            
        self.log("\n" + "="*70, Colors.BOLD + Colors.MAGENTA)

def main():
    stress_test = StressTest()
    success = stress_test.run_all_tests()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
