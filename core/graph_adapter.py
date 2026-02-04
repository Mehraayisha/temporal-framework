# core/graph_adapter.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import logging
from core.tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple

logger = logging.getLogger(__name__)


class GraphAdapter:
    """
    Adapter for integrating temporal framework with Neo4j and Graphiti
    """
    
    def __init__(self):
        self.node_labels = {
            "TemporalContext": "TemporalContext",
            "TimeWindow": "TimeWindow", 
            "Incident": "Incident",
            "Service": "Service",
            "User": "User",
            "PolicyRule": "PolicyRule"
        }
        
    def temporal_context_to_graph_node(self, context: TemporalContext) -> Dict[str, Any]:
        """
        Convert TemporalContext to Neo4j node format
        """
        return {
            "labels": [self.node_labels["TemporalContext"]],
            "properties": context.get_graph_properties(),
            "node_id": context.node_id
        }
    
    def time_window_to_graph_node(self, window: TimeWindow) -> Dict[str, Any]:
        """
        Convert TimeWindow to Neo4j node format
        """
        return {
            "labels": [self.node_labels["TimeWindow"]],
            "properties": {
                "node_id": window.node_id,
                "start": window.start.isoformat() if window.start else None,
                "end": window.end.isoformat() if window.end else None,
                "window_type": window.window_type,
                "description": window.description,
                "created_at": window.created_at.isoformat(),
            },
            "node_id": window.node_id
        }
    
    def create_temporal_relationships(self, context: TemporalContext) -> List[Dict[str, Any]]:
        """
        Create relationship definitions for temporal context
        """
        relationships = []
        
        for rel_type, target_id in context.get_relationships().items():
            relationships.append({
                "type": rel_type,
                "start_node": context.node_id,
                "end_node": target_id,
                "properties": {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "strength": self._calculate_relationship_strength(rel_type, context)
                }
            })
        
        return relationships
    
    def _calculate_relationship_strength(self, rel_type: str, context: TemporalContext) -> float:
        """
        Calculate relationship strength for graph analytics
        """
        base_strength = 1.0
        
        if context.emergency_override:
            base_strength *= 1.5
        
        if rel_type == "RELATES_TO_INCIDENT" and context.situation == "EMERGENCY":
            base_strength *= 2.0
        
        if not context.business_hours:
            base_strength *= 0.8
        
        return min(base_strength, 3.0)  # Cap at 3.0
    
    def create_cypher_queries(self, context: TemporalContext) -> Dict[str, str]:
        """
        Generate Cypher queries for Neo4j operations
        """
        queries = {}
        
        # Create TemporalContext node
        node_props = context.get_graph_properties()
        prop_string = ", ".join([f"{k}: ${k}" for k in node_props.keys()])
        
        queries["create_context"] = f"""
        CREATE (tc:TemporalContext {{{prop_string}}})
        RETURN tc.node_id as node_id
        """
        
        # Find related temporal contexts
        queries["find_related"] = f"""
        MATCH (tc:TemporalContext {{node_id: $node_id}})
        OPTIONAL MATCH (tc)-[r]-(related)
        RETURN tc, r, related
        """
        
        # Update temporal context
        queries["update_context"] = f"""
        MATCH (tc:TemporalContext {{node_id: $node_id}})
        SET tc.updated_at = $updated_at,
            tc.situation = $situation,
            tc.emergency_override = $emergency_override
        RETURN tc
        """
        
        return queries
    
    def prepare_graphiti_format(self, context: TemporalContext) -> Dict[str, Any]:
        """
        Prepare data for Graphiti knowledge graph format
        """
        return {
            "entity": {
                "id": context.node_id,
                "type": "TemporalContext",
                "properties": context.get_graph_properties(),
                "embeddings": self._generate_embeddings_metadata(context)
            },
            "relationships": [
                {
                    "from": context.node_id,
                    "to": target_id,
                    "type": rel_type,
                    "properties": {
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "temporal_weight": self._calculate_relationship_strength(rel_type, context)
                    }
                }
                for rel_type, target_id in context.get_relationships().items()
            ]
        }
    
    def _generate_embeddings_metadata(self, context: TemporalContext) -> Dict[str, Any]:
        """
        Generate metadata for embedding generation in Graphiti
        """
        text_representation = f"""
        Temporal context for {context.situation} situation at {context.timestamp.isoformat()}.
        Business hours: {context.business_hours}, Emergency: {context.emergency_override}.
        Role: {context.temporal_role or 'standard'}, Timezone: {context.timezone}.
        """
        
        return {
            "text": text_representation.strip(),
            "temporal_features": {
                "hour_of_day": context.timestamp.hour,
                "day_of_week": context.timestamp.weekday(),
                "is_business_hours": context.business_hours,
                "is_emergency": context.emergency_override,
                "data_freshness": context.data_freshness_seconds or 0
            }
        }


class TemporalGraphQueries:
    """
    Pre-defined Cypher queries for common temporal operations
    """
    
    @staticmethod
    def get_active_emergency_contexts() -> str:
        return """
        MATCH (tc:TemporalContext {emergency_override: true})
        WHERE tc.situation = 'EMERGENCY'
        RETURN tc
        ORDER BY tc.timestamp DESC
        """
    
    @staticmethod
    def get_contexts_for_service(service_id: str) -> str:
        return """
        MATCH (tc:TemporalContext)-[:APPLIES_TO_SERVICE]->(s:Service {node_id: $service_id})
        RETURN tc, s
        ORDER BY tc.timestamp DESC
        LIMIT 50
        """
    
    @staticmethod
    def get_temporal_patterns() -> str:
        return """
        MATCH (tc:TemporalContext)
        WITH tc.situation as situation, 
             tc.business_hours as business_hours,
             count(*) as occurrence_count
        RETURN situation, business_hours, occurrence_count
        ORDER BY occurrence_count DESC
        """


class TeamBGraphitiAdapter:
    """
    Team B adapter: Calls Graphiti API to enrich organizational context
    
    This adapter integrates with Team B's Graphiti knowledge graph service
    to fetch organizational relationships, acting roles, and department info
    for use in temporal access control decisions.
    """
    
    def __init__(self, graphiti_client=None):
        """
        Initialize Team B adapter
        
        Args:
            graphiti_client: GraphitiClient instance (optional, lazy-initialized on first call)
        """
        self.graphiti_client = graphiti_client
        self.cache = {}  # Simple in-memory cache
    
    def get_org_context(self, 
                       subject_id: str,
                       resource_owner_id: str,
                       context: Optional[TemporalContext] = None) -> Dict[str, Any]:
        """
        Fetch organizational context from Graphiti for two parties
        
        Args:
            subject_id: Requesting user ID (employee ID)
            resource_owner_id: Resource/data owner ID
            context: Optional TemporalContext for enrichment
        
        Returns:
            Dict with keys: 
                - reporting_relationship (bool)
                - same_department (bool)
                - shared_projects (list)
                - subject_acting_roles (list)
                - owner_acting_roles (list)
                - last_updated (datetime)
        """
        # Check cache first
        cache_key = f"org:{subject_id}:{resource_owner_id}"
        if cache_key in self.cache:
            logger.debug(f"Returning cached org context for {subject_id}/{resource_owner_id}")
            return self.cache[cache_key]
        
        try:
            if self.graphiti_client is None:
                from core.graphiti_client import GraphitiClient
                from core.graphiti_config import GraphitiConfig
                config = GraphitiConfig()
                self.graphiti_client = GraphitiClient(config)
            
            # Fetch 4 pieces of org data in parallel (simulated sequentially here)
            reporting_rel = self._get_reporting_relationship(subject_id, resource_owner_id)
            dept_rel = self._get_department_relationship(subject_id, resource_owner_id)
            projects = self._get_shared_projects(subject_id, resource_owner_id)
            subject_roles = self._get_temporal_roles(subject_id)
            owner_roles = self._get_temporal_roles(resource_owner_id)
            
            result = {
                "reporting_relationship": reporting_rel,
                "same_department": dept_rel,
                "shared_projects": projects,
                "subject_acting_roles": subject_roles,
                "owner_acting_roles": owner_roles,
                "last_updated": datetime.now(timezone.utc),
            }
            
            # Cache for 5 minutes
            self.cache[cache_key] = result
            return result
        
        except Exception as e:
            logger.error(f"Error fetching org context from Graphiti: {e}")
            # Return safe defaults if API unavailable
            return {
                "reporting_relationship": False,
                "same_department": False,
                "shared_projects": [],
                "subject_acting_roles": [],
                "owner_acting_roles": [],
                "last_updated": datetime.now(timezone.utc),
                "error": str(e)
            }
    
    def _get_reporting_relationship(self, employee_id: str, manager_id: str) -> bool:
        """Check if employee reports to manager"""
        try:
            from core.graphiti_config import RelationshipReportingRequest
            req = RelationshipReportingRequest(
                employee_id=employee_id,
                manager_id=manager_id
            )
            response = self.graphiti_client.get_reporting_relationship(req)
            return response.is_reporting_relationship
        except Exception as e:
            logger.warning(f"Failed to get reporting relationship: {e}")
            return False
    
    def _get_department_relationship(self, person_a_id: str, person_b_id: str) -> bool:
        """Check if two people are in the same department"""
        try:
            from core.graphiti_config import RelationshipDepartmentRequest
            req = RelationshipDepartmentRequest(
                sender_id=person_a_id,
                recipient_id=person_b_id
            )
            response = self.graphiti_client.get_department_relationship(req)
            return response.same_department
        except Exception as e:
            logger.warning(f"Failed to get department relationship: {e}")
            return False
    
    def _get_shared_projects(self, person_a_id: str, person_b_id: str) -> List[str]:
        """Get shared projects between two people"""
        try:
            from core.graphiti_config import RelationshipProjectsRequest
            req = RelationshipProjectsRequest(
                sender_id=person_a_id,
                recipient_id=person_b_id
            )
            response = self.graphiti_client.get_shared_projects(req)
            return response.project_ids
        except Exception as e:
            logger.warning(f"Failed to get shared projects: {e}")
            return []
    
    def _get_temporal_roles(self, person_id: str) -> List[Dict[str, Any]]:
        """Get acting/temporary roles for a person"""
        try:
            from core.graphiti_config import RolesTemporalRequest
            req = RolesTemporalRequest(person_id=person_id)
            response = self.graphiti_client.get_temporal_roles(req)
            return [
                {
                    "role_id": role.role_id,
                    "title": role.title,
                    "start_date": role.start_date.isoformat() if role.start_date else None,
                    "end_date": role.end_date.isoformat() if role.end_date else None,
                    "active": role.active
                }
                for role in response.temporal_roles
            ]
        except Exception as e:
            logger.warning(f"Failed to get temporal roles: {e}")
            return []
    
    def clear_cache(self, cache_key: Optional[str] = None) -> None:
        """Clear cache (optionally for specific key)"""
        if cache_key:
            self.cache.pop(cache_key, None)
            logger.debug(f"Cleared cache for {cache_key}")
        else:
            self.cache.clear()
            logger.debug("Cleared all cache")