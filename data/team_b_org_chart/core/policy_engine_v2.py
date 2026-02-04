"""
Policy-Based Access Control Engine (v2)
Uses PRD queries to check graph facts + YAML policies to make decisions

Architecture:
1. YAML policies define RULES (what to check)
2. PRD queries check FACTS (actual graph data)  
3. Policy engine evaluates RULES against FACTS
4. Returns access decision
"""

import yaml
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AccessDecision(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"

@dataclass
class AccessResult:
    decision: AccessDecision
    reason: str
    confidence: float
    factors: List[str]
    policy_rules_applied: List[str]
    response_time_ms: float
    data_source: str = "policy_engine_with_prd_queries"

@dataclass
class PolicyRule:
    name: str
    description: str
    priority: int
    conditions: Dict[str, Any]
    action: AccessDecision
    confidence_boost: float = 0.0

class PolicyEngine:
    """
    Policy-driven access control using PRD queries
    
    This is the CORRECT architecture:
    - Policies in YAML say "check if CEO", "check if same dept", etc.
    - PRD queries actually CHECK the graph for those facts
    - Policy engine matches policies to facts and returns decision
    """
    
    def __init__(self, privacy_queries, policy_config_path: str = "config/access_policies.yaml"):
        """
        Args:
            privacy_queries: PrivacyFirewallQueries instance (the PRD queries)
            policy_config_path: Path to YAML policy file
        """
        self.privacy_queries = privacy_queries
        self.policies = []
        self.load_policies(policy_config_path)
    
    def load_policies(self, file_path: str):
        """Load policy rules from YAML file"""
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.policies = []
            for policy_data in config.get('policies', []):
                policy = PolicyRule(
                    name=policy_data['name'],
                    description=policy_data['description'],
                    priority=policy_data['priority'],
                    conditions=policy_data['conditions'],
                    action=AccessDecision(policy_data['action']),
                    confidence_boost=policy_data.get('confidence_boost', 0.5)
                )
                self.policies.append(policy)
            
            # Sort by priority (highest first)
            self.policies.sort(key=lambda p: p.priority, reverse=True)
            
            logger.info(f"Loaded {len(self.policies)} policies from {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")
            # Use minimal default policy
            self.policies = [
                PolicyRule(
                    name="default_deny",
                    description="Deny all access by default",
                    priority=1,
                    conditions={},
                    action=AccessDecision.DENY,
                    confidence_boost=0.9
                )
            ]
    
    async def evaluate_access(
        self, 
        requester_id: str, 
        target_id: str, 
        resource_type: str = None
    ) -> AccessResult:
        """
        Main access evaluation function
        
        Steps:
        1. Use PRD queries to get FACTS from graph
        2. Evaluate policy RULES against those FACTS
        3. Return decision
        """
        start_time = datetime.now()
        
        # STEP 1: Use PRD queries to check actual graph facts
        facts = await self._check_graph_facts(requester_id, target_id)
        
        # Handle entity not found
        if facts.get('entity_not_found'):
            return AccessResult(
                decision=AccessDecision.DENY,
                reason=f"Entity not found: requester={requester_id}, target={target_id}",
                confidence=1.0,
                factors=["entity_not_found"],
                policy_rules_applied=[],
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
        
        # STEP 2: Evaluate each policy rule against facts
        # Policies are sorted by priority (highest first)
        # Take the FIRST matching policy
        applied_rules = []
        factors = []
        total_confidence = 0.0
        final_decision = AccessDecision.DENY
        final_reason = "No policy matched"
        
        for policy in self.policies:
            if self._policy_matches_facts(policy, facts):
                applied_rules.append(policy.name)
                factors.extend(self._extract_factors(policy, facts))
                total_confidence += policy.confidence_boost
                final_decision = policy.action
                final_reason = f"Access {policy.action.value.lower()}: Policy rules applied: {policy.name}"
                
                logger.info(f"Policy matched: {policy.name} (priority={policy.priority}, action={policy.action.value})")
                
                # Use FIRST matching policy (highest priority wins)
                break
        
        # Calculate final confidence
        final_confidence = min(1.0, total_confidence / max(1, len(applied_rules)))
        
        # Calculate response time
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return AccessResult(
            decision=final_decision,
            reason=final_reason,
            confidence=final_confidence,
            factors=factors,
            policy_rules_applied=applied_rules,
            response_time_ms=elapsed_ms
        )
    
    async def evaluate_resource_access(
        self,
        requester_id: str,
        resource_owner: str,
        resource_classification: str,
        resource_type: str,
        action: str = "read",
        timestamp: Optional[datetime] = None
    ) -> AccessResult:
        """
        Evaluate resource-based access control (CORRECT ARCHITECTURE)
        
        This is the proper model: "Can employee X access resource Y owned by Z?"
        NOT "Can employee X access employee Y?"
        
        Steps:
        1. Get requester context (hierarchy, clearance, department, etc.)
        2. Determine resource owner context (department/team/employee)
        3. Calculate hierarchy relationship (downward/lateral/upward)
        4. Check clearance requirements
        5. Evaluate temporal validity (contractor expiry, business hours)
        6. Match against YAML policies
        7. Return decision
        """
        start_time = datetime.now()
        
        # STEP 1: Check resource-based facts from graph
        facts = await self._check_resource_facts(
            requester_id, 
            resource_owner, 
            resource_classification,
            resource_type,
            action,
            timestamp
        )
        
        # Handle entity not found
        if facts.get('entity_not_found'):
            return AccessResult(
                decision=AccessDecision.DENY,
                reason=f"Entity not found: requester={requester_id} or resource_owner={resource_owner}",
                confidence=1.0,
                factors=["entity_not_found"],
                policy_rules_applied=[],
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
        
        # STEP 2: Evaluate policies against facts
        applied_rules = []
        factors = []
        total_confidence = 0.0
        final_decision = AccessDecision.DENY
        final_reason = "No policy matched"
        
        for policy in self.policies:
            if self._policy_matches_facts(policy, facts):
                applied_rules.append(policy.name)
                factors.extend(self._extract_factors(policy, facts))
                total_confidence += policy.confidence_boost
                final_decision = policy.action
                final_reason = f"Access {policy.action.value.lower()}: {policy.description} (policy: {policy.name})"
                
                logger.info(f"Policy matched: {policy.name} (priority={policy.priority}, action={policy.action.value})")
                
                # Use FIRST matching policy (highest priority wins)
                break
        
        # Calculate final confidence
        final_confidence = min(1.0, total_confidence / max(1, len(applied_rules)))
        
        # Calculate response time
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return AccessResult(
            decision=final_decision,
            reason=final_reason,
            confidence=final_confidence,
            factors=factors,
            policy_rules_applied=applied_rules,
            response_time_ms=elapsed_ms
        )
    
    async def _check_resource_facts(
        self,
        requester_id: str,
        resource_owner: str,
        resource_classification: str,
        resource_type: str,
        action: str,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Check facts for resource-based access control
        
        This replaces employee-to-employee checking with employee-to-resource checking
        """
        facts = {
            'resource_classification': resource_classification,
            'resource_type': resource_type,
            'action': action,
            'emergency_mode': False
        }
        
        try:
            # Get requester context
            requester_context = await self.privacy_queries.get_employee_context(requester_id)
            if not requester_context:
                facts['entity_not_found'] = True
                return facts
            
            # Extract requester facts
            facts['requester_role'] = requester_context.get('role', '').lower()
            facts['requester_department'] = requester_context.get('department', '')
            facts['requester_team'] = requester_context.get('team', '')
            facts['requester_type'] = requester_context.get('employee_type', 'full_time')
            facts['requester_clearance'] = requester_context.get('security_clearance', 'standard')
            facts['requester_direct_reports'] = len(requester_context.get('direct_reports', []))
            
            # Calculate hierarchy level for requester
            facts['requester_hierarchy_level'] = self._calculate_hierarchy_level(requester_context)
            
            # Check if requester is CEO/executive
            facts['is_ceo'] = facts['requester_role'] in ['ceo', 'chief executive officer']
            facts['is_executive'] = (
                facts['is_ceo'] or 
                facts['requester_direct_reports'] >= 5 or
                any(title in facts['requester_role'] for title in ['ceo', 'cto', 'cfo', 'vp', 'vice president'])
            )
            
            # Determine resource owner type (department, team, or employee)
            resource_owner_type = await self._determine_resource_owner_type(resource_owner)
            facts['resource_owner_type'] = resource_owner_type
            facts['resource_owner_id'] = resource_owner
            
            if resource_owner_type == 'department':
                # Resource owned by department
                facts['resource_owner_department'] = resource_owner
                facts['same_department'] = requester_context.get('department', '') == resource_owner
                facts['resource_owner_hierarchy_level'] = 3  # Department level
                
            elif resource_owner_type == 'team':
                # Resource owned by team
                facts['resource_owner_team'] = resource_owner
                facts['same_team'] = requester_context.get('team', '') == resource_owner
                facts['resource_owner_hierarchy_level'] = 2  # Team level
                
                # Get team's parent department
                team_dept = await self._get_team_department(resource_owner)
                if team_dept:
                    facts['resource_owner_department'] = team_dept
                    facts['same_department'] = requester_context.get('department', '') == team_dept
                    
            elif resource_owner_type == 'employee':
                # Resource owned by specific employee
                owner_context = await self.privacy_queries.get_employee_context(resource_owner)
                if owner_context:
                    facts['resource_owner_department'] = owner_context.get('department', '')
                    facts['resource_owner_team'] = owner_context.get('team', '')
                    facts['resource_owner_hierarchy_level'] = self._calculate_hierarchy_level(owner_context)
                    
                    # Check relationships
                    facts['same_department'] = requester_context.get('department') == owner_context.get('department')
                    facts['same_team'] = requester_context.get('team') == owner_context.get('team')
                    
                    # Check management relationship
                    is_manager_of = await self.privacy_queries.check_direct_report(resource_owner, requester_id)
                    is_report_of = await self.privacy_queries.check_direct_report(requester_id, resource_owner)
                    facts['is_manager_of_owner'] = is_manager_of
                    facts['is_report_of_owner'] = is_report_of
                else:
                    facts['entity_not_found'] = True
                    return facts
            
            # Calculate hierarchy relationship
            req_level = facts.get('requester_hierarchy_level', 1)
            owner_level = facts.get('resource_owner_hierarchy_level', 1)
            
            if req_level > owner_level:
                facts['hierarchy_relationship'] = 'downward'  # Higher can access lower
            elif req_level == owner_level:
                facts['hierarchy_relationship'] = 'lateral'   # Same level
            else:
                facts['hierarchy_relationship'] = 'upward'    # Lower trying to access higher
            
            # Map classification to clearance requirements
            clearance_map = {
                'public': 'basic',
                'internal': 'basic',
                'confidential': 'standard',
                'restricted': 'elevated',
                'secret': 'restricted',
                'top_secret': 'top_secret'
            }
            facts['required_clearance'] = clearance_map.get(resource_classification, 'standard')
            
            # Check clearance sufficiency
            clearance_levels = {
                'basic': 0,
                'standard': 1,
                'elevated': 2,
                'restricted': 3,
                'top_secret': 4,
                'executive': 5  # Executive clearance - highest level
            }
            req_clearance_level = clearance_levels.get(facts['requester_clearance'], 1)
            required_clearance_level = clearance_levels.get(facts['required_clearance'], 1)
            facts['has_sufficient_clearance'] = req_clearance_level >= required_clearance_level
            facts['insufficient_clearance'] = not facts['has_sufficient_clearance']
            
            # Temporal validation for contractors
            if facts['requester_type'] in ['contractor', 'vendor', 'consultant', 'freelancer']:
                contract_end = requester_context.get('contract_end_date')
                if contract_end:
                    try:
                        end_date = datetime.fromisoformat(contract_end)
                        now = timestamp or datetime.now()
                        is_valid = now <= end_date
                        facts['is_expired_contractor'] = not is_valid
                        facts['is_valid_contractor'] = is_valid
                    except (ValueError, TypeError):
                        facts['is_expired_contractor'] = False
                        facts['is_valid_contractor'] = True
                else:
                    facts['is_expired_contractor'] = False
                    facts['is_valid_contractor'] = True
            
            # Business hours check
            if timestamp:
                facts['is_business_hours'] = self._check_business_hours(
                    requester_context.get('working_hours', {}),
                    requester_context.get('timezone', 'UTC'),
                    timestamp
                )
            
            return facts
            
        except Exception as e:
            logger.error(f"Error checking resource facts: {e}", exc_info=True)
            facts['error'] = str(e)
            return facts
    
    def _calculate_hierarchy_level(self, employee_context: Dict) -> int:
        """
        Calculate hierarchy level from employee context
        
        Returns:
            5: CEO/Founder
            4: VP/C-level
            3: Director/Department Head
            2: Manager/Team Lead
            1: Individual Contributor
        """
        role = employee_context.get('role', '').lower()
        direct_reports = len(employee_context.get('direct_reports', []))
        
        # CEO/Founder
        if 'ceo' in role or 'founder' in role or 'chief executive' in role:
            return 5
        
        # C-level / VP
        if any(title in role for title in ['cto', 'cfo', 'coo', 'vp', 'vice president', 'chief']):
            return 4
        
        # Director / Department Head
        if 'director' in role or 'head' in role or direct_reports >= 10:
            return 3
        
        # Manager / Team Lead
        if 'manager' in role or 'lead' in role or direct_reports >= 3:
            return 2
        
        # Individual Contributor
        return 1
    
    async def _determine_resource_owner_type(self, resource_owner: str) -> str:
        """
        Determine if resource_owner is a department, team, or employee
        
        Returns: 'department', 'team', or 'employee'
        """
        # Check if it's an employee ID (emp-XXX pattern)
        if resource_owner.startswith('emp-'):
            return 'employee'
        
        # Check if it's a department name (query Neo4j)
        # For now, use simple heuristics
        dept_keywords = ['engineering', 'product', 'finance', 'operations', 'marketing', 'sales', 'hr', 'human resources']
        team_keywords = ['backend', 'frontend', 'mobile', 'infrastructure', 'data', 'analytics', 'design']
        
        owner_lower = resource_owner.lower()
        
        if any(keyword in owner_lower for keyword in dept_keywords):
            return 'department'
        elif any(keyword in owner_lower for keyword in team_keywords):
            return 'team'
        else:
            # Default to employee if unclear
            return 'employee'
    
    async def _get_team_department(self, team_name: str) -> Optional[str]:
        """Get parent department for a team"""
        # TODO: Query Neo4j for team->department relationship
        # For now, use simple mapping
        team_dept_map = {
            'Backend Engineering Team': 'Engineering',
            'Frontend Engineering Team': 'Engineering',
            'Mobile Team': 'Engineering',
            'Infrastructure Team': 'Engineering',
            'Product Strategy Team': 'Product',
            'Product Design Team': 'Product',
            'Finance Team': 'Finance',
            'Accounting Team': 'Finance'
        }
        return team_dept_map.get(team_name)
    
    def _check_business_hours(self, working_hours: Dict, timezone: str, timestamp: datetime) -> bool:
        """Check if timestamp is within business hours"""
        try:
            import pytz
            tz = pytz.timezone(timezone)
            local_time = timestamp.astimezone(tz)
            
            start_time = datetime.strptime(working_hours.get("start", "09:00"), "%H:%M").time()
            end_time = datetime.strptime(working_hours.get("end", "17:00"), "%H:%M").time()
            
            return start_time <= local_time.time() <= end_time
        except:
            return True  # Default to True if can't determine
    
    async def _check_graph_facts(self, requester_id: str, target_id: str) -> Dict[str, Any]:
        """
        Use PRD queries to check actual facts from the graph
        
        This is the KEY integration point - we use Lawrence's PRD queries!
        """
        facts = {
            # Default: emergency_mode is False unless explicitly set
            'emergency_mode': False
        }
        
        try:
            # =================================================================
            # PRD QUERY 1: Check direct reporting relationship
            # =================================================================
            is_requester_manages_target = await self.privacy_queries.check_direct_report(
                target_id, requester_id
            )
            is_target_manages_requester = await self.privacy_queries.check_direct_report(
                requester_id, target_id
            )
            
            facts['is_direct_manager'] = is_requester_manages_target
            facts['is_direct_report'] = is_target_manages_requester
            facts['has_management_relationship'] = is_requester_manages_target or is_target_manages_requester
            
            # =================================================================
            # PRD QUERY 2: Check same department
            # =================================================================
            dept_info = await self.privacy_queries.check_same_department(requester_id, target_id)
            facts['same_department'] = dept_info is not None
            if dept_info:
                facts['shared_department'] = dept_info['department']
                facts['department_classification'] = dept_info['data_classification']
            
            # =================================================================
            # PRD QUERY 3: Check shared projects
            # =================================================================
            shared_projects = await self.privacy_queries.check_shared_project(requester_id, target_id)
            facts['shared_projects'] = len(shared_projects) > 0
            facts['shared_project_count'] = len(shared_projects)
            if shared_projects:
                facts['project_names'] = [p['project'] for p in shared_projects]
                facts['project_scopes'] = [p['data_scope'] for p in shared_projects]
            
            # =================================================================
            # EXTENDED QUERIES: Get employee context for policy evaluation
            # =================================================================
            requester_context = await self.privacy_queries.get_employee_context(requester_id)
            target_context = await self.privacy_queries.get_employee_context(target_id)
            
            if not requester_context or not target_context:
                facts['entity_not_found'] = True
                return facts
            
            # Extract requester facts
            facts['requester_role'] = requester_context.get('role', '').lower()
            facts['requester_department'] = requester_context.get('department', '')
            facts['requester_type'] = requester_context.get('employee_type', 'full_time')
            facts['requester_clearance'] = requester_context.get('security_clearance', 'basic')
            facts['requester_direct_reports'] = len(requester_context.get('direct_reports', []))
            facts['requester_timezone'] = requester_context.get('timezone', 'UTC')
            
            # Temporal validation for contractors
            emp_type = facts['requester_type']
            if emp_type in ['contractor', 'vendor', 'consultant', 'freelancer']:
                # Check contract end date
                contract_end = requester_context.get('contract_end_date')
                if contract_end:
                    from datetime import datetime
                    try:
                        end_date = datetime.fromisoformat(contract_end)
                        is_valid = datetime.now() <= end_date
                        facts['contract_valid'] = is_valid
                        facts['is_expired_contractor'] = not is_valid
                        facts['contract_end_date'] = contract_end
                    except (ValueError, TypeError):
                        facts['contract_valid'] = True  # Assume valid if date parse fails
                        facts['is_expired_contractor'] = False
                        facts['contract_end_date'] = contract_end
                else:
                    facts['contract_valid'] = True  # No end date = assume valid
                    facts['is_expired_contractor'] = False
            else:
                facts['contract_valid'] = True  # Full-time employees always valid
                facts['is_expired_contractor'] = False
            
            # Acting/temporary role support
            acting_role_start = requester_context.get('acting_role_start')
            acting_role_end = requester_context.get('acting_role_end')
            
            if acting_role_start and acting_role_end:
                from datetime import datetime
                try:
                    start = datetime.fromisoformat(acting_role_start)
                    end = datetime.fromisoformat(acting_role_end)
                    now = datetime.now()
                    is_valid = start <= now <= end
                    facts['has_acting_role'] = is_valid
                    facts['has_valid_acting_role'] = is_valid
                    facts['has_expired_acting_role'] = not is_valid and now > end
                    facts['acting_role_valid_until'] = acting_role_end
                    facts['acting_role_start'] = acting_role_start
                except (ValueError, TypeError):
                    facts['has_acting_role'] = False
                    facts['has_valid_acting_role'] = False
                    facts['has_expired_acting_role'] = False
            else:
                facts['has_acting_role'] = False
                facts['has_valid_acting_role'] = False
                facts['has_expired_acting_role'] = False
            
            # Business hours check (basic implementation)
            working_hours = requester_context.get('working_hours', {})
            if isinstance(working_hours, dict) and 'start' in working_hours and 'end' in working_hours:
                from datetime import datetime
                current_time = datetime.now().time()
                try:
                    start_time = datetime.strptime(working_hours['start'], '%H:%M').time()
                    end_time = datetime.strptime(working_hours['end'], '%H:%M').time()
                    facts['in_business_hours'] = start_time <= current_time <= end_time
                except (ValueError, TypeError):
                    facts['in_business_hours'] = True  # Default to True if parsing fails
            else:
                facts['in_business_hours'] = True
            
            # Detect CEO/Executive
            role = facts['requester_role']
            facts['is_ceo'] = 'ceo' in role or 'chief executive' in role
            facts['is_executive'] = any(x in role for x in [
                'ceo', 'cto', 'cfo', 'coo', 'chief', 'vp', 'vice president'
            ])
            
            # Extract target facts
            facts['target_role'] = target_context.get('role', '').lower()
            facts['target_department'] = target_context.get('department', '')
            facts['target_type'] = target_context.get('employee_type', 'full_time')
            facts['target_clearance'] = target_context.get('security_clearance', 'basic')
            
            # =================================================================
            # CLEARANCE LEVEL CHECK - Pure YAML-driven
            # =================================================================
            clearance_hierarchy = {
                'basic': 0,
                'standard': 1,
                'elevated': 2,
                'restricted': 3,
                'top_secret': 4,
                'executive': 5  # Executive clearance - highest level
            }
            req_level = clearance_hierarchy.get(facts['requester_clearance'], 0)
            tgt_level = clearance_hierarchy.get(facts['target_clearance'], 0)
            facts['insufficient_clearance'] = req_level < tgt_level
            
            # =================================================================
            # EXTENDED QUERIES: Manager hierarchy (skip-level)
            # =================================================================
            if not facts['has_management_relationship']:
                is_in_chain, levels = await self.privacy_queries.check_manager_hierarchy(
                    target_id, requester_id
                )
                facts['is_skip_level_manager'] = is_in_chain
                facts['management_levels'] = levels
            else:
                facts['is_skip_level_manager'] = False
                facts['management_levels'] = 0
            
            # =================================================================
            # EXTENDED QUERIES: Same team
            # =================================================================
            same_team = await self.privacy_queries.check_same_team(requester_id, target_id)
            facts['same_team'] = same_team
            
        except Exception as e:
            logger.error(f"Error checking graph facts: {e}")
            facts['error'] = str(e)
        
        return facts
    
    def _policy_matches_facts(self, policy: PolicyRule, facts: Dict[str, Any]) -> bool:
        """
        Check if policy conditions match the facts from PRD queries
        
        The policy says "check if CEO", facts say "is_ceo: True"
        This function matches them up
        """
        conditions = policy.conditions
        
        # Empty conditions = always match (e.g., default_deny)
        if not conditions:
            return True
        
        # =================================================================
        # Check emergency mode FIRST (before any other checks)
        # Emergency policies should ONLY match when emergency is active
        # =================================================================
        if 'emergency_mode' in conditions:
            # Only allow emergency access if BOTH:
            # 1. Policy requires emergency_mode=true
            # 2. Request context has emergency_mode=true
            logger.debug(f"Checking emergency_mode: conditions={conditions.get('emergency_mode')}, facts={facts.get('emergency_mode')}")
            if conditions['emergency_mode'] and facts.get('emergency_mode') is True:
                # Emergency is active - continue checking other conditions
                logger.info("Emergency mode active - checking other conditions")
                # Fall through to check remaining conditions
            else:
                # Emergency required but not active - policy doesn't match
                logger.debug("Emergency mode check failed - policy requires emergency but not active")
                return False
        
        # =================================================================
        # Check CEO/Executive hierarchy
        # =================================================================
        if 'requester_hierarchy_level' in conditions:
            required_levels = conditions['requester_hierarchy_level']
            
            # Check for CEO
            if any(x in required_levels for x in ['ceo', 'chief_executive']):
                if facts.get('is_ceo'):
                    return True
            
            # Check for Executive
            if any(x in required_levels for x in ['executive', 'c_level', 'vp', 'vice_president']):
                if facts.get('is_executive'):
                    return True
            
            # Check for manager/senior_manager based on direct reports
            if 'manager' in required_levels or 'senior_manager' in required_levels:
                if facts.get('requester_direct_reports', 0) > 0:
                    return True
        
        # =================================================================
        # Check minimum direct reports (for executive policies)
        # =================================================================
        if 'min_direct_reports' in conditions:
            min_reports = conditions['min_direct_reports']
            actual_reports = facts.get('requester_direct_reports', 0)
            if actual_reports < min_reports:
                return False
        
        # =================================================================
        # Check relationship patterns (management relationships)
        # =================================================================
        if 'relationship_patterns' in conditions:
            patterns = conditions['relationship_patterns']
            
            # Management patterns: manages, supervises, leads
            if any(p in patterns for p in ['manages', 'supervises', 'leads', 'oversees']):
                if facts.get('is_direct_manager'):
                    return True
                if facts.get('is_skip_level_manager'):
                    return True
            
            # Reporting patterns: reports to, managed by
            if any(p in patterns for p in ['reports to', 'managed by', 'supervised by']):
                if facts.get('is_direct_report'):
                    return True
            
            # Acting/temporary role patterns
            if any(p in patterns for p in ['acting', 'temporary', 'interim', 'covering for']):
                # Check for acting/temporary relationships with time validity
                if facts.get('has_acting_role'):
                    # Verify acting role is currently valid
                    if self._is_acting_role_valid(facts):
                        return True
        
        # =================================================================
        # Check shared context types (dept/team/project)
        # =================================================================
        if 'shared_context_types' in conditions:
            context_types = conditions['shared_context_types']
            
            # Department/Division
            if any(t in context_types for t in ['department', 'division', 'unit']):
                if facts.get('same_department'):
                    return True
            
            # Team/Squad
            if any(t in context_types for t in ['team', 'squad', 'group']):
                if facts.get('same_team'):
                    return True
            
            # Project/Initiative
            if any(t in context_types for t in ['project', 'initiative', 'task', 'workstream']):
                if facts.get('shared_projects'):
                    return True
        
        # =================================================================
        # Check contractor restrictions
        # =================================================================
        if 'requester_type' in conditions:
            restricted_types = conditions['requester_type']
            actual_type = facts.get('requester_type', 'full_time')
            if actual_type in restricted_types:
                # This is a DENY rule for contractors
                # Check if contractor contract is still valid
                if actual_type in ['contractor', 'vendor', 'consultant', 'freelancer']:
                    if not facts.get('contract_valid', False):
                        logger.info("Contractor contract expired - denying access")
                        return True  # Contract expired - deny access
                return True
        
        # =================================================================
        # Check time restrictions (business hours, timezone)
        # =================================================================
        if 'time_restrictions' in conditions:
            time_rules = conditions['time_restrictions']
            
            # Business hours check
            if time_rules.get('business_hours_only'):
                if not facts.get('in_business_hours', True):
                    return False  # Outside business hours
            
            # Timezone check (if specified)
            if 'timezone' in time_rules:
                required_tz = time_rules['timezone']
                actual_tz = facts.get('requester_timezone', 'UTC')
                # For now, just log - full timezone handling needs pytz
                logger.debug(f"Timezone check: required={required_tz}, actual={actual_tz}")
        
        # =================================================================
        # Check relationship recency (for project collaboration, etc)
        # =================================================================
        if 'relationship_recency_days' in conditions:
            max_days = conditions['relationship_recency_days']
            relationship_age_days = facts.get('relationship_age_days', 0)
            if relationship_age_days > max_days:
                return False  # Relationship too old
        
        # =================================================================
        # Check relationship strength/weight
        # =================================================================
        if 'min_relationship_weight' in conditions:
            min_weight = conditions['min_relationship_weight']
            actual_weight = facts.get('relationship_weight', 0.0)
            if actual_weight < min_weight:
                return False  # Relationship not strong enough
        
        # =================================================================
        # DIRECT FACT MATCHING - Check any remaining simple conditions
        # For conditions like: is_ceo: true, same_department: true, etc.
        # =================================================================
        # Get all condition keys we've already processed above
        processed_keys = {
            'emergency_mode', 'requester_hierarchy_level', 'min_direct_reports',
            'relationship_patterns', 'shared_context_types', 'requester_type',
            'time_restrictions', 'relationship_recency_days', 'min_relationship_weight'
        }
        
        # Check remaining conditions against facts directly
        for condition_key, condition_value in conditions.items():
            if condition_key in processed_keys:
                continue  # Already checked above
            
            # Direct boolean/value matching
            fact_value = facts.get(condition_key)
            
            # If condition expects True, fact must be True
            if condition_value is True:
                if fact_value is not True:
                    return False
            # If condition expects False, fact must be False
            elif condition_value is False:
                if fact_value is not False:
                    return False
            # For other values, do equality check
            else:
                if fact_value != condition_value:
                    return False
        
        # All conditions matched
        return True
    
    def _is_acting_role_valid(self, facts: Dict[str, Any]) -> bool:
        """
        Check if acting/temporary role is currently valid
        
        Args:
            facts: Dictionary with acting role information
            
        Returns:
            True if acting role is currently active and valid
        """
        if not facts.get('has_acting_role'):
            return False
        
        # Check if acting role has expired
        acting_valid_until = facts.get('acting_role_valid_until')
        if acting_valid_until:
            from datetime import datetime
            try:
                expiry = datetime.fromisoformat(acting_valid_until)
                if datetime.now() > expiry:
                    logger.info("Acting role has expired")
                    return False
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid acting role expiry date: {e}")
                return False
        
        # Check maximum acting role duration (90 days default)
        acting_start = facts.get('acting_role_start')
        if acting_start:
            from datetime import datetime, timedelta
            try:
                start_date = datetime.fromisoformat(acting_start)
                max_duration = timedelta(days=90)
                if datetime.now() - start_date > max_duration:
                    logger.info("Acting role exceeded maximum duration")
                    return False
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid acting role start date: {e}")
                return False
        
        return True
    
    def _extract_factors(self, policy: PolicyRule, facts: Dict[str, Any]) -> List[str]:
        """Extract which specific facts triggered this policy"""
        factors = [f"policy:{policy.name}"]
        
        # Add specific facts
        if facts.get('is_direct_manager'):
            factors.append("direct_manager")
        if facts.get('is_ceo'):
            factors.append("ceo_access")
        if facts.get('is_executive'):
            factors.append("executive_access")
        if facts.get('same_department'):
            factors.append(f"same_dept:{facts.get('shared_department', 'unknown')}")
        if facts.get('same_team'):
            factors.append("same_team")
        if facts.get('shared_projects'):
            factors.append(f"shared_projects:{facts.get('shared_project_count', 0)}")
        if facts.get('is_skip_level_manager'):
            factors.append(f"skip_level:{facts.get('management_levels', 0)}")
        
        return factors
