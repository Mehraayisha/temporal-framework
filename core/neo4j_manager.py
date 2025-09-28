# core/neo4j_manager.py
from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
import os
from .tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple

logger = logging.getLogger(__name__)

class TemporalNeo4jManager:
    """Neo4j database manager for temporal framework"""
    
    def __init__(self, uri: str, username: str, password: str):
        """
        Initialize Neo4j connection for temporal framework
        
        Args:
            uri: Neo4j connection URI (e.g., "neo4j://localhost:7687")
            username: Neo4j username
            password: Neo4j password
        """
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = None
        self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 'Neo4j connection successful' as message")
                logger.info(result.single()["message"])
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
    
    def create_temporal_context(self, context: TemporalContext) -> str:
        """
        Create TemporalContext node in Neo4j
        
        Args:
            context: TemporalContext instance to store
            
        Returns:
            str: Node ID of created context
        """
        with self.driver.session() as session:
            # Create the TemporalContext node
            query = """
            MERGE (tc:TemporalContext {node_id: $node_id})
            SET tc += $properties
            SET tc.team = 'llm_security'
            SET tc.last_updated = datetime()
            RETURN tc.node_id as created_id
            """
            
            result = session.run(query,
                node_id=context.node_id,
                properties=context.get_graph_properties()
            )
            
            created_id = result.single()["created_id"]
            
            # Create relationships
            self._create_relationships(session, context)
            
            logger.info(f"Created TemporalContext node: {created_id}")
            return created_id
    
    def create_time_window(self, window: TimeWindow) -> str:
        """
        Create TimeWindow node in Neo4j
        
        Args:
            window: TimeWindow instance to store
            
        Returns:
            str: Node ID of created window
        """
        with self.driver.session() as session:
            query = """
            MERGE (tw:TimeWindow {node_id: $node_id})
            SET tw.start = datetime($start)
            SET tw.end = datetime($end)
            SET tw.window_type = $window_type
            SET tw.description = $description
            SET tw.created_at = datetime($created_at)
            SET tw.team = 'llm_security'
            RETURN tw.node_id as created_id
            """
            
            result = session.run(query,
                node_id=window.node_id,
                start=window.start.isoformat() if window.start else None,
                end=window.end.isoformat() if window.end else None,
                window_type=window.window_type,
                description=window.description,
                created_at=window.created_at.isoformat()
            )
            
            created_id = result.single()["created_id"]
            logger.info(f"Created TimeWindow node: {created_id}")
            return created_id
    
    def create_6_tuple(self, tuple_6: EnhancedContextualIntegrityTuple) -> Dict[str, str]:
        """
        Create 6-tuple (AccessTuple + TemporalContext) in Neo4j
        
        Args:
            tuple_6: EnhancedContextualIntegrityTuple instance
            
        Returns:
            Dict with created node IDs
        """
        with self.driver.session() as session:
            # First create temporal context
            tc_id = self.create_temporal_context(tuple_6.temporal_context)
            
            # Create AccessTuple node
            tuple_id = f"at_{tuple_6.temporal_context.node_id[3:]}"  # Use same suffix
            
            query = """
            CREATE (at:AccessTuple {
                tuple_id: $tuple_id,
                data_type: $data_type,
                data_subject: $data_subject,
                data_sender: $data_sender,
                data_recipient: $data_recipient,
                transmission_principle: $transmission_principle,
                created_at: datetime(),
                team: 'llm_security'
            })
            WITH at
            MATCH (tc:TemporalContext {node_id: $tc_id})
            CREATE (at)-[:HAS_TEMPORAL_CONTEXT]->(tc)
            RETURN at.tuple_id as tuple_id, tc.node_id as context_id
            """
            
            result = session.run(query,
                tuple_id=tuple_id,
                data_type=tuple_6.data_type,
                data_subject=tuple_6.data_subject,
                data_sender=tuple_6.data_sender,
                data_recipient=tuple_6.data_recipient,
                transmission_principle=tuple_6.transmission_principle,
                tc_id=tc_id
            )
            
            record = result.single()
            logger.info(f"Created 6-tuple: {record['tuple_id']} -> {record['context_id']}")
            return {
                "tuple_id": record["tuple_id"],
                "context_id": record["context_id"]
            }
    
    def _create_relationships(self, session, context: TemporalContext):
        """Create relationships for TemporalContext"""
        relationships = context.get_relationships()
        
        for rel_type, target_id in relationships.items():
            if rel_type == "RELATES_TO_INCIDENT":
                session.run("""
                    MATCH (tc:TemporalContext {node_id: $tc_id})
                    MERGE (i:Incident {id: $incident_id, team: 'llm_security'})
                    MERGE (tc)-[:RELATES_TO_INCIDENT]->(i)
                """, tc_id=context.node_id, incident_id=target_id)
                
            elif rel_type == "APPLIES_TO_SERVICE":
                session.run("""
                    MATCH (tc:TemporalContext {node_id: $tc_id})
                    MERGE (s:Service {id: $service_id, team: 'llm_security'})
                    MERGE (tc)-[:APPLIES_TO_SERVICE]->(s)
                """, tc_id=context.node_id, service_id=target_id)
                
            elif rel_type == "GOVERNS_USER":
                session.run("""
                    MATCH (tc:TemporalContext {node_id: $tc_id})
                    MERGE (u:User {id: $user_id, team: 'llm_security'})
                    MERGE (tc)-[:GOVERNS_USER]->(u)
                """, tc_id=context.node_id, user_id=target_id)
                
            elif rel_type == "HAS_ACCESS_WINDOW":
                session.run("""
                    MATCH (tc:TemporalContext {node_id: $tc_id})
                    MATCH (tw:TimeWindow {node_id: $tw_id})
                    MERGE (tc)-[:HAS_ACCESS_WINDOW]->(tw)
                """, tc_id=context.node_id, tw_id=target_id)
    
    def find_temporal_contexts_by_service(self, service_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find temporal contexts for a specific service"""
        with self.driver.session() as session:
            query = """
            MATCH (tc:TemporalContext)-[:APPLIES_TO_SERVICE]->(s:Service {id: $service_id})
            WHERE tc.team = 'llm_security'
            RETURN tc, s
            ORDER BY tc.timestamp DESC
            LIMIT $limit
            """
            
            results = []
            for record in session.run(query, service_id=service_id, limit=limit):
                results.append({
                    "temporal_context": dict(record["tc"]),
                    "service": dict(record["s"])
                })
            
            return results
    
    def find_emergency_contexts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Find all emergency temporal contexts"""
        with self.driver.session() as session:
            query = """
            MATCH (tc:TemporalContext {emergency_override: true, team: 'llm_security'})
            OPTIONAL MATCH (tc)-[:RELATES_TO_INCIDENT]->(i:Incident)
            OPTIONAL MATCH (tc)-[:APPLIES_TO_SERVICE]->(s:Service)
            RETURN tc, i, s
            ORDER BY tc.timestamp DESC
            LIMIT $limit
            """
            
            results = []
            for record in session.run(query, limit=limit):
                result = {"temporal_context": dict(record["tc"])}
                if record["i"]:
                    result["incident"] = dict(record["i"])
                if record["s"]:
                    result["service"] = dict(record["s"])
                results.append(result)
            
            return results
    
    def get_temporal_access_patterns(self) -> Dict[str, Any]:
        """Analyze temporal access patterns"""
        with self.driver.session() as session:
            # Emergency access patterns
            emergency_query = """
            MATCH (tc:TemporalContext {emergency_override: true, team: 'llm_security'})
            RETURN 
                tc.situation as situation,
                count(*) as count
            ORDER BY count DESC
            """
            
            # Business hours patterns
            business_hours_query = """
            MATCH (tc:TemporalContext {team: 'llm_security'})
            RETURN 
                tc.business_hours as in_business_hours,
                count(*) as count
            """
            
            # Time zone distribution
            timezone_query = """
            MATCH (tc:TemporalContext {team: 'llm_security'})
            RETURN 
                tc.timezone as timezone,
                count(*) as count
            ORDER BY count DESC
            """
            
            patterns = {}
            
            # Get emergency patterns
            patterns["emergency_situations"] = [
                dict(record) for record in session.run(emergency_query)
            ]
            
            # Get business hours patterns
            patterns["business_hours_distribution"] = [
                dict(record) for record in session.run(business_hours_query)
            ]
            
            # Get timezone patterns
            patterns["timezone_distribution"] = [
                dict(record) for record in session.run(timezone_query)
            ]
            
            return patterns
    
    def cleanup_test_data(self):
        """Clean up test data (use with caution!)"""
        with self.driver.session() as session:
            query = """
            MATCH (n {team: 'llm_security'})
            WHERE n.node_id STARTS WITH 'tc_' OR n.node_id STARTS WITH 'tw_' OR n.tuple_id STARTS WITH 'at_'
            DETACH DELETE n
            """
            
            result = session.run(query)
            logger.info("Cleaned up test data")


class Neo4jConfig:
    """
    Configuration for Neo4j connection
    
    Note from Lawrence: "Try not to access Neo4j directly. This is the mail that I got from my boss 
    for using the Neo4J." - Use this framework as the abstraction layer.
    """
    
    # Company Neo4j server (from Lawrence's email)
    COMPANY_URI = "neo4j://ssh.phorena.com:57687"
    COMPANY_USERNAME = "llm_security"
    COMPANY_PASSWORD = None  # Use environment variable NEO4J_PASSWORD
    
    # Local development
    LOCAL_URI = "neo4j://localhost:7687"
    LOCAL_USERNAME = "neo4j"
    LOCAL_PASSWORD = "temporal123"
    
    @classmethod
    def get_company_manager(cls, password: str = None) -> TemporalNeo4jManager:
        """Get manager for company Neo4j server"""
        # Priority: parameter > environment variable > error
        neo4j_password = password or os.getenv('NEO4J_PASSWORD')
        
        if not neo4j_password:
            raise ValueError(
                "Neo4j password required. Set NEO4J_PASSWORD environment variable or pass password parameter."
            )
            
        return TemporalNeo4jManager(
            uri=cls.COMPANY_URI,
            username=cls.COMPANY_USERNAME,
            password=neo4j_password
        )
    
    @classmethod
    def get_local_manager(cls, password: str = None) -> TemporalNeo4jManager:
        """Get manager for company Neo4j server (redirected from local for convenience)"""
        # Priority: parameter > environment variable > error
        neo4j_password = password or os.getenv('NEO4J_PASSWORD')
        
        if not neo4j_password:
            raise ValueError(
                "Neo4j password required. Set NEO4J_PASSWORD environment variable or pass password parameter."
            )
            
        return TemporalNeo4jManager(
            uri=cls.COMPANY_URI,
            username=cls.COMPANY_USERNAME,
            password=neo4j_password
        )