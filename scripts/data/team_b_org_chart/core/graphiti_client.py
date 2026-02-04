"""
Graphiti Client - Organizational Graph Database Interface

Refactored from LLM Data team's db.py with coding guidelines:
- Deal contracts for pre/post conditions
- YAML configuration for all constants
- Enhanced logging with function context
- Comprehensive error handling
- Unit test ready structure
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import List, Optional

import deal
import yaml
from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver
from graphiti_core.edges import EntityEdge
from graphiti_core.llm_client import LLMConfig, OpenAIClient
from graphiti_core.llm_client.groq_client import GroqClient
from graphiti_core.nodes import EntityNode
from graphiti_core.search.search_config import (
    EdgeSearchConfig,
    EdgeSearchMethod,
    NodeSearchConfig,
    NodeSearchMethod,
    SearchConfig,
)
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.utils.maintenance.graph_data_operations import clear_data

from .models import Department, Employee, Project, Team

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "DEBUG"),
    format="%(asctime)s - %(name)s - [%(filename)s:%(funcName)s:%(lineno)d] - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class GraphitiClientError(Exception):
    """Base exception for GraphitiClient errors"""

    pass


class EntityNotFoundError(GraphitiClientError):
    """Raised when an entity is not found in the graph"""

    pass


class EntityCreationError(GraphitiClientError):
    """Raised when entity creation fails"""

    pass


class EdgeCreationError(GraphitiClientError):
    """Raised when edge creation fails"""

    pass


# ============================================================================
# CONFIGURATION LOADER
# ============================================================================


def load_config(config_file: str) -> dict:
    """Load YAML configuration file"""
    try:
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", config_file
        )
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load config {config_file}: {e}")
        return {}


# Load configurations
DB_CONFIG = load_config("database.yaml")
TEMPORAL_CONFIG = load_config("temporal.yaml")


# ============================================================================
# GRAPHITI CLIENT
# ============================================================================


class GraphitiClient:
    """
    Enhanced Graphiti client for organizational graph operations
    
    Provides direct entity/edge creation bypassing episode pipeline for speed.
    Follows coding guidelines with deal contracts, YAML config, and logging.
    """

    @deal.pre(lambda _: True)  # Constructor always valid
    def __init__(self):
        """Initialize Graphiti client with Neo4j and LLM configuration"""
        logger.info("Initializing GraphitiClient")

        # Get Neo4j connection details
        neo4j_uri = os.getenv(
            "NEO4J_URI", DB_CONFIG.get("neo4j", {}).get("default_uri")
        )
        neo4j_user = os.getenv(
            "NEO4J_USER", DB_CONFIG.get("neo4j", {}).get("default_user")
        )
        neo4j_password = os.getenv(
            "NEO4J_PASSWORD", DB_CONFIG.get("neo4j", {}).get("default_password")
        )

        logger.debug(f"Connecting to Neo4j at {neo4j_uri}")

        # Initialize Neo4j driver
        self.driver = Neo4jDriver(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=DB_CONFIG.get("neo4j", {}).get("database", "neo4j"),
        )

        # Initialize LLM client based on environment
        environment = os.getenv(
            "ENVIRONMENT",
            DB_CONFIG.get("llm", {}).get("default_environment", "development"),
        )
        logger.info(f"Environment: {environment}")

        if environment == "development":
            llm_config = LLMConfig(
                api_key=os.getenv("GROQ_API_KEY"),
                model=DB_CONFIG.get("llm", {}).get("dev", {}).get("model"),
            )
            llm_client = GroqClient(llm_config)
            logger.info("Using Groq LLM for development")
        else:
            llm_config = LLMConfig(
                small_model=DB_CONFIG.get("llm", {}).get("prod", {}).get("small_model"),
                model=DB_CONFIG.get("llm", {}).get("prod", {}).get("model"),
            )
            llm_client = OpenAIClient(llm_config)
            logger.info("Using OpenAI LLM for production")

        # Initialize Graphiti
        self.graphiti = Graphiti(graph_driver=self.driver, llm_client=llm_client)
        logger.info("GraphitiClient initialized successfully")

    # ========================================================================
    # DATABASE INITIALIZATION
    # ========================================================================

    @deal.pre(lambda self: self.graphiti is not None)
    @deal.post(lambda result: result is None)
    async def init_database(self):
        """
        Initialize the graph database with indices and constraints.
        
        WARNING: This clears all existing data! Only use for fresh setup.
        """
        logger.warning("Initializing database - this will CLEAR ALL DATA")
        try:
            await clear_data(self.graphiti.driver)
            logger.info("Database cleared successfully")

            await self.graphiti.build_indices_and_constraints()
            logger.info("Indices and constraints built successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            raise GraphitiClientError(f"Failed to initialize database: {e}")

    # ========================================================================
    # COMPANY OPERATIONS
    # ========================================================================

    async def add_company(self, company) -> EntityNode:
        """
        Add the company root node to the organizational graph
        
        Args:
            company: Company model with validated data
            
        Returns:
            Created EntityNode for the company
            
        Raises:
            EntityCreationError: If company creation fails
        """
        logger.info(f"Adding company: {company.name}")

        try:
            attributes = company.attributes()
            node = EntityNode(
                name=company.name,
                labels=["Company"],
                attributes=attributes,
                group_id="",
            )

            await node.generate_name_embedding(self.graphiti.embedder)
            await node.save(self.graphiti.driver)

            logger.info(f"Company added successfully: {company.name}", extra={"node_uuid": node.uuid})
            return node

        except Exception as e:
            error_msg = f"Failed to create company: {str(e)}"
            logger.error(f"{error_msg}: {company.name}", exc_info=True)
            raise EntityCreationError(error_msg)

    async def find_company(self, name: str) -> Optional[EntityNode]:
        """Find a company by exact name match"""
        query = """
        MATCH (c:Entity:Company {name: $name})
        RETURN c
        """
        
        records, _, _ = await self.driver.execute_query(
            query, name=name, routing_="r"
        )
        
        if not records:
            return None
        
        record = records[0]
        node_data = record["c"]
        
        return EntityNode(
            uuid=node_data.element_id,
            name=node_data["name"],
            labels=list(node_data.labels),
            attributes=dict(node_data),
            group_id="",
        )

    # ========================================================================
    # DEPARTMENT OPERATIONS
    # ========================================================================

    @deal.pre(lambda self, department: isinstance(department, Department))
    @deal.post(lambda result: result is not None)
    async def add_department(self, department: Department) -> EntityNode:
        """
        Add a department to the organizational graph
        
        Args:
            department: Department model with validated data
            
        Returns:
            Created EntityNode for the department
            
        Raises:
            EntityCreationError: If department creation fails
        """
        logger.info(f"Adding department: {department.name}", extra={"dept_id": department.id})

        try:
            attributes = department.attributes()
            node = EntityNode(
                name=department.name,
                labels=["Department"],
                attributes=attributes,
                group_id="",
            )

            await node.generate_name_embedding(self.graphiti.embedder)
            await node.save(self.graphiti.driver)

            logger.info(
                f"Department added successfully: {department.name}",
                extra={"dept_id": department.id, "node_uuid": node.uuid},
            )
            return node

        except Exception as e:
            error_msg = DB_CONFIG.get("errors", {}).get("department_creation_failed", "Failed to create department").format(reason=str(e))
            logger.error(f"{error_msg}: {department.name}", exc_info=True)
            raise EntityCreationError(error_msg)

    @deal.pre(lambda self, departments: isinstance(departments, list))
    @deal.post(lambda result: result is None)
    async def add_departments(self, departments: List[Department]):
        """Add multiple departments in parallel"""
        logger.info(f"Adding {len(departments)} departments in batch")
        
        promises = [self.add_department(dept) for dept in departments]
        await asyncio.gather(*promises)
        
        logger.info(f"Successfully added {len(departments)} departments")

    # ========================================================================
    # TEAM OPERATIONS
    # ========================================================================

    @deal.pre(lambda self, team: isinstance(team, Team))
    @deal.post(lambda result: result is not None)
    async def add_team(self, team: Team) -> EntityNode:
        """
        Add a team to the organizational graph
        
        Args:
            team: Team model with validated data
            
        Returns:
            Created EntityNode for the team
            
        Raises:
            EntityCreationError: If team creation fails
        """
        logger.info(f"Adding team: {team.name}", extra={"team_id": team.id})

        try:
            attributes = team.attributes()
            node = EntityNode(
                name=team.name,
                labels=["Team"],
                attributes=attributes,
                group_id="",
            )

            await node.generate_name_embedding(self.graphiti.embedder)
            await node.save(self.graphiti.driver)

            logger.info(
                f"Team added successfully: {team.name}",
                extra={"team_id": team.id, "node_uuid": node.uuid},
            )
            return node

        except Exception as e:
            error_msg = DB_CONFIG.get("errors", {}).get("team_creation_failed", "Failed to create team").format(reason=str(e))
            logger.error(f"{error_msg}: {team.name}", exc_info=True)
            raise EntityCreationError(error_msg)

    @deal.pre(lambda self, teams: isinstance(teams, list))
    @deal.post(lambda result: result is None)
    async def add_teams(self, teams: List[Team]):
        """Add multiple teams in parallel"""
        logger.info(f"Adding {len(teams)} teams in batch")
        
        promises = [self.add_team(team) for team in teams]
        await asyncio.gather(*promises)
        
        logger.info(f"Successfully added {len(teams)} teams")

    # ========================================================================
    # EMPLOYEE OPERATIONS
    # ========================================================================

    @deal.pre(lambda self, employee: isinstance(employee, Employee))
    @deal.post(lambda result: result is not None)
    async def _add_employee_node(self, employee: Employee) -> EntityNode:
        """
        Create employee node in graph (internal method)
        
        Args:
            employee: Employee model with validated data
            
        Returns:
            Created EntityNode for the employee
        """
        logger.debug(f"Creating employee node: {employee.name}", extra={"emp_id": employee.id})

        try:
            attributes = employee.attributes()
            node = EntityNode(
                name=employee.name,
                labels=["Employee"],
                attributes=attributes,
                group_id="",
            )

            await node.generate_name_embedding(self.graphiti.embedder)
            await node.save(self.graphiti.driver)

            logger.debug(
                f"Employee node created: {employee.name}",
                extra={"emp_id": employee.id, "node_uuid": node.uuid},
            )
            return node

        except Exception as e:
            error_msg = DB_CONFIG.get("errors", {}).get("employee_creation_failed", "Failed to create employee").format(reason=str(e))
            logger.error(f"{error_msg}: {employee.name}", exc_info=True)
            raise EntityCreationError(error_msg)

    @deal.pre(
        lambda self, employee, node, cache=None: isinstance(employee, Employee)
        and isinstance(node, EntityNode)
    )
    @deal.post(lambda result: result is None)
    async def _add_employee_to_dept(
        self,
        employee: Employee,
        node: EntityNode,
        cache: Optional[dict] = None,
    ):
        """
        Create MEMBER_OF edge from employee to department
        
        Uses cache to avoid repeated department lookups
        """
        logger.debug(
            f"Linking {employee.name} to department {employee.department}",
            extra={"emp_id": employee.id},
        )

        try:
            # Check cache first
            if cache is not None and employee.department in cache:
                dept_node = cache[employee.department]
                logger.debug(f"Department {employee.department} found in cache")
            else:
                dept_node = await self.find_department(employee.department)
                if cache is not None:
                    cache[employee.department] = dept_node

            # Create MEMBER_OF edge
            edge = EntityEdge(
                group_id="",
                source_node_uuid=node.uuid,
                target_node_uuid=dept_node.uuid,
                created_at=datetime.now(),
                name="MEMBER_OF",
                fact=f"{employee.name} is a member of {dept_node.name}",
            )

            await edge.generate_embedding(self.graphiti.embedder)
            await edge.save(self.graphiti.driver)

            logger.debug(
                f"MEMBER_OF edge created: {employee.name} -> {dept_node.name}"
            )

        except Exception as e:
            error_msg = DB_CONFIG.get("errors", {}).get("edge_creation_failed", "Failed to create edge").format(edge_type="MEMBER_OF", reason=str(e))
            logger.error(f"{error_msg}", exc_info=True)
            raise EdgeCreationError(error_msg)

    @deal.pre(
        lambda self, employee, node, cache=None: isinstance(employee, Employee)
        and isinstance(node, EntityNode)
    )
    @deal.post(lambda result: result is None)
    async def _add_employee_to_team(
        self,
        employee: Employee,
        node: EntityNode,
        cache: Optional[dict] = None,
    ):
        """
        Create MEMBER_OF edge from employee to team
        
        Uses cache to avoid repeated team lookups
        """
        logger.debug(
            f"Linking {employee.name} to team {employee.team}",
            extra={"emp_id": employee.id},
        )

        try:
            # Check cache first
            if cache is not None and employee.team in cache:
                team_node = cache[employee.team]
                logger.debug(f"Team {employee.team} found in cache")
            else:
                team_node = await self.find_team(employee.team)
                if cache is not None:
                    cache[employee.team] = team_node

            # Create MEMBER_OF edge
            edge = EntityEdge(
                group_id="",
                source_node_uuid=node.uuid,
                target_node_uuid=team_node.uuid,
                created_at=datetime.now(),
                name="MEMBER_OF",
                fact=f"{employee.name} is a member of {team_node.name}",
            )

            await edge.generate_embedding(self.graphiti.embedder)
            await edge.save(self.graphiti.driver)

            logger.debug(f"MEMBER_OF edge created: {employee.name} -> {team_node.name}")

        except Exception as e:
            error_msg = DB_CONFIG.get("errors", {}).get("edge_creation_failed", "Failed to create edge").format(edge_type="MEMBER_OF", reason=str(e))
            logger.error(f"{error_msg}", exc_info=True)
            raise EdgeCreationError(error_msg)

    @deal.pre(
        lambda self, employee, node: isinstance(employee, Employee)
        and isinstance(node, EntityNode)
    )
    @deal.post(lambda result: result is None)
    async def _add_employee_managers(self, employee: Employee, node: EntityNode):
        """
        Create REPORTS_TO edge from employee to their manager
        """
        logger.debug(
            f"Finding manager for {employee.name} in team {employee.team}",
            extra={"emp_id": employee.id},
        )

        try:
            manager_node = await self.find_manager_of_team(employee.team)
            
            # Skip if no manager found or employee is their own manager
            if not manager_node or manager_node.uuid == node.uuid:
                logger.debug(f"No manager found or self-manager for {employee.name}")
                return

            # Create REPORTS_TO edge
            edge = EntityEdge(
                group_id="",
                source_node_uuid=node.uuid,
                target_node_uuid=manager_node.uuid,
                created_at=datetime.now(),
                name="REPORTS_TO",
                fact=f"{employee.name} reports to {manager_node.name}",
            )

            await edge.generate_embedding(self.graphiti.embedder)
            await edge.save(self.graphiti.driver)

            logger.debug(
                f"REPORTS_TO edge created: {employee.name} -> {manager_node.name}"
            )

        except Exception as e:
            # Manager edge is optional, log but don't fail
            logger.warning(
                f"Could not create REPORTS_TO edge for {employee.name}: {e}"
            )

    @deal.pre(lambda self, employees: isinstance(employees, list) and len(employees) > 0)
    @deal.post(lambda result: result is None)
    async def add_employees(self, employees: List[Employee]):
        """
        Add multiple employees with all relationships in optimized batch operation
        
        This is the main method for loading employee data efficiently:
        1. Create all employee nodes in parallel
        2. Create department links in parallel (with caching)
        3. Create team links in parallel (with caching)
        4. Resolve team managers
        5. Create reporting relationships in parallel
        
        Args:
            employees: List of Employee models
        """
        logger.info(f"Adding {len(employees)} employees in batch")

        # Step 1: Create all employee nodes
        logger.info("Step 1/5: Creating employee nodes...")
        nodes = await asyncio.gather(
            *[self._add_employee_node(emp) for emp in employees]
        )
        logger.info(f"Created {len(nodes)} employee nodes")

        # Step 2: Create department links with caching
        logger.info("Step 2/5: Creating department links...")
        dept_cache = {}
        await asyncio.gather(
            *[
                self._add_employee_to_dept(emp, node, dept_cache)
                for emp, node in zip(employees, nodes)
            ]
        )
        logger.info(f"Created {len(employees)} department links")

        # Step 3: Create team links with caching
        logger.info("Step 3/5: Creating team links...")
        team_cache = {}
        await asyncio.gather(
            *[
                self._add_employee_to_team(emp, node, team_cache)
                for emp, node in zip(employees, nodes)
            ]
        )
        logger.info(f"Created {len(employees)} team links")

        # Step 4: Resolve team managers
        logger.info("Step 4/5: Resolving team managers...")
        await self._try_resolve_managers()

        # Step 5: Create reporting relationships
        logger.info("Step 5/5: Creating employee reporting relationships...")
        await asyncio.gather(
            *[
                self._add_employee_managers(emp, node)
                for emp, node in zip(employees, nodes)
            ]
        )

        logger.info(f"Successfully added {len(employees)} employees with all relationships")

    # ========================================================================
    # MANAGER RESOLUTION
    # ========================================================================

    @deal.pre(lambda self, team_node: isinstance(team_node, EntityNode))
    @deal.post(lambda result: result is None)
    async def _add_employee_manager(self, team_node: EntityNode):
        """
        Create MANAGES edge from team lead to team
        """
        team_name = team_node.name
        lead_name = team_node.attributes.get("lead")

        if not lead_name:
            logger.warning(f"Team {team_name} has no lead defined")
            return

        logger.debug(f"Resolving manager {lead_name} for team {team_name}")

        try:
            manager_node = await self.find_employee(lead_name)
            
            if not manager_node:
                logger.warning(f"Manager {lead_name} not found for team {team_name}")
                return

            edge = EntityEdge(
                group_id="",
                source_node_uuid=manager_node.uuid,
                target_node_uuid=team_node.uuid,
                created_at=datetime.now(),
                name="MANAGES",
                fact=f"{manager_node.name} manages {team_node.name}",
            )

            await edge.generate_embedding(self.graphiti.embedder)
            await edge.save(self.graphiti.driver)

            logger.info(f"MANAGES edge created: {manager_node.name} -> {team_name}")

        except Exception as e:
            logger.warning(f"Could not create MANAGES edge for team {team_name}: {e}")

    async def _find_teams_with_unresolved_managers(self) -> List[EntityNode]:
        """Find all teams that don't have a MANAGES relationship yet"""
        logger.debug("Finding teams with unresolved managers")

        try:
            records, _, _ = await self.graphiti.driver.execute_query(
                """
                MATCH (t:Team)
                OPTIONAL MATCH (n)-[r]->(t)
                WHERE r.name = "MANAGES"
                WITH t, r
                WHERE r IS NULL
                RETURN t.uuid
                """,
                routing_="r",
            )

            team_uuids = [record["t.uuid"] for record in records]
            logger.debug(f"Found {len(team_uuids)} teams with unresolved managers")

            return await EntityNode.get_by_uuids(self.graphiti.driver, team_uuids)

        except Exception as e:
            logger.error(f"Error finding unresolved teams: {e}", exc_info=True)
            return []

    async def _try_resolve_managers(self):
        """Attempt to resolve all unresolved team managers"""
        logger.info("Resolving team managers")

        teams = await self._find_teams_with_unresolved_managers()
        logger.info(f"Found {len(teams)} teams needing manager resolution")

        await asyncio.gather(*[self._add_employee_manager(team) for team in teams])
        logger.info("Manager resolution complete")

    # ========================================================================
    # SEARCH/QUERY OPERATIONS
    # ========================================================================

    @deal.pre(lambda self, name: isinstance(name, str) and len(name) > 0)
    async def find_employee(self, name: str) -> Optional[EntityNode]:
        """
        Find employee by name using semantic search
        
        Args:
            name: Employee name to search for
            
        Returns:
            EntityNode if found, None otherwise
        """
        logger.debug(f"Searching for employee: {name}")

        try:
            search_config = SearchConfig(
                node_config=NodeSearchConfig(
                    search_methods=[
                        NodeSearchMethod.bm25,
                        NodeSearchMethod.cosine_similarity,
                    ],
                ),
                limit=1,
            )
            search_filters = SearchFilters(node_labels=["Employee"])
            
            results = await self.graphiti.search_(
                name, config=search_config, search_filter=search_filters
            )

            if results.nodes:
                logger.debug(f"Found employee: {results.nodes[0].name}")
                return results.nodes[0]
            else:
                logger.debug(f"Employee not found: {name}")
                return None

        except Exception as e:
            logger.error(f"Error searching for employee {name}: {e}", exc_info=True)
            return None

    @deal.pre(lambda self, department: isinstance(department, str) and len(department) > 0)
    async def find_department(self, department: str) -> Optional[EntityNode]:
        """
        Find department by name using semantic search
        
        Args:
            department: Department name to search for
            
        Returns:
            EntityNode if found, None otherwise
            
        Raises:
            EntityNotFoundError: If department not found
        """
        logger.debug(f"Searching for department: {department}")

        try:
            search_config = SearchConfig(
                node_config=NodeSearchConfig(
                    search_methods=[
                        NodeSearchMethod.bm25,
                        NodeSearchMethod.cosine_similarity,
                    ],
                ),
                limit=1,
            )
            search_filters = SearchFilters(node_labels=["Department"])
            
            results = await self.graphiti.search_(
                f"Department: {department}",
                config=search_config,
                search_filter=search_filters,
            )

            if results.nodes:
                logger.debug(f"Found department: {results.nodes[0].name}")
                return results.nodes[0]
            else:
                error_msg = DB_CONFIG.get("errors", {}).get("entity_not_found", "Entity not found").format(
                    entity_name=department, entity_type="Department"
                )
                logger.error(error_msg)
                raise EntityNotFoundError(error_msg)

        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error searching for department {department}: {e}", exc_info=True)
            raise EntityNotFoundError(f"Failed to find department: {e}")

    @deal.pre(lambda self, team: isinstance(team, str) and len(team) > 0)
    async def find_team(self, team: str) -> Optional[EntityNode]:
        """
        Find team by name using semantic search
        
        Args:
            team: Team name to search for
            
        Returns:
            EntityNode if found, None otherwise
            
        Raises:
            EntityNotFoundError: If team not found
        """
        logger.debug(f"Searching for team: {team}")

        try:
            search_config = SearchConfig(
                node_config=NodeSearchConfig(
                    search_methods=[
                        NodeSearchMethod.bm25,
                        NodeSearchMethod.cosine_similarity,
                    ],
                ),
                limit=1,
            )
            search_filters = SearchFilters(node_labels=["Team"])
            
            results = await self.graphiti.search_(
                f"Team: {team}",
                config=search_config,
                search_filter=search_filters,
            )

            if results.nodes:
                logger.debug(f"Found team: {results.nodes[0].name}")
                return results.nodes[0]
            else:
                error_msg = DB_CONFIG.get("errors", {}).get("entity_not_found", "Entity not found").format(
                    entity_name=team, entity_type="Team"
                )
                logger.error(error_msg)
                raise EntityNotFoundError(error_msg)

        except EntityNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error searching for team {team}: {e}", exc_info=True)
            raise EntityNotFoundError(f"Failed to find team: {e}")

    @deal.pre(lambda self, team: isinstance(team, str) and len(team) > 0)
    async def find_manager_of_team(self, team: str) -> Optional[EntityNode]:
        """
        Find the manager (lead) of a team using edge search
        
        Args:
            team: Team name
            
        Returns:
            EntityNode of manager if found, None otherwise
        """
        logger.debug(f"Finding manager for team: {team}")

        try:
            search_config = SearchConfig(
                edge_config=EdgeSearchConfig(
                    search_methods=[
                        EdgeSearchMethod.bm25,
                        EdgeSearchMethod.cosine_similarity,
                    ],
                ),
                limit=1,
            )
            search_filters = SearchFilters(edge_types=["MANAGES"])
            
            results = await self.graphiti.search_(
                f"manages {team}",
                config=search_config,
                search_filter=search_filters,
            )

            if results.edges:
                manager_uuid = results.edges[0].source_node_uuid
                manager_node = await EntityNode.get_by_uuid(
                    self.graphiti.driver, manager_uuid
                )
                logger.debug(f"Found manager: {manager_node.name} for team {team}")
                return manager_node
            else:
                logger.debug(f"No manager found for team: {team}")
                return None

        except Exception as e:
            logger.error(f"Error finding manager for team {team}: {e}", exc_info=True)
            return None

    @deal.pre(lambda self, query: isinstance(query, str) and len(query) > 0)
    async def query(self, query: str) -> str:
        """
        Execute natural language query against the graph
        
        Args:
            query: Natural language query string
            
        Returns:
            Query results as string
        """
        logger.info(f"Executing query: {query}")

        try:
            result = await self.graphiti.search(query)
            logger.info(f"Query executed successfully")
            return result
        except Exception as e:
            logger.error(f"Query execution failed: {e}", exc_info=True)
            raise GraphitiClientError(f"Query failed: {e}")
