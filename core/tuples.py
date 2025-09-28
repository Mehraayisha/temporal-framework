# core/tuples.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
import uuid


@dataclass
class TimeWindow:
    # Graph-specific fields
    node_id: str = field(default_factory=lambda: f"tw_{uuid.uuid4().hex[:8]}")
    node_type: str = "TimeWindow"
    
    # Time data
    start: Optional[datetime] = None  # ISO datetime (can be timezone-aware)
    end: Optional[datetime] = None
    
    # Graph metadata
    window_type: str = "access_window"  # "business_hours", "emergency", "access_window"
    description: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "window_type": self.window_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        def _parse(s):
            if s is None: return None
            return datetime.fromisoformat(s)
        return cls(
            node_id=d.get("node_id", f"tw_{uuid.uuid4().hex[:8]}"),
            node_type=d.get("node_type", "TimeWindow"),
            start=_parse(d.get("start")),
            end=_parse(d.get("end")),
            window_type=d.get("window_type", "access_window"),
            description=d.get("description"),
            created_at=_parse(d.get("created_at")) or datetime.now(timezone.utc)
        )


@dataclass
class TemporalContext:
    # Graph-specific fields
    node_id: str = field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:8]}")
    node_type: str = "TemporalContext"
    
    # Relationship IDs (references to other graph nodes)
    incident_id: Optional[str] = None
    service_id: Optional[str] = None  
    user_id: Optional[str] = None
    access_window_id: Optional[str] = None  # Reference to TimeWindow node
    
    # Temporal data
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timezone: str = "UTC"
    business_hours: bool = False
    emergency_override: bool = False
    data_freshness_seconds: Optional[int] = None
    situation: Optional[str] = "NORMAL"
    temporal_role: Optional[str] = None
    event_correlation: Optional[str] = None
    
    # For backward compatibility - will be deprecated
    access_window: Optional[TimeWindow] = None
    
    # Graph metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "incident_id": self.incident_id,
            "service_id": self.service_id,
            "user_id": self.user_id,
            "access_window_id": self.access_window_id,
            "timestamp": self.timestamp.isoformat(),
            "timezone": self.timezone,
            "business_hours": self.business_hours,
            "emergency_override": self.emergency_override,
            "access_window": self.access_window.to_dict() if self.access_window else None,
            "data_freshness_seconds": self.data_freshness_seconds,
            "situation": self.situation,
            "temporal_role": self.temporal_role,
            "event_correlation": self.event_correlation,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        def _parse_datetime(s):
            if s is None: 
                return datetime.now(timezone.utc)
            if isinstance(s, datetime):
                return s
            return datetime.fromisoformat(s)
            
        ts = _parse_datetime(d.get("timestamp"))
        aw = None
        if d.get("access_window"):
            aw = TimeWindow.from_dict(d["access_window"])
            
        return cls(
            node_id=d.get("node_id", f"tc_{uuid.uuid4().hex[:8]}"),
            node_type=d.get("node_type", "TemporalContext"),
            incident_id=d.get("incident_id"),
            service_id=d.get("service_id"),
            user_id=d.get("user_id"),
            access_window_id=d.get("access_window_id"),
            timestamp=ts,
            timezone=d.get("timezone", "UTC"),
            business_hours=bool(d.get("business_hours", False)),
            emergency_override=bool(d.get("emergency_override", False)),
            access_window=aw,
            data_freshness_seconds=d.get("data_freshness_seconds"),
            situation=d.get("situation", "NORMAL"),
            temporal_role=d.get("temporal_role"),
            event_correlation=d.get("event_correlation"),
            created_at=_parse_datetime(d.get("created_at")),
            updated_at=_parse_datetime(d.get("updated_at")),
        )

    def get_graph_properties(self) -> Dict[str, Any]:
        """Get properties suitable for Neo4j node creation"""
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp.isoformat(),
            "timezone": self.timezone,
            "business_hours": self.business_hours,
            "emergency_override": self.emergency_override,
            "data_freshness_seconds": self.data_freshness_seconds,
            "situation": self.situation,
            "temporal_role": self.temporal_role,
            "event_correlation": self.event_correlation,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def get_relationships(self) -> Dict[str, str]:
        """Get relationship mappings for graph storage"""
        relationships = {}
        if self.incident_id:
            relationships["RELATES_TO_INCIDENT"] = self.incident_id
        if self.service_id:
            relationships["APPLIES_TO_SERVICE"] = self.service_id
        if self.user_id:
            relationships["GOVERNS_USER"] = self.user_id
        if self.access_window_id:
            relationships["HAS_ACCESS_WINDOW"] = self.access_window_id
        return relationships
    
    def save_to_neo4j(self, neo4j_manager) -> str:
        """
        Save this TemporalContext to Neo4j database
        
        Args:
            neo4j_manager: TemporalNeo4jManager instance
            
        Returns:
            str: Node ID of saved context
        """
        return neo4j_manager.create_temporal_context(self)
    
    def save_to_graphiti(self, graphiti_manager) -> str:
        """
        Save this TemporalContext to Graphiti knowledge graph
        
        Args:
            graphiti_manager: TemporalGraphitiManager instance
            
        Returns:
            str: Entity ID of saved context
        """
        return graphiti_manager.create_temporal_context(self)
    
    @classmethod
    def find_by_service_neo4j(cls, neo4j_manager, service_id: str, limit: int = 10):
        """
        Find temporal contexts for a service from Neo4j
        
        Args:
            neo4j_manager: TemporalNeo4jManager instance
            service_id: Service identifier
            limit: Maximum results to return
            
        Returns:
            List of TemporalContext instances
        """
        results = neo4j_manager.find_temporal_contexts_by_service(service_id, limit)
        contexts = []
        
        for result in results:
            tc_data = result["temporal_context"]
            # Convert Neo4j datetime strings back to datetime objects
            if "timestamp" in tc_data:
                tc_data["timestamp"] = datetime.fromisoformat(tc_data["timestamp"].replace("Z", "+00:00"))
            if "created_at" in tc_data:
                tc_data["created_at"] = datetime.fromisoformat(tc_data["created_at"].replace("Z", "+00:00"))
            if "updated_at" in tc_data:
                tc_data["updated_at"] = datetime.fromisoformat(tc_data["updated_at"].replace("Z", "+00:00"))
            
            contexts.append(cls.from_dict(tc_data))
        
        return contexts
    
    @classmethod
    def find_by_service_graphiti(cls, graphiti_manager, service_id: str, limit: int = 10):
        """
        Find temporal contexts for a service from Graphiti knowledge graph
        
        Args:
            graphiti_manager: TemporalGraphitiManager instance
            service_id: Service identifier
            limit: Maximum results to return
            
        Returns:
            List of TemporalContext instances
        """
        results = graphiti_manager.find_temporal_contexts_by_service(service_id, limit)
        contexts = []
        
        for result in results:
            tc_data = result["temporal_context"]
            # Convert Graphiti data back to TemporalContext
            if "timestamp" in tc_data:
                try:
                    tc_data["timestamp"] = datetime.fromisoformat(tc_data["timestamp"])
                except (ValueError, TypeError):
                    tc_data["timestamp"] = datetime.now(timezone.utc)
            
            contexts.append(cls.from_dict(tc_data))
        
        return contexts


@dataclass
class EnhancedContextualIntegrityTuple:
    data_type: str
    data_subject: str
    data_sender: str
    data_recipient: str
    transmission_principle: str
    temporal_context: TemporalContext

    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_type": self.data_type,
            "data_subject": self.data_subject,
            "data_sender": self.data_sender,
            "data_recipient": self.data_recipient,
            "transmission_principle": self.transmission_principle,
            "temporal_context": self.temporal_context.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        return cls(
            data_type=d["data_type"],
            data_subject=d["data_subject"],
            data_sender=d["data_sender"],
            data_recipient=d["data_recipient"],
            transmission_principle=d.get("transmission_principle", ""),
            temporal_context=TemporalContext.from_dict(d["temporal_context"]),
        )
