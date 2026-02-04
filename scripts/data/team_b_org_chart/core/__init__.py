"""
Core Package - Organizational Graph Database Interface
"""

from .graphiti_client import (
    EdgeCreationError,
    EntityCreationError,
    EntityNotFoundError,
    GraphitiClient,
    GraphitiClientError,
)
from .models import (
    ActingRole,
    Company,
    CompanyAttributes,
    Department,
    DepartmentAttributes,
    Employee,
    EmployeeAttributes,
    GRAPHITI_EDGES_TYPE_MAP,
    GRAPHITI_EDGE_TYPES,
    GRAPHITI_ENTITIES,
    MemberOf,
    Project,
    ProjectAttributes,
    ReportsTo,
    Team,
    TeamAttributes,
)
from .privacy_queries import PrivacyFirewallQueries

__all__ = [
    # Client
    "GraphitiClient",
    # Privacy Queries
    "PrivacyFirewallQueries",
    # Exceptions
    "GraphitiClientError",
    "EntityNotFoundError",
    "EntityCreationError",
    "EdgeCreationError",
    # Models
    "Company",
    "CompanyAttributes",
    "Employee",
    "EmployeeAttributes",
    "Department",
    "DepartmentAttributes",
    "Team",
    "TeamAttributes",
    "Project",
    "ProjectAttributes",
    "MemberOf",
    "ReportsTo",
    "ActingRole",
    "GRAPHITI_ENTITIES",
    "GRAPHITI_EDGES_TYPE_MAP",
    "GRAPHITI_EDGE_TYPES",
]
