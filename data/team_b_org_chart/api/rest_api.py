"""
FastAPI REST API for AI Privacy Firewall

This module provides REST API endpoints for Team A and Team C integration.
Wraps the core PrivacyFirewallAPI with HTTP endpoints.

Author: Aithel Christo Sunil
Date: November 6, 2025
Team: Team B - Organizational Chart Integration
"""

import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from api.privacy_api import get_employee_context, check_access, PrivacyFirewallAPI
from logs.audit_logger import get_audit_logger, AuditDecision

logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title="AI Privacy Firewall API",
    description="Team B - Organizational Chart Integration REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AccessCheckRequest(BaseModel):
    """Request model for access control check"""
    employee_email: EmailStr = Field(..., description="Employee email address")
    resource_id: str = Field(..., min_length=1, max_length=200, description="Resource identifier")
    classification: str = Field(..., description="Resource classification level")
    
    class Config:
        schema_extra = {
            "example": {
                "employee_email": "john.doe@techflow.com",
                "resource_id": "RES-001",
                "classification": "confidential"
            }
        }


class AccessCheckResponse(BaseModel):
    """Response model for access control check"""
    access_granted: bool = Field(..., description="Whether access is granted")
    reason: str = Field(..., description="Human-readable reason for decision")
    policy_matched: Optional[str] = Field(None, description="Policy that was applied")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")
    employee_context: Optional[Dict[str, Any]] = Field(None, description="Employee organizational context")


class EmployeeContextResponse(BaseModel):
    """Response model for employee organizational context"""
    employee_id: str
    name: str
    email: str
    title: str
    department: Optional[str]
    team: Optional[str]
    security_clearance: str
    employment_type: str
    hierarchy_level: Optional[int]
    is_manager: bool
    is_executive: bool
    is_ceo: bool
    reports_to: Optional[Dict[str, str]]
    direct_reports: List[Dict[str, str]]
    projects: List[Dict[str, str]]
    working_hours: Dict[str, str]
    location: str
    phone: str
    is_active: bool
    contract_end_date: Optional[str]


class AccessibleResource(BaseModel):
    """Model for an accessible resource"""
    resource_id: str
    resource_type: str
    reason: str


class AccessibleResourcesResponse(BaseModel):
    """Response model for accessible resources"""
    employee_email: str
    classification: str
    accessible_resources: List[AccessibleResource]
    total_count: int


class ResourceViewer(BaseModel):
    """Model for a resource viewer"""
    employee_email: str
    name: str
    reason: str
    department: Optional[str]


class ResourceViewersResponse(BaseModel):
    """Response model for resource viewers"""
    resource_id: str
    viewers: List[ResourceViewer]
    total_viewers: int


class AuditLogEntry(BaseModel):
    """Model for audit log entry"""
    timestamp: str
    employee_email: str
    resource_id: str
    decision: str
    reason: str
    policy_matched: Optional[str]
    resource_classification: str
    employee_clearance: str
    additional_context: Optional[Dict[str, Any]]


class AuditTrailResponse(BaseModel):
    """Response model for audit trail"""
    entries: List[AuditLogEntry]
    total_entries: int
    filters_applied: Dict[str, Any]


class AuditStatsResponse(BaseModel):
    """Response model for audit statistics"""
    total_accesses: int
    allowed: int
    denied: int
    errors: int
    success_rate: float
    by_employee: Dict[str, int]
    by_resource: Dict[str, int]
    by_policy: Dict[str, int]
    period: Dict[str, str]


class HealthCheckResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics"""
    employee_context_cache: Dict[str, Any]
    policy_cache: Dict[str, Any]
    relationship_cache: Dict[str, Any]
    total_hits: int
    total_misses: int
    overall_hit_rate: float
    timestamp: str


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post(
    "/api/v1/check-access",
    response_model=AccessCheckResponse,
    summary="Check resource access",
    description="Check if an employee can access a specific resource based on organizational context and policies",
    tags=["Access Control"]
)
async def check_resource_access(request: AccessCheckRequest):
    """
    Check if employee can access a resource
    
    This is the main access control endpoint that Team A will call to determine
    if access should be allowed.
    
    Args:
        request: Access check request with employee email, resource ID, and classification
        
    Returns:
        Access decision with reason, policy matched, and employee context
        
    Raises:
        HTTPException: If request is invalid or internal error occurs
    """
    try:
        logger.info(
            f"Access check request: {request.employee_email} -> {request.resource_id} ({request.classification})"
        )
        
        # Call core privacy API
        result = await check_access(
            employee_email=request.employee_email,
            resource_id=request.resource_id,
            resource_classification=request.classification
        )
        
        # Transform to API response format
        response = AccessCheckResponse(
            access_granted=result.get("access_granted", False),
            reason=result.get("reason", "Unknown reason"),
            policy_matched=result.get("policy_matched"),
            confidence=result.get("confidence"),
            employee_context=result.get("employee_context")
        )
        
        logger.info(
            f"Access check result: {response.access_granted} - {response.reason}"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error in check_resource_access: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post(
    "/api/v1/check-employee-access",
    summary="Check employee-to-employee access",
    description="Check if one employee can access another employee's data (using organizational relationships)",
    tags=["Access Control"]
)
async def check_employee_to_employee_access(
    requester_email: EmailStr = Query(..., description="Employee requesting access"),
    target_email: EmailStr = Query(..., description="Employee whose data is being accessed"),
    resource_type: str = Query(..., description="Type of resource: pto_calendar, salary_info, performance_review, etc.")
):
    """
    Check employee-to-employee access based on organizational relationships
    
    This endpoint uses the actual Neo4j relationships (manager, team, department, project)
    to make access decisions. This will show real ALLOW/DENY decisions!
    
    Args:
        requester_email: Email of employee requesting access
        target_email: Email of employee whose data is being accessed  
        resource_type: Type of resource (pto_calendar, salary_info, code_repository, etc.)
        
    Returns:
        Access decision with detailed relationship context
        
    Example:
        POST /api/v1/check-employee-access?requester_email=priya.patel@techflow.com&target_email=emily.zhang@techflow.com&resource_type=pto_calendar
    """
    try:
        logger.info(f"Employee access check: {requester_email} -> {target_email} ({resource_type})")
        
        # Get employee contexts
        requester = await get_employee_context(requester_email)
        target = await get_employee_context(target_email)
        
        if not requester:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requester not found: {requester_email}"
            )
        
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target employee not found: {target_email}"
            )
        
        # Use the working employee-to-employee access check
        api = PrivacyFirewallAPI()
        result = await api.check_access_permission(
            requester_id=requester["employee_id"],
            target_id=target["employee_id"],
            resource_type=resource_type
        )
        
        logger.info(f"Access decision: {result['allowed']} - {result['reason']}")
        
        return {
            "access_granted": result["allowed"],
            "reason": result["reason"],
            "relationship_context": result.get("context", {}),
            "requester": {
                "email": requester_email,
                "name": requester["name"],
                "title": requester["title"],
                "department": requester.get("department"),
                "is_manager": requester.get("is_manager", False)
            },
            "target": {
                "email": target_email,
                "name": target["name"],
                "title": target["title"],
                "department": target.get("department")
            },
            "resource_type": resource_type,
            "timestamp": result.get("timestamp")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in check_employee_to_employee_access: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/api/v1/employee-context/{email}",
    response_model=EmployeeContextResponse,
    summary="Get employee context",
    description="Get complete organizational context for an employee including department, team, reports, projects",
    tags=["Employee Context"]
)
async def get_employee_context_endpoint(email: str):
    """
    Get organizational context for employee
    
    Returns complete employee information including:
    - Basic info (name, title, email)
    - Department and team
    - Security clearance
    - Manager and direct reports
    - Projects
    - Working hours and location
    
    Args:
        email: Employee email address
        
    Returns:
        Complete employee organizational context
        
    Raises:
        HTTPException: If employee not found or error occurs
    """
    try:
        logger.info(f"Employee context request: {email}")
        
        # Call core privacy API
        context = await get_employee_context(email)
        
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee not found: {email}"
            )
        
        # Transform to API response format
        response = EmployeeContextResponse(**context)
        
        logger.info(f"Employee context retrieved: {context['name']} ({context['title']})")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_employee_context_endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/api/v1/accessible-resources/{email}",
    response_model=AccessibleResourcesResponse,
    summary="Get accessible resources",
    description="Get list of resources accessible to an employee at a given classification level",
    tags=["Access Control"]
)
async def get_accessible_resources(
    email: str,
    classification: Optional[str] = Query(None, description="Resource classification filter")
):
    """
    Get resources accessible to employee
    
    This endpoint returns a list of resources that the employee can access,
    optionally filtered by classification level.
    
    Args:
        email: Employee email address
        classification: Optional classification filter (public, internal, confidential, top_secret)
        
    Returns:
        List of accessible resources with reasons
        
    Raises:
        HTTPException: If employee not found or error occurs
    """
    try:
        logger.info(f"Accessible resources request: {email}, classification={classification}")
        
        # Get employee context first
        employee = await get_employee_context(email)
        
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee not found: {email}"
            )
        
        # TODO: Implement actual resource listing
        # For now, return placeholder based on employee context
        accessible_resources = []
        
        # Add department resources
        if employee.get("department"):
            accessible_resources.append(
                AccessibleResource(
                    resource_id=f"RES-{employee['department']}-DOCS",
                    resource_type="department_docs",
                    reason=f"Department member: {employee['department']}"
                )
            )
        
        # Add team resources
        if employee.get("team"):
            accessible_resources.append(
                AccessibleResource(
                    resource_id=f"RES-{employee['team']}-TEAM",
                    resource_type="team_calendar",
                    reason=f"Team member: {employee['team']}"
                )
            )
        
        # Add project resources
        for project in employee.get("projects", []):
            accessible_resources.append(
                AccessibleResource(
                    resource_id=f"RES-{project['project_id']}",
                    resource_type="project_docs",
                    reason=f"Project team member: {project['name']}"
                )
            )
        
        response = AccessibleResourcesResponse(
            employee_email=email,
            classification=classification or "all",
            accessible_resources=accessible_resources,
            total_count=len(accessible_resources)
        )
        
        logger.info(f"Found {len(accessible_resources)} accessible resources for {email}")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_accessible_resources: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/api/v1/resource-viewers/{resource_id}",
    response_model=ResourceViewersResponse,
    summary="Get resource viewers",
    description="Get list of employees who can access a specific resource",
    tags=["Access Control"]
)
async def get_resource_viewers(resource_id: str):
    """
    Get employees who can access a resource
    
    This endpoint returns a list of employees who have permission to access
    the specified resource.
    
    Args:
        resource_id: Resource identifier
        
    Returns:
        List of employees who can access the resource
        
    Raises:
        HTTPException: If resource not found or error occurs
    """
    try:
        logger.info(f"Resource viewers request: {resource_id}")
        
        # TODO: Implement actual viewer listing
        # For now, return placeholder
        viewers = []
        
        response = ResourceViewersResponse(
            resource_id=resource_id,
            viewers=viewers,
            total_viewers=len(viewers)
        )
        
        logger.info(f"Found {len(viewers)} viewers for resource {resource_id}")
        
        return response
    
    except Exception as e:
        logger.error(f"Error in get_resource_viewers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/api/v1/audit-trail",
    response_model=AuditTrailResponse,
    summary="Get audit trail",
    description="Query audit logs with optional filters for employee, resource, decision, and date range",
    tags=["Audit"]
)
async def get_audit_trail_endpoint(
    employee_email: Optional[str] = Query(None, description="Filter by employee email"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    decision: Optional[str] = Query(None, description="Filter by decision (ALLOW, DENY, ERROR)"),
    start_date: Optional[date] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of entries to return")
):
    """
    Get audit trail with filters
    
    Query audit logs for access control decisions. Supports filtering by:
    - Employee email
    - Resource ID
    - Decision type (ALLOW, DENY, ERROR)
    - Date range
    
    Args:
        employee_email: Optional employee email filter
        resource_id: Optional resource ID filter
        decision: Optional decision filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        limit: Maximum entries to return (default 100, max 1000)
        
    Returns:
        Filtered audit log entries
    """
    try:
        logger.info(
            f"Audit trail request: employee={employee_email}, resource={resource_id}, "
            f"decision={decision}, start={start_date}, end={end_date}, limit={limit}"
        )
        
        audit_logger = get_audit_logger()
        
        # Convert decision string to enum if provided
        decision_enum = None
        if decision:
            try:
                decision_enum = AuditDecision[decision.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid decision value. Must be one of: ALLOW, DENY, ERROR"
                )
        
        # Query audit trail
        entries = audit_logger.get_audit_trail(
            employee_email=employee_email,
            resource_id=resource_id,
            decision=decision_enum,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Transform to API response format
        api_entries = [
            AuditLogEntry(
                timestamp=entry.timestamp.isoformat(),
                employee_email=entry.employee_email,
                resource_id=entry.resource_id,
                decision=entry.decision.value,
                reason=entry.reason,
                policy_matched=entry.policy_matched,
                resource_classification=entry.resource_classification,
                employee_clearance=entry.employee_clearance,
                additional_context=entry.additional_context
            )
            for entry in entries
        ]
        
        # Build filters_applied dict
        filters_applied = {"limit": limit}
        if employee_email:
            filters_applied["employee_email"] = employee_email
        if resource_id:
            filters_applied["resource_id"] = resource_id
        if decision:
            filters_applied["decision"] = decision
        if start_date:
            filters_applied["start_date"] = start_date.isoformat()
        if end_date:
            filters_applied["end_date"] = end_date.isoformat()
        
        response = AuditTrailResponse(
            entries=api_entries,
            total_entries=len(api_entries),
            filters_applied=filters_applied
        )
        
        logger.info(f"Retrieved {len(api_entries)} audit trail entries")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_audit_trail_endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/api/v1/audit-stats",
    response_model=AuditStatsResponse,
    summary="Get audit statistics",
    description="Get aggregated statistics from audit logs for a date range",
    tags=["Audit"]
)
async def get_audit_stats_endpoint(
    start_date: Optional[date] = Query(None, description="Start date for statistics (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date for statistics (YYYY-MM-DD)")
):
    """
    Get audit statistics
    
    Returns aggregated statistics including:
    - Total access attempts
    - Allowed/denied/error counts
    - Success rate
    - Breakdowns by employee, resource, and policy
    
    Args:
        start_date: Optional start date (defaults to today)
        end_date: Optional end date (defaults to today)
        
    Returns:
        Aggregated audit statistics
    """
    try:
        logger.info(f"Audit stats request: start={start_date}, end={end_date}")
        
        # Default to today if no dates provided
        if not start_date:
            start_date = datetime.now().date()
        if not end_date:
            end_date = datetime.now().date()
        
        audit_logger = get_audit_logger()
        
        # Get statistics
        stats = audit_logger.get_stats(
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate success rate
        total = stats.get("total_accesses", 0)
        allowed = stats.get("allowed", 0)
        success_rate = (allowed / total * 100.0) if total > 0 else 0.0
        
        response = AuditStatsResponse(
            total_accesses=stats.get("total_accesses", 0),
            allowed=stats.get("allowed", 0),
            denied=stats.get("denied", 0),
            errors=stats.get("errors", 0),
            success_rate=round(success_rate, 2),
            by_employee=stats.get("by_employee", {}),
            by_resource=stats.get("by_resource", {}),
            by_policy=stats.get("by_policy", {}),
            period={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )
        
        logger.info(
            f"Audit stats: {response.total_accesses} total, "
            f"{response.allowed} allowed, {response.denied} denied"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error in get_audit_stats_endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get(
    "/api/v1/health",
    response_model=HealthCheckResponse,
    summary="Health check",
    description="Check API health and service status",
    tags=["System"]
)
async def health_check():
    """
    Health check endpoint
    
    Returns the health status of the API and its dependencies.
    
    Returns:
        Health status with service checks
    """
    try:
        # Check services
        services = {
            "audit_logger": "operational"
        }
        
        # TODO: Add Neo4j connection check
        # try:
        #     # Test Neo4j connection
        #     services["neo4j"] = "connected"
        # except:
        #     services["neo4j"] = "disconnected"
        
        response = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            timestamp=datetime.now().isoformat(),
            services=services
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error in health_check: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


@app.get(
    "/api/v1/cache-stats",
    response_model=CacheStatsResponse,
    summary="Cache statistics",
    description="Get cache performance metrics and hit rates",
    tags=["System"]
)
async def get_cache_stats():
    """
    Get cache statistics
    
    Returns cache performance metrics including hit rates for employee context,
    policy results, and relationship caches.
    
    Returns:
        Cache statistics with hit rates and cache sizes
    """
    try:
        # Import cache singleton
        from core.cache import get_cache
        
        # Get cache instance (singleton)
        cache = get_cache()
        stats = cache.stats()
        
        # Calculate totals across all caches
        total_hits = (
            stats["employee_context"]["hits"] +
            stats["policy_results"]["hits"] +
            stats["relationships"]["hits"]
        )
        total_misses = (
            stats["employee_context"]["misses"] +
            stats["policy_results"]["misses"] +
            stats["relationships"]["misses"]
        )
        
        overall_hit_rate = (
            total_hits / (total_hits + total_misses) 
            if (total_hits + total_misses) > 0 
            else 0.0
        )
        
        response = CacheStatsResponse(
            employee_context_cache=stats["employee_context"],
            policy_cache=stats["policy_results"],
            relationship_cache=stats["relationships"],
            total_hits=total_hits,
            total_misses=total_misses,
            overall_hit_rate=round(overall_hit_rate, 4),
            timestamp=datetime.now().isoformat()
        )
        
        logger.info(
            f"Cache stats: {total_hits} hits, {total_misses} misses, "
            f"{response.overall_hit_rate:.2%} hit rate"
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error in get_cache_stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


# ============================================================================
# STARTUP/SHUTDOWN HANDLERS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("AI Privacy Firewall API starting up...")
    logger.info("API documentation available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("AI Privacy Firewall API shutting down...")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "status_code": 500
    }
