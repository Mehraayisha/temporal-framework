"""
Pytest configuration and fixtures for testing
"""

import asyncio
import os

import pytest
from dotenv import load_dotenv

from core import GraphitiClient

# Load environment variables
load_dotenv()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def graphiti_client():
    """
    Create a fresh GraphitiClient instance for each test.
    
    Note: This initializes the database (clears all data) for each test.
    """
    client = GraphitiClient()
    await client.init_database()  # Clear and rebuild indices
    yield client
    # Cleanup if needed


@pytest.fixture
def sample_department():
    """Sample department data for testing"""
    return {
        "name": "Engineering",
        "id": "dept-test-001",
        "description": "Software engineering department",
        "budget": 1000000.0,
        "head_count": 10,
        "data_classification": "internal",
    }


@pytest.fixture
def sample_team():
    """Sample team data for testing"""
    return {
        "name": "Backend Team",
        "department": "Engineering",
        "id": "team-test-001",
        "lead": "Alice Johnson",
        "purpose": "Build and maintain backend services",
        "data_classification": "internal",
    }


@pytest.fixture
def sample_employee():
    """Sample employee data for testing"""
    return {
        "name": "Alice Johnson",
        "department": "Engineering",
        "team": "Backend Team",
        "id": "emp-test-001",
        "email": "alice@company.com",
        "title": "Engineering Manager",
        "skills": ["Python", "Leadership", "System Design"],
        "location": "San Francisco",
        "phone": "+1-555-0001",
        "timezone": "America/Los_Angeles",
        "working_hours_start": "09:00",
        "working_hours_end": "17:00",
        "security_clearance": "elevated",
        "employee_type": "full_time",
    }


@pytest.fixture
def sample_employees():
    """Multiple employees for batch testing"""
    return [
        {
            "name": "Alice Johnson",
            "department": "Engineering",
            "team": "Backend Team",
            "id": "emp-test-001",
            "email": "alice@company.com",
            "title": "Engineering Manager",
            "skills": ["Python", "Leadership"],
            "location": "San Francisco",
            "phone": "+1-555-0001",
            "timezone": "America/Los_Angeles",
            "working_hours_start": "09:00",
            "working_hours_end": "17:00",
            "security_clearance": "elevated",
            "employee_type": "full_time",
        },
        {
            "name": "Bob Smith",
            "department": "Engineering",
            "team": "Backend Team",
            "id": "emp-test-002",
            "email": "bob@company.com",
            "title": "Senior Backend Engineer",
            "skills": ["Python", "PostgreSQL"],
            "location": "San Francisco",
            "phone": "+1-555-0002",
            "timezone": "America/Los_Angeles",
            "working_hours_start": "09:00",
            "working_hours_end": "17:00",
            "security_clearance": "basic",
            "employee_type": "full_time",
        },
    ]
