"""
Team B Graphiti API Integration - Configuration & Client
========================================================

This module defines the Graphiti API endpoints, authentication, and request/response
schemas needed to integrate with Team B's organizational graph service.

STEP 1: Graphiti API Configuration & Client

Required from Team B:
- Base URL (staging + production)
- Auth token / service identity headers
- Endpoint specifications (request/response schemas)
- Rate limits & timeout expectations
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import os
from datetime import datetime, timedelta

# Helper to parse ISO8601 with optional 'Z' suffix
def _parse_iso(dt_str: str) -> datetime:
    try:
        if dt_str is None:
            return datetime.utcnow()
        # Accept 'Z' suffix by converting to '+00:00'
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        # Fallback to now if parsing fails
        return datetime.utcnow()

# ============================================================================
# CONFIG SECTION - Update with Team B's actual API details
# ============================================================================

class GraphitiEnvironment(str, Enum):
    """Graphiti deployment environments"""
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class GraphitiConfig:
    """Configuration for Graphiti API integration"""
    
    # ---- ENDPOINTS ----
    # Base URL for Graphiti (Team B provides this)
    base_url: str = os.environ.get("GRAPHITI_BASE_URL", "https://graphiti-staging.internal.example.com")
    environment: GraphitiEnvironment = GraphitiEnvironment.STAGING
    
    # ---- AUTHENTICATION ----
    # Auth token (from Team B - service account or API key)
    auth_token: str = os.environ.get("GRAPHITI_AUTH_TOKEN", "")
    service_identity: str = os.environ.get("GRAPHITI_SERVICE_ID", "temporal-engine")
    
    # ---- TIMEOUTS & RATE LIMITS ----
    # Timeout (seconds) for API calls
    request_timeout: int = 10
    
    # Rate limit: max requests per minute
    max_requests_per_minute: int = 100
    
    # Backoff strategy for retries
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    
    # ---- ENDPOINT PATHS (relative to base_url) ----
    relationship_reporting_path: str = "/v1/relationship/reporting"
    relationship_department_path: str = "/v1/relationship/department"
    relationship_projects_path: str = "/v1/relationship/projects"
    roles_temporal_path: str = "/v1/roles/temporal"
    
    @property
    def api_url(self) -> str:
        """Full API URL"""
        return self.base_url.rstrip("/")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Standard headers for all Graphiti requests"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "X-Service-ID": self.service_identity,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "TemporalEngine/1.0"
        }


# ============================================================================
# REQUEST SCHEMAS - What we send to Graphiti
# ============================================================================

@dataclass
class RelationshipReportingRequest:
    """Query: /relationship/reporting?employee=E&manager=M
    
    Purpose: Get the reporting relationship between two people
    """
    employee_id: str      # ID of the employee
    manager_id: str       # ID of the manager
    include_history: bool = False  # Include historical relationships
    
    def to_query_params(self) -> Dict[str, str]:
        return {
            "employee": self.employee_id,
            "manager": self.manager_id,
            "include_history": "true" if self.include_history else "false"
        }


@dataclass
class RelationshipDepartmentRequest:
    """Query: /relationship/department?sender=S&recipient=R
    
    Purpose: Determine if sender and recipient are in the same department
    """
    sender_id: str        # ID of the sender
    recipient_id: str     # ID of the recipient
    include_parent_depts: bool = True  # Include parent department relationships
    
    def to_query_params(self) -> Dict[str, str]:
        return {
            "sender": self.sender_id,
            "recipient": self.recipient_id,
            "include_parent_depts": "true" if self.include_parent_depts else "false"
        }


@dataclass
class RelationshipProjectsRequest:
    """Query: /relationship/projects?sender=S&recipient=R
    
    Purpose: Find shared projects between sender and recipient
    """
    sender_id: str        # ID of the sender
    recipient_id: str     # ID of the recipient
    project_status: str = "active"  # Filter: active, all, archived
    
    def to_query_params(self) -> Dict[str, str]:
        return {
            "sender": self.sender_id,
            "recipient": self.recipient_id,
            "project_status": self.project_status
        }


@dataclass
class RolesTemporalRequest:
    """Query: /roles/temporal?person_id=P&time=T
    
    Purpose: Get temporary/acting roles for a person at a specific time
    """
    person_id: str                          # ID of the person
    timestamp: Optional[datetime] = None    # Time to check (default: now)
    include_future: bool = False            # Include future scheduled roles
    
    def to_query_params(self) -> Dict[str, str]:
        ts = (self.timestamp or datetime.utcnow()).isoformat()
        return {
            "person_id": self.person_id,
            "time": ts,
            "include_future": "true" if self.include_future else "false"
        }


# ============================================================================
# RESPONSE SCHEMAS - What Graphiti returns to us
# ============================================================================

@dataclass
class RelationshipReportingResponse:
    """Response from /relationship/reporting"""
    is_direct_report: bool           # True if employee reports directly to manager
    relationship_type: str           # "direct", "indirect", "none"
    chain_length: int                # Number of steps in the reporting chain
    department_ids: List[str]        # Department path from employee to manager
    effective_date: datetime         # When relationship became effective
    end_date: Optional[datetime]     # When relationship ended (if applicable)
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "RelationshipReportingResponse":
        """Parse Graphiti JSON response"""
        return cls(
            is_direct_report=data.get("is_direct_report", False),
            relationship_type=data.get("relationship_type", "none"),
            chain_length=data.get("chain_length", -1),
            department_ids=data.get("department_ids", []),
            effective_date=_parse_iso(data.get("effective_date", datetime.utcnow().isoformat())),
            end_date=_parse_iso(data["end_date"]) if data.get("end_date") else None
        )


@dataclass
class RelationshipDepartmentResponse:
    """Response from /relationship/department"""
    same_department: bool           # True if both in same direct department
    same_parent_department: bool    # True if in same parent/org unit
    sender_department: str          # Department ID of sender
    recipient_department: str       # Department ID of recipient
    department_distance: int        # Steps between departments (0 = same, 1 = parent/child, etc.)
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "RelationshipDepartmentResponse":
        """Parse Graphiti JSON response"""
        return cls(
            same_department=data.get("same_department", False),
            same_parent_department=data.get("same_parent_department", False),
            sender_department=data.get("sender_department", ""),
            recipient_department=data.get("recipient_department", ""),
            department_distance=data.get("department_distance", -1)
        )


@dataclass
class RelationshipProjectsResponse:
    """Response from /relationship/projects"""
    shared_projects: List[Dict[str, Any]]  # List of project objects
    project_count: int                      # Number of shared projects
    projects_ids: List[str]                 # IDs of shared projects
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "RelationshipProjectsResponse":
        """Parse Graphiti JSON response"""
        projects = data.get("shared_projects", [])
        return cls(
            shared_projects=projects,
            project_count=len(projects),
            projects_ids=[p.get("id") for p in projects if "id" in p]
        )


@dataclass
class TemporalRole:
    """Represents a temporary/acting role"""
    role_id: str
    role_name: str
    base_role: str                  # The permanent role this is acting on behalf of
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None    # Why the acting role was assigned (e.g., "vacancy fill", "coverage")
    delegation_chain: List[str] = None  # Chain of delegation if delegated
    
    def is_active_at(self, timestamp: Optional[datetime] = None) -> bool:
        """Check if role is active at given timestamp"""
        ts = timestamp or datetime.utcnow()
        return self.start_date <= ts < self.end_date


@dataclass
class RolesTemporalResponse:
    """Response from /roles/temporal"""
    person_id: str
    permanent_roles: List[str]              # Permanent/base roles
    temporary_roles: List[TemporalRole]     # Acting/temporary roles
    active_roles: List[str]                 # Union of active permanent + temporary roles
    query_timestamp: datetime
    
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "RolesTemporalResponse":
        """Parse Graphiti JSON response"""
        temp_roles = [
            TemporalRole(
                role_id=r.get("role_id", ""),
                role_name=r.get("role_name", ""),
                base_role=r.get("base_role", ""),
                start_date=_parse_iso(r.get("start_date", datetime.utcnow().isoformat())),
                end_date=_parse_iso(r.get("end_date", (datetime.utcnow() + timedelta(days=1)).isoformat())),
                reason=r.get("reason"),
                delegation_chain=r.get("delegation_chain", [])
            )
            for r in data.get("temporary_roles", [])
        ]
        
        return cls(
            person_id=data.get("person_id", ""),
            permanent_roles=data.get("permanent_roles", []),
            temporary_roles=temp_roles,
            active_roles=data.get("active_roles", []),
            query_timestamp=_parse_iso(data.get("query_timestamp", datetime.utcnow().isoformat()))
        )


# ============================================================================
# ERROR HANDLING
# ============================================================================

class GraphitiAPIError(Exception):
    """Base exception for Graphiti API errors"""
    pass


class GraphitiConnectionError(GraphitiAPIError):
    """Network/connection error"""
    pass


class GraphitiAuthError(GraphitiAPIError):
    """Authentication/authorization error"""
    pass


class GraphitiRateLimitError(GraphitiAPIError):
    """Rate limit exceeded"""
    pass


class GraphitiNotFoundError(GraphitiAPIError):
    """Resource not found"""
    pass


class GraphitiValidationError(GraphitiAPIError):
    """Request validation error"""
    pass


# ============================================================================
# HTTP STATUS CODE MAPPING
# ============================================================================

HTTP_ERROR_MAP = {
    400: GraphitiValidationError,
    401: GraphitiAuthError,
    403: GraphitiAuthError,
    404: GraphitiNotFoundError,
    429: GraphitiRateLimitError,
    500: GraphitiAPIError,
    502: GraphitiConnectionError,
    503: GraphitiConnectionError,
    504: GraphitiConnectionError,
}


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Example configuration
    config = GraphitiConfig(
        base_url="https://graphiti-staging.internal.example.com",
        auth_token="your-token-here",
        service_identity="temporal-engine"
    )
    
    print(f"Graphiti API Config:")
    print(f"  Base URL: {config.api_url}")
    print(f"  Service ID: {config.service_identity}")
    print(f"  Reporting endpoint: {config.api_url}{config.relationship_reporting_path}")
    print(f"  Department endpoint: {config.api_url}{config.relationship_department_path}")
    print(f"  Projects endpoint: {config.api_url}{config.relationship_projects_path}")
    print(f"  Temporal Roles endpoint: {config.api_url}{config.roles_temporal_path}")
    print(f"\nHeaders: {config.headers}")
