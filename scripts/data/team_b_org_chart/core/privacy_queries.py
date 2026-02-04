"""
Privacy Firewall Query Interface

Implements PRD-specified organizational relationship queries for AI Privacy Firewall.
These are the CORE deliverables for Team B.

Author: Aithel Christo Sunil
Date: October 25, 2025
Team: Team B - Organizational Chart Integration
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import deal
import yaml

logger = logging.getLogger(__name__)


# ============================================================================
# PRIVACY FIREWALL QUERIES - PRD REQUIREMENTS
# ============================================================================


class PrivacyFirewallQueries:
    """
    Direct Cypher queries for Privacy Firewall organizational relationship checks
    
    Implements the 3 core PRD requirements:
    1. Check direct reporting relationship
    2. Check same department membership  
    3. Check shared project membership
    
    Performance target: <100ms per query (99th percentile)
    """

    @deal.pre(lambda _, graphiti_client, cache=None: graphiti_client is not None)
    def __init__(self, graphiti_client, cache=None):
        """
        Initialize Privacy Firewall Queries
        
        Args:
            graphiti_client: GraphitiClient instance with active Neo4j connection
            cache: PrivacyFirewallCache instance for relationship caching (optional)
        """
        logger.info("Initializing PrivacyFirewallQueries")
        self.client = graphiti_client
        self.driver = graphiti_client.driver
        self.cache = cache
        logger.info("PrivacyFirewallQueries initialized successfully")

    # ========================================================================
    # PRD REQUIREMENT 1: Direct Reporting Relationship
    # ========================================================================

    @deal.pre(lambda self, employee_id, manager_id: 
              isinstance(employee_id, str) and len(employee_id) > 0 and
              isinstance(manager_id, str) and len(manager_id) > 0)
    @deal.post(lambda result: isinstance(result, bool))
    async def check_direct_report(
        self, 
        employee_id: str, 
        manager_id: str
    ) -> bool:
        """
        Check if employee directly reports to manager
        
        ACTUAL Schema:
        - All relationships are :RELATES_TO
        - Actual relationship type is in r.fact property
        - Looking for facts containing "reports to" or "managed by"
        
        Args:
            employee_id: Employee NAME (not ID) - e.g., "Alice Cooper"
            manager_id: Manager NAME (not ID) - e.g., "Marcus Johnson"
            
        Returns:
            True if direct reporting relationship exists, False otherwise
            
        Performance: <100ms (direct index lookup)
        """
        logger.info(
            f"Checking direct report: {employee_id} -> {manager_id}",
            extra={"employee_id": employee_id, "manager_id": manager_id}
        )

        # Check cache first
        if self.cache:
            cached = self.cache.get_relationship(employee_id, manager_id, "reports_to")
            if cached is not None:
                logger.debug(f"Cache HIT for direct report: {employee_id} -> {manager_id}")
                return cached

        logger.debug(f"Cache MISS for direct report: {employee_id} -> {manager_id}")

        try:
            # Graphiti stores relationships as RELATES_TO with name property and fact text
            query = """
            MATCH (employee:Entity)-[r:RELATES_TO]->(manager:Entity)
            WHERE employee.id = $employee_id 
            AND manager.id = $manager_id
            AND (r.name = 'REPORTS_TO' OR r.fact CONTAINS 'reports to' OR r.fact CONTAINS 'managed by')
            RETURN count(r) > 0 as has_relationship
            """

            records, _, _ = await self.driver.execute_query(
                query,
                employee_id=employee_id,
                manager_id=manager_id,
                routing_="r"
            )

            result = records[0]["has_relationship"] if records else False
            
            # Cache the result
            if self.cache:
                self.cache.set_relationship(employee_id, manager_id, "reports_to", result)
            
            logger.info(
                f"Direct report check result: {result}",
                extra={"employee_id": employee_id, "manager_id": manager_id, "result": result}
            )
            
            return result

        except Exception as e:
            logger.error(
                f"Error checking direct report relationship: {e}",
                exc_info=True,
                extra={"employee_id": employee_id, "manager_id": manager_id}
            )
            return False

    # ========================================================================
    # PRD REQUIREMENT 2: Same Department Check
    # ========================================================================

    @deal.pre(lambda self, sender_id, recipient_id: 
              isinstance(sender_id, str) and len(sender_id) > 0 and
              isinstance(recipient_id, str) and len(recipient_id) > 0)
    async def check_same_department(
        self, 
        sender_id: str, 
        recipient_id: str
    ) -> Optional[Dict]:
        """
        Check if two employees are in the same department
        
        ACTUAL Schema:
        - Relationships are :RELATES_TO with fact="is a member of"
        - Both employees must connect to same Department entity
        
        Args:
            sender_id: First employee NAME - e.g., "Alice Cooper"
            recipient_id: Second employee NAME - e.g., "Bob Chen"
            
        Returns:
            {
                "department": str,
                "data_classification": str
            } if same department, None otherwise
            
        Performance: <100ms (indexed graph traversal)
        """
        logger.info(
            f"Checking same department: {sender_id} <-> {recipient_id}",
            extra={"sender_id": sender_id, "recipient_id": recipient_id}
        )

        try:
            query = """
            MATCH (p1:Entity)-[r1:RELATES_TO]->(d:Entity:Department)<-[r2:RELATES_TO]-(p2:Entity)
            WHERE p1.id = $sender_id 
            AND p2.id = $recipient_id
            AND (r1.fact CONTAINS 'member of' OR r1.name IN ['MEMBER_OF', 'BELONGS_TO'])
            AND (r2.fact CONTAINS 'member of' OR r2.name IN ['MEMBER_OF', 'BELONGS_TO'])
            RETURN d.name as dept_name, d.data_classification as classification
            """

            records, _, _ = await self.driver.execute_query(
                query,
                sender_id=sender_id,
                recipient_id=recipient_id,
                routing_="r"
            )

            if records:
                result = {
                    "department": records[0]["dept_name"],
                    "data_classification": records[0]["classification"]
                }
                logger.info(
                    f"Same department: {result['department']}",
                    extra={"sender_id": sender_id, "recipient_id": recipient_id, "department": result['department']}
                )
                return result
            else:
                logger.info(
                    "Not in same department",
                    extra={"sender_id": sender_id, "recipient_id": recipient_id}
                )
                return None

        except Exception as e:
            logger.error(
                f"Error checking same department: {e}",
                exc_info=True,
                extra={"sender_id": sender_id, "recipient_id": recipient_id}
            )
            return None

    # ========================================================================
    # PRD REQUIREMENT 3: Project Membership Check
    # ========================================================================

    @deal.pre(lambda self, sender_id, recipient_id: 
              isinstance(sender_id, str) and len(sender_id) > 0 and
              isinstance(recipient_id, str) and len(recipient_id) > 0)
    @deal.post(lambda result: isinstance(result, list))
    async def check_shared_project(
        self, 
        sender_id: str, 
        recipient_id: str
    ) -> List[Dict]:
        """
        Check if two employees share active project membership
        
        ACTUAL Schema:
        - Would use :RELATES_TO with fact containing "working on" or "assigned to"
        - Projects would be :Entity:Project nodes
        - Currently no projects in database, so this returns empty
        
        Args:
            sender_id: First employee NAME
            recipient_id: Second employee NAME
            
        Returns:
            List of shared projects (empty for now - no projects loaded)
            
        Performance: <100ms (indexed graph traversal)
        """
        logger.info(
            f"Checking shared projects: {sender_id} <-> {recipient_id}",
            extra={"sender_id": sender_id, "recipient_id": recipient_id}
        )

        try:
            query = """
            MATCH (p1:Entity)-[r1:RELATES_TO]->(proj:Entity:Project)<-[r2:RELATES_TO]-(p2:Entity)
            WHERE p1.id = $sender_id 
            AND p2.id = $recipient_id
            AND (r1.fact CONTAINS 'working on' OR r1.fact CONTAINS 'assigned to' OR r1.name IN ['WORKS_ON', 'ASSIGNED_TO'])
            AND (r2.fact CONTAINS 'working on' OR r2.fact CONTAINS 'assigned to' OR r2.name IN ['WORKS_ON', 'ASSIGNED_TO'])
            RETURN proj.name as project_name, 
                   proj.data_classification as data_scope,
                   'active' as status
            """

            records, _, _ = await self.driver.execute_query(
                query,
                sender_id=sender_id,
                recipient_id=recipient_id,
                routing_="r"
            )

            results = [
                {
                    "project": record["project_name"],
                    "data_scope": record["data_scope"],
                    "status": record["status"]
                }
                for record in records
            ]

            logger.info(
                f"Found {len(results)} shared projects",
                extra={"sender_id": sender_id, "recipient_id": recipient_id, "count": len(results)}
            )

            return results

        except Exception as e:
            logger.error(
                f"Error checking shared projects: {e}",
                exc_info=True,
                extra={"sender_id": sender_id, "recipient_id": recipient_id}
            )
            return []

    # ========================================================================
    # EXTENDED QUERIES - Full Context Support
    # ========================================================================

    @deal.pre(lambda self, employee_id: isinstance(employee_id, str) and len(employee_id) > 0)
    async def get_employee_context(
        self, 
        employee_id: str, 
        timestamp: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Get full organizational context for employee
        
        Used by Team A (Temporal Framework) to get complete context.
        This is the main integration point for temporal access decisions.
        
        Args:
            employee_id: Employee ID
            timestamp: Point in time for temporal context (future use)
            
        Returns:
            {
                "employee_id": str,
                "name": str,
                "department": str,
                "team": str,
                "role": str,
                "security_clearance": str,
                "manager": str,
                "direct_reports": List[str],
                "projects": List[str],
                "employee_type": str,
                "timezone": str,
                "working_hours": {"start": str, "end": str},
                "location": str,
                "phone": str,
                "email": str
            } or None if employee not found
        """
        logger.info(
            f"Getting employee context: {employee_id}",
            extra={"employee_id": employee_id}
        )

        try:
            # Graphiti uses Entity nodes with RELATES_TO relationships
            # Relationship types are stored in both r.name property and r.fact property
            query = """
            MATCH (e:Entity:Employee)
            WHERE e.id = $employee_id
            OPTIONAL MATCH (e)-[rd:RELATES_TO]->(d:Entity:Department)
            WHERE rd.fact CONTAINS 'member of' OR rd.name IN ['MEMBER_OF', 'BELONGS_TO']
            OPTIONAL MATCH (e)-[rt:RELATES_TO]->(t:Entity:Team)
            WHERE rt.fact CONTAINS 'member of' OR rt.name IN ['MEMBER_OF', 'BELONGS_TO']
            OPTIONAL MATCH (e)-[rm:RELATES_TO]->(m:Entity:Employee)
            WHERE rm.fact CONTAINS 'reports to' OR rm.name = 'REPORTS_TO'
            OPTIONAL MATCH (report:Entity:Employee)-[rr:RELATES_TO]->(e)
            WHERE rr.fact CONTAINS 'reports to' OR rr.name = 'REPORTS_TO'
            OPTIONAL MATCH (e)-[rp:RELATES_TO]->(p:Entity:Project)
            WHERE rp.fact CONTAINS 'working on' OR rp.name IN ['WORKS_ON', 'ASSIGNED_TO']
            RETURN 
                e.id as employee_id,
                e.name as name,
                d.name as department,
                t.name as team,
                COALESCE(e.title, e.name) as role,
                COALESCE(e.security_clearance, 'standard') as clearance,
                COALESCE(e.employee_type, 'full_time') as emp_type,
                COALESCE(e.timezone, 'UTC-8') as timezone,
                COALESCE(e.work_start, '09:00') as work_start,
                COALESCE(e.work_end, '17:00') as work_end,
                COALESCE(e.location, 'San Francisco') as location,
                COALESCE(e.phone, '+1-555-0100') as phone,
                lower(replace(e.name, ' ', '.')) + '@company.com' as email,
                m.name as manager,
                collect(DISTINCT report.name) as reports,
                collect(DISTINCT p.name) as projects,
                e.contract_end_date as contract_end_date,
                e.acting_role_start as acting_role_start,
                e.acting_role_end as acting_role_end
            """

            records, _, _ = await self.driver.execute_query(
                query,
                employee_id=employee_id,
                routing_="r"
            )

            if not records:
                logger.warning(
                    f"Employee not found: {employee_id}",
                    extra={"employee_id": employee_id}
                )
                return None

            r = records[0]
            context = {
                "employee_id": r["employee_id"],
                "name": r["name"],
                "department": r["department"],
                "team": r["team"],
                "role": r["role"],
                "security_clearance": r["clearance"],
                "employee_type": r["emp_type"],
                "timezone": r["timezone"],
                "working_hours": {
                    "start": r["work_start"],
                    "end": r["work_end"]
                },
                "location": r["location"],
                "phone": r["phone"],
                "email": r["email"],
                "manager": r["manager"],
                "direct_reports": [rep for rep in r["reports"] if rep],
                "projects": [proj for proj in r["projects"] if proj],
                # Temporal fields for contractors and acting roles
                "contract_end_date": r.get("contract_end_date"),
                "acting_role_start": r.get("acting_role_start"),
                "acting_role_end": r.get("acting_role_end")
            }

            logger.info(
                f"Retrieved context for {r['name']}",
                extra={"employee_id": employee_id, "emp_name": r['name'], "department": r['department']}
            )

            return context

        except Exception as e:
            logger.error(
                f"Error getting employee context: {e}",
                exc_info=True,
                extra={"employee_id": employee_id}
            )
            return None

    # ========================================================================
    # MANAGER HIERARCHY QUERIES
    # ========================================================================

    @deal.pre(lambda self, employee_id, potential_manager_id: 
              isinstance(employee_id, str) and len(employee_id) > 0 and
              isinstance(potential_manager_id, str) and len(potential_manager_id) > 0)
    async def check_manager_hierarchy(
        self,
        employee_id: str,
        potential_manager_id: str,
        max_levels: int = 5
    ) -> Tuple[bool, int]:
        """
        Check if potential_manager is anywhere in employee's management chain
        
        Args:
            employee_id: Employee to check
            potential_manager_id: Potential manager in chain
            max_levels: Maximum levels to traverse (default: 5)
            
        Returns:
            (is_in_chain, levels_up) tuple
            - (True, 1): Direct manager
            - (True, 2): Skip-level manager
            - (False, 0): Not in management chain
            
        Examples:
            >>> check_manager_hierarchy("emp-005", "emp-004")
            (True, 1)  # emp-004 is direct manager of emp-005
            
            >>> check_manager_hierarchy("emp-005", "emp-002")
            (True, 2)  # emp-002 is skip-level manager
            
            >>> check_manager_hierarchy("emp-005", "emp-031")
            (False, 0)  # emp-031 is in Finance, no relationship
        """
        logger.info(
            f"Checking manager hierarchy: {employee_id} -> {potential_manager_id}",
            extra={"employee_id": employee_id, "manager_id": potential_manager_id}
        )

        try:
            # Use RELATES_TO with both name property and fact matching (Graphiti schema)
            query = f"""
            MATCH path = (e:Entity)-[r:RELATES_TO*1..{max_levels}]->(m:Entity)
            WHERE e.id = $employee_id 
            AND m.id = $manager_id
            AND ALL(rel IN relationships(path) WHERE rel.name = 'REPORTS_TO' OR rel.fact CONTAINS 'reports to' OR rel.fact CONTAINS 'managed by')
            RETURN length(path) as levels
            ORDER BY levels
            LIMIT 1
            """

            records, _, _ = await self.driver.execute_query(
                query,
                employee_id=employee_id,
                manager_id=potential_manager_id,
                routing_="r"
            )

            if records:
                levels = records[0]["levels"]
                logger.info(
                    f"Manager found at level {levels}",
                    extra={"employee_id": employee_id, "manager_id": potential_manager_id, "levels": levels}
                )
                return (True, levels)
            else:
                logger.info(
                    "Not in management chain",
                    extra={"employee_id": employee_id, "manager_id": potential_manager_id}
                )
                return (False, 0)

        except Exception as e:
            logger.error(
                f"Error checking manager hierarchy: {e}",
                exc_info=True,
                extra={"employee_id": employee_id, "manager_id": potential_manager_id}
            )
            return (False, 0)

    # ========================================================================
    # TEAM QUERIES
    # ========================================================================

    @deal.pre(lambda self, sender_id, recipient_id: 
              isinstance(sender_id, str) and len(sender_id) > 0 and
              isinstance(recipient_id, str) and len(recipient_id) > 0)
    @deal.post(lambda result: isinstance(result, bool))
    async def check_same_team(
        self,
        sender_id: str,
        recipient_id: str
    ) -> bool:
        """
        Check if two employees are on the same team
        
        Args:
            sender_id: First employee ID
            recipient_id: Second employee ID
            
        Returns:
            True if same team, False otherwise
        """
        logger.debug(
            f"Checking same team: {sender_id} <-> {recipient_id}",
            extra={"sender_id": sender_id, "recipient_id": recipient_id}
        )

        # Check cache first
        if self.cache:
            cached = self.cache.get_relationship(sender_id, recipient_id, "same_team")
            if cached is not None:
                logger.debug(f"Cache HIT for same team: {sender_id} <-> {recipient_id}")
                return cached

        logger.debug(f"Cache MISS for same team: {sender_id} <-> {recipient_id}")

        try:
            # Use RELATES_TO with both name property and fact matching (Graphiti schema)
            query = """
            MATCH (p1:Entity)-[r1:RELATES_TO]->(t:Entity:Team)<-[r2:RELATES_TO]-(p2:Entity)
            WHERE p1.id = $sender_id 
            AND p2.id = $recipient_id
            AND (r1.fact CONTAINS 'member of' OR r1.name IN ['MEMBER_OF', 'BELONGS_TO'])
            AND (r2.fact CONTAINS 'member of' OR r2.name IN ['MEMBER_OF', 'BELONGS_TO'])
            RETURN count(*) > 0 as same_team
            """

            records, _, _ = await self.driver.execute_query(
                query,
                sender_id=sender_id,
                recipient_id=recipient_id,
                routing_="r"
            )

            result = records[0]["same_team"] if records else False
            
            # Cache the result
            if self.cache:
                self.cache.set_relationship(sender_id, recipient_id, "same_team", result)
            
            logger.debug(
                f"Same team check: {result}",
                extra={"sender_id": sender_id, "recipient_id": recipient_id, "result": result}
            )
            
            return result

        except Exception as e:
            logger.error(
                f"Error checking same team: {e}",
                exc_info=True,
                extra={"sender_id": sender_id, "recipient_id": recipient_id}
            )
            return False

    # ========================================================================
    # PERFORMANCE UTILITIES
    # ========================================================================

    async def get_performance_stats(self) -> Dict:
        """
        Get query performance statistics from Neo4j
        
        Returns:
            {
                "node_count": int,
                "relationship_count": int,
                "employee_count": int,
                "department_count": int,
                "team_count": int,
                "project_count": int
            }
        """
        logger.info("Getting performance stats")

        try:
            query = """
            MATCH (e:Entity:Employee)
            WITH count(e) as emp_count
            MATCH (d:Entity:Department)
            WITH emp_count, count(d) as dept_count
            MATCH (t:Entity:Team)
            WITH emp_count, dept_count, count(t) as team_count
            MATCH (p:Entity:Project)
            WITH emp_count, dept_count, team_count, count(p) as proj_count
            MATCH (n:Entity)
            WITH emp_count, dept_count, team_count, proj_count, count(n) as total_nodes
            MATCH (:Entity)-[r]->(:Entity)
            RETURN 
                total_nodes,
                count(r) as total_rels,
                emp_count,
                dept_count,
                team_count,
                proj_count
            """

            records, _, _ = await self.driver.execute_query(query, routing_="r")

            if records:
                r = records[0]
                stats = {
                    "node_count": r["total_nodes"],
                    "relationship_count": r["total_rels"],
                    "employee_count": r["emp_count"],
                    "department_count": r["dept_count"],
                    "team_count": r["team_count"],
                    "project_count": r["proj_count"]
                }
                logger.info(f"Performance stats: {stats}")
                return stats
            else:
                return {
                    "node_count": 0,
                    "relationship_count": 0,
                    "employee_count": 0,
                    "department_count": 0,
                    "team_count": 0,
                    "project_count": 0
                }

        except Exception as e:
            logger.error(f"Error getting performance stats: {e}", exc_info=True)
            return {}
