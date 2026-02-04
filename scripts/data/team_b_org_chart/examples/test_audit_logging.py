#!/usr/bin/env python3
"""
Test Audit Logging Integration

This script tests the audit logging system integrated into the privacy API.
It performs various access checks and verifies that audit logs are created.

Author: Aithel Christo Sunil
Date: December 2024
Team: Team B
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.privacy_api import check_access, get_employee_context
from logs.audit_logger import get_audit_logger, AuditDecision


async def test_audit_logging():
    """Test audit logging across different access scenarios"""
    
    print("=" * 80)
    print("AUDIT LOGGING TEST")
    print("=" * 80)
    print()
    
    audit_logger = get_audit_logger()
    
    # Test 1: Successful access (manager with correct clearance)
    print("Test 1: Manager accessing team resource (should ALLOW)")
    print("-" * 80)
    result = await check_access(
        employee_email="priya.patel@techflow.com",  # Backend Engineering Manager
        resource_id="RES-BACKEND-001",
        resource_classification="confidential"
    )
    print(f"✓ Access granted: {result['access_granted']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Policy: {result['policy_matched']}")
    print(f"  Employee: {result['employee_context']['name']} ({result['employee_context']['title']})")
    print()
    
    # Test 2: Denied access (contractor with insufficient clearance)
    print("Test 2: Contractor accessing executive resource (should DENY)")
    print("-" * 80)
    result = await check_access(
        employee_email="lisa.kumar@techflow.com",  # QA Contractor
        resource_id="RES-EXEC-001",
        resource_classification="top_secret"
    )
    print(f"✓ Access granted: {result['access_granted']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Policy: {result['policy_matched']}")
    print(f"  Employee: {result['employee_context']['name']} ({result['employee_context']['title']})")
    print()
    
    # Test 3: Executive accessing sensitive data (should ALLOW)
    print("Test 3: CEO accessing financial data (should ALLOW)")
    print("-" * 80)
    result = await check_access(
        employee_email="sarah.chen@techflow.com",  # CEO
        resource_id="RES-FINANCE-001",
        resource_classification="top_secret"
    )
    print(f"✓ Access granted: {result['access_granted']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Policy: {result['policy_matched']}")
    print(f"  Employee: {result['employee_context']['name']} ({result['employee_context']['title']})")
    print()
    
    # Test 4: IC accessing department resource (should ALLOW)
    print("Test 4: Engineer accessing department document (should ALLOW)")
    print("-" * 80)
    result = await check_access(
        employee_email="alice.cooper@techflow.com",  # Frontend Engineer
        resource_id="RES-ENGINEERING-001",
        resource_classification="internal"
    )
    print(f"✓ Access granted: {result['access_granted']}")
    print(f"  Reason: {result['reason']}")
    print(f"  Policy: {result['policy_matched']}")
    print(f"  Employee: {result['employee_context']['name']} ({result['employee_context']['title']})")
    print()
    
    # Test 5: Non-existent employee (should DENY with error)
    print("Test 5: Non-existent employee (should DENY)")
    print("-" * 80)
    result = await check_access(
        employee_email="nonexistent@techflow.com",
        resource_id="RES-TEST-001",
        resource_classification="confidential"
    )
    print(f"✓ Access granted: {result['access_granted']}")
    print(f"  Reason: {result['reason']}")
    print()
    
    # ========================================================================
    # VERIFY AUDIT LOGS
    # ========================================================================
    
    print()
    print("=" * 80)
    print("AUDIT LOG VERIFICATION")
    print("=" * 80)
    print()
    
    # Get today's audit trail
    today = datetime.now().date()
    audit_trail = audit_logger.get_audit_trail(
        start_date=today,
        end_date=today,
        limit=100
    )
    
    print(f"Total audit entries today: {len(audit_trail)}")
    print()
    
    # Show recent entries
    print("Recent Audit Entries (last 5):")
    print("-" * 80)
    for entry in audit_trail[-5:]:
        timestamp = entry.timestamp.strftime("%H:%M:%S")
        decision_symbol = "✓" if entry.decision == AuditDecision.ALLOW else "✗"
        print(f"{decision_symbol} {timestamp} | {entry.employee_email}")
        print(f"  Resource: {entry.resource_id}")
        print(f"  Decision: {entry.decision.value}")
        print(f"  Reason: {entry.reason}")
        print(f"  Classification: {entry.resource_classification}")
        print(f"  Clearance: {entry.employee_clearance}")
        if entry.additional_context:
            if "department" in entry.additional_context:
                print(f"  Department: {entry.additional_context['department']}")
            if "is_manager" in entry.additional_context:
                print(f"  Is Manager: {entry.additional_context['is_manager']}")
        print()
    
    # ========================================================================
    # AUDIT STATISTICS
    # ========================================================================
    
    print()
    print("=" * 80)
    print("AUDIT STATISTICS")
    print("=" * 80)
    print()
    
    stats = audit_logger.get_stats(start_date=today, end_date=today)
    
    print(f"Total Accesses: {stats['total_accesses']}")
    print(f"Allowed: {stats['allowed']} ({stats['allowed'] / max(stats['total_accesses'], 1) * 100:.1f}%)")
    print(f"Denied: {stats['denied']} ({stats['denied'] / max(stats['total_accesses'], 1) * 100:.1f}%)")
    print(f"Errors: {stats['errors']}")
    print()
    
    if stats['by_employee']:
        print("Access by Employee:")
        for email, count in sorted(stats['by_employee'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {email}: {count}")
        print()
    
    if stats['by_resource']:
        print("Access by Resource:")
        for resource, count in sorted(stats['by_resource'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {resource}: {count}")
        print()
    
    if stats['by_policy']:
        print("Access by Policy:")
        for policy, count in sorted(stats['by_policy'].items(), key=lambda x: x[1], reverse=True):
            print(f"  {policy}: {count}")
        print()
    
    # ========================================================================
    # VERIFY LOG FILE
    # ========================================================================
    
    print()
    print("=" * 80)
    print("LOG FILE VERIFICATION")
    print("=" * 80)
    print()
    
    log_file = Path("logs") / f"audit_{today.isoformat()}.jsonl"
    if log_file.exists():
        print(f"✓ Audit log file exists: {log_file}")
        
        # Read and parse log file
        with open(log_file, "r") as f:
            lines = f.readlines()
        
        print(f"  Total entries in file: {len(lines)}")
        
        # Parse last entry
        if lines:
            last_entry = json.loads(lines[-1])
            print(f"  Last entry:")
            print(f"    Timestamp: {last_entry['timestamp']}")
            print(f"    Employee: {last_entry['employee_email']}")
            print(f"    Resource: {last_entry['resource_id']}")
            print(f"    Decision: {last_entry['decision']}")
            print(f"    Reason: {last_entry['reason']}")
    else:
        print(f"✗ Audit log file not found: {log_file}")
    
    print()
    print("=" * 80)
    print("AUDIT LOGGING TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_audit_logging())
