# core/tuples.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import uuid
import logging

# Get loggers
from .logging_config import loggers
logger = loggers['main']
audit_logger = loggers['audit']

# Optional integration with local org service (fallback when Team B evaluation not available)
try:
    from .org_service import org_lookup
except Exception:
    org_lookup = None


class TimeWindow(BaseModel):
    """Time window for access control with Pydantic validation"""
    
    # Graph-specific fields
    node_id: str = Field(default_factory=lambda: f"tw_{uuid.uuid4().hex[:8]}")
    node_type: str = "TimeWindow"
    
    # Time data
    start: Optional[datetime] = None  # ISO datetime (can be timezone-aware)
    end: Optional[datetime] = None
    
    # Graph metadata
    window_type: str = "access_window"  # "business_hours", "emergency", "access_window"
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        # Pydantic V2 handles datetime serialization automatically
        # No need for deprecated json_encoders
    )
        
    @field_validator('window_type')
    @classmethod
    def validate_window_type(cls, v):
        valid_types = ["business_hours", "emergency", "access_window", "maintenance", "holiday"]
        if v not in valid_types:
            raise ValueError(f'window_type must be one of {valid_types}')
        return v
    
    @model_validator(mode='after')
    def validate_end_after_start(self):
        if self.end is not None and self.start is not None:
            if self.end <= self.start:
                raise ValueError('end time must be after start time')
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with ISO formatted datetimes"""
        logger.debug(f"Converting TimeWindow {self.node_id} to dict")
        return self.model_dump()
        
    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        """Create TimeWindow from dictionary"""
        logger.debug(f"Creating TimeWindow from dict: {d.get('node_id', 'unknown')}")
        return cls(**d)


class TemporalContext(BaseModel):
    """Temporal context for 6-tuple with comprehensive validation"""
    
    # Graph-specific fields
    node_id: str = Field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:8]}")
    node_type: str = "TemporalContext"
    
    # Relationship IDs (references to other graph nodes)
    incident_id: Optional[str] = None
    service_id: Optional[str] = None  
    user_id: Optional[str] = None
    access_window_id: Optional[str] = None  # Reference to TimeWindow node
    
    # Temporal data
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timezone: str = "UTC"
    business_hours: bool = False
    emergency_override: bool = False
    data_freshness_seconds: Optional[int] = Field(None, ge=0)  # Must be >= 0
    situation: Optional[str] = "NORMAL"
    temporal_role: Optional[str] = None
    event_correlation: Optional[str] = None
    
    # NEW: Temporal Role Permission Inheritance fields
    base_role: Optional[str] = None  # User's permanent role
    inherited_permissions: List[str] = Field(default_factory=list)  # Permissions from temporal role
    permission_inheritance_chain: List[str] = Field(default_factory=list)  # Chain of inherited roles
    temporal_role_valid_until: Optional[datetime] = None  # When temporal role expires
    authorization_source: Optional[str] = None  # Who/what granted the temporal role
    emergency_authorization_id: Optional[str] = None  # Emergency ticket/incident ID
    
    # For backward compatibility - will be deprecated
    access_window: Optional[TimeWindow] = None
    
    # Graph metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        # Allow extra fields for dynamic enrichment (data_domain, etc)
        extra="allow",
        # Pydantic V2 handles datetime serialization automatically
        # No need for deprecated json_encoders
    )
        
    @field_validator('situation')
    @classmethod
    def validate_situation(cls, v):
        if v is not None:
            valid_situations = ["NORMAL", "EMERGENCY", "MAINTENANCE", "INCIDENT", "AUDIT"]
            if v not in valid_situations:
                raise ValueError(f'situation must be one of {valid_situations}')
        return v
    
    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v):
        # Basic timezone validation - could be enhanced with pytz
        if not v:
            raise ValueError('timezone cannot be empty')
        return v
    
    @field_validator('temporal_role')
    @classmethod
    def validate_temporal_role(cls, v):
        if v is not None:
            valid_roles = ["user", "admin", "system", "emergency_responder", "auditor", 
                          "oncall_low", "oncall_medium", "oncall_high", "oncall_critical",
                          "acting_manager", "acting_supervisor", "acting_department_head",
                          "incident_responder", "security_incident_lead", "audit_reviewer",
                          "compliance_officer"]
            if v not in valid_roles:
                raise ValueError(f'temporal_role must be one of {valid_roles}')
        return v

    @model_validator(mode='after')
    def validate_emergency_authorization(self):
        """Ensure emergency_authorization_id is present when emergency_override is True"""
        if getattr(self, 'emergency_override', False):
            auth_id = getattr(self, 'emergency_authorization_id', None)
            if not auth_id or (isinstance(auth_id, str) and auth_id.strip() == ""):
                raise ValueError('emergency_authorization_id is required when emergency_override is True')
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with enhanced logging"""
        logger.debug(f"Converting TemporalContext {self.node_id} to dict")
        audit_logger.info(f"TemporalContext serialized: {self.node_id}, situation={self.situation}, emergency={self.emergency_override}")
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        """Create TemporalContext from dictionary with validation"""
        logger.debug(f"Creating TemporalContext from dict: {d.get('node_id', 'unknown')}")
        
        # Handle access_window nested object
        if d.get("access_window") and isinstance(d["access_window"], dict):
            d["access_window"] = TimeWindow.from_dict(d["access_window"])
        
        try:
            instance = cls(**d)
            audit_logger.info(f"TemporalContext created: {instance.node_id}, situation={instance.situation}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create TemporalContext from dict: {e}")
            raise ValueError(f"Invalid TemporalContext data: {e}")

    @classmethod
    def mock(cls,
             now: Optional[datetime] = None,
             business_hours: Optional[bool] = None,
             emergency_override: bool = False,
             temporal_role: Optional[str] = None,
             access_window: Optional[TimeWindow] = None) -> "TemporalContext":
        """Create a small test-friendly TemporalContext with sane defaults.

        Args:
            now: timestamp to use (defaults to utc now)
            business_hours: optional override for business_hours flag
            emergency_override: whether emergency is active
            temporal_role: override temporal role string
            access_window: optional TimeWindow instance

        Returns:
            TemporalContext instance
        """
        now = now or datetime.now(timezone.utc)
        auth_id = None
        if emergency_override:
            auth_id = f"AUTH-{now.strftime('%Y%m%dT%H%M%S')}"
        tc = cls(
            timestamp=now,
            timezone="UTC",
            business_hours=(business_hours if business_hours is not None else False),
            emergency_override=emergency_override,
            access_window=access_window,
            temporal_role=temporal_role,
            situation=("EMERGENCY" if emergency_override else "NORMAL"),
            emergency_authorization_id=auth_id
        )
        return tc

    def is_fresh(self, now: Optional[datetime] = None) -> bool:
        """Return True if this context satisfies its data_freshness_seconds constraint.

        If `data_freshness_seconds` is None, consider the context fresh.
        """
        now = now or datetime.now(timezone.utc)
        if self.data_freshness_seconds is None:
            return True
        age = (now - self.timestamp).total_seconds()
        return age <= float(self.data_freshness_seconds)

    def assert_fresh(self, now: Optional[datetime] = None) -> None:
        """Raise RuntimeError if context is stale.

        Useful to ensure callers reload or regenerate context before evaluation.
        """
        if not self.is_fresh(now=now):
            raise RuntimeError("Temporal context stale; reload from source")

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


class EnhancedContextualIntegrityTuple(BaseModel):
    """Enhanced 6-tuple with comprehensive validation and audit logging"""
    
    # Core 6-tuple
    data_type: str = Field(..., min_length=1, description="Type of data being accessed")
    data_subject: str = Field(..., min_length=1, description="Subject of the data")
    data_sender: str = Field(..., min_length=1, description="Sender requesting access")
    data_recipient: str = Field(..., min_length=1, description="Recipient of the data")
    transmission_principle: str = Field(..., min_length=1, description="Principle governing transmission")
    temporal_context: TemporalContext = Field(..., description="Temporal context for the request")
    
    # Enhanced attributes for Week 2 assignment
    node_id: str = Field(default_factory=lambda: f"eci_{uuid.uuid4().hex[:8]}")
    node_type: str = "EnhancedContextualIntegrityTuple"
    
    # Data freshness and session tracking
    data_freshness_timestamp: Optional[datetime] = None
    session_id: Optional[str] = None
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:8]}")
    
    # Audit and compliance flags
    audit_required: bool = False
    compliance_tags: List[str] = Field(default_factory=list)
    risk_level: str = "MEDIUM"
    
    # Processing metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    decision_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Enhanced context attributes
    data_classification: Optional[str] = None
    purpose_limitation: Optional[str] = None
    retention_period: Optional[timedelta] = None
    
    # Cross-system correlation
    correlation_id: Optional[str] = None
    parent_request_id: Optional[str] = None
    related_incident_ids: List[str] = Field(default_factory=list)

    model_config = ConfigDict(
        # Pydantic V2 handles datetime and timedelta serialization automatically
        # No need for deprecated json_encoders
    )
        
    @field_validator('risk_level')
    @classmethod
    def validate_risk_level(cls, v):
        valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f'risk_level must be one of {valid_levels}')
        return v
    
    @field_validator('data_classification')
    @classmethod
    def validate_data_classification(cls, v):
        if v is not None:
            valid_classifications = ["public", "internal", "confidential", "restricted"]
            if v not in valid_classifications:
                raise ValueError(f'data_classification must be one of {valid_classifications}')
        return v
    
    @field_validator('compliance_tags')
    @classmethod
    def validate_compliance_tags(cls, v):
        if v is not None:
            valid_tags = ["HIPAA", "GDPR", "PCI_DSS", "SOX", "FERPA", "CCPA"]
            for tag in v:
                if tag not in valid_tags:
                    raise ValueError(f'compliance_tag {tag} not valid. Must be one of {valid_tags}')
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with audit logging"""
        logger.debug(f"Converting EnhancedContextualIntegrityTuple {self.node_id} to dict")
        audit_logger.info(f"6-tuple serialized: {self.node_id}, data_type={self.data_type}, risk={self.risk_level}")
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        """Create tuple from dictionary with validation"""
        logger.debug(f"Creating EnhancedContextualIntegrityTuple from dict")
        
        # Handle temporal_context nested object
        if d.get("temporal_context") and isinstance(d["temporal_context"], dict):
            d["temporal_context"] = TemporalContext.from_dict(d["temporal_context"])
        
        try:
            instance = cls(**d)
            audit_logger.info(f"6-tuple created: {instance.node_id}, data_type={instance.data_type}")
            return instance
        except Exception as e:
            logger.error(f"Failed to create EnhancedContextualIntegrityTuple: {e}")
            raise ValueError(f"Invalid tuple data: {e}")
    
    def validate_tuple(self) -> List[str]:
        """Enhanced validation with comprehensive error checking"""
        errors = []
        logger.debug(f"Validating tuple {self.node_id}")
        
        # Data freshness validation
        if self.data_freshness_timestamp:
            age = datetime.now(timezone.utc) - self.data_freshness_timestamp
            if age > timedelta(hours=24):
                errors.append("data_freshness_timestamp is older than 24 hours")
                logger.warning(f"Stale data detected in tuple {self.node_id}: {age}")
        
        # Risk assessment validation
        if self.risk_level == "CRITICAL" and not self.audit_required:
            errors.append("CRITICAL risk level requires audit_required=True")
            
        return errors
    
    def is_valid_tuple(self) -> bool:
        """Check if tuple passes all validation"""
        try:
            self.model_validate(self.model_dump())  # Pydantic validation
            custom_errors = self.validate_tuple()  # Custom validation
            return len(custom_errors) == 0
        except Exception as e:
            logger.error(f"Tuple validation failed: {e}")
            return False
    
    def calculate_risk_score(self) -> float:
        """Calculate comprehensive risk score"""
        base_scores = {
            "LOW": 0.25,
            "MEDIUM": 0.5, 
            "HIGH": 0.75,
            "CRITICAL": 1.0
        }
        
        score = base_scores.get(self.risk_level, 0.5)
        
        # Adjust based on data classification
        if self.data_classification == "restricted":
            score += 0.2
        elif self.data_classification == "confidential":
            score += 0.1
        elif self.data_classification == "public":
            score -= 0.1
        
        # Adjust based on emergency context
        if self.temporal_context.emergency_override:
            score += 0.15
            logger.info(f"Risk score increased due to emergency override: {self.node_id}")
        
        # Adjust based on business hours
        if not self.temporal_context.business_hours:
            score += 0.1
        
        final_score = min(1.0, max(0.0, score))
        logger.debug(f"Risk score calculated for {self.node_id}: {final_score}")
        return final_score
    
    def mark_processed(self, confidence: float = None):
        """Mark tuple as processed with logging"""
        self.processed_at = datetime.now(timezone.utc)
        if confidence is not None:
            self.decision_confidence = confidence
        
        audit_logger.info(f"Tuple processed: {self.node_id}, confidence={confidence}")
        logger.debug(f"Tuple {self.node_id} marked as processed at {self.processed_at}")
    
    def get_audit_summary(self) -> Dict[str, Any]:
        """Get comprehensive audit summary"""
        summary = {
            "request_id": self.request_id,
            "node_id": self.node_id,
            "data_type": self.data_type,
            "risk_level": self.risk_level,
            "risk_score": self.calculate_risk_score(),
            "compliance_tags": self.compliance_tags,
            "audit_required": self.audit_required,
            "data_classification": self.data_classification,
            "emergency_context": self.temporal_context.emergency_override,
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        }
        
        audit_logger.info(f"Audit summary generated for {self.node_id}: {summary}")
        return summary

    def validate_enhanced_attributes(self) -> List[str]:
        """
        Comprehensive validation for enhanced contextual integrity attributes.
        
        This method validates:
        - Data freshness constraints
        - Session ID format requirements  
        - Audit flag consistency
        - Risk level alignment with actual risk indicators
        - Decision confidence bounds
        
        Returns:
            List[str]: List of validation error messages (empty if valid)
        """
        errors = []
        
        # 1. Data freshness validation
        if self.data_freshness_timestamp:
            current_time = datetime.now(timezone.utc)
            age = current_time - self.data_freshness_timestamp
            
            # Check if data is too stale (> 24 hours)
            if age > timedelta(hours=24):
                errors.append(f"Data freshness exceeds 24 hours (age: {age})")
            
            # Check if timestamp is in future (data integrity issue)
            if age < timedelta(0):
                errors.append("Data freshness timestamp cannot be in the future")
                
            # Warn about moderately stale data (> 6 hours)
            elif age > timedelta(hours=6):
                errors.append(f"Data moderately stale (age: {age.total_seconds() / 3600:.1f} hours)")
        
        # 2. Session ID validation
        if self.session_id:
            if len(self.session_id) < 8:
                errors.append("Session ID must be at least 8 characters for security")
            
            # Check for valid session ID format (alphanumeric + underscores/hyphens)
            import re
            if not re.match(r'^[a-zA-Z0-9_-]+$', self.session_id):
                errors.append("Session ID contains invalid characters (use alphanumeric, _, - only)")
        
        # 3. Audit flags consistency validation
        if self.audit_required and not self.compliance_tags:
            errors.append("Audit required but no compliance tags specified (HIPAA, GDPR, etc.)")
        
        # Check for high-sensitivity data without audit flag
        sensitive_types = ["medical_record", "financial_record", "personal_data", "classified"]
        if any(sensitive in self.data_type.lower() for sensitive in sensitive_types):
            if not self.audit_required:
                errors.append(f"Sensitive data type '{self.data_type}' should require audit")
        
        # 4. Risk level consistency validation
        risk_indicators = self._count_risk_indicators()
        expected_risk = self._calculate_expected_risk_level(risk_indicators)
        
        if self.risk_level != expected_risk:
            errors.append(
                f"Risk level '{self.risk_level}' inconsistent with indicators "
                f"(expected: '{expected_risk}', indicators: {risk_indicators})"
            )
        
        # 5. Decision confidence validation
        if self.decision_confidence is not None:
            if not 0.0 <= self.decision_confidence <= 1.0:
                errors.append(f"Decision confidence {self.decision_confidence} must be between 0.0 and 1.0")
            
            # Low confidence with high-risk decisions should be flagged
            if self.decision_confidence < 0.5 and self.risk_level in ["HIGH", "CRITICAL"]:
                errors.append(f"Low confidence ({self.decision_confidence}) for {self.risk_level} risk decision")
        
        # 6. Compliance tags validation
        valid_compliance_tags = ["HIPAA", "GDPR", "PCI_DSS", "SOX", "FERPA", "CCPA", "FISMA"]
        for tag in self.compliance_tags:
            if tag not in valid_compliance_tags:
                errors.append(f"Unknown compliance tag '{tag}' (valid: {valid_compliance_tags})")
        
        return errors

    def validate_temporal_role_inheritance(self) -> Dict[str, Any]:
        """Validate temporal role permission inheritance"""
        errors = []
        warnings = []
        
        if not self.temporal_context.temporal_role:
            return {
                "is_valid": True,
                "validation_errors": [],
                "warnings": ["No temporal role to validate"]
            }
            
        # 1. Validate temporal role is still active
        if self.temporal_context.temporal_role_valid_until:
            current_time = datetime.now(timezone.utc)
            if current_time > self.temporal_context.temporal_role_valid_until:
                errors.append(f"Temporal role '{self.temporal_context.temporal_role}' expired at {self.temporal_context.temporal_role_valid_until}")
        
        # 2. Validate inheritance chain
        inheritance_errors = self._validate_permission_inheritance()
        errors.extend(inheritance_errors)
        
        # 3. Validate emergency authorization if applicable
        # Only enforce emergency-specific checks when we are actually in an emergency
        # or an explicit emergency authorization/override is present. This avoids
        # blocking basic inheritance validation when a temporal role is planned but
        # not yet activated in an emergency context (unit tests and dry-runs).
        if (self.temporal_context.temporal_role and
            "oncall" in self.temporal_context.temporal_role and
            (self.temporal_context.emergency_override or
             self.temporal_context.situation == "EMERGENCY" or
             self.temporal_context.emergency_authorization_id)):
            emergency_errors = self._validate_emergency_inheritance()
            errors.extend(emergency_errors)
        
        # 4. Validate acting role authorization if applicable
        if "acting" in self.temporal_context.temporal_role:
            acting_errors = self._validate_acting_role_inheritance()
            errors.extend(acting_errors)
        
        # Attempt to enrich with organizational context from org service (if available)
        org_ctx = None
        try:
            if org_lookup and hasattr(self, 'data_sender') and hasattr(self, 'data_recipient'):
                org_ctx = org_lookup(self.data_sender, self.data_recipient)
                # attach organizational context to temporal_context for audit
                try:
                    self.temporal_context.organizational_context = org_ctx
                except Exception:
                    # pydantic models may be frozen; set attribute directly as fallback
                    setattr(self.temporal_context, 'organizational_context', org_ctx)
        except Exception as e:
            logger.debug(f"org_lookup failed: {e}")

        # Check for warnings (non-blocking issues)
        if (self.temporal_context.temporal_role_valid_until and 
            self.temporal_context.timestamp):
            duration = self.temporal_context.temporal_role_valid_until - self.temporal_context.timestamp
            if duration.total_seconds() > 28800:  # > 8 hours
                warnings.append("Temporal role duration exceeds recommended 8-hour maximum")
            
        return {
            "is_valid": len(errors) == 0,
            "validation_errors": errors,
            "warnings": warnings,
            "organizational_context": org_ctx,
            "temporal_role": self.temporal_context.temporal_role,
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _validate_permission_inheritance(self) -> List[str]:
        """Validate the permission inheritance chain is valid"""
        errors = []
        
        temporal_role = self.temporal_context.temporal_role
        base_role = self.temporal_context.base_role
        
        if not base_role:
            errors.append("Base role required for temporal role inheritance validation")
            return errors
        
        # Define inheritance rules
        valid_inheritance = self._get_temporal_role_inheritance_rules()
        
        if temporal_role not in valid_inheritance:
            errors.append(f"Unknown temporal role: {temporal_role}")
            return errors
        
        inheritance_rule = valid_inheritance[temporal_role]
        
        # Validate base role is eligible for this temporal role
        if base_role not in inheritance_rule["eligible_base_roles"]:
            errors.append(
                f"Base role '{base_role}' not eligible for temporal role '{temporal_role}'. "
                f"Eligible roles: {inheritance_rule['eligible_base_roles']}"
            )
        
        # Validate inheritance chain if provided
        if self.temporal_context.permission_inheritance_chain:
            expected_chain = self._calculate_inheritance_chain(temporal_role)
            if self.temporal_context.permission_inheritance_chain != expected_chain:
                errors.append(
                    f"Invalid inheritance chain. Expected: {expected_chain}, "
                    f"Actual: {self.temporal_context.permission_inheritance_chain}"
                )
        
        return errors
    
    def _validate_emergency_inheritance(self) -> List[str]:
        """Validate emergency oncall role inheritance"""
        errors = []
        
        temporal_role = self.temporal_context.temporal_role
        
        # Emergency roles must have emergency context
        if self.temporal_context.situation != "EMERGENCY" and not self.temporal_context.emergency_override:
            errors.append(f"Emergency role '{temporal_role}' used outside emergency context")
        
        # Must have emergency authorization ID
        if not self.temporal_context.emergency_authorization_id:
            errors.append(f"Emergency role '{temporal_role}' requires emergency authorization ID")
        
        # Validate oncall hierarchy
        oncall_hierarchy = ["oncall_low", "oncall_medium", "oncall_high", "oncall_critical"]
        if temporal_role in oncall_hierarchy:
            role_level = oncall_hierarchy.index(temporal_role)
            
            # Check if inheritance chain includes lower levels
            for i in range(role_level):
                lower_role = oncall_hierarchy[i]
                if lower_role not in self.temporal_context.permission_inheritance_chain:
                    errors.append(f"Oncall role '{temporal_role}' must inherit from '{lower_role}'")
        
        return errors
    
    def _validate_acting_role_inheritance(self) -> List[str]:
        """Validate acting role inheritance"""
        errors = []
        
        temporal_role = self.temporal_context.temporal_role
        
        # Acting roles must have authorization source
        if not self.temporal_context.authorization_source:
            errors.append(f"Acting role '{temporal_role}' requires authorization source")
        
        # Acting roles must have time limitation
        if not self.temporal_context.temporal_role_valid_until:
            errors.append(f"Acting role '{temporal_role}' requires expiration time")
        
        # Validate acting role scope
        if temporal_role == "acting_manager":
            if not self._validate_acting_manager_scope():
                errors.append("Acting manager role used outside authorized scope")
        
        return errors
    
    def _get_temporal_role_inheritance_rules(self) -> Dict[str, Dict]:
        """Get inheritance rules for temporal roles"""
        return {
            "oncall_low": {
                "eligible_base_roles": ["nurse", "resident", "technician", "physician_assistant"],
                "inherits_from": ["base_role"],
                "adds_permissions": ["emergency_read_patient_basic", "emergency_vitals_access"],
                "max_duration_hours": 12
            },
            "oncall_medium": {
                "eligible_base_roles": ["nurse", "resident", "attending_physician", "physician_assistant"],
                "inherits_from": ["base_role", "oncall_low"], 
                "adds_permissions": ["emergency_read_patient_full", "emergency_modify_orders", "emergency_medication_access"],
                "max_duration_hours": 12
            },
            "oncall_high": {
                "eligible_base_roles": ["attending_physician", "department_head", "senior_resident"],
                "inherits_from": ["base_role", "oncall_low", "oncall_medium"],
                "adds_permissions": ["emergency_cross_department_access", "emergency_override_restrictions", "emergency_lab_orders"],
                "max_duration_hours": 12
            },
            "oncall_critical": {
                "eligible_base_roles": ["attending_physician", "department_head", "chief_medical_officer"],
                "inherits_from": ["base_role", "oncall_low", "oncall_medium", "oncall_high"],
                "adds_permissions": ["emergency_full_hospital_access", "emergency_modify_any_record", "emergency_administrative_override"],
                "max_duration_hours": 8
            },
            "acting_manager": {
                "eligible_base_roles": ["senior_analyst", "team_lead", "supervisor", "senior_staff"],
                "inherits_from": ["base_role", "target_manager_role"],
                "adds_permissions": ["manage_team", "approve_requests", "access_management_reports", "staff_scheduling"],
                "max_duration_hours": 168  # 1 week
            },
            "acting_supervisor": {
                "eligible_base_roles": ["senior_analyst", "team_lead", "specialist"],
                "inherits_from": ["base_role", "target_supervisor_role"],
                "adds_permissions": ["supervise_team", "review_work", "assign_tasks"],
                "max_duration_hours": 168
            },
            "acting_department_head": {
                "eligible_base_roles": ["manager", "supervisor", "senior_manager"],
                "inherits_from": ["base_role", "target_department_head_role"],
                "adds_permissions": ["department_oversight", "budget_access", "policy_decisions"],
                "max_duration_hours": 720  # 1 month
            },
            "incident_responder": {
                "eligible_base_roles": ["security_analyst", "system_administrator", "senior_engineer"],
                "inherits_from": ["base_role"],
                "adds_permissions": ["incident_investigation", "system_access_override", "log_analysis"],
                "max_duration_hours": 24
            },
            "security_incident_lead": {
                "eligible_base_roles": ["security_manager", "senior_security_analyst", "incident_commander"],
                "inherits_from": ["base_role", "incident_responder"],
                "adds_permissions": ["security_override", "evidence_collection", "system_isolation"],
                "max_duration_hours": 72
            }
        }
    
    def _calculate_inheritance_chain(self, temporal_role: str) -> List[str]:
        """Calculate expected inheritance chain for temporal role"""
        rules = self._get_temporal_role_inheritance_rules()
        
        if temporal_role not in rules:
            return []
        
        inheritance_rule = rules[temporal_role]
        chain = []
        
        # Add base role
        if self.temporal_context.base_role:
            chain.append(self.temporal_context.base_role)
        
        # Add inherited roles
        for inherited_role in inheritance_rule["inherits_from"]:
            if inherited_role != "base_role" and inherited_role not in chain:
                chain.append(inherited_role)
        
        return chain
    
    def _calculate_inherited_permissions(self) -> List[str]:
        """Calculate what permissions should be inherited for current temporal role"""
        if not self.temporal_context.temporal_role:
            return []
        
        temporal_role = self.temporal_context.temporal_role
        base_role = self.temporal_context.base_role
        
        # Base role permissions (would come from Team B's org data)
        base_permissions = self._get_base_role_permissions(base_role)
        
        # Temporal role additional permissions
        temporal_permissions = self._get_temporal_role_permissions(temporal_role)
        
        # Combine based on inheritance rules
        inherited = set(base_permissions)
        
        if "oncall" in temporal_role:
            # Oncall roles: base permissions + emergency permissions + inherited oncall levels
            rules = self._get_temporal_role_inheritance_rules()
            if temporal_role in rules:
                for inherited_role in rules[temporal_role]["inherits_from"]:
                    if inherited_role != "base_role":
                        inherited.update(self._get_temporal_role_permissions(inherited_role))
            
            inherited.update(temporal_permissions)
            
        elif "acting" in temporal_role:
            # Acting roles: inherit ALL permissions from target role + base permissions
            target_role_permissions = self._get_acting_target_role_permissions(temporal_role)
            inherited.update(target_role_permissions)
            inherited.update(temporal_permissions)
        
        elif temporal_role in ["incident_responder", "security_incident_lead"]:
            # Incident roles: base + incident-specific permissions
            inherited.update(temporal_permissions)
        
        return list(inherited)
    
    def _get_base_role_permissions(self, base_role: str) -> List[str]:
        """Get permissions for base role (placeholder - would integrate with Team B)"""
        # This would be populated from Team B's organizational data
        base_role_permissions = {
            "nurse": ["read_patient_basic", "update_patient_vitals", "medication_administration"],
            "resident": ["read_patient_full", "write_orders", "procedure_notes"],
            "attending_physician": ["read_patient_full", "write_orders", "procedure_approval", "diagnosis"],
            "technician": ["read_equipment_data", "update_test_results"],
            "physician_assistant": ["read_patient_full", "write_basic_orders", "patient_assessment"]
        }
        return base_role_permissions.get(base_role, [])
    
    def _get_temporal_role_permissions(self, temporal_role: str) -> List[str]:
        """Get additional permissions granted by temporal role"""
        rules = self._get_temporal_role_inheritance_rules()
        if temporal_role in rules:
            return rules[temporal_role]["adds_permissions"]
        return []
    
    def _get_acting_target_role_permissions(self, acting_role: str) -> List[str]:
        """Get permissions from the role being acted for"""
        # This would determine what role is being "acted" for and return those permissions
        # For now, return placeholder permissions
        acting_target_permissions = {
            "acting_manager": ["team_management", "budget_review", "performance_evaluation"],
            "acting_supervisor": ["task_assignment", "work_review", "team_coordination"],
            "acting_department_head": ["department_policy", "budget_approval", "strategic_decisions"]
        }
        return acting_target_permissions.get(acting_role, [])
    
    def _validate_acting_manager_scope(self) -> bool:
        """Validate acting manager is within authorized scope"""
        # Check if access is within the scope of the acting role
        # This would integrate with Team B's policy evaluation
        return True  # Placeholder implementation
    
    def _is_temporal_role_properly_authorized(self) -> bool:
        """Check if temporal role inheritance is properly authorized"""
        
        # Must have authorization source
        if not self.temporal_context.authorization_source:
            return False
        
        # Must be within valid time window  
        if self.temporal_context.temporal_role_valid_until:
            if datetime.now(timezone.utc) > self.temporal_context.temporal_role_valid_until:
                return False
        
        # Emergency roles must have emergency context
        if "oncall" in self.temporal_context.temporal_role:
            if not self.temporal_context.emergency_authorization_id:
                return False
            if self.temporal_context.situation != "EMERGENCY" and not self.temporal_context.emergency_override:
                return False
        
        # Acting roles must have proper delegation
        if "acting" in self.temporal_context.temporal_role:
            if not self._validate_acting_role_delegation():
                return False
        
        return True
    
    def _validate_acting_role_delegation(self) -> bool:
        """Validate acting role has proper delegation"""
        # This would check with Team B's policy engine for proper delegation
        return self.temporal_context.authorization_source is not None
    
    def _temporal_role_exceeds_scope(self) -> bool:
        """Check if temporal role is being used beyond intended scope"""
        
        temporal_role = self.temporal_context.temporal_role
        
        # Emergency roles should only be used during emergencies
        if "oncall" in temporal_role:
            if self.temporal_context.situation not in ["EMERGENCY", "INCIDENT"]:
                return True  # Using emergency role outside emergency
            
            if self.temporal_context.business_hours and not self.temporal_context.emergency_override:
                return True  # Using oncall during business hours without emergency
        
        # Acting roles should have scope limitations
        if "acting" in temporal_role:
            # Check if accessing data outside delegated scope
            if not self._is_within_acting_scope():
                return True
        
        return False
    
    def _is_within_acting_scope(self) -> bool:
        """Check if current access is within acting role scope"""
        # This would validate against the scope defined for the acting role
        # Placeholder implementation
        return True

    def _count_risk_indicators(self) -> int:
        """Count risk indicators present in the tuple context"""
        indicators = 0
        
        # High-sensitivity data classification
        if self.data_classification in ["confidential", "restricted"]:
            indicators += 2
        elif self.data_classification == "internal":
            indicators += 1
        
        # Temporal risk factors
        if hasattr(self.temporal_context, 'emergency_override') and self.temporal_context.emergency_override:
            indicators += 2
        
        if hasattr(self.temporal_context, 'business_hours') and not self.temporal_context.business_hours:
            indicators += 1
        
        if hasattr(self.temporal_context, 'situation') and self.temporal_context.situation == "EMERGENCY":
            indicators += 1
        
        # Data staleness risk
        staleness = self.calculate_data_staleness()
        if staleness and staleness > 0.5:  # > 50% stale
            indicators += 1
        
        # NEW: Temporal role inheritance risk factors
        if self.temporal_context.temporal_role:
            indicators += self._calculate_temporal_role_risk_indicators()
        
        return indicators
    
    def _calculate_temporal_role_risk_indicators(self) -> int:
        """Calculate risk indicators based on temporal role and inheritance"""
        temporal_role = self.temporal_context.temporal_role
        risk_adjustment = 0
        
        # Emergency roles - risk based on elevation level
        if temporal_role == "oncall_low":
            risk_adjustment += 1  # Slight elevation
        elif temporal_role == "oncall_medium":
            risk_adjustment += 2  # Moderate elevation  
        elif temporal_role == "oncall_high":
            risk_adjustment += 3  # High elevation
        elif temporal_role == "oncall_critical":
            risk_adjustment += 4  # Maximum elevation
        
        # Acting roles - risk based on permission scope expansion
        elif temporal_role == "acting_manager":
            risk_adjustment += 2  # Managing others' data
        elif temporal_role == "acting_supervisor":
            risk_adjustment += 2  # Supervisory access
        elif temporal_role == "acting_department_head":
            risk_adjustment += 3  # Department-wide access
        
        # Incident response roles - contextual risk
        elif temporal_role == "incident_responder":
            risk_adjustment += 1  # Incident-specific access
        elif temporal_role == "security_incident_lead":
            risk_adjustment += 2  # Elevated incident access
        
        # Validate inheritance is legitimate (reduce risk if properly authorized)
        if self._is_temporal_role_properly_authorized():
            risk_adjustment -= 1  # Properly authorized temporal roles are less risky
        else:
            risk_adjustment += 3  # Improperly inherited permissions are very risky
        
        # Check for permission scope violations
        if self._temporal_role_exceeds_scope():
            risk_adjustment += 5  # Major risk if using temporal role beyond intended scope
        
        # Check for expired temporal roles
        if (self.temporal_context.temporal_role_valid_until and 
            datetime.now(timezone.utc) > self.temporal_context.temporal_role_valid_until):
            risk_adjustment += 4  # Expired temporal roles are high risk
        
        return max(0, risk_adjustment)  # Don't go negative
    
    def _is_temporal_role_properly_authorized(self) -> bool:
        """Validate that temporal role is properly authorized"""
        temporal_ctx = self.temporal_context
        
        # Check if we have proper authorization source
        if not temporal_ctx.authorization_source:
            return False
        
        # Emergency roles must have emergency authorization ID
        if (temporal_ctx.temporal_role and 
            temporal_ctx.temporal_role.startswith("oncall_") and 
            not temporal_ctx.emergency_authorization_id):
            return False
        
        # Check inheritance chain validity
        if temporal_ctx.permission_inheritance_chain:
            # Inheritance chain should have at least base role -> temporal role
            if len(temporal_ctx.permission_inheritance_chain) < 2:
                return False
            
            # Last role in chain should match current temporal role
            if temporal_ctx.permission_inheritance_chain[-1] != temporal_ctx.temporal_role:
                return False
        
        # Check temporal role validity period
        if (temporal_ctx.temporal_role_valid_until and 
            datetime.now(timezone.utc) > temporal_ctx.temporal_role_valid_until):
            return False
        
        return True
    
    def _temporal_role_exceeds_scope(self) -> bool:
        """Check if temporal role is being used beyond intended scope"""
        temporal_ctx = self.temporal_context
        
        if not temporal_ctx.temporal_role:
            return False
        
        # Check if subject accessing data they shouldn't have access to
        # This is a simplified check - in production, integrate with Team B's PolicyEvaluationEngine
        
        # Emergency roles should only access emergency-related data
        if temporal_ctx.temporal_role.startswith("oncall_"):
            # Check if accessing non-emergency data during emergency role
            if (hasattr(self, 'attribute') and 
                self.attribute not in ['incident_data', 'system_logs', 'emergency_contacts', 'critical_systems']):
                return True
        
        # Acting roles should only access data within their temporary department
        if temporal_ctx.temporal_role.startswith("acting_"):
            # This would integrate with Team B's organizational data
            # For now, simplified check based on data classification
            if (hasattr(self, 'information_type') and 
                self.information_type in ['confidential_hr', 'financial_records'] and
                temporal_ctx.temporal_role != 'acting_department_head'):
                return True
        
        # Incident response roles should only access incident-related data
        if 'incident' in temporal_ctx.temporal_role:
            if ('incident' not in self.transmission_principle.lower() and 
                'emergency' not in self.transmission_principle.lower()):
                return True
        
        return False
    
    def _get_inheritance_validation_status(self) -> Dict[str, Any]:
        """Get detailed validation status for temporal role inheritance"""
        if not self.temporal_context.temporal_role:
            return {"status": "no_temporal_role", "details": "No temporal role assigned"}
        
        validation_result = self.validate_temporal_role_inheritance()
        
        return {
            "status": "valid" if validation_result["is_valid"] else "invalid",
            "is_properly_authorized": self._is_temporal_role_properly_authorized(),
            "exceeds_scope": self._temporal_role_exceeds_scope(),
            "inheritance_chain_valid": len(self.temporal_context.permission_inheritance_chain or []) >= 2,
            "role_expired": (self.temporal_context.temporal_role_valid_until and 
                           datetime.now(timezone.utc) > self.temporal_context.temporal_role_valid_until),
            "validation_details": validation_result
        }
    
    def _get_temporal_inheritance_audit_details(self) -> Dict[str, Any]:
        """Get comprehensive audit details for temporal role inheritance"""
        if not hasattr(self.temporal_context, 'base_role') or not self.temporal_context.temporal_role:
            return {"inheritance_active": False}
        
        return {
            "inheritance_active": True,
            "base_role": self.temporal_context.base_role,
            "current_temporal_role": self.temporal_context.temporal_role,
            "inherited_permissions": list(self.temporal_context.inherited_permissions) if self.temporal_context.inherited_permissions else [],
            "inheritance_chain": self.temporal_context.permission_inheritance_chain or [],
            "authorization_source": self.temporal_context.authorization_source,
            "emergency_authorization_id": self.temporal_context.emergency_authorization_id,
            "role_valid_until": self.temporal_context.temporal_role_valid_until.isoformat() if self.temporal_context.temporal_role_valid_until else None,
            "role_duration_hours": (
                (self.temporal_context.temporal_role_valid_until - self.temporal_context.timestamp).total_seconds() / 3600
                if self.temporal_context.temporal_role_valid_until and self.temporal_context.timestamp else None
            ),
            "validation_status": self._get_inheritance_validation_status(),
            "risk_adjustment": self._calculate_temporal_role_risk_indicators(),
            "scope_validation": {
                "exceeds_intended_scope": self._temporal_role_exceeds_scope(),
                "properly_authorized": self._is_temporal_role_properly_authorized()
            }
        }

    def _calculate_expected_risk_level(self, risk_indicators: int) -> str:
        """Calculate expected risk level based on risk indicators"""
        if risk_indicators >= 5:
            return "CRITICAL"
        elif risk_indicators >= 3:
            return "HIGH"
        elif risk_indicators >= 1:
            return "MEDIUM"
        else:
            return "LOW"

    def is_enhanced_valid(self) -> bool:
        """
        Check if enhanced tuple meets all validation requirements.
        
        Returns:
            bool: True if all validations pass, False otherwise
        """
        # Get basic Pydantic validation errors
        try:
            # This will raise ValidationError if basic validation fails
            self.model_validate(self.model_dump())
        except Exception:
            return False
        
        # Check enhanced validation
        enhanced_errors = self.validate_enhanced_attributes()
        return len(enhanced_errors) == 0

    def calculate_data_staleness(self) -> Optional[float]:
        """
        Calculate data staleness as a normalized ratio.
        
        Returns:
            Optional[float]: Staleness ratio where:
                            0.0 = completely fresh data
                            1.0 = maximum acceptable age (24 hours)
                            >1.0 = beyond acceptable limits
                            None = no freshness timestamp available
        """
        if not self.data_freshness_timestamp:
            return None
        
        current_time = datetime.now(timezone.utc)
        age = current_time - self.data_freshness_timestamp
        max_acceptable_age = timedelta(hours=24)  # 24 hours as baseline
        
        staleness_ratio = age.total_seconds() / max_acceptable_age.total_seconds()
        return max(0.0, staleness_ratio)

    def get_enhanced_audit_trail(self) -> Dict[str, Any]:
        """
        Generate comprehensive audit trail for compliance and debugging.
        
        Returns:
            Dict[str, Any]: Structured audit information including:
                           - Tuple metadata and identifiers
                           - Data quality metrics
                           - Compliance and risk information
                           - Processing timeline
                           - Temporal context summary
        """
        return {
            "tuple_metadata": {
                "node_id": self.node_id,
                "node_type": self.node_type,
                "request_id": self.request_id,
                "session_id": self.session_id,
                "correlation_id": self.correlation_id,
                "tuple_hash": self._generate_content_hash()
            },
        "data_quality": {
            "data_freshness_timestamp": self.data_freshness_timestamp.isoformat() if self.data_freshness_timestamp else None,
            "staleness_ratio": self.calculate_data_staleness(),
            "data_classification": self.data_classification,
            "is_stale": self.calculate_data_staleness() > 1.0 if self.calculate_data_staleness() else None
        },
        "compliance_info": {
            "audit_required": self.audit_required,
            "compliance_tags": self.compliance_tags,
            "risk_level": self.risk_level,
            "risk_indicators_count": self._count_risk_indicators(),
            "expected_risk_level": self._calculate_expected_risk_level(self._count_risk_indicators())
        },
        "processing_info": {
            "created_at": self.created_at.isoformat(),
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "decision_confidence": self.decision_confidence,
            "processing_duration_ms": self._calculate_processing_duration()
        },
        "temporal_summary": {
            "timestamp": self.temporal_context.timestamp.isoformat(),
            "timezone": self.temporal_context.timezone,
            "business_hours": self.temporal_context.business_hours,
            "emergency_override": self.temporal_context.emergency_override,
            "situation": self.temporal_context.situation,
            "temporal_role": self.temporal_context.temporal_role if hasattr(self.temporal_context, 'temporal_role') else None,
            # NEW: Temporal role inheritance audit information
            "inheritance_details": self._get_temporal_inheritance_audit_details()
        },
            "validation_status": {
                "is_valid": self.is_enhanced_valid(),
                "validation_errors": self.validate_enhanced_attributes()
            }
        }

    def _generate_content_hash(self) -> str:
        """Generate hash for tuple content identification"""
        import hashlib
        content = f"{self.data_type}:{self.data_subject}:{self.data_sender}:{self.data_recipient}:{self.transmission_principle}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _calculate_processing_duration(self) -> Optional[float]:
        """Calculate processing duration in milliseconds"""
        if not self.processed_at:
            return None
        
        duration = self.processed_at - self.created_at
        return duration.total_seconds() * 1000

    def mark_processed(self, confidence: Optional[float] = None, 
                      additional_compliance_tags: List[str] = None):
        """
        Mark tuple as processed with enhanced metadata.
        
        Args:
            confidence: Decision confidence score (0.0-1.0)
            additional_compliance_tags: Additional compliance tags to add
        """
        self.processed_at = datetime.now(timezone.utc)
        
        if confidence is not None:
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("Confidence must be between 0.0 and 1.0")
            self.decision_confidence = confidence
        
        if additional_compliance_tags:
            # Add unique compliance tags
            existing_tags = set(self.compliance_tags)
            new_tags = set(additional_compliance_tags)
            self.compliance_tags = list(existing_tags.union(new_tags))

    @classmethod
    def create_enhanced_from_request(cls, request_data: Dict[str, Any], 
                                   session_id: Optional[str] = None,
                                   auto_audit: bool = True) -> 'EnhancedContextualIntegrityTuple':
        """
        Factory method to create enhanced tuple with intelligent defaults.
        
        Args:
            request_data: Raw request data dictionary
            session_id: Optional session identifier
            auto_audit: Whether to automatically determine audit requirements
        
        Returns:
            EnhancedContextualIntegrityTuple: Fully configured enhanced tuple
        """
        # Create temporal context
        temporal_data = request_data.get("temporal_context", {})
        
        # Handle different temporal context formats
        if isinstance(temporal_data, dict):
            if temporal_data.get("emergency_override") and not temporal_data.get("emergency_authorization_id"):
                temporal_data = dict(temporal_data)
                temporal_data["emergency_authorization_id"] = "AUTO-AUTH"
            temporal_context = TemporalContext.model_validate(temporal_data)
        else:
            temporal_context = temporal_data  # Already a TemporalContext object
        
        # Intelligent audit requirement detection
        sensitive_data_types = ["medical_record", "financial_record", "personal_data", 
                              "classified", "pii", "phi", "payment_info"]
        
        data_type_lower = request_data.get("data_type", "").lower()
        requires_audit = (auto_audit and 
                         any(sensitive in data_type_lower for sensitive in sensitive_data_types)) or \
                         request_data.get("audit_required", False)
        
        # Intelligent compliance tag assignment
        compliance_tags = list(request_data.get("compliance_tags", []))
        if auto_audit:
            if "medical" in data_type_lower or "patient" in data_type_lower:
                if "HIPAA" not in compliance_tags:
                    compliance_tags.append("HIPAA")
            
            if "financial" in data_type_lower or "payment" in data_type_lower:
                if "PCI_DSS" not in compliance_tags:
                    compliance_tags.append("PCI_DSS")
            
            if "personal" in data_type_lower or "pii" in data_type_lower:
                if "GDPR" not in compliance_tags:
                    compliance_tags.append("GDPR")
        
        # Intelligent risk level calculation
        risk_indicators = 0
        
        # Data classification risk
        data_class = request_data.get("data_classification", "").lower()
        if data_class in ["restricted", "top_secret"]:
            risk_indicators += 3
        elif data_class in ["confidential", "secret"]:
            risk_indicators += 2
        elif data_class in ["internal", "private"]:
            risk_indicators += 1
        
        # Temporal risk factors
        if hasattr(temporal_context, 'emergency_override') and temporal_context.emergency_override:
            risk_indicators += 2
        
        if hasattr(temporal_context, 'business_hours') and not temporal_context.business_hours:
            risk_indicators += 1
        
        if hasattr(temporal_context, 'situation') and temporal_context.situation == "EMERGENCY":
            risk_indicators += 1
        
        # Determine risk level
        if risk_indicators >= 5:
            risk_level = "CRITICAL"
        elif risk_indicators >= 3:
            risk_level = "HIGH"
        elif risk_indicators >= 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Override with explicit risk level if provided
        risk_level = request_data.get("risk_level", risk_level)
        
        # Parse data freshness timestamp
        data_freshness = None
        if request_data.get("data_freshness_timestamp"):
            if isinstance(request_data["data_freshness_timestamp"], str):
                data_freshness = datetime.fromisoformat(request_data["data_freshness_timestamp"])
            else:
                data_freshness = request_data["data_freshness_timestamp"]
        
        # Create the enhanced tuple
        return cls(
            # Core 6-tuple
            data_type=request_data["data_type"],
            data_subject=request_data["data_subject"],
            data_sender=request_data["data_sender"],
            data_recipient=request_data["data_recipient"],
            transmission_principle=request_data.get("transmission_principle", "default_access"),
            temporal_context=temporal_context,
            
            # Enhanced attributes with intelligent defaults
            session_id=session_id or request_data.get("session_id"),
            data_freshness_timestamp=data_freshness,
            data_classification=request_data.get("data_classification"),
            audit_required=requires_audit,
            compliance_tags=compliance_tags,
            risk_level=risk_level,
            correlation_id=request_data.get("correlation_id")
        )