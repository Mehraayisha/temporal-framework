# core/graph_adapter.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from core.tuples import TemporalContext, TimeWindow, EnhancedContextualIntegrityTuple


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