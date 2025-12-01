# API Reference Documentation

This document provides comprehensive API documentation for the Temporal Framework.

## Core Modules

### `core.tuples` - Data Models

The core data models implementing the 6-tuple contextual integrity framework with Pydantic validation.

#### Classes

##### `TimeWindow`

**Purpose**: Represents a temporal boundary for access control with validation.

```python
class TimeWindow(BaseModel):
    """
    Time window for access control with Pydantic validation.
    
    TimeWindows define temporal boundaries during which certain access
    policies are active. They support hierarchical relationships and
    various window types for different use cases.
    
    Attributes:
        node_id (str): Unique identifier for graph operations
        node_type (str): Type identifier ("TimeWindow") 
        start (Optional[datetime]): Window start time (timezone-aware)
        end (Optional[datetime]): Window end time (timezone-aware)
        window_type (str): Type of window - one of:
            - "business_hours": Regular business operating hours
            - "emergency": Emergency access periods
            - "access_window": General access periods  
            - "maintenance": System maintenance windows
            - "holiday": Holiday/special event periods
        description (Optional[str]): Human-readable description
        created_at (datetime): Creation timestamp (UTC)
        
    Validation:
        - end time must be after start time (if both provided)
        - window_type must be one of the predefined valid types
        
    Example:
        >>> from datetime import datetime, timezone, timedelta
        >>> window = TimeWindow(
        ...     start=datetime.now(timezone.utc),
        ...     end=datetime.now(timezone.utc) + timedelta(hours=8),
        ...     window_type="business_hours",
        ...     description="Standard business hours"
        ... )
        >>> print(window.node_id)  # e.g., "tw_a1b2c3d4"
    """
```

**Methods**:

- `to_dict() -> Dict[str, Any]`: Convert to dictionary with ISO formatted datetimes
- `from_dict(cls, d: Dict[str, Any]) -> TimeWindow`: Create from dictionary
- `save_to_neo4j(neo4j_manager) -> str`: Save to Neo4j database
- `save_to_graphiti(graphiti_manager) -> str`: Save to Graphiti knowledge graph

##### `TemporalContext`

**Purpose**: Rich temporal context providing time-aware access control information.

```python
class TemporalContext(BaseModel):
    """
    Temporal context for 6-tuple contextual integrity framework.
    
    TemporalContext provides comprehensive contextual information including
    time windows, location, user details, and situational factors that
    influence access control decisions.
    
    Attributes:
        service_id (str): Identifier of the requesting service
        user_id (str): Identifier of the user making the request
        location (str): Physical or logical location of the request
        timezone (str): Timezone for time calculations (default: "UTC")
        time_windows (List[TimeWindow]): List of applicable time windows
        emergency_override (bool): Flag indicating emergency access mode
        data_freshness_seconds (Optional[int]): Maximum age of acceptable data
        situation (Optional[str]): Current situational context, one of:
            - "NORMAL": Standard operating conditions
            - "EMERGENCY": Emergency response situation  
            - "MAINTENANCE": System maintenance period
            - "INCIDENT": Active incident response
            - "AUDIT": Audit or compliance review
        temporal_role (Optional[str]): Time-based role assignment
        event_correlation (Optional[str]): Related event identifier
        access_window (Optional[TimeWindow]): Backward compatibility field
        created_at (datetime): Creation timestamp (UTC)
        updated_at (datetime): Last update timestamp (UTC)
        
    Validation:
        - service_id, user_id, location must not be empty
        - timezone must be valid timezone string
        - situation must be one of predefined values
        - temporal_role must be valid role if provided
        - data_freshness_seconds must be >= 0 if provided
        
    Example:
        >>> context = TemporalContext(
        ...     service_id="medical_records",
        ...     user_id="dr_smith",
        ...     location="emergency_department", 
        ...     timezone="UTC",
        ...     situation="EMERGENCY",
        ...     emergency_override=True
        ... )
        >>> print(context.node_id)  # e.g., "tc_x1y2z3w4"
    """
```

**Methods**:

- `to_dict() -> Dict[str, Any]`: Convert to dictionary
- `from_dict(cls, d: Dict[str, Any]) -> TemporalContext`: Create from dictionary  
- `save_to_neo4j(neo4j_manager) -> str`: Save to Neo4j database
- `save_to_graphiti(graphiti_manager) -> str`: Save to Graphiti knowledge graph
- `find_by_service_neo4j(cls, neo4j_manager, service_id: str, limit: int = 10) -> List[TemporalContext]`: Find contexts by service

##### `EnhancedContextualIntegrityTuple`

**Purpose**: The main 6-tuple model extending traditional 5-tuple with temporal awareness.

```python
class EnhancedContextualIntegrityTuple(BaseModel):
    """
    Enhanced 6-tuple contextual integrity model with comprehensive validation.
    
    This class implements the core 6-tuple access control model that extends
    traditional 5-tuple contextual integrity with temporal awareness. It includes
    comprehensive audit logging, risk assessment, and compliance tracking.
    
    Core 6-Tuple Attributes:
        data_type (str): Type of data being accessed (e.g., "patient_record")
        data_subject (str): Subject of the data (e.g., "patient_12345")  
        data_sender (str): Entity requesting access (e.g., "dr_smith")
        data_recipient (str): Entity receiving data (e.g., "trauma_team")
        transmission_principle (str): Governing principle (e.g., "emergency_access")
        temporal_context (TemporalContext): Temporal context (6th tuple element)
        
    Enhanced Attributes:
        node_id (str): Unique identifier for graph operations
        node_type (str): Type identifier ("EnhancedContextualIntegrityTuple")
        data_freshness_timestamp (Optional[datetime]): Data freshness indicator
        session_id (Optional[str]): Session tracking identifier
        request_id (str): Unique request identifier
        audit_required (bool): Force audit logging flag
        compliance_tags (List[str]): Regulatory compliance tags
        risk_level (str): Risk assessment - one of:
            - "LOW": Minimal risk access
            - "MEDIUM": Standard risk access (default)
            - "HIGH": Elevated risk access
            - "CRITICAL": Maximum risk access
        created_at (datetime): Creation timestamp (UTC)
        processed_at (Optional[datetime]): Processing completion time
        decision_confidence (Optional[float]): Decision confidence (0.0-1.0)
        data_classification (Optional[str]): Data classification level
        purpose_limitation (Optional[str]): Purpose limitation description
        retention_period (Optional[timedelta]): Data retention period
        correlation_id (Optional[str]): Cross-system correlation ID
        parent_request_id (Optional[str]): Parent request reference
        related_incident_ids (List[str]): Related incident identifiers
        
    Validation:
        - All core 6-tuple fields are required and non-empty
        - risk_level must be valid risk level
        - decision_confidence must be between 0.0 and 1.0
        - All string fields have minimum length requirements
        
    Example:
        >>> tuple_obj = EnhancedContextualIntegrityTuple(
        ...     data_type="patient_medical_record",
        ...     data_subject="patient_12345",
        ...     data_sender="emergency_physician",
        ...     data_recipient="trauma_team", 
        ...     transmission_principle="emergency_access",
        ...     temporal_context=temporal_context,
        ...     risk_level="HIGH",
        ...     audit_required=True
        ... )
        >>> print(tuple_obj.request_id)  # e.g., "req_m1n2o3p4"
    """
```

**Methods**:

- `to_dict() -> Dict[str, Any]`: Convert to dictionary
- `from_dict(cls, d: Dict[str, Any]) -> EnhancedContextualIntegrityTuple`: Create from dictionary
- `save_to_neo4j(neo4j_manager) -> str`: Save to Neo4j database  
- `save_to_graphiti(graphiti_manager) -> str`: Save to Graphiti knowledge graph

### `core.policy_engine` - Policy Evaluation

The policy evaluation engine implementing temporal access control logic.

#### Classes

##### `PolicyDecision`

**Purpose**: Represents the result of a policy evaluation.

```python
@dataclass
class PolicyDecision:
    """
    Result of policy evaluation with comprehensive metadata.
    
    Attributes:
        allowed (bool): Whether access is granted
        reason (str): Human-readable explanation of decision
        confidence (float): Decision confidence score (0.0-1.0)
        risk_level (str): Assessed risk level
        expiry_time (Optional[datetime]): When decision expires
        next_review_time (Optional[datetime]): When to review decision
        applied_rules (List[str]): Names of rules that were applied
        metadata (Dict[str, Any]): Additional decision metadata
    """
```

##### `TemporalPolicyEngine`

**Purpose**: Main policy evaluation engine with temporal logic support.

```python
class TemporalPolicyEngine:
    """
    Temporal policy evaluation engine for 6-tuple access control.
    
    This engine evaluates access requests using temporal policies that
    consider time windows, emergency overrides, situational context,
    and graph-based relationship data.
    
    Features:
        - Time-aware policy evaluation
        - Emergency override handling  
        - Graph database integration
        - Comprehensive audit logging
        - Risk assessment and confidence scoring
        
    Args:
        rules_file (Optional[str]): Path to policy rules YAML file
        neo4j_manager (Optional[TemporalNeo4jManager]): Neo4j integration
        graphiti_manager (Optional[TemporalGraphitiManager]): Graphiti integration
        enable_caching (bool): Enable policy decision caching
        cache_ttl_seconds (int): Cache time-to-live in seconds
        
    Example:
        >>> engine = TemporalPolicyEngine(
        ...     rules_file="policies/rules.yaml",
        ...     enable_caching=True,
        ...     cache_ttl_seconds=300
        ... )
        >>> decision = engine.evaluate_request(access_tuple)
        >>> print(f"Access: {decision.allowed}, Reason: {decision.reason}")
    """
```

**Methods**:

- `evaluate_request(access_tuple: EnhancedContextualIntegrityTuple, neo4j_manager: Optional[TemporalNeo4jManager] = None) -> PolicyDecision`: Evaluate access request
- `load_rules(rules_file: str) -> None`: Load policy rules from file
- `add_rule(rule: PolicyRule) -> None`: Add policy rule dynamically
- `get_applicable_rules(access_tuple: EnhancedContextualIntegrityTuple) -> List[PolicyRule]`: Get matching rules
- `calculate_risk_level(access_tuple: EnhancedContextualIntegrityTuple) -> str`: Assess risk level
- `calculate_confidence(access_tuple: EnhancedContextualIntegrityTuple, decision: bool) -> float`: Calculate decision confidence

### `core.neo4j_manager` - Graph Database Integration

Neo4j integration for persistent graph storage and relationship queries.

#### Classes

##### `TemporalNeo4jManager`

**Purpose**: Manages Neo4j database connections and temporal graph operations.

```python
class TemporalNeo4jManager:
    """
    Neo4j database manager for temporal contextual integrity graphs.
    
    Provides comprehensive Neo4j integration including connection management,
    graph operations, and temporal query support for the 6-tuple framework.
    
    Features:
        - Connection pooling and management
        - Temporal context and tuple persistence
        - Relationship modeling and queries
        - Transaction support
        - Query optimization
        - Error handling and retry logic
        
    Args:
        uri (str): Neo4j connection URI (e.g., "bolt://localhost:7687")
        user (str): Database username
        password (str): Database password
        database (str): Target database name (default: "neo4j")
        max_connection_lifetime (int): Connection lifetime in seconds
        max_connection_pool_size (int): Maximum connection pool size
        
    Example:
        >>> manager = TemporalNeo4jManager(
        ...     uri="bolt://localhost:7687",
        ...     user="neo4j",
        ...     password="password"
        ... )
        >>> context_id = manager.create_temporal_context(temporal_context)
        >>> print(f"Saved context: {context_id}")
    """
```

**Methods**:

- `create_temporal_context(context: TemporalContext) -> str`: Create temporal context node
- `create_time_window(window: TimeWindow) -> str`: Create time window node
- `create_enhanced_tuple(tuple_obj: EnhancedContextualIntegrityTuple) -> str`: Create tuple node
- `find_temporal_contexts_by_service(service_id: str, limit: int = 10) -> List[Dict]`: Find contexts by service
- `find_related_contexts(context_id: str, relationship_type: str = "RELATED_TO") -> List[Dict]`: Find related contexts
- `create_relationship(from_id: str, to_id: str, relationship_type: str, properties: Dict = None) -> None`: Create relationship
- `execute_temporal_query(query: str, parameters: Dict = None) -> List[Dict]`: Execute Cypher query
- `close() -> None`: Close database connection

### `core.graphiti_manager` - AI Knowledge Graph Integration  

Graphiti integration for AI-enhanced contextual reasoning and knowledge graphs.

#### Classes

##### `TemporalGraphitiManager`

**Purpose**: Manages Graphiti AI knowledge graph integration.

```python
class TemporalGraphitiManager:
    """
    Graphiti knowledge graph manager for AI-enhanced temporal reasoning.
    
    Integrates with Graphiti AI knowledge graphs to provide enhanced
    contextual reasoning, pattern recognition, and intelligent policy
    recommendations for temporal access control.
    
    Features:
        - AI-enhanced context enrichment
        - Pattern recognition and learning
        - Intelligent policy recommendations  
        - Natural language query support
        - Semantic relationship modeling
        - Automated knowledge extraction
        
    Args:
        server_url (Optional[str]): Graphiti server URL
        api_key (Optional[str]): API authentication key
        dataset_name (str): Target dataset name
        enable_learning (bool): Enable machine learning features
        
    Example:
        >>> manager = TemporalGraphitiManager(
        ...     server_url="https://api.graphiti.ai",
        ...     api_key="your_api_key",
        ...     dataset_name="temporal_framework"
        ... )
        >>> await manager.initialize()
        >>> entity_id = await manager.create_temporal_context(context)
    """
```

**Methods**:

- `async initialize() -> None`: Initialize Graphiti connection
- `async create_temporal_context(context: TemporalContext) -> str`: Create context entity
- `async create_enhanced_tuple(tuple_obj: EnhancedContextualIntegrityTuple) -> str`: Create tuple entity
- `async enrich_context(context: TemporalContext) -> TemporalContext`: AI-enhance context
- `async search_similar_contexts(query: str, limit: int = 10) -> List[Dict]`: Find similar contexts
- `async get_policy_recommendations(access_tuple: EnhancedContextualIntegrityTuple) -> List[str]`: Get AI recommendations
- `async close() -> None`: Close Graphiti connection

### `core.evaluator` - Request Evaluation

High-level request evaluation orchestrating policy engines and enrichment.

#### Classes

##### `TemporalEvaluator`

**Purpose**: Orchestrates request evaluation with enrichment and policy application.

```python
class TemporalEvaluator:
    """
    High-level temporal request evaluator with enrichment pipeline.
    
    Orchestrates the complete evaluation pipeline including context enrichment,
    policy evaluation, audit logging, and decision formatting. Provides a
    simplified interface for complex temporal access control scenarios.
    
    Features:
        - Automated context enrichment
        - Multi-stage policy evaluation
        - Comprehensive audit logging
        - Performance optimization
        - Error handling and fallbacks
        
    Args:
        policy_engine (TemporalPolicyEngine): Policy evaluation engine
        enricher (Optional[TemporalEnricher]): Context enrichment service
        enable_audit (bool): Enable comprehensive audit logging
        fallback_decision (bool): Fallback decision on errors (default: False)
        
    Example:
        >>> evaluator = TemporalEvaluator(
        ...     policy_engine=policy_engine,
        ...     enricher=enricher,
        ...     enable_audit=True
        ... )
        >>> result = evaluator.evaluate(access_tuple)
        >>> print(f"Decision: {result.decision.allowed}")
    """
```

**Methods**:

- `evaluate(access_tuple: EnhancedContextualIntegrityTuple) -> EvaluationResult`: Complete evaluation
- `evaluate_batch(tuples: List[EnhancedContextualIntegrityTuple]) -> List[EvaluationResult]`: Batch evaluation
- `set_enricher(enricher: TemporalEnricher) -> None`: Set context enricher
- `set_policy_engine(engine: TemporalPolicyEngine) -> None`: Set policy engine

### `core.enricher` - Context Enrichment

Context enrichment services for enhanced temporal reasoning.

#### Classes

##### `TemporalEnricher`

**Purpose**: Enriches temporal contexts with additional graph-based information.

```python  
class TemporalEnricher:
    """
    Context enrichment service for temporal frameworks.
    
    Enriches TemporalContext objects with additional information from
    graph databases, external services, and AI reasoning systems to
    provide comprehensive context for access control decisions.
    
    Features:
        - Graph-based relationship enrichment
        - External service integration
        - AI-powered context enhancement
        - Caching and performance optimization
        - Configurable enrichment strategies
        
    Args:
        neo4j_manager (Optional[TemporalNeo4jManager]): Neo4j integration
        graphiti_manager (Optional[TemporalGraphitiManager]): Graphiti integration  
        enable_caching (bool): Enable enrichment caching
        cache_ttl_seconds (int): Cache time-to-live
        
    Example:
        >>> enricher = TemporalEnricher(
        ...     neo4j_manager=neo4j_manager,
        ...     graphiti_manager=graphiti_manager,
        ...     enable_caching=True
        ... )
        >>> enriched = enricher.enrich_context(temporal_context)
        >>> print(f"Enriched with {len(enriched.time_windows)} time windows")
    """
```

**Methods**:

- `enrich_context(context: TemporalContext) -> TemporalContext`: Enrich temporal context
- `enrich_tuple(tuple_obj: EnhancedContextualIntegrityTuple) -> EnhancedContextualIntegrityTuple`: Enrich access tuple  
- `add_related_contexts(context: TemporalContext) -> TemporalContext`: Add related context information
- `update_time_windows(context: TemporalContext) -> TemporalContext`: Update time window information

## Error Handling

### Exception Hierarchy

```python
class TemporalFrameworkError(Exception):
    """Base exception for temporal framework errors."""
    pass

class ValidationError(TemporalFrameworkError):
    """Raised when data validation fails."""
    pass

class PolicyEngineError(TemporalFrameworkError):
    """Raised when policy evaluation fails."""
    pass

class DatabaseError(TemporalFrameworkError):
    """Raised when database operations fail."""
    pass

class EnrichmentError(TemporalFrameworkError):
    """Raised when context enrichment fails."""
    pass
```

### Error Response Format

```python
@dataclass
class ErrorResponse:
    """Standardized error response format."""
    error_type: str
    error_message: str
    error_code: int
    timestamp: datetime
    correlation_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
```

## Configuration

### Environment Variables

```bash
# Required Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Optional Configuration  
GRAPHITI_SERVER_URL=https://api.graphiti.ai
GRAPHITI_API_KEY=your_api_key
LOG_LEVEL=INFO
AUDIT_LOG_ENABLED=true
SECURITY_LOG_ENABLED=true
EMERGENCY_OVERRIDE_ENABLED=true
DEFAULT_TIMEZONE=UTC
MAX_CONTEXT_AGE_HOURS=24
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
```

### Configuration Classes

```python
from pydantic import BaseSettings

class FrameworkSettings(BaseSettings):
    """Framework configuration with environment variable support."""
    
    # Database settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"  
    neo4j_password: str
    
    # Logging settings
    log_level: str = "INFO"
    audit_log_enabled: bool = True
    security_log_enabled: bool = True
    
    # Framework settings
    emergency_override_enabled: bool = True
    default_timezone: str = "UTC"
    max_context_age_hours: int = 24
    
    # Performance settings
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    
    class Config:
        env_file = ".env"
```

## Performance Considerations

### Caching Strategies

```python
# Method-level caching
from functools import lru_cache

@lru_cache(maxsize=128)
def get_policy_rules(service_id: str) -> List[PolicyRule]:
    """Cache frequently accessed policy rules."""
    return load_policy_rules_from_database(service_id)

# Class-level caching
from cachetools import TTLCache

class CachedPolicyEngine(TemporalPolicyEngine):
    def __init__(self, cache_ttl: int = 300):
        super().__init__()
        self._cache = TTLCache(maxsize=1000, ttl=cache_ttl)
    
    def evaluate_request(self, access_tuple: EnhancedContextualIntegrityTuple) -> PolicyDecision:
        cache_key = self._generate_cache_key(access_tuple)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        decision = super().evaluate_request(access_tuple)
        self._cache[cache_key] = decision
        return decision
```

### Async Operations

```python
# Async context enrichment
async def enrich_context_async(
    context: TemporalContext,
    enricher: TemporalEnricher
) -> TemporalContext:
    """Asynchronously enrich temporal context."""
    
    # Run enrichment operations concurrently
    tasks = [
        enricher.add_graph_relationships(context),
        enricher.fetch_external_data(context), 
        enricher.apply_ai_reasoning(context)
    ]
    
    enriched_data = await asyncio.gather(*tasks)
    return enricher.merge_enriched_data(context, enriched_data)

# Batch processing
async def evaluate_batch_async(
    tuples: List[EnhancedContextualIntegrityTuple],
    evaluator: TemporalEvaluator
) -> List[PolicyDecision]:
    """Evaluate multiple requests concurrently."""
    
    tasks = [evaluator.evaluate_async(tuple_obj) for tuple_obj in tuples]
    return await asyncio.gather(*tasks)
```

## Testing API

### Test Utilities

```python
from core.testing import TemporalTestCase, MockNeo4jManager

class TestPolicyEngine(TemporalTestCase):
    """Test case with temporal framework utilities."""
    
    def setUp(self):
        """Set up test environment with mock dependencies."""
        self.mock_neo4j = MockNeo4jManager()
        self.policy_engine = TemporalPolicyEngine(
            neo4j_manager=self.mock_neo4j
        )
    
    def test_emergency_access(self):
        """Test emergency access override functionality."""
        tuple_obj = self.create_emergency_tuple(
            data_type="patient_record",
            situation="EMERGENCY"
        )
        
        decision = self.policy_engine.evaluate_request(tuple_obj)
        
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "emergency_override")
        self.assertGreater(decision.confidence, 0.9)
```

### Mock Objects

```python
class MockTemporalContext(TemporalContext):
    """Mock temporal context for testing."""
    
    def save_to_neo4j(self, manager) -> str:
        return f"mock_context_{self.node_id}"
    
    def save_to_graphiti(self, manager) -> str:
        return f"mock_entity_{self.node_id}"

class MockPolicyEngine(TemporalPolicyEngine):
    """Mock policy engine with predictable responses."""
    
    def evaluate_request(self, access_tuple) -> PolicyDecision:
        return PolicyDecision(
            allowed=True,
            reason="mock_allow",
            confidence=0.95,
            risk_level="LOW"
        )
```

---

For more detailed examples and advanced usage patterns, see the [examples/](../examples/) directory and the comprehensive [README.md](../README.md).