"""
Test Team B FastAPI Integration via HTTP

Tests the enricher's Team B adapter using httpx mock responses.
"""

import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Set Team B mode before importing enricher
os.environ["GRAPHITI_MODE"] = "team_b_api"
os.environ["TEAM_B_API_URL"] = "http://localhost:8000"

from core.enricher import build_temporal_context_from_graphiti


@pytest.fixture
def mock_team_b_response():
    """Mock Team B employee context response"""
    return {
        "employee_id": "EMP-DR-SMITH",
        "name": "Dr. Jane Smith",
        "email": "dr_smith@hospital.com",
        "title": "Attending Physician",
        "department": "Emergency Medicine",
        "team": "Trauma Response",
        "security_clearance": "confidential",
        "employment_type": "full_time",
        "hierarchy_level": 4,
        "is_manager": True,
        "is_executive": False,
        "is_ceo": False,
        "reports_to": {"employee_id": "EMP-001", "name": "Dr. Chief"},
        "direct_reports": [
            {"employee_id": "EMP-002", "name": "Nurse Johnson"}
        ],
        "projects": [
            {"project_id": "PROJ-ER-2024", "name": "ER Modernization"}
        ],
        "working_hours": {
            "timezone": "America/New_York",
            "start": "08:00",
            "end": "18:00"
        },
        "location": "Emergency Department",
        "phone": "+1-555-0123",
        "is_active": True,
        "contract_end_date": None
    }


@pytest.mark.asyncio
async def test_team_b_http_adapter_success(mock_team_b_response):
    """Test successful Team B API call and TemporalContext mapping"""
    
    # Mock httpx AsyncClient
    with patch("httpx.AsyncClient") as mock_client_cls:
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_team_b_response
        mock_response.raise_for_status = MagicMock()
        
        # Setup async context manager
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client
        
        # Call enricher
        timestamp = datetime.now(timezone.utc)
        tc = build_temporal_context_from_graphiti(
            sender_id="dr_smith",
            recipient_id="patient_12345",
            data_type="medical_records",
            timestamp=timestamp
        )
        
        # Verify API was called
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "/api/v1/employee-context/" in call_args[0][0]
        assert "dr_smith" in call_args[0][0]
        
        # Verify TemporalContext mapping
        assert tc.timezone == "America/New_York"
        assert tc.temporal_role == "acting_manager"  # is_manager=True
        assert tc.user_id == "dr_smith"
        assert tc.situation == "NORMAL"
        
        # Check extra fields
        assert hasattr(tc, "data_domain")
        assert tc.data_domain == "Emergency Medicine"
        assert hasattr(tc, "security_clearance")
        assert tc.security_clearance == "confidential"


@pytest.mark.asyncio
async def test_team_b_http_adapter_fallback_on_error():
    """Test fallback to Graphiti when Team B API fails"""
    
    with patch("httpx.AsyncClient") as mock_client_cls:
        # Setup mock to raise connection error
        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client
        
        # Mock Graphiti fallback to return minimal context
        with patch("core.enricher._create_minimal_temporal_context") as mock_minimal:
            from core.tuples import TemporalContext
            mock_minimal.return_value = TemporalContext(
                timestamp=datetime.now(timezone.utc),
                timezone="UTC",
                business_hours=False,
                temporal_role="user",
                situation="INCIDENT"
            )
            
            # Call enricher - should fallback gracefully
            timestamp = datetime.now(timezone.utc)
            tc = build_temporal_context_from_graphiti(
                sender_id="test_user",
                recipient_id="test_recipient",
                data_type="test_data",
                timestamp=timestamp
            )
            
            # Verify fallback was used
            assert tc.situation == "INCIDENT"
            assert tc.timezone == "UTC"


@pytest.mark.asyncio  
async def test_team_b_email_construction():
    """Test email construction from sender_id"""
    
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "employee_id": "EMP-TEST",
            "name": "Test User",
            "email": "test@company.com",
            "title": "Engineer",
            "department": "Engineering",
            "team": "Backend",
            "security_clearance": "internal",
            "employment_type": "full_time",
            "hierarchy_level": 2,
            "is_manager": False,
            "is_executive": False,
            "is_ceo": False,
            "reports_to": None,
            "direct_reports": [],
            "projects": [],
            "working_hours": {"timezone": "UTC"},
            "location": "Office",
            "phone": "",
            "is_active": True,
            "contract_end_date": None
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client
        
        # Test with username (no @)
        timestamp = datetime.now(timezone.utc)
        tc = build_temporal_context_from_graphiti(
            sender_id="john_smith",
            recipient_id="recipient",
            data_type="test_data",
            timestamp=timestamp
        )
        
        # Verify email was constructed
        call_args = mock_client.get.call_args
        assert "john_smith@company.com" in call_args[0][0]
        
        # Reset mock
        mock_client.get.reset_mock()
        
        # Test with full email
        tc = build_temporal_context_from_graphiti(
            sender_id="jane@example.org",
            recipient_id="recipient",
            data_type="test_data",
            timestamp=timestamp
        )
        
        # Verify email was used as-is
        call_args = mock_client.get.call_args
        assert "jane@example.org" in call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
