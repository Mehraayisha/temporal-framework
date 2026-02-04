"""
Privacy Firewall API - Team A Integration Interface

This module provides the main API interface for AI Privacy Firewall integration.
Team A (Temporal Framework) calls these functions to get organizational context
and make access control decisions.

Author: Aithel Christo Sunil
Date: October 25, 2025
Team: Team B - Organizational Chart Integration
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import deal

from core.graphiti_client import GraphitiClient
from core.privacy_queries import PrivacyFirewallQueries
from core.cache import get_cache, PrivacyFirewallCache
from logs.audit_logger import get_audit_logger, AuditDecision

logger = logging.getLogger(__name__)


# ============================================================================
# PRIVACY FIREWALL API - MAIN INTEGRATION INTERFACE
# ============================================================================


class PrivacyFirewallAPI:
    """
    Main API interface for AI Privacy Firewall integration
    
    This is the primary interface that Team A (Temporal Framework) and
    Team C (Ontology) use to query organizational relationships and context.
    
    Key Methods:
    - check_access_permission(): Main access control check
    - get_temporal_context(): Get time-aware organizational context
    - check_organizational_relationship(): Check specific relationships
    
    Performance: All methods <100ms (99th percentile)
    """

    def __init__(self):
        """
        Initialize Privacy Firewall API
        
        Creates GraphitiClient, PrivacyFirewallQueries, and Cache instances
        """
        logger.info("Initializing PrivacyFirewallAPI")
        self.client = GraphitiClient()
        self.cache = get_cache()
        self.queries = PrivacyFirewallQueries(self.client, self.cache)
        logger.info("PrivacyFirewallAPI initialized successfully")

    # ========================================================================
    # MAIN ACCESS CONTROL INTERFACE - RESOURCE-BASED MODEL
    # ========================================================================

    @deal.pre(lambda self, requester_id, resource_owner, resource_classification, resource_type, action:
              isinstance(requester_id, str) and len(requester_id) > 0 and
              isinstance(resource_owner, str) and len(resource_owner) > 0 and
              isinstance(resource_classification, str) and len(resource_classification) > 0 and
              isinstance(resource_type, str) and len(resource_type) > 0)
    @deal.post(lambda result: isinstance(result, dict) and "allowed" in result)
    async def check_resource_access(
        self,
        requester_id: str,
        resource_owner: str,  # Department, team, or employee ID
        resource_classification: str,  # confidential, secret, top_secret, public
        resource_type: str,
        action: str = "read",
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        Check if employee can access a resource (CORRECT ARCHITECTURE)
        
        This is the proper resource-based access control model.
        Instead of "Can David access Sarah?", we ask "Can David access Engineering_Budget.xlsx?"
        
        Args:
            requester_id: Employee requesting access (e.g., "emp-004")
            resource_owner: Who owns the resource (e.g., "Engineering", "Backend Engineering Team", or "emp-001")
            resource_classification: Classification level
                - "public": Anyone can access
                - "internal": Requires company membership
                - "confidential": Requires department/team membership
                - "restricted": Requires manager approval
                - "secret": Requires elevated clearance
                - "top_secret": CEO/executive only
            resource_type: Type of resource
                - "document": General document
                - "financial_report": Financial data
                - "source_code": Code repository
                - "database": Database access
                - "api_endpoint": API access
                - "customer_data": Customer PII
            action: What action (read, write, delete, execute)
            timestamp: When access is requested
            
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "context": {
                    "requester_hierarchy_level": int,
                    "resource_owner_hierarchy_level": int,
                    "hierarchy_relationship": str,  # downward, lateral, upward
                    "requester_clearance": str,
                    "required_clearance": str,
                    "same_department": bool,
                    "same_team": bool,
                    "temporal_valid": bool
                },
                "timestamp": str
            }
            
        Examples:
            >>> # Engineer accessing Engineering department document
            >>> await api.check_resource_access(
            ...     requester_id="emp-005",  # Alice Cooper (Engineer)
            ...     resource_owner="Engineering",
            ...     resource_classification="confidential",
            ...     resource_type="document",
            ...     action="read"
            ... )
            {
                "allowed": True,
                "reason": "Access granted - same department, sufficient clearance",
                ...
            }
            
            >>> # Engineer trying to access CEO's top_secret financial report
            >>> await api.check_resource_access(
            ...     requester_id="emp-005",  # Alice Cooper (Engineer)
            ...     resource_owner="emp-001",  # Sarah Chen (CEO)
            ...     resource_classification="top_secret",
            ...     resource_type="financial_report",
            ...     action="read"
            ... )
            {
                "allowed": False,
                "reason": "Access denied - insufficient clearance (standard < top_secret)",
                ...
            }
        """
        from core.policy_engine_v2 import PolicyEngine
        
        logger.info(
            f"Resource access check: {requester_id} -> {resource_owner}/{resource_type} ({resource_classification})",
            extra={
                "requester_id": requester_id,
                "resource_owner": resource_owner,
                "resource_classification": resource_classification,
                "resource_type": resource_type,
                "action": action
            }
        )

        try:
            # Initialize policy engine with resource-based evaluation
            policy_engine = PolicyEngine(self.queries, policy_config_path="config/resource_policies.yaml")
            
            # Evaluate access using policy engine
            result = await policy_engine.evaluate_resource_access(
                requester_id=requester_id,
                resource_owner=resource_owner,
                resource_classification=resource_classification,
                resource_type=resource_type,
                action=action,
                timestamp=timestamp
            )
            
            # Build response
            allowed = result.decision.value == "ALLOW"
            response = {
                "allowed": allowed,
                "reason": result.reason,
                "confidence": result.confidence,
                "context": result.factors,
                "policies_applied": result.policy_rules_applied,
                "timestamp": (timestamp or datetime.now()).isoformat(),
                "response_time_ms": result.response_time_ms
            }
            
            # Audit logging
            audit_logger = get_audit_logger()
            audit_logger.log_access(
                employee_email=requester_id,
                resource_id=f"{resource_owner}/{resource_type}",
                decision=AuditDecision.ALLOW if allowed else AuditDecision.DENY,
                reason=result.reason,
                policy_matched=",".join(result.policy_rules_applied) if result.policy_rules_applied else "none",
                resource_classification=resource_classification,
                employee_clearance=result.factors.get("requester_clearance", "unknown"),
                additional_context={
                    "resource_owner": resource_owner,
                    "resource_type": resource_type,
                    "action": action,
                    "confidence": result.confidence,
                    "response_time_ms": result.response_time_ms,
                    "factors": result.factors
                }
            )
            
            return response

        except Exception as e:
            logger.error(
                f"Error in resource access check: {e}",
                exc_info=True,
                extra={
                    "requester_id": requester_id,
                    "resource_owner": resource_owner,
                    "resource_classification": resource_classification
                }
            )
            
            # Audit logging for error case
            audit_logger = get_audit_logger()
            audit_logger.log_access(
                employee_email=requester_id,
                resource_id=f"{resource_owner}/{resource_type}",
                decision=AuditDecision.ERROR,
                reason=f"Access check failed: {str(e)}",
                policy_matched="error",
                resource_classification=resource_classification,
                employee_clearance="unknown",
                additional_context={
                    "resource_owner": resource_owner,
                    "resource_type": resource_type,
                    "action": action,
                    "error": str(e)
                }
            )
            
            # Fail closed
            return {
                "allowed": False,
                "reason": f"Access check failed: {str(e)}",
                "context": {},
                "timestamp": (timestamp or datetime.now()).isoformat(),
                "error": str(e)
            }

    # ========================================================================
    # LEGACY INTERFACE - EMPLOYEE-TO-EMPLOYEE (DEPRECATED)
    # ========================================================================

    @deal.pre(lambda self, requester_id, target_id, resource_type: 
              isinstance(requester_id, str) and len(requester_id) > 0 and
              isinstance(target_id, str) and len(target_id) > 0 and
              isinstance(resource_type, str) and len(resource_type) > 0)
    @deal.post(lambda result: isinstance(result, dict) and "allowed" in result)
    async def check_access_permission(
        self,
        requester_id: str,
        target_id: str,
        resource_type: str,
        timestamp: Optional[datetime] = None
    ) -> Dict:
        """
        Main access permission check for Privacy Firewall
        
        This is the PRIMARY method Team A calls to determine if access should be allowed.
        
        Args:
            requester_id: Employee ID requesting access (e.g., "emp-004")
            target_id: Employee ID whose data is being accessed (e.g., "emp-005")
            resource_type: Type of resource being accessed
                - "pto_calendar": PTO/vacation calendar
                - "salary_info": Salary and compensation data
                - "performance_review": Performance review documents
                - "code_repository": Source code access
                - "project_docs": Project documentation
                - "department_docs": Department-level documents
                - "team_calendar": Team calendar and schedules
                - "financial_reports": Financial data
            timestamp: When access is requested (for temporal validation)
            
        Returns:
            {
                "allowed": bool,  # Whether access is granted
                "reason": str,    # Human-readable reason for decision
                "context": {
                    "relationship": str,  # Type of relationship (manager, report, peer, none)
                    "department_match": bool,
                    "team_match": bool,
                    "project_shared": bool,
                    "manager_relationship": bool,
                    "hierarchy_level": int  # 0=none, 1=direct, 2=skip-level, etc.
                },
                "timestamp": str  # ISO timestamp of decision
            }
            
        Examples:
            >>> # Manager accessing team member's PTO calendar
            >>> await api.check_access_permission(
            ...     requester_id="emp-004",  # Marcus Johnson (Manager)
            ...     target_id="emp-005",      # Alice Cooper (Engineer)
            ...     resource_type="pto_calendar"
            ... )
            {
                "allowed": True,
                "reason": "Access granted - direct manager relationship",
                "context": {...}
            }
            
            >>> # Contractor attempting financial data access
            >>> await api.check_access_permission(
            ...     requester_id="emp-039",  # Lisa Kumar (Contractor)
            ...     target_id="emp-031",      # Robert Lee (Finance)
            ...     resource_type="financial_reports"
            ... )
            {
                "allowed": False,
                "reason": "Access denied - no organizational relationship",
                "context": {...}
            }
        """
        logger.info(
            f"Access check: {requester_id} -> {target_id} ({resource_type})",
            extra={
                "requester_id": requester_id,
                "target_id": target_id,
                "resource_type": resource_type
            }
        )

        # Check cache first
        cached_result = self.cache.get_policy_result(
            requester_id, target_id, resource_type, "unknown"
        )
        if cached_result is not None:
            logger.debug(f"Cache HIT for access permission: {requester_id} -> {target_id}")
            return cached_result

        logger.debug(f"Cache MISS for access permission: {requester_id} -> {target_id}")

        # Initialize context
        context = {
            "relationship": "none",
            "department_match": False,
            "team_match": False,
            "project_shared": False,
            "manager_relationship": False,
            "hierarchy_level": 0
        }

        try:
            # Check 1: Direct reporting relationship (bidirectional)
            is_manager_of = await self.queries.check_direct_report(target_id, requester_id)
            is_report_of = await self.queries.check_direct_report(requester_id, target_id)

            if is_manager_of:
                context["relationship"] = "manager"
                context["manager_relationship"] = True
                context["hierarchy_level"] = 1
            elif is_report_of:
                context["relationship"] = "report"
                context["manager_relationship"] = True
                context["hierarchy_level"] = -1  # Negative = subordinate

            # Check 2: Manager hierarchy (skip-level)
            if not context["manager_relationship"]:
                is_in_chain, levels = await self.queries.check_manager_hierarchy(
                    target_id, requester_id
                )
                if is_in_chain:
                    context["relationship"] = f"skip_level_manager_{levels}"
                    context["manager_relationship"] = True
                    context["hierarchy_level"] = levels

            # Check 3: Same team
            same_team = await self.queries.check_same_team(requester_id, target_id)
            if same_team:
                context["team_match"] = True
                if context["relationship"] == "none":
                    context["relationship"] = "teammate"

            # Check 4: Same department
            dept_info = await self.queries.check_same_department(requester_id, target_id)
            if dept_info:
                context["department_match"] = True
                context["department_name"] = dept_info["department"]
                context["data_classification"] = dept_info["data_classification"]
                if context["relationship"] == "none":
                    context["relationship"] = "department_peer"

            # Check 5: Shared projects
            projects = await self.queries.check_shared_project(requester_id, target_id)
            if projects:
                context["project_shared"] = True
                context["shared_projects"] = [p["project"] for p in projects]
                if context["relationship"] == "none":
                    context["relationship"] = "project_collaborator"

            # ================================================================
            # DECISION LOGIC - Apply access rules based on resource type
            # ================================================================

            allowed = False
            reason = "Access denied - no organizational relationship"

            # RULE 1: Manager can access team member data
            if context["manager_relationship"] and context["hierarchy_level"] > 0:
                allowed = True
                reason = f"Access granted - {context['relationship']} relationship"

            # RULE 2: Project members can access shared project resources
            elif context["project_shared"] and resource_type in [
                "project_docs", "code_repository", "team_calendar"
            ]:
                allowed = True
                project_list = ", ".join(context["shared_projects"][:2])
                reason = f"Access granted - shared project: {project_list}"

            # RULE 3: Same team can access team-level resources
            elif context["team_match"] and resource_type in [
                "team_calendar", "code_repository"
            ]:
                allowed = True
                reason = "Access granted - same team, appropriate resource type"

            # RULE 4: Same department can access department-level resources
            elif context["department_match"] and resource_type in [
                "department_docs", "team_calendar"
            ]:
                allowed = True
                reason = f"Access granted - same department ({context['department_name']})"

            # RULE 5: Sensitive resources require direct relationship
            if resource_type in ["salary_info", "performance_review", "financial_reports"]:
                # Override previous decision for sensitive data
                if not context["manager_relationship"]:
                    allowed = False
                    reason = "Access denied - sensitive resource requires direct manager relationship"

            # RULE 6: Self-access is always allowed
            if requester_id == target_id:
                allowed = True
                reason = "Access granted - self-access"
                context["relationship"] = "self"

            # ================================================================
            # BUILD RESPONSE
            # ================================================================

            response = {
                "allowed": allowed,
                "reason": reason,
                "context": context,
                "timestamp": (timestamp or datetime.now()).isoformat(),
                "resource_type": resource_type
            }

            logger.info(
                f"Access decision: {'ALLOWED' if allowed else 'DENIED'}",
                extra={
                    "requester_id": requester_id,
                    "target_id": target_id,
                    "resource_type": resource_type,
                    "allowed": allowed,
                    "reason": reason
                }
            )

            # Audit logging
            audit_logger = get_audit_logger()
            audit_logger.log_access(
                employee_email=requester_id,
                resource_id=f"{target_id}/{resource_type}",
                decision=AuditDecision.ALLOW if allowed else AuditDecision.DENY,
                reason=reason,
                policy_matched=context.get("relationship", "none"),
                resource_classification=context.get("data_classification", "unknown"),
                employee_clearance="unknown",  # Will enhance with enrichment context later
                additional_context={
                    "target_employee": target_id,
                    "resource_type": resource_type,
                    "relationship": context.get("relationship"),
                    "department_match": context.get("department_match"),
                    "team_match": context.get("team_match"),
                    "project_shared": context.get("project_shared"),
                    "hierarchy_level": context.get("hierarchy_level")
                }
            )

            # Cache the result
            self.cache.set_policy_result(
                requester_id, target_id, resource_type, "unknown", response
            )

            return response

        except Exception as e:
            logger.error(
                f"Error in access check: {e}",
                exc_info=True,
                extra={
                    "requester_id": requester_id,
                    "target_id": target_id,
                    "resource_type": resource_type
                }
            )
            
            # Audit logging for error case
            audit_logger = get_audit_logger()
            audit_logger.log_access(
                employee_email=requester_id,
                resource_id=f"{target_id}/{resource_type}",
                decision=AuditDecision.ERROR,
                reason=f"Access check failed: {str(e)}",
                policy_matched="error",
                resource_classification="unknown",
                employee_clearance="unknown",
                additional_context={
                    "target_employee": target_id,
                    "resource_type": resource_type,
                    "error": str(e)
                }
            )
            
            # Fail closed - deny access on error
            return {
                "allowed": False,
                "reason": f"Access check failed: {str(e)}",
                "context": context,
                "timestamp": (timestamp or datetime.now()).isoformat(),
                "error": str(e)
            }

    # ========================================================================
    # TEMPORAL CONTEXT INTERFACE (Team A Integration)
    # ========================================================================

    @deal.pre(lambda self, employee_id: isinstance(employee_id, str) and len(employee_id) > 0)
    async def get_temporal_context(
        self,
        employee_id: str,
        timestamp: datetime
    ) -> Optional[Dict]:
        """
        Get temporal organizational context for employee
        
        Team A (Temporal Framework) calls this to get time-aware organizational context.
        
        Args:
            employee_id: Employee ID
            timestamp: Point in time for context retrieval
            
        Returns:
            {
                "employee_id": str,
                "name": str,
                "department": str,
                "team": str,
                "role": str,
                "security_clearance": str,
                "employee_type": str,
                "manager": str,
                "direct_reports": List[str],
                "projects": List[str],
                "timezone": str,
                "working_hours": {"start": str, "end": str},
                "is_active": bool,
                "in_business_hours": bool,
                "location": str,
                "phone": str,
                "email": str,
                "temporal_valid": bool
            } or None if employee not found
        """
        logger.info(
            f"Getting temporal context: {employee_id} at {timestamp}",
            extra={"employee_id": employee_id, "timestamp": timestamp.isoformat()}
        )

        try:
            # Get base organizational context
            context = await self.queries.get_employee_context(employee_id, timestamp)
            
            if not context:
                logger.warning(
                    f"Employee not found: {employee_id}",
                    extra={"employee_id": employee_id}
                )
                return None

            # Add temporal validation fields
            # TODO: Implement contract expiry, acting roles, etc.
            context["is_active"] = True  # TODO: Check contract validity
            context["temporal_valid"] = True  # TODO: Temporal validation
            
            # Check business hours
            context["in_business_hours"] = self._check_business_hours(
                context["working_hours"],
                context["timezone"],
                timestamp
            )

            logger.info(
                f"Retrieved temporal context for {context['name']}",
                extra={
                    "employee_id": employee_id,
                    "name": context['name'],
                    "is_active": context["is_active"],
                    "in_business_hours": context["in_business_hours"]
                }
            )

            return context

        except Exception as e:
            logger.error(
                f"Error getting temporal context: {e}",
                exc_info=True,
                extra={"employee_id": employee_id}
            )
            return None

    # ========================================================================
    # SPECIFIC RELATIONSHIP CHECKS
    # ========================================================================

    @deal.pre(lambda self, user_a_id, user_b_id, relationship_type: 
              isinstance(user_a_id, str) and len(user_a_id) > 0 and
              isinstance(user_b_id, str) and len(user_b_id) > 0 and
              isinstance(relationship_type, str) and len(relationship_type) > 0)
    @deal.post(lambda result: isinstance(result, bool))
    async def check_organizational_relationship(
        self,
        user_a_id: str,
        user_b_id: str,
        relationship_type: str
    ) -> bool:
        """
        Check specific organizational relationship between two users
        
        Args:
            user_a_id: First employee ID
            user_b_id: Second employee ID
            relationship_type: Type of relationship to check
                - "direct_report": user_a reports to user_b
                - "manager": user_a manages user_b
                - "same_team": both on same team
                - "same_department": both in same department
                - "project_member": both on same active project
                - "manager_chain": user_b is in user_a's management chain
                
        Returns:
            True if relationship exists, False otherwise
        """
        logger.debug(
            f"Checking relationship: {user_a_id} <{relationship_type}> {user_b_id}",
            extra={"user_a": user_a_id, "user_b": user_b_id, "type": relationship_type}
        )

        try:
            if relationship_type == "direct_report":
                return await self.queries.check_direct_report(user_a_id, user_b_id)
            
            elif relationship_type == "manager":
                return await self.queries.check_direct_report(user_b_id, user_a_id)
            
            elif relationship_type == "same_team":
                return await self.queries.check_same_team(user_a_id, user_b_id)
            
            elif relationship_type == "same_department":
                result = await self.queries.check_same_department(user_a_id, user_b_id)
                return result is not None
            
            elif relationship_type == "project_member":
                projects = await self.queries.check_shared_project(user_a_id, user_b_id)
                return len(projects) > 0
            
            elif relationship_type == "manager_chain":
                is_in_chain, _ = await self.queries.check_manager_hierarchy(user_a_id, user_b_id)
                return is_in_chain
            
            else:
                logger.warning(
                    f"Unknown relationship type: {relationship_type}",
                    extra={"type": relationship_type}
                )
                return False

        except Exception as e:
            logger.error(
                f"Error checking relationship: {e}",
                exc_info=True,
                extra={"user_a": user_a_id, "user_b": user_b_id, "type": relationship_type}
            )
            return False

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _check_business_hours(
        self,
        working_hours: Dict[str, str],
        timezone: str,
        timestamp: datetime
    ) -> bool:
        """
        Check if timestamp is within employee's business hours
        
        Args:
            working_hours: {"start": "09:00", "end": "17:00"}
            timezone: Employee timezone (e.g., "America/Los_Angeles")
            timestamp: Timestamp to check
            
        Returns:
            True if within business hours, False otherwise
        """
        try:
            import pytz
            from datetime import time

            # Convert timestamp to employee's timezone
            tz = pytz.timezone(timezone)
            local_time = timestamp.astimezone(tz)

            # Parse working hours
            start_time = datetime.strptime(working_hours["start"], "%H:%M").time()
            end_time = datetime.strptime(working_hours["end"], "%H:%M").time()

            # Check if within range
            return start_time <= local_time.time() <= end_time

        except Exception as e:
            logger.warning(
                f"Error checking business hours: {e}",
                extra={"timezone": timezone, "working_hours": working_hours}
            )
            # Default to True if can't determine
            return True

    # ========================================================================
    # EMPLOYEE CONTEXT ENRICHMENT API (Team A/C Integration)
    # ========================================================================

    @deal.pre(lambda self, employee_email: isinstance(employee_email, str) and len(employee_email) > 0)
    async def get_employee_enrichment_context(
        self,
        employee_email: str,
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Get complete employee organizational context for Team A/C integration
        
        This is the primary enrichment endpoint that Team C calls to gather
        organizational context before sending requests to Team A's temporal engine.
        
        Team C receives a request like:
            {
                "data_field": "patient_heart_rate",
                "requester_email": "dr.smith@hospital.com",
                "urgency_level": "critical"
            }
        
        Team C calls this endpoint to enrich with org context:
            context = await get_employee_enrichment_context("dr.smith@hospital.com")
        
        Then Team C uses this data to build Team A's temporal tuple:
            EnhancedContextualIntegrityTuple(
                data_recipient=context["title"],  # "Emergency Physician"
                temporal_role="oncall_critical",  # mapped from urgency + context
                ...
            )
        
        Args:
            employee_email: Employee email address (e.g., "sarah.chen@acme.com")
            timestamp: Point in time for context (defaults to now)
            
        Returns:
            {
                "employee_id": str,
                "name": str,
                "email": str,
                "title": str,
                "department": str,
                "team": str,
                "security_clearance": str,       # basic|standard|elevated|restricted|top_secret|executive
                "employment_type": str,          # full_time|contractor
                "hierarchy_level": int,          # 1 (CEO) to 6 (Individual Contributor)
                "is_manager": bool,
                "is_executive": bool,
                "is_ceo": bool,
                "reports_to": {
                    "name": str,
                    "email": str,
                    "title": str
                } or None,
                "direct_reports": [
                    {
                        "name": str,
                        "email": str,
                        "title": str
                    }
                ],
                "projects": [
                    {
                        "name": str,
                        "project_id": str,
                        "role": str,
                        "status": str
                    }
                ],
                "working_hours": {
                    "start": str,
                    "end": str,
                    "timezone": str
                },
                "location": str,
                "phone": str,
                "is_active": bool,
                "contract_end_date": str or None  # For contractors
            } or None if employee not found
            
        Example Response:
            {
                "employee_id": "emp-001",
                "name": "Sarah Chen",
                "email": "sarah.chen@acme.com",
                "title": "CEO & Co-Founder",
                "department": "Executive",
                "team": "Executive Team",
                "security_clearance": "executive",
                "employment_type": "full_time",
                "hierarchy_level": 1,
                "is_manager": True,
                "is_executive": True,
                "is_ceo": True,
                "reports_to": None,
                "direct_reports": [
                    {
                        "name": "Priya Patel",
                        "email": "priya.patel@acme.com",
                        "title": "CTO"
                    },
                    ...
                ],
                "projects": [],
                "working_hours": {
                    "start": "08:00",
                    "end": "18:00",
                    "timezone": "America/Los_Angeles"
                },
                "location": "San Francisco, CA",
                "phone": "+1-415-555-0001",
                "is_active": True,
                "contract_end_date": None
            }
        """
        logger.info(
            f"Getting employee enrichment context: {employee_email}",
            extra={"employee_email": employee_email}
        )

        # Check cache first
        cached_context = self.cache.get_employee_context(employee_email)
        if cached_context is not None:
            logger.debug(f"Cache HIT for employee context: {employee_email}")
            return cached_context
        
        logger.debug(f"Cache MISS for employee context: {employee_email}")

        try:
            # Query Neo4j for complete employee context
            # Graphiti uses Entity nodes with RELATES_TO relationships
            # Relationship types are stored in r.fact property
            query = """
            MATCH (e:Entity:Employee)
            WHERE e.email = $email
            OPTIONAL MATCH (e)-[rm:RELATES_TO]->(manager:Entity:Employee)
            WHERE rm.fact CONTAINS 'reports to'
            OPTIONAL MATCH (report:Entity:Employee)-[rr:RELATES_TO]->(e)
            WHERE rr.fact CONTAINS 'reports to'
            OPTIONAL MATCH (e)-[rt:RELATES_TO]->(team:Entity:Team)
            WHERE rt.fact CONTAINS 'member of'
            OPTIONAL MATCH (e)-[rd:RELATES_TO]->(dept:Entity:Department)
            WHERE rd.fact CONTAINS 'member of'
            OPTIONAL MATCH (e)-[rp:RELATES_TO]->(project:Entity:Project)
            WHERE rp.fact CONTAINS 'working on'
            WITH e, manager, dept, collect(DISTINCT report) as reports, team,
                 collect(DISTINCT project) as projects
            RETURN 
                e.id as employee_id,
                e.name as name,
                e.email as email,
                COALESCE(e.title, e.name) as title,
                dept.name as department,
                team.name as team_name,
                COALESCE(e.security_clearance, 'standard') as security_clearance,
                COALESCE(e.employee_type, 'full_time') as employment_type,
                COALESCE(e.hierarchy_level, 6) as hierarchy_level,
                COALESCE(e.location, 'San Francisco, CA') as location,
                COALESCE(e.phone, '+1-555-0100') as phone,
                COALESCE(e.timezone, 'America/Los_Angeles') as timezone,
                COALESCE(e.working_hours_start, '09:00') as working_hours_start,
                COALESCE(e.working_hours_end, '17:00') as working_hours_end,
                e.contract_end_date as contract_end_date,
                manager {.name, .email, .title} as manager_info,
                [r IN reports | {name: r.name, email: r.email, title: COALESCE(r.title, r.name)}] as direct_reports,
                [p IN projects | {
                    name: p.name, 
                    project_id: COALESCE(p.project_id, p.name), 
                    status: COALESCE(p.status, 'active')
                }] as project_list
            """

            # Use driver from queries instance (same as privacy_queries.py pattern)
            records, _, _ = await self.queries.driver.execute_query(
                query,
                email=employee_email,
                routing_="r"
            )
            
            if not records:
                logger.warning(
                    f"Employee not found: {employee_email}",
                    extra={"employee_email": employee_email}
                )
                return None

            data = records[0]
            
            # Determine if employee is manager/executive/CEO
            is_manager = len(data.get("direct_reports", [])) > 0
            hierarchy_level = data.get("hierarchy_level", 6)
            is_executive = hierarchy_level <= 2  # Level 1-2 are executives
            is_ceo = data.get("title", "").upper().startswith("CEO")
            
            # Build enriched context response
            context = {
                "employee_id": data.get("employee_id"),
                "name": data.get("name"),
                "email": data.get("email"),
                "title": data.get("title"),
                "department": data.get("department"),
                "team": data.get("team_name"),
                "security_clearance": data.get("security_clearance", "standard"),
                "employment_type": data.get("employment_type", "full_time"),
                "hierarchy_level": hierarchy_level,
                "is_manager": is_manager,
                "is_executive": is_executive,
                "is_ceo": is_ceo,
                "reports_to": data.get("manager_info"),
                "direct_reports": data.get("direct_reports", []),
                "projects": data.get("project_list", []),
                "working_hours": {
                    "start": data.get("working_hours_start", "09:00"),
                    "end": data.get("working_hours_end", "17:00"),
                    "timezone": data.get("timezone", "UTC")
                },
                "location": data.get("location"),
                "phone": data.get("phone"),
                "is_active": True,  # TODO: Check contract validity if needed
                "contract_end_date": data.get("contract_end_date")
            }
            
            # Cache the result
            self.cache.set_employee_context(employee_email, context)
            
            logger.info(
                f"Retrieved enrichment context for {context['name']} ({context['title']})",
                extra={
                    "employee_email": employee_email,
                    "department": context["department"],
                    "clearance": context["security_clearance"],
                    "is_manager": is_manager,
                    "is_executive": is_executive
                }
            )
            
            return context

        except Exception as e:
            logger.error(
                f"Error getting employee enrichment context: {e}",
                exc_info=True,
                extra={"employee_email": employee_email}
            )
            return None

    async def get_system_stats(self) -> Dict:
        """
        Get system statistics and health metrics
        
        Returns:
            {
                "node_count": int,
                "relationship_count": int,
                "employee_count": int,
                "department_count": int,
                "team_count": int,
                "project_count": int,
                "status": "healthy" | "degraded" | "error"
            }
        """
        try:
            stats = await self.queries.get_performance_stats()
            stats["status"] = "healthy" if stats.get("employee_count", 0) > 0 else "error"
            return stats
        except Exception as e:
            logger.error(f"Error getting system stats: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }


# ============================================================================
# CONVENIENCE WRAPPER FUNCTIONS (For Easy Import)
# ============================================================================

# Singleton API instance
_api_instance = None

def _get_api() -> PrivacyFirewallAPI:
    """Get or create singleton API instance"""
    global _api_instance
    if _api_instance is None:
        _api_instance = PrivacyFirewallAPI()
    return _api_instance


async def get_employee_context(employee_email: str) -> Optional[Dict]:
    """
    Get complete employee organizational context (convenience wrapper)
    
    Args:
        employee_email: Employee email address
        
    Returns:
        Complete organizational context dict or None
        
    Example:
        >>> from api.privacy_api import get_employee_context
        >>> context = await get_employee_context("sarah.chen@acme.com")
        >>> print(context["title"])
        "CEO & Co-Founder"
    """
    api = _get_api()
    return await api.get_employee_enrichment_context(employee_email)


async def check_access(
    employee_email: str,
    resource_id: str,
    resource_classification: str
) -> Dict:
    """
    Check if employee can access a resource (convenience wrapper)
    
    Args:
        employee_email: Employee email requesting access
        resource_id: Resource identifier
        resource_classification: Classification level (public, internal, confidential, etc.)
        
    Returns:
        {
            "access_granted": bool,
            "reason": str,
            "policy_matched": str,
            "employee_context": dict
        }
        
    Example:
        >>> from api.privacy_api import check_access
        >>> result = await check_access(
        ...     "john.smith@acme.com",
        ...     "RES-001",
        ...     "confidential"
        ... )
        >>> print(result["access_granted"])
        True
    """
    from core.policy_engine_v2 import PolicyEngine
    
    api = _get_api()
    audit_logger = get_audit_logger()
    
    # Get employee context
    employee = await api.get_employee_enrichment_context(employee_email)
    if not employee:
        # Audit log for employee not found
        audit_logger.log_access(
            employee_email=employee_email,
            resource_id=resource_id,
            decision=AuditDecision.DENY,
            reason=f"Employee not found: {employee_email}",
            policy_matched="none",
            resource_classification=resource_classification,
            employee_clearance="unknown",
            additional_context={"error": "employee_not_found"}
        )
        
        return {
            "access_granted": False,
            "reason": f"Employee not found: {employee_email}",
            "policy_matched": None,
            "employee_context": None
        }
    
    # Evaluate access using policy engine
    policy_engine = PolicyEngine(api.queries, policy_config_path="config/resource_policies.yaml")
    
    result = await policy_engine.evaluate_resource_access(
        requester_id=employee["employee_id"],
        resource_owner=resource_id,
        resource_classification=resource_classification,
        resource_type="document",
        action="read"
    )
    
    access_granted = result.decision.value == "ALLOW"
    
    # Audit log the access decision
    audit_logger.log_access(
        employee_email=employee_email,
        resource_id=resource_id,
        decision=AuditDecision.ALLOW if access_granted else AuditDecision.DENY,
        reason=result.reason,
        policy_matched=result.policy_rules_applied[0] if result.policy_rules_applied else "none",
        resource_classification=resource_classification,
        employee_clearance=employee.get("security_clearance", "unknown"),
        additional_context={
            "employee_id": employee["employee_id"],
            "department": employee.get("department"),
            "team": employee.get("team"),
            "confidence": result.confidence,
            "is_manager": employee.get("is_manager", False),
            "is_executive": employee.get("is_executive", False)
        }
    )
    
    return {
        "access_granted": access_granted,
        "reason": result.reason,
        "policy_matched": result.policy_rules_applied[0] if result.policy_rules_applied else None,
        "employee_context": employee,
        "confidence": result.confidence
    }


async def get_accessible_resources(
    employee_email: str,
    classification: str = "confidential"
) -> List[Dict]:
    """
    Get all resources an employee can access at given classification (convenience wrapper)
    
    Args:
        employee_email: Employee email
        classification: Resource classification level
        
    Returns:
        List of accessible resources with reasons
        
    Example:
        >>> from api.privacy_api import get_accessible_resources
        >>> resources = await get_accessible_resources("sarah.chen@acme.com", "confidential")
        >>> for r in resources:
        ...     print(f"{r['id']}: {r['reason']}")
    """
    api = _get_api()
    employee = await api.get_employee_enrichment_context(employee_email)
    
    if not employee:
        return []
    
    # TODO: Implement resource listing
    # For now, return context
    return [{
        "employee": employee,
        "classification": classification,
        "note": "Resource listing not yet implemented"
    }]


async def get_resource_viewers(
    resource_id: str,
    resource_classification: str
) -> List[Dict]:
    """
    Get all employees who can view a resource (convenience wrapper)
    
    Args:
        resource_id: Resource identifier
        resource_classification: Classification level
        
    Returns:
        List of employees with access
        
    Example:
        >>> from api.privacy_api import get_resource_viewers
        >>> viewers = await get_resource_viewers("RES-EXEC-001", "top_secret")
        >>> for v in viewers:
        ...     print(f"{v['name']} ({v['title']}): {v['reason']}")
    """
    # TODO: Implement viewer listing
    return [{
        "resource_id": resource_id,
        "classification": resource_classification,
        "note": "Viewer listing not yet implemented"
    }]
