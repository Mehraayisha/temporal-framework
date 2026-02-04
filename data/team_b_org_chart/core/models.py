"""
Data Models for Organizational Graph

Pydantic models for Employee, Department, Team, and Projects with validation.
Enhanced from LLM Data team's models with additional temporal fields.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# COMPANY MODEL
# ============================================================================


class CompanyAttributes(BaseModel):
    """Attributes stored on Company node"""

    founded: str = Field(..., description="Company founding date (ISO format)")
    headquarters: str = Field(..., description="Company headquarters location")
    employee_count: int = Field(..., description="Total number of employees")
    description: str = Field(..., description="Company description")


class Company(CompanyAttributes):
    """Complete Company model"""

    name: str = Field(..., description="Company name")

    def attributes(self) -> dict:
        """Return attributes dict for node creation (excludes name)"""
        return self.model_dump(exclude={"name"})


# ============================================================================
# EMPLOYEE MODELS
# ============================================================================


class EmployeeAttributes(BaseModel):
    """Attributes stored on Employee node (excluding name which is node property)"""

    id: str = Field(..., description="Unique identifier for the employee")
    email: str = Field(..., description="Email address of the employee")
    title: str = Field(..., description="Job title of the employee")
    skills: list[str] = Field(
        default_factory=list, description="List of skills the employee possesses"
    )
    location: str = Field(..., description="Physical location of the employee")
    phone: str = Field(..., description="Phone number of the employee")

    # Temporal fields
    timezone: str = Field(
        default="America/Los_Angeles", description="Employee's timezone"
    )
    working_hours_start: str = Field(
        default="09:00",
        description="Working day start time (HH:MM format)",
    )
    working_hours_end: str = Field(
        default="17:00",
        description="Working day end time (HH:MM format)",
    )
    security_clearance: str = Field(
        default="basic", description="Security clearance level"
    )
    employee_type: str = Field(
        default="full_time",
        description="Employee type: full_time, contractor, intern, part_time",
    )

    # Optional temporal fields
    contract_end_date: Optional[str] = Field(
        None, description="Contract end date for contractors/interns (ISO format YYYY-MM-DD)"
    )
    contract_expired: Optional[bool] = Field(
        None, description="Whether the contract has expired (calculated field)"
    )
    start_date: Optional[str] = Field(
        None, description="Employee start date (ISO format)"
    )
    
    # Acting role fields
    acting_role: Optional[bool] = Field(
        None, description="Whether employee has an acting role"
    )
    acting_role_target: Optional[str] = Field(
        None, description="Target position for acting role"
    )
    acting_role_start: Optional[str] = Field(
        None, description="Acting role start date (ISO format YYYY-MM-DD)"
    )
    acting_role_valid_until: Optional[str] = Field(
        None, description="Acting role expiration date (ISO format YYYY-MM-DD)"
    )

    @field_validator("security_clearance")
    @classmethod
    def validate_clearance(cls, v):
        valid_clearances = ["basic", "standard", "elevated", "restricted", "top_secret", "executive"]
        if v not in valid_clearances:
            raise ValueError(f"Invalid security clearance: {v}")
        return v

    @field_validator("employee_type")
    @classmethod
    def validate_employee_type(cls, v):
        valid_types = ["full_time", "contractor", "intern", "part_time"]
        if v not in valid_types:
            raise ValueError(f"Invalid employee type: {v}")
        return v


class Employee(EmployeeAttributes):
    """Complete Employee model including relationships"""

    name: str = Field(..., description="Full name of the employee")
    department: str = Field(..., description="Department the employee belongs to")
    team: str = Field(..., description="Team the employee belongs to")

    # Optional acting roles
    acting_roles: list[dict] = Field(
        default_factory=list,
        description="Temporary acting roles with start/end dates",
    )

    # Optional on-call status
    on_call_schedule: Optional[dict] = Field(
        None, description="On-call rotation schedule"
    )

    def attributes(self) -> dict:
        """Return attributes dict for node creation (excludes name, department, team)"""
        return self.model_dump(
            exclude={"name", "department", "team", "acting_roles", "on_call_schedule"}
        )


# ============================================================================
# DEPARTMENT MODELS
# ============================================================================


class DepartmentAttributes(BaseModel):
    """Attributes stored on Department node"""

    id: str = Field(..., description="Unique identifier for the department")
    description: str = Field(..., description="Description of the department")
    budget: float = Field(..., description="Budget allocated to the department")
    head_count: int = Field(
        ..., description="Number of employees in the department"
    )
    data_classification: str = Field(
        default="internal", description="Default data classification level"
    )


class Department(DepartmentAttributes):
    """Complete Department model"""

    name: str = Field(..., description="Name of the department")

    def attributes(self) -> dict:
        """Return attributes dict for node creation (excludes name)"""
        return self.model_dump(exclude={"name"})


# ============================================================================
# TEAM MODELS
# ============================================================================


class TeamAttributes(BaseModel):
    """Attributes stored on Team node"""

    id: str = Field(..., description="Unique identifier for the team")
    lead: str = Field(..., description="Name of team lead")
    purpose: str = Field(..., description="Purpose/mission of the team")
    data_classification: str = Field(
        default="internal", description="Team's data classification level"
    )


class Team(TeamAttributes):
    """Complete Team model"""

    name: str = Field(..., description="Name of the team")
    department: str = Field(..., description="Department the team belongs to")

    def attributes(self) -> dict:
        """Return attributes dict for node creation (excludes name, department)"""
        return self.model_dump(exclude={"name", "department"})


# ============================================================================
# PROJECT MODELS
# ============================================================================


class ProjectAttributes(BaseModel):
    """Attributes stored on Project node"""

    id: str = Field(..., description="Unique identifier for the project")
    description: str = Field(..., description="Project description")
    status: str = Field(..., description="Project status: active, completed, on_hold")
    start_date: str = Field(..., description="Project start date (ISO format)")
    end_date: Optional[str] = Field(
        None, description="Project end date (ISO format)"
    )
    data_classification: str = Field(
        default="confidential", description="Project data classification"
    )


class Project(ProjectAttributes):
    """Complete Project model"""

    name: str = Field(..., description="Project name")
    departments: list[str] = Field(
        default_factory=list, description="Departments involved"
    )
    teams: list[str] = Field(default_factory=list, description="Teams involved")
    members: list[str] = Field(default_factory=list, description="Team member names")

    def attributes(self) -> dict:
        """Return attributes dict for node creation"""
        return self.model_dump(
            exclude={"name", "departments", "teams", "members"}
        )


# ============================================================================
# ENTITY TYPE REGISTRY
# ============================================================================

GRAPHITI_ENTITIES = {
    "Company": CompanyAttributes,
    "Employee": EmployeeAttributes,
    "Department": DepartmentAttributes,
    "Team": TeamAttributes,
    "Project": ProjectAttributes,
}


# ============================================================================
# EDGE TYPE DEFINITIONS
# ============================================================================

GRAPHITI_EDGES_TYPE_MAP = {
    ("Company", "Department"): ["HAS_DEPARTMENT"],
    ("Department", "Team"): ["HAS_TEAM"],
    ("Employee", "Employee"): ["REPORTS_TO", "MANAGES", "COLLABORATES_WITH"],
    ("Employee", "Department"): ["MEMBER_OF"],
    ("Employee", "Team"): ["MEMBER_OF"],
    ("Employee", "Project"): ["ASSIGNED_TO"],
    ("Manager", "Team"): ["MANAGES"],
}


# Edge attribute models (for future use with rich edge properties)
class MemberOf(BaseModel):
    """Attributes for MEMBER_OF relationship"""

    since: Optional[str] = Field(None, description="Membership start date")
    role: Optional[str] = Field(None, description="Role in team/department")


class ReportsTo(BaseModel):
    """Attributes for REPORTS_TO relationship"""

    since: Optional[str] = Field(None, description="Reporting relationship start date")
    reporting_percentage: Optional[int] = Field(
        100, description="Percentage of time reporting to this manager"
    )


class ActingRole(BaseModel):
    """Attributes for temporary ACTING_AS relationship"""

    role: str = Field(..., description="Acting role title")
    start_date: str = Field(..., description="Acting role start date (ISO format)")
    end_date: str = Field(..., description="Acting role end date (ISO format)")
    temporary_clearance: Optional[str] = Field(
        None, description="Temporary elevated clearance"
    )


GRAPHITI_EDGE_TYPES = {
    "MEMBER_OF": MemberOf,
    "REPORTS_TO": ReportsTo,
    "ACTING_AS": ActingRole,
}
