#!/usr/bin/env python3
"""
Mock Graphiti Server - Local Development
=========================================

This mock server implements the 4 Graphiti endpoints that temporal-framework calls.
Use this for testing/demo without running actual Graphiti or Team B services.

Usage:
    pip install fastapi uvicorn
    uvicorn mock_graphiti_server:app --host 127.0.0.1 --port 9000
    
Then set in your .env:
    GRAPHITI_BASE_URL=http://localhost:9000
"""

from fastapi import FastAPI, Query
from typing import Dict, List, Optional
from datetime import datetime

app = FastAPI(
    title="Mock Graphiti API",
    description="Development mock for Graphiti organizational graph endpoints",
    version="1.0.0"
)


@app.get("/")
def root():
    """Health check"""
    return {
        "status": "healthy",
        "service": "Mock Graphiti Server",
        "endpoints": [
            "/v1/relationship/reporting",
            "/v1/relationship/department",
            "/v1/relationship/projects",
            "/v1/roles/temporal"
        ]
    }


@app.get("/v1/relationship/reporting")
def get_reporting_relationship(
    employee: str = Query(..., description="Employee ID"),
    manager: str = Query(..., description="Manager ID"),
    include_history: bool = Query(False, description="Include historical relationships")
) -> Dict:
    """
    Mock: Get reporting relationship between employee and manager
    
    Returns mock data indicating direct report relationship
    """
    return {
        "is_direct_report": True,
        "is_reporting_relationship": True,  # Code expects this attribute
        "relationship_type": "direct",
        "chain_length": 1,
        "department_ids": ["dept_emergency", "dept_medical"],
        "effective_date": "2024-01-01T00:00:00Z",
        "end_date": None,
        "employee": employee,
        "manager": manager
    }


@app.get("/v1/relationship/department")
def get_department_relationship(
    sender: str = Query(..., description="Sender ID"),
    recipient: str = Query(..., description="Recipient ID"),
    include_parent_depts: bool = Query(True, description="Include parent departments")
) -> Dict:
    """
    Mock: Check if sender and recipient are in same department
    
    Returns mock data indicating same department
    """
    return {
        "same_department": True,
        "same_parent_department": True,
        "sender_department": "Emergency Medicine",
        "recipient_department": "Emergency Medicine",
        "department_distance": 0,
        "sender": sender,
        "recipient": recipient
    }


@app.get("/v1/relationship/projects")
def get_shared_projects(
    sender: str = Query(..., description="Sender ID"),
    recipient: str = Query(..., description="Recipient ID"),
    project_status: str = Query("active", description="Project status filter")
) -> Dict:
    """
    Mock: Get shared projects between sender and recipient
    
    Returns mock shared projects
    """
    return {
        "shared_projects": [
            {
                "id": "proj_er_modernization",
                "name": "ER Modernization",
                "status": "active",
                "role_sender": "lead_physician",
                "role_recipient": "care_team_member"
            },
            {
                "id": "proj_patient_safety",
                "name": "Patient Safety Initiative",
                "status": "active",
                "role_sender": "contributor",
                "role_recipient": "contributor"
            }
        ],
        "project_count": 2,
        "projects_ids": ["proj_er_modernization", "proj_patient_safety"],
        "sender": sender,
        "recipient": recipient
    }


@app.get("/v1/roles/temporal")
def get_temporal_roles(
    person_id: str = Query(..., description="Person ID"),
    time: str = Query(..., description="ISO timestamp"),
    include_future: bool = Query(False, description="Include future roles")
) -> Dict:
    """
    Mock: Get temporal/acting roles for a person at specific time
    
    Returns mock acting roles (e.g., acting_head, oncall)
    """
    # Parse time to check if it's outside business hours
    try:
        ts = datetime.fromisoformat(time.replace('Z', '+00:00'))
        hour = ts.hour
    except:
        ts = datetime.utcnow()
        hour = ts.hour

    # Build roles in Graphiti-style schema expected by client
    permanent_roles: List[str] = ["user"]
    temporary_roles: List[Dict] = []

    # After hours or weekend - add on-call/acting roles
    if hour < 8 or hour >= 18:
        temporary_roles.append({
            "role_id": "temp_oncall_critical",
            "role_name": "Oncall Critical",
            "base_role": "user",
            "start_date": (ts.replace(hour=18, minute=0, second=0, microsecond=0)).isoformat() + "Z",
            "end_date": (ts.replace(hour=23, minute=59, second=0, microsecond=0)).isoformat() + "Z",
            "reason": "Emergency rotation",
            "delegation_chain": []
        })
        temporary_roles.append({
            "role_id": "temp_acting_head",
            "role_name": "Acting Head",
            "base_role": "manager",
            "start_date": ts.isoformat() + "Z",
            "end_date": (ts.replace(hour=min(23, hour+4))).isoformat() + "Z",
            "reason": "Coverage",
            "delegation_chain": []
        })

    active_roles: List[str] = permanent_roles + [r["role_name"].lower().replace(" ", "_") for r in temporary_roles]

    return {
        "person_id": person_id,
        "permanent_roles": permanent_roles,
        "temporary_roles": temporary_roles,
        "active_roles": active_roles,
        "query_timestamp": ts.isoformat() + "Z"
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Mock Graphiti Server on http://localhost:9000")
    print("📝 Endpoints available:")
    print("   • /v1/relationship/reporting")
    print("   • /v1/relationship/department")
    print("   • /v1/relationship/projects")
    print("   • /v1/roles/temporal")
    print("\n✅ Set GRAPHITI_BASE_URL=http://localhost:9000 in your .env")
    uvicorn.run(app, host="127.0.0.1", port=9000)
