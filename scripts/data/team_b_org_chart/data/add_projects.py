"""
Dynamic Project Ingestion Script

This script demonstrates adding projects dynamically to the existing graph.
Tests the architecture's ability to handle incremental updates without full reload.

The LLM data team will use similar patterns for dynamic org chart updates.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.graphiti_client import GraphitiClient
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ProjectIngestionError(Exception):
    """Custom exception for project ingestion errors"""
    pass


async def load_projects_from_json(file_path: Path = None) -> List[Dict]:
    """Load project data from org_data.json"""
    if file_path is None:
        file_path = Path(__file__).parent / "org_data.json"
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        projects = data.get("projects", [])
        logger.info(f"✅ Loaded {len(projects)} projects from {file_path.name}")
        return projects
    except FileNotFoundError:
        logger.error(f"❌ Data file not found: {file_path}")
        raise ProjectIngestionError(f"Data file not found: {file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in data file: {e}")
        raise ProjectIngestionError(f"Invalid JSON: {e}")


async def find_employee_by_name(client: GraphitiClient, name: str) -> EntityNode:
    """Find an employee entity by name"""
    result = await client.driver.execute_query(
        """
        MATCH (e:Entity:Employee)
        WHERE e.name = $name
        RETURN e
        LIMIT 1
        """,
        name=name,
        routing_='r'
    )
    
    if result[0]:
        return result[0][0]["e"]
    return None


async def find_department_by_name(client: GraphitiClient, name: str) -> EntityNode:
    """Find a department entity by name"""
    result = await client.driver.execute_query(
        """
        MATCH (d:Entity:Department)
        WHERE d.name = $name
        RETURN d
        LIMIT 1
        """,
        name=name,
        routing_='r'
    )
    
    if result[0]:
        return result[0][0]["d"]
    return None


async def project_exists(client: GraphitiClient, project_id: str) -> bool:
    """Check if project already exists in database"""
    result = await client.driver.execute_query(
        """
        MATCH (p:Entity:Project)
        WHERE p.id = $project_id
        RETURN count(p) > 0 as exists
        """,
        project_id=project_id,
        routing_='r'
    )
    
    return result[0][0]["exists"] if result[0] else False


async def add_project(client: GraphitiClient, project_data: Dict) -> EntityNode:
    """
    Dynamically add a single project to the graph
    
    Creates:
    - Project entity node
    - Relationships to project lead (employee)
    - Relationships to team members (employees)
    - Relationship to department
    """
    project_id = project_data["id"]
    project_name = project_data["name"]
    
    # Check if already exists
    if await project_exists(client, project_id):
        logger.warning(f"⚠️  Project {project_id} already exists, skipping...")
        return None
    
    logger.info(f"🚀 Adding project: {project_name} ({project_id})")
    
    # Create project entity directly
    logger.info("   Creating Project entity...")
    result = await client.driver.execute_query(
        """
        CREATE (p:Entity:Project {
            id: $id,
            name: $name,
            description: $description,
            status: $status,
            start_date: $start_date,
            end_date: $end_date,
            budget: $budget,
            data_classification: $classification,
            created_at: datetime()
        })
        RETURN p
        """,
        id=project_id,
        name=project_name,
        description=project_data.get("description", ""),
        status=project_data.get("status", "active"),
        start_date=project_data.get("start_date", ""),
        end_date=project_data.get("end_date", ""),
        budget=float(project_data.get("budget", 0)),
        classification=project_data.get("data_classification", "internal"),
        routing_='w'
    )
    project_node = result[0][0]["p"] if result[0] else None
    
    if not project_node:
        raise ProjectIngestionError(f"Failed to create project node for {project_id}")
    
    logger.info(f"   ✓ Created project node")
    
    # Link project lead
    project_lead = project_data.get("project_lead")
    if project_lead:
        lead_node = await find_employee_by_name(client, project_lead)
        if lead_node:
            await client.driver.execute_query(
                """
                MATCH (e:Entity:Employee {name: $lead_name})
                MATCH (p:Entity:Project {id: $project_id})
                CREATE (e)-[r:RELATES_TO {
                    fact: $lead_name + ' leads project ' + $project_name,
                    created_at: datetime()
                }]->(p)
                """,
                lead_name=project_lead,
                project_id=project_id,
                project_name=project_name,
                routing_='w'
            )
            logger.info(f"   ✓ Linked project lead: {project_lead}")
        else:
            logger.warning(f"   ⚠️  Project lead not found: {project_lead}")
    
    # Link team members
    team_members = project_data.get("team_members", [])
    linked_members = 0
    for member_name in team_members:
        member_node = await find_employee_by_name(client, member_name)
        if member_node:
            await client.driver.execute_query(
                """
                MATCH (e:Entity:Employee {name: $member_name})
                MATCH (p:Entity:Project {id: $project_id})
                CREATE (e)-[r:RELATES_TO {
                    fact: $member_name + ' working on project ' + $project_name,
                    created_at: datetime()
                }]->(p)
                """,
                member_name=member_name,
                project_id=project_id,
                project_name=project_name,
                routing_='w'
            )
            linked_members += 1
        else:
            logger.warning(f"   ⚠️  Team member not found: {member_name}")
    
    logger.info(f"   ✓ Linked {linked_members}/{len(team_members)} team members")
    
    # Link to department
    dept_name = project_data.get("department")
    if dept_name:
        dept_node = await find_department_by_name(client, dept_name)
        if dept_node:
            await client.driver.execute_query(
                """
                MATCH (p:Entity:Project {id: $project_id})
                MATCH (d:Entity:Department {name: $dept_name})
                CREATE (p)-[r:RELATES_TO {
                    fact: $project_name + ' belongs to department ' + $dept_name,
                    created_at: datetime()
                }]->(d)
                """,
                project_id=project_id,
                project_name=project_name,
                dept_name=dept_name,
                routing_='w'
            )
            logger.info(f"   ✓ Linked to department: {dept_name}")
        else:
            logger.warning(f"   ⚠️  Department not found: {dept_name}")
    
    logger.info(f"✅ Successfully added project: {project_name}")
    return project_node


async def verify_projects(client: GraphitiClient):
    """Verify projects and their relationships"""
    logger.info("\n" + "=" * 70)
    logger.info("VERIFICATION - Projects in Database")
    logger.info("=" * 70)
    
    # Count projects
    result = await client.driver.execute_query(
        """
        MATCH (p:Entity:Project)
        RETURN count(p) as count
        """,
        routing_='r'
    )
    project_count = result[0][0]["count"] if result[0] else 0
    logger.info(f"\n📊 Total Projects: {project_count}")
    
    # Get project details
    result = await client.driver.execute_query(
        """
        MATCH (p:Entity:Project)
        OPTIONAL MATCH (lead:Entity:Employee)-[rl:RELATES_TO]->(p)
        WHERE rl.fact CONTAINS 'leads project'
        OPTIONAL MATCH (member:Entity:Employee)-[rm:RELATES_TO]->(p)
        WHERE rm.fact CONTAINS 'working on project'
        WITH p, lead, collect(DISTINCT member.name) as members
        RETURN p.id as id, p.name as name, p.status as status, 
               lead.name as lead, size(members) as member_count
        ORDER BY p.name
        """,
        routing_='r'
    )
    
    if result[0]:
        logger.info("\n📋 Project Details:")
        for record in result[0]:
            logger.info(f"\n  • {record['name']} ({record['id']})")
            logger.info(f"    Status: {record['status']}")
            logger.info(f"    Lead: {record['lead'] or 'N/A'}")
            logger.info(f"    Team Members: {record['member_count']}")
    
    logger.info("\n" + "=" * 70)


async def main():
    """Main execution function"""
    logger.info("=" * 70)
    logger.info("DYNAMIC PROJECT INGESTION")
    logger.info("=" * 70)
    logger.info("Testing incremental updates to the organizational graph\n")
    
    try:
        # Initialize client
        client = GraphitiClient()
        logger.info("✅ Connected to Neo4j\n")
        
        # Load projects from JSON
        projects = await load_projects_from_json()
        
        if not projects:
            logger.warning("⚠️  No projects found in org_data.json")
            return
        
        # Add each project dynamically
        logger.info(f"📥 Processing {len(projects)} projects...\n")
        added_count = 0
        
        for project_data in projects:
            try:
                result = await add_project(client, project_data)
                if result:
                    added_count += 1
                print()  # Blank line between projects
            except Exception as e:
                logger.error(f"❌ Failed to add project {project_data.get('id')}: {e}")
                continue
        
        logger.info(f"\n✅ Successfully added {added_count}/{len(projects)} projects")
        
        # Verify results
        await verify_projects(client)
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ DYNAMIC INGESTION COMPLETE")
        logger.info("=" * 70)
        logger.info("\n💡 The system successfully handled dynamic updates!")
        logger.info("   LLM data team can use similar patterns for org changes.\n")
        
    except Exception as e:
        logger.error(f"\n❌ Error during project ingestion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
