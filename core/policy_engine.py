# core/policy_engine.py
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from core.tuples import EnhancedContextualIntegrityTuple, TemporalContext
import yaml
from pathlib import Path

class TemporalPolicyEngine:
    """
    Core engine for evaluating temporal policies based on the 6-tuple framework
    """
    
    def __init__(self, config_file: str = "mocks/rules.yaml", neo4j_manager=None, graphiti_manager=None):
        """Initialize PolicyEngine with YAML config file and optional Neo4j or Graphiti manager."""
        self.config_file = config_file
        self.neo4j_manager = neo4j_manager
        self.graphiti_manager = graphiti_manager
        
        # Set up file paths for YAML fallback
        self.rules_file = config_file
        self.oncall_file = "mocks/oncall.yaml"
        self.incidents_file = "mocks/incidents.yaml"
        
        # Set up data source preferences
        self.use_neo4j = neo4j_manager is not None
        self.use_graphiti = graphiti_manager is not None
        
        self.rules = self._load_rules()
    
    def _load_rules(self):
        """Load rules from Graphiti, Neo4j or YAML file."""
        if self.graphiti_manager:
            try:
                return self._load_rules_from_graphiti()
            except Exception as e:
                print(f"Failed to load rules from Graphiti: {e}")
                print("Falling back to YAML file...")
        elif self.neo4j_manager:
            try:
                return self._load_rules_from_neo4j()
            except Exception as e:
                print(f"Failed to load rules from Neo4j: {e}")
                print("Falling back to YAML file...")
        
        return self._load_yaml_data()[0]  # Return just rules from YAML
    
    def _load_rules_from_graphiti(self) -> List[Dict[str, Any]]:
        """Load policy rules from Graphiti knowledge graph"""
        try:
            # Search for policy rule entities
            rule_entities = self.graphiti_manager.search_entities(
                entity_type="PolicyRule",
                filters={"team": "llm_security"}
            )
            
            rules = []
            for entity in rule_entities:
                # Convert Graphiti entity to rule dictionary
                rule_dict = self._convert_graphiti_rule_to_dict(entity)
                rules.append(rule_dict)
            
            # Sort by priority and creation time
            rules.sort(key=lambda r: (r.get("priority", 100), r.get("created_at", "")))
            
            return rules if rules else self._load_yaml_data()[0]  # Fallback to YAML
        except Exception as e:
            print(f"Error loading rules from Graphiti: {e}")
            return self._load_yaml_data()[0]  # Fallback to YAML
    
    def _convert_graphiti_rule_to_dict(self, graphiti_entity) -> Dict[str, Any]:
        """Convert Graphiti entity format to expected dictionary format"""
        props = graphiti_entity.get("properties", {})
        
        return {
            "id": props.get("rule_id", props.get("id")),
            "action": props.get("action", "DENY"),
            "tuples": {
                "data_type": props.get("data_type"),
                "data_sender": props.get("data_sender"),
                "data_recipient": props.get("data_recipient"),
                "transmission_principle": props.get("transmission_principle")
            },
            "temporal_context": {
                "situation": props.get("situation"),
                "require_emergency_override": props.get("require_emergency_override", False),
                "access_window": props.get("access_window")
            },
            "priority": props.get("priority", 100),
            "created_at": props.get("created_at")
        }
    
    def save_rule_to_graphiti(self, rule: Dict[str, Any]) -> str:
        """Save a policy rule to Graphiti knowledge graph"""
        if not self.graphiti_manager:
            raise ValueError("Graphiti manager not configured")
        
        # Extract rule components
        tuples = rule.get("tuples", {})
        temporal_context = rule.get("temporal_context", {})
        
        # Create PolicyRule entity
        entity_id = self.graphiti_manager.create_entity(
            entity_type="PolicyRule",
            properties={
                "rule_id": rule.get("id"),
                "action": rule.get("action", "DENY"),
                "data_type": tuples.get("data_type"),
                "data_sender": tuples.get("data_sender"),
                "data_recipient": tuples.get("data_recipient"),
                "transmission_principle": tuples.get("transmission_principle"),
                "situation": temporal_context.get("situation"),
                "require_emergency_override": temporal_context.get("require_emergency_override", False),
                "access_window": temporal_context.get("access_window"),
                "priority": rule.get("priority", 100),
                "team": "llm_security"
            }
        )
        
        return entity_id
    
    def evaluate_temporal_access(
        self, 
        request: EnhancedContextualIntegrityTuple,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate temporal access based on 6-tuple contextual integrity
        """
        result = {
            "decision": "DENY",
            "reasons": [],
            "temporal_factors": {},
            "policy_matched": None,
            "expires_at": None,
            "next_review": None,
            "confidence_score": 0.0,
            "risk_level": "high"
        }
        
        # Load temporal policies (Neo4j first, YAML fallback)
        if self.use_neo4j:
            try:
                rules = self._load_rules_from_neo4j()
                oncall_data = self._load_oncall_data_from_neo4j()
                incidents_data = self._load_incidents_from_neo4j()
            except Exception as e:
                # Fallback to YAML if Neo4j fails
                print(f"Warning: Neo4j load failed, using YAML fallback: {e}")
                rules, oncall_data, incidents_data = self._load_yaml_data()
        else:
            rules, oncall_data, incidents_data = self._load_yaml_data()
        
        # Evaluate temporal context
        temporal_eval = self._evaluate_temporal_context(
            request.temporal_context, 
            oncall_data,
            incidents_data
        )
        result["temporal_factors"] = temporal_eval
        
        # Check emergency override first (highest priority)
        if request.temporal_context.emergency_override:
            result["decision"] = "ALLOW"
            result["reasons"].append("Emergency override active")
            result["expires_at"] = (
                datetime.now(timezone.utc) + timedelta(hours=4)
            ).isoformat()
            result["confidence_score"] = 0.9
            result["risk_level"] = "medium"
            return result
        
        # Check critical service bypass
        service_bypass = self._check_service_bypass(request, oncall_data)
        if service_bypass["allowed"]:
            result["decision"] = "ALLOW"
            result["reasons"].extend(service_bypass["reasons"])
            result["expires_at"] = service_bypass.get("expires_at")
            result["confidence_score"] = 0.8
            result["risk_level"] = "low"
            return result
        
        # Evaluate against temporal rules
        best_match = None
        best_score = 0
        
        for rule in rules:
            match_result = self._matches_temporal_rule(request, rule)
            if match_result["matches"] and match_result["score"] > best_score:
                best_match = rule
                best_score = match_result["score"]
        
        if best_match:
            result["decision"] = best_match.get("action", "DENY")
            result["policy_matched"] = best_match.get("id")
            result["reasons"].append(f"Matched policy: {best_match.get('id')}")
            result["confidence_score"] = best_score
            result["risk_level"] = self._calculate_risk_level(request, best_match)
            
            # Set expiration based on rule
            if "temporal_context" in best_match:
                tc = best_match["temporal_context"]
                if "access_window" in tc and tc["access_window"].get("end"):
                    result["expires_at"] = tc["access_window"]["end"]
                else:
                    # Default 8-hour expiration for matched policies
                    result["expires_at"] = (
                        datetime.now(timezone.utc) + timedelta(hours=8)
                    ).isoformat()
        
        # Default deny with comprehensive reasons
        if result["decision"] == "DENY":
            result["reasons"].append("No matching temporal policy found")
            if not temporal_eval["business_hours"]:
                result["reasons"].append("Outside business hours")
            if temporal_eval["weekend"] and not temporal_eval["weekend_support"]:
                result["reasons"].append("Weekend access not permitted for this service")
            if temporal_eval["data_stale"]:
                result["reasons"].append("Data freshness requirements not met")
        
        # Set next review time
        result["next_review"] = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat()
        
        return result
    
    def _evaluate_temporal_context(
        self, 
        temporal_context: TemporalContext,
        oncall_data: Dict[str, Any],
        incidents_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate the temporal context against business rules
        """
        now = temporal_context.timestamp
        bh = oncall_data.get("business_hours", {})
        
        # Check if weekend
        is_weekend = now.weekday() >= 5
        weekend_support = bh.get("weekend_support", {})
        
        # Check data freshness
        data_stale = (
            temporal_context.data_freshness_seconds is not None and 
            temporal_context.data_freshness_seconds > 3600
        )
        
        # Count active incidents
        active_incidents = len([
            inc for inc in incidents_data.get("incidents", [])
            if inc.get("status") == "investigating"
        ])
        
        return {
            "business_hours": temporal_context.business_hours,
            "emergency_active": temporal_context.emergency_override,
            "current_hour": now.hour,
            "timezone": temporal_context.timezone,
            "situation": temporal_context.situation,
            "temporal_role": temporal_context.temporal_role,
            "data_stale": data_stale,
            "weekend": is_weekend,
            "weekend_support": not weekend_support.get("critical_only", True),
            "active_incidents_count": active_incidents,
            "data_freshness_ok": not data_stale
        }
    
    def _check_service_bypass(
        self,
        request: EnhancedContextualIntegrityTuple,
        oncall_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if service qualifies for emergency bypass
        """
        global_policies = oncall_data.get("global_policies", {})
        bypass_roles = global_policies.get("emergency_bypass_roles", [])
        
        # Extract service from recipient or sender
        service = None
        if hasattr(request, 'data_sender'):
            service = request.data_sender
        elif hasattr(request, 'data_recipient'):
            service = request.data_recipient
        
        if service in bypass_roles:
            return {
                "allowed": True,
                "reasons": [f"Service {service} has emergency bypass authorization"],
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
            }
        
        # Check for critical service during incident
        if (request.temporal_context.emergency_override and 
            request.temporal_context.temporal_role and 
            "critical" in request.temporal_context.temporal_role):
            return {
                "allowed": True,
                "reasons": ["Critical service during active incident"],
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            }
        
        return {"allowed": False, "reasons": []}
    
    def _matches_temporal_rule(
        self, 
        request: EnhancedContextualIntegrityTuple, 
        rule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if request matches a temporal rule with scoring
        """
        score = 0.0
        max_score = 6.0  # 6-tuple elements
        
        # Check tuple matching
        tuples = rule.get("tuples", {})
        tuple_match = self._matches_tuple_fields(request, tuples)
        if not tuple_match["matches"]:
            return {"matches": False, "score": 0.0}
        
        score += tuple_match["score"]
        
        # Check temporal constraints
        temporal_constraints = rule.get("temporal_context", {})
        temporal_match = self._matches_temporal_constraints(
            request.temporal_context, 
            temporal_constraints
        )
        
        if not temporal_match["matches"]:
            return {"matches": False, "score": 0.0}
        
        score += temporal_match["score"]
        
        return {"matches": True, "score": score / max_score}
    
    def _matches_tuple_fields(
        self, 
        request: EnhancedContextualIntegrityTuple, 
        rule_tuples: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if request matches tuple field constraints with scoring
        """
        score = 0.0
        fields_checked = 0
        
        tuple_fields = {
            "data_type": getattr(request, "data_type", None),
            "data_sender": getattr(request, "data_sender", None),
            "data_recipient": getattr(request, "data_recipient", None),
            "transmission_principle": getattr(request, "transmission_principle", None)
        }
        
        for field, expected in rule_tuples.items():
            if field in tuple_fields:
                fields_checked += 1
                actual = tuple_fields[field]
                
                if expected == "*":
                    score += 0.5  # Wildcard match gets partial credit
                elif isinstance(expected, list):
                    if actual in expected:
                        score += 1.0  # Exact list match
                    else:
                        return {"matches": False, "score": 0.0}
                elif actual == expected:
                    score += 1.0  # Exact match
                else:
                    return {"matches": False, "score": 0.0}
        
        return {"matches": True, "score": score}
    
    def _matches_temporal_constraints(
        self, 
        temporal_context: TemporalContext,
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if temporal context matches temporal constraints with scoring
        """
        score = 0.0
        constraints_checked = 0
        
        # Situation matching
        if "situation" in constraints:
            constraints_checked += 1
            if temporal_context.situation == constraints["situation"]:
                score += 1.0
            else:
                return {"matches": False, "score": 0.0}
        
        # Emergency override requirement
        if "require_emergency_override" in constraints:
            constraints_checked += 1
            required = constraints["require_emergency_override"]
            if required == temporal_context.emergency_override:
                score += 1.0
            else:
                return {"matches": False, "score": 0.0}
        
        # Access window validation
        if "access_window" in constraints:
            constraints_checked += 1
            window = constraints["access_window"]
            now = temporal_context.timestamp
            
            window_valid = True
            if "start" in window:
                start_time = datetime.fromisoformat(window["start"])
                if now < start_time:
                    window_valid = False
            
            if "end" in window:
                end_time = datetime.fromisoformat(window["end"])
                if now > end_time:
                    window_valid = False
            
            if window_valid:
                score += 1.0
            else:
                return {"matches": False, "score": 0.0}
        
        # If no temporal constraints, give partial credit
        if constraints_checked == 0:
            score = 0.5
        
        return {"matches": True, "score": score}
    
    def _load_yaml_data(self) -> tuple:
        """Load data from YAML files (fallback method)"""
        with open(self.rules_file, 'r') as f:
            rules_data = yaml.safe_load(f)
            rules = rules_data.get("rules", [])
        
        with open(self.oncall_file, 'r') as f:
            oncall_data = yaml.safe_load(f)
        
        with open(self.incidents_file, 'r') as f:
            incidents_data = yaml.safe_load(f)
            
        return rules, oncall_data, incidents_data
    
    def _load_rules_from_neo4j(self) -> List[Dict[str, Any]]:
        """Load policy rules from Neo4j"""
        with self.neo4j_manager.driver.session() as session:
            query = """
            MATCH (rule:PolicyRule {team: 'llm_security'})
            RETURN rule
            ORDER BY rule.priority DESC, rule.created_at ASC
            """
            
            rules = []
            for record in session.run(query):
                rule_data = dict(record["rule"])
                # Convert Neo4j properties back to expected format
                rules.append(self._convert_neo4j_rule_to_dict(rule_data))
            
            return rules if rules else self._load_yaml_data()[0]  # Fallback to YAML
    
    def _load_oncall_data_from_neo4j(self) -> Dict[str, Any]:
        """Load oncall configuration from Neo4j"""
        with self.neo4j_manager.driver.session() as session:
            # Load services
            services_query = """
            MATCH (svc:Service {team: 'llm_security'})
            RETURN svc
            """
            
            services = {}
            for record in session.run(services_query):
                svc_data = dict(record["svc"])
                services[svc_data.get("name", svc_data["id"])] = {
                    "oncall": svc_data.get("oncall", []),
                    "timezone": svc_data.get("timezone", "UTC"),
                    "escalation_delay_minutes": svc_data.get("escalation_delay_minutes", 30),
                    "service_criticality": svc_data.get("service_criticality", "medium")
                }
            
            # Load global policies
            policies_query = """
            MATCH (policy:GlobalPolicy {team: 'llm_security'})
            RETURN policy
            """
            
            global_policies = {}
            business_hours = {"start_hour": 9, "end_hour": 17}
            
            for record in session.run(policies_query):
                policy_data = dict(record["policy"])
                if policy_data.get("type") == "business_hours":
                    business_hours = {
                        "start_hour": policy_data.get("start_hour", 9),
                        "end_hour": policy_data.get("end_hour", 17),
                        "weekend_support": policy_data.get("weekend_support", {})
                    }
                elif policy_data.get("type") == "global":
                    global_policies.update(policy_data.get("policies", {}))
            
            oncall_data = {
                "services": services,
                "business_hours": business_hours,
                "global_policies": global_policies
            }
            
            return oncall_data if services else self._load_yaml_data()[1]  # Fallback to YAML
    
    def _load_incidents_from_neo4j(self) -> Dict[str, Any]:
        """Load incident data from Neo4j"""
        with self.neo4j_manager.driver.session() as session:
            query = """
            MATCH (inc:Incident {team: 'llm_security'})
            RETURN inc
            ORDER BY inc.created_at DESC
            """
            
            incidents = []
            for record in session.run(query):
                inc_data = dict(record["inc"])
                incidents.append(inc_data)
            
            return {"incidents": incidents} if incidents else self._load_yaml_data()[2]  # Fallback to YAML
    
    def _convert_neo4j_rule_to_dict(self, neo4j_rule: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Neo4j rule format to expected dictionary format"""
        return {
            "id": neo4j_rule.get("rule_id", neo4j_rule.get("id")),
            "action": neo4j_rule.get("action", "DENY"),
            "tuples": {
                "data_type": neo4j_rule.get("data_type"),
                "data_sender": neo4j_rule.get("data_sender"),
                "data_recipient": neo4j_rule.get("data_recipient"),
                "transmission_principle": neo4j_rule.get("transmission_principle")
            },
            "temporal_context": {
                "situation": neo4j_rule.get("situation"),
                "require_emergency_override": neo4j_rule.get("require_emergency_override", False),
                "access_window": neo4j_rule.get("access_window")
            }
        }
    
    def save_rule_to_neo4j(self, rule: Dict[str, Any]) -> str:
        """Save a policy rule to Neo4j"""
        if not self.neo4j_manager:
            raise ValueError("Neo4j manager not configured")
        
        with self.neo4j_manager.driver.session() as session:
            query = """
            CREATE (rule:PolicyRule {
                rule_id: $rule_id,
                action: $action,
                data_type: $data_type,
                data_sender: $data_sender,
                data_recipient: $data_recipient,
                transmission_principle: $transmission_principle,
                situation: $situation,
                require_emergency_override: $require_emergency_override,
                access_window: $access_window,
                priority: $priority,
                team: 'llm_security',
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN rule.rule_id as rule_id
            """
            
            tuples = rule.get("tuples", {})
            temporal_context = rule.get("temporal_context", {})
            
            result = session.run(query,
                rule_id=rule.get("id"),
                action=rule.get("action", "DENY"),
                data_type=tuples.get("data_type"),
                data_sender=tuples.get("data_sender"),
                data_recipient=tuples.get("data_recipient"),
                transmission_principle=tuples.get("transmission_principle"),
                situation=temporal_context.get("situation"),
                require_emergency_override=temporal_context.get("require_emergency_override", False),
                access_window=temporal_context.get("access_window"),
                priority=rule.get("priority", 100)
            )
            
            return result.single()["rule_id"]
    
    def _calculate_risk_level(
        self,
        request: EnhancedContextualIntegrityTuple,
        rule: Dict[str, Any]
    ) -> str:
        """
        Calculate risk level based on request and matched rule
        """
        risk_factors = []
        
        # Check data sensitivity
        if hasattr(request, 'data_type'):
            sensitive_data = ["financial", "personal", "health", "security"]
            if any(sensitive in request.data_type.lower() for sensitive in sensitive_data):
                risk_factors.append("sensitive_data")
        
        # Check time factors
        if not request.temporal_context.business_hours:
            risk_factors.append("after_hours")
        
        if request.temporal_context.emergency_override:
            risk_factors.append("emergency_context")
        
        # Check rule action
        if rule.get("action") == "ALLOW":
            risk_factors.append("permissive_rule")
        
        # Calculate risk level
        risk_count = len(risk_factors)
        if risk_count >= 3:
            return "high"
        elif risk_count >= 2:
            return "medium"
        else:
            return "low"