# core/graphiti_manager.py
"""
Graphiti Knowledge Graph Manager for Temporal Framework

This replaces direct Neo4j access with Graphiti as requested by management.
Graphiti provides a higher-level abstraction over Neo4j with built-in
knowledge graph capabilities.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

try:
    from graphiti_core import Graphiti
    # Don't import GraphitiConfig from graphiti - we'll define our own
    from graphiti_core.nodes import EntityNode, EpisodicNode
    from graphiti_core.edges import Edge
    GRAPHITI_AVAILABLE = True
except ImportError as e:
    # Fallback if Graphiti not installed
    print(f"Warning: Graphiti not installed. Using mock classes. Error: {e}")
    GRAPHITI_AVAILABLE = False
    
    class Graphiti:
        def __init__(self, *args, **kwargs): pass
        def close(self): pass
        def build_indices(self): pass
        def add_nodes(self, nodes): return [{"uuid": f"node-{i}"} for i in range(len(nodes))]
        def add_edges(self, edges): return [{"uuid": f"edge-{i}"} for i in range(len(edges))]
        def search(self, query): return []
        def add_entity(self, entity_data): return f"entity-{entity_data.get('id', 'unknown')}"

    class EntityNode:
        def __init__(self, *args, **kwargs): pass
    
    class EpisodeNode:
        def __init__(self, *args, **kwargs): pass
    
    class Edge:
        def __init__(self, *args, **kwargs): pass

@dataclass
class GraphitiConfig:
    """Configuration for Graphiti knowledge graph connection."""
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    team_namespace: str = "default"
    connection_timeout: int = 30
    max_retry_attempts: int = 3

from .tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple

logger = logging.getLogger(__name__)


class TemporalGraphitiManager:
    """
    Graphiti-based manager for temporal framework knowledge graph
    
    This provides the same interface as TemporalNeo4jManager but uses
    Graphiti's knowledge graph capabilities instead of direct Neo4j access.
    """
    
    def __init__(self, config: GraphitiConfig):
        """
        Initialize Graphiti connection
        
        Args:
            config: GraphitiConfig instance with connection details
        """
        self.config = config
        
        try:
            # Initialize Graphiti with proper parameters based on documentation
            self.graphiti = Graphiti(
                uri=self.config.neo4j_uri,
                user=self.config.neo4j_user,
                password=self.config.neo4j_password
            )
            # Note: build_indices() method not available in this version
            logger.info("Successfully initialized Graphiti knowledge graph")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise
    
    def close(self):
        """Close Graphiti connection"""
        try:
            if hasattr(self, 'graphiti'):
                # Graphiti close is async, skip for now
                logger.info("Graphiti connection cleanup (async method skipped)")
        except Exception as e:
            logger.warning(f"Error closing Graphiti connection: {e}")
    
    def create_temporal_context(self, context: TemporalContext) -> str:
        """
        Create TemporalContext as Graphiti entity
        
        Args:
            context: TemporalContext instance to store
            
        Returns:
            str: Entity ID of created context
        """
        try:
            # For now, return mock ID since Graphiti API is async
            # TODO: Implement proper async handling or use sync wrapper
            logger.warning("Graphiti integration requires async implementation - using mock ID")
            entity_id = context.node_id
            logger.info(f"Created TemporalContext entity (mock): {entity_id}")
            return entity_id
        except Exception as e:
            logger.error(f"Failed to create TemporalContext: {e}")
            return context.node_id
    
    def create_time_window(self, window: TimeWindow) -> str:
        """
        Create TimeWindow as Graphiti entity
        
        Args:
            window: TimeWindow instance to store
            
        Returns:
            str: Entity ID of created window
        """
        entity_data = {
            "id": window.node_id,
            "type": "TimeWindow",
            "name": f"Time Window ({window.window_type})",
            "description": f"Time window for {window.window_type}: {window.description or 'Access window'}",
            "properties": window.to_dict(),
            "team": "llm_security"
        }
        
        entity = self.graphiti.add_entity(
            name=entity_data["name"],
            entity_type=entity_data["type"],
            properties=entity_data["properties"],
            summary=entity_data["description"]
        )
        
        logger.info(f"Created TimeWindow entity: {entity.id}")
        return entity.id
    
    def create_6_tuple(self, tuple_6: EnhancedContextualIntegrityTuple) -> Dict[str, str]:
        """
        Create 6-tuple (AccessTuple + TemporalContext) in Graphiti
        
        Args:
            tuple_6: EnhancedContextualIntegrityTuple instance
            
        Returns:
            Dict with created entity IDs
        """
        # First create temporal context entity
        tc_id = self.create_temporal_context(tuple_6.temporal_context)
        
        # Create AccessTuple entity
        tuple_data = {
            "id": f"at_{tuple_6.temporal_context.node_id[3:]}",
            "type": "AccessTuple",
            "name": f"Access Tuple ({tuple_6.data_type})",
            "description": self._generate_tuple_description(tuple_6),
            "properties": {
                "data_type": tuple_6.data_type,
                "data_subject": tuple_6.data_subject,
                "data_sender": tuple_6.data_sender,
                "data_recipient": tuple_6.data_recipient,
                "transmission_principle": tuple_6.transmission_principle,
                "team": "llm_security"
            }
        }
        
        tuple_entity = self.graphiti.add_entity(
            name=tuple_data["name"],
            entity_type=tuple_data["type"],
            properties=tuple_data["properties"],
            summary=tuple_data["description"]
        )
        
        # Create relationship between AccessTuple and TemporalContext
        self.graphiti.add_edge(
            source_id=tuple_entity.id,
            target_id=tc_id,
            relation_type="HAS_TEMPORAL_CONTEXT",
            summary=f"Access tuple has temporal context for {tuple_6.temporal_context.situation}"
        )
        
        logger.info(f"Created 6-tuple: {tuple_entity.id} -> {tc_id}")
        return {
            "tuple_id": tuple_entity.id,
            "context_id": tc_id
        }
    
    def find_temporal_contexts_by_service(self, service_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find temporal contexts for a specific service using Graphiti search"""
        search_query = f"temporal contexts for service {service_id}"
        
        search_results = self.graphiti.search(
            query=search_query,
            limit=limit,
            center_node_type="TemporalContext"
        )
        
        results = []
        for result in search_results:
            if result.entity_type == "TemporalContext":
                # Get related service information
                service_edges = self.graphiti.get_edges(
                    source_id=result.id,
                    relation_type="APPLIES_TO_SERVICE"
                )
                
                service_info = None
                for edge in service_edges:
                    service_entity = self.graphiti.get_entity(edge.target_id)
                    if service_entity and service_entity.properties.get("id") == service_id:
                        service_info = service_entity.properties
                        break
                
                if service_info:
                    results.append({
                        "temporal_context": result.properties,
                        "service": service_info
                    })
        
        return results
    
    def find_emergency_contexts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Find all emergency temporal contexts using Graphiti search"""
        search_query = "emergency temporal contexts with emergency override"
        
        search_results = self.graphiti.search(
            query=search_query,
            limit=limit,
            center_node_type="TemporalContext"
        )
        
        results = []
        for result in search_results:
            if (result.entity_type == "TemporalContext" and 
                result.properties.get("emergency_override") == True):
                
                # Get related incident and service information
                incident_info = self._get_related_entity(result.id, "RELATES_TO_INCIDENT", "Incident")
                service_info = self._get_related_entity(result.id, "APPLIES_TO_SERVICE", "Service")
                
                result_data = {"temporal_context": result.properties}
                if incident_info:
                    result_data["incident"] = incident_info
                if service_info:
                    result_data["service"] = service_info
                
                results.append(result_data)
        
        return results
    
    def get_temporal_access_patterns(self) -> Dict[str, Any]:
        """Analyze temporal access patterns using Graphiti analytics"""
        patterns = {
            "emergency_situations": [],
            "business_hours_distribution": [],
            "timezone_distribution": []
        }
        
        # Search for all temporal contexts
        all_contexts = self.graphiti.search(
            query="all temporal contexts",
            limit=1000,
            center_node_type="TemporalContext"
        )
        
        # Analyze patterns
        emergency_situations = {}
        business_hours_dist = {"True": 0, "False": 0}
        timezone_dist = {}
        
        for context in all_contexts:
            if context.entity_type == "TemporalContext":
                props = context.properties
                
                # Emergency situations
                if props.get("emergency_override"):
                    situation = props.get("situation", "UNKNOWN")
                    emergency_situations[situation] = emergency_situations.get(situation, 0) + 1
                
                # Business hours distribution
                bh = str(props.get("business_hours", False))
                business_hours_dist[bh] += 1
                
                # Timezone distribution
                tz = props.get("timezone", "UTC")
                timezone_dist[tz] = timezone_dist.get(tz, 0) + 1
        
        # Convert to expected format
        patterns["emergency_situations"] = [
            {"situation": k, "count": v} for k, v in emergency_situations.items()
        ]
        patterns["business_hours_distribution"] = [
            {"in_business_hours": k == "True", "count": v} for k, v in business_hours_dist.items()
        ]
        patterns["timezone_distribution"] = [
            {"timezone": k, "count": v} for k, v in timezone_dist.items()
        ]
        
        return patterns
    
    def cleanup_test_data(self):
        """Clean up test data (use with caution!)"""
        # Search for all entities with team = llm_security
        test_entities = self.graphiti.search(
            query="test data llm_security team",
            limit=1000
        )
        
        deleted_count = 0
        for entity in test_entities:
            if entity.properties.get("team") == "llm_security":
                # Check if it's test data (node_id starts with tc_, tw_, or at_)
                node_id = entity.properties.get("node_id", "")
                if (node_id.startswith("tc_") or 
                    node_id.startswith("tw_") or 
                    entity.properties.get("tuple_id", "").startswith("at_")):
                    
                    self.graphiti.delete_entity(entity.id)
                    deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} test entities")
    
    def _generate_context_description(self, context: TemporalContext) -> str:
        """Generate natural language description for temporal context"""
        desc = f"Temporal context for {context.situation or 'normal'} situation"
        
        if context.emergency_override:
            desc += " with emergency override active"
        
        if context.service_id:
            desc += f" affecting {context.service_id} service"
        
        if context.temporal_role:
            desc += f" involving {context.temporal_role} role"
        
        desc += f" at {context.timestamp.isoformat()}"
        
        if not context.business_hours:
            desc += " outside business hours"
        
        return desc
    
    def _generate_tuple_description(self, tuple_6: EnhancedContextualIntegrityTuple) -> str:
        """Generate natural language description for access tuple"""
        return (f"Access tuple for {tuple_6.data_type} data from {tuple_6.data_sender} "
                f"to {tuple_6.data_recipient} using {tuple_6.transmission_principle} principle")
    
    def _create_graphiti_relationships(self, context: TemporalContext, entity_id: str):
        """Create relationships for TemporalContext in Graphiti"""
        relationships = context.get_relationships()
        
        for rel_type, target_id in relationships.items():
            # Create or get target entity
            target_entity = self._ensure_related_entity(rel_type, target_id)
            
            if target_entity:
                # Create edge
                self.graphiti.add_edge(
                    source_id=entity_id,
                    target_id=target_entity.id,
                    relation_type=rel_type,
                    summary=f"Temporal context {rel_type.lower().replace('_', ' ')} {target_id}"
                )
    
    def _ensure_related_entity(self, rel_type: str, target_id: str):
        """Ensure related entity exists in Graphiti"""
        # Map relationship types to entity types
        entity_type_map = {
            "RELATES_TO_INCIDENT": "Incident",
            "APPLIES_TO_SERVICE": "Service", 
            "GOVERNS_USER": "User",
            "HAS_ACCESS_WINDOW": "TimeWindow"
        }
        
        entity_type = entity_type_map.get(rel_type, "Entity")
        
        # Try to find existing entity
        search_results = self.graphiti.search(
            query=f"{entity_type} {target_id}",
            limit=1,
            center_node_type=entity_type
        )
        
        if search_results:
            return search_results[0]
        
        # Create new entity if not found
        return self.graphiti.add_entity(
            name=f"{entity_type} {target_id}",
            entity_type=entity_type,
            properties={"id": target_id, "team": "llm_security"},
            summary=f"{entity_type} entity for {target_id}"
        )
    
    def _get_related_entity(self, source_id: str, relation_type: str, entity_type: str):
        """Get related entity information"""
        edges = self.graphiti.get_edges(
            source_id=source_id,
            relation_type=relation_type
        )
        
        for edge in edges:
            entity = self.graphiti.get_entity(edge.target_id)
            if entity and entity.entity_type == entity_type:
                return entity.properties
        
        return None

    def search_entities(self, entity_type: str = None, filters: Dict[str, Any] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for entities in the Graphiti knowledge graph
        
        Args:
            entity_type: Type of entities to search for
            filters: Dictionary of property filters
            limit: Maximum number of results
            
        Returns:
            List of entity dictionaries with properties
        """
        try:
            # For now, return empty list since Graphiti API is async
            # TODO: Implement proper async handling or sync wrapper
            logger.warning("Graphiti search requires async implementation - returning empty results")
            return []
            
        except Exception as e:
            logger.error(f"Error searching entities in Graphiti: {e}")
            return []


def get_company_graphiti_manager(password: str = None) -> TemporalGraphitiManager:
    """
    Get Graphiti manager for company Neo4j server using knowledge graph abstraction
    
    Args:
        password: Neo4j password (if not provided, uses NEO4J_PASSWORD env var)
        
    Returns:
        TemporalGraphitiManager connected to company server via Graphiti
        
    Raises:
        ValueError: If password not provided and NEO4J_PASSWORD not set
    """
    neo4j_password = password or os.getenv('NEO4J_PASSWORD')
    
    if not neo4j_password:
        raise ValueError(
            "Neo4j password required for company Graphiti server. "
            "Set NEO4J_PASSWORD environment variable or pass password parameter."
        )
    
    config = GraphitiConfig(
        neo4j_uri="bolt://ssh.phorena.com:57687",  # Company Neo4j server
        neo4j_user="llm_security",                 # LLM Security team user
        neo4j_password=neo4j_password,
        team_namespace="llm_security"              # Team isolation
    )
    
    return TemporalGraphitiManager(config)


def get_local_graphiti_manager(password: str = "test") -> TemporalGraphitiManager:
    """
    Get Graphiti manager for local development (redirected to company server for consistency)
    
    Args:
        password: Neo4j password for local development
        
    Returns:
        TemporalGraphitiManager (connects to company server for consistency)
    """
    # For consistency, always use company server
    return get_company_graphiti_manager(password)