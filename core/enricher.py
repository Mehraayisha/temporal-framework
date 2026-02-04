# core/enricher.py
import logging
import os
import yaml
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Tuple, Optional
from collections import deque
from core.tuples import TemporalContext, TimeWindow
from core import incidents

logger = logging.getLogger(__name__)

MOCK_DIR = Path(__file__).resolve().parent.parent / "mocks"


# STEP 6: Failure tracking for Graphiti fallback behavior
class GraphitiFailureTracker:
    """
    Track Graphiti API failures to enable fallback behavior and alerting.
    
    Monitors failure rate over 5-minute windows:
    - Alert if >5% failures in last 5 minutes
    - Trigger fallback to minimal context with ALLOW_WITH_AUDIT decision
    """
    
    def __init__(self, window_seconds: int = 300, failure_threshold_pct: float = 5.0):
        """
        Initialize failure tracker.
        
        Args:
            window_seconds: Time window for failure rate calculation (default 300 = 5 minutes)
            failure_threshold_pct: Alert threshold percentage (default 5.0 = 5%)
        """
        self.window_seconds = window_seconds
        self.failure_threshold_pct = failure_threshold_pct
        self.failure_times: deque = deque()  # (timestamp, error_type)
        self.success_times: deque = deque()  # (timestamp,)
        self.alert_logged = False
        logger.info(f"Initialized GraphitiFailureTracker (window={window_seconds}s, threshold={failure_threshold_pct}%)")
    
    def record_failure(self, error_msg: str) -> None:
        """Record a Graphiti API failure."""
        now = datetime.now(timezone.utc)
        self.failure_times.append((now, error_msg))
        self._check_alert()
    
    def record_success(self) -> None:
        """Record a successful Graphiti API call."""
        now = datetime.now(timezone.utc)
        self.success_times.append(now)
        self.alert_logged = False  # Reset alert flag on success
    
    def _check_alert(self) -> None:
        """Check if failure rate exceeds threshold and alert if needed."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old entries
        while self.failure_times and self.failure_times[0][0] < cutoff:
            self.failure_times.popleft()
        while self.success_times and self.success_times[0] < cutoff:
            self.success_times.popleft()
        
        total = len(self.failure_times) + len(self.success_times)
        if total == 0:
            return
        
        failure_rate = (len(self.failure_times) / total) * 100
        
        if failure_rate > self.failure_threshold_pct and not self.alert_logged:
            logger.critical(
                f"ALERT: Graphiti failure rate {failure_rate:.1f}% (>threshold {self.failure_threshold_pct}%) "
                f"in last {self.window_seconds}s. "
                f"Failures: {len(self.failure_times)}, Successes: {len(self.success_times)}. "
                f"Engaging fallback mode with ALLOW_WITH_AUDIT decisions."
            )
            self.alert_logged = True
    
    def get_stats(self) -> Dict:
        """Get current failure tracking statistics."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)
        
        # Clean old entries
        while self.failure_times and self.failure_times[0][0] < cutoff:
            self.failure_times.popleft()
        while self.success_times and self.success_times[0] < cutoff:
            self.success_times.popleft()
        
        total = len(self.failure_times) + len(self.success_times)
        failure_rate = (len(self.failure_times) / total * 100) if total > 0 else 0
        
        return {
            "window_seconds": self.window_seconds,
            "failures": len(self.failure_times),
            "successes": len(self.success_times),
            "total": total,
            "failure_rate_pct": failure_rate,
            "threshold_pct": self.failure_threshold_pct,
            "alert_active": failure_rate > self.failure_threshold_pct,
        }


# STEP 5: Cache for Graphiti context with TTL-based eviction
class GraphitiContextCache:
    """
    Thread-safe cache for enriched temporal contexts from Graphiti APIs.
    
    Cache key: (sender_id, recipient_id)
    TTL: Configurable (default 120 seconds)
    Auto-eviction: Expired entries removed on access
    """
    
    def __init__(self, ttl_seconds: int = 120):
        """
        Initialize cache with TTL configuration.
        
        Args:
            ttl_seconds: Time-to-live for cache entries (default 120)
                        Recommended range: 60-180 seconds
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[Tuple[str, str], Tuple[TemporalContext, datetime]] = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        logger.info(f"Initialized GraphitiContextCache with TTL={ttl_seconds}s")
    
    def get(self, sender_id: str, recipient_id: str) -> Optional[TemporalContext]:
        """
        Retrieve cached context if available and not expired.
        
        Args:
            sender_id: Request sender ID
            recipient_id: Resource owner ID
        
        Returns:
            TemporalContext if found and not expired, None otherwise
        """
        key = (sender_id, recipient_id)
        now = datetime.now(timezone.utc)
        
        if key not in self._cache:
            self.misses += 1
            logger.debug(f"Cache miss for {key}")
            return None
        
        context, cached_at = self._cache[key]
        age = (now - cached_at).total_seconds()
        
        if age > self.ttl_seconds:
            # Expired entry
            del self._cache[key]
            self.evictions += 1
            self.misses += 1
            logger.debug(f"Cache expired for {key} (age: {age:.1f}s)")
            return None
        
        self.hits += 1
        logger.debug(f"Cache hit for {key} (age: {age:.1f}s, TTL: {self.ttl_seconds}s)")
        return context
    
    def set(self, sender_id: str, recipient_id: str, context: TemporalContext) -> None:
        """
        Cache an enriched temporal context.
        
        Args:
            sender_id: Request sender ID
            recipient_id: Resource owner ID
            context: Enriched TemporalContext to cache
        """
        key = (sender_id, recipient_id)
        now = datetime.now(timezone.utc)
        self._cache[key] = (context, now)
        logger.debug(f"Cached context for {key}")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        logger.info(f"Cache cleared: {self.hits} hits, {self.misses} misses, {self.evictions} evictions")
    
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "entries": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": f"{hit_rate:.1f}%",
            "ttl_seconds": self.ttl_seconds
        }


# Global cache instance for Graphiti context (STEP 5)
# TTL: 120 seconds (2 minutes) - prevents hammering Graphiti with duplicate queries
_graphiti_context_cache = GraphitiContextCache(ttl_seconds=120)


# Global failure tracker for Graphiti (STEP 6)
# Monitors failures and triggers fallback/alerting if >5% failures in 5 minutes
_graphiti_failure_tracker = GraphitiFailureTracker(
    window_seconds=300,           # 5-minute window
    failure_threshold_pct=5.0     # Alert at >5% failure rate
)


def _create_minimal_temporal_context(
    timestamp: datetime,
    fallback_reason: str = "Graphiti unavailable"
) -> TemporalContext:
    """
    Create minimal TemporalContext for fallback (STEP 6).
    
    Used when Graphiti API is unavailable. Provides safe defaults
    with ALLOW_WITH_AUDIT decision to maintain compliance.
    
    Args:
        timestamp: Current timestamp
        fallback_reason: Reason for fallback (logged for audit)
    
    Returns:
        Minimal TemporalContext with safe defaults
    """
    logger.warning(f"Using minimal fallback context: {fallback_reason}")
    
    return TemporalContext(
        timestamp=timestamp,
        timezone="UTC",
        temporal_role="user",          # Assume least privilege
        situation="AUDIT",             # Mark for audit (fallback mode)
        data_domain="unknown",         # Cannot determine domain without Graphiti
    )


def load_yaml(name):
    """Load YAML file from mocks directory"""
    with open(MOCK_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def enrich_temporal_context(service_name: str, now: datetime = None, neo4j_manager=None, graphiti_manager=None) -> TemporalContext:
    """
    Enhanced temporal context enrichment using YAML data with service-aware logic
    """
    now = now or datetime.now(timezone.utc)
    oncall = load_yaml("oncall.yaml")
    incidents_yaml = load_yaml("incidents.yaml")
    
    # Enhanced business hours detection with timezone awareness
    bh = oncall.get("business_hours", {"start_hour": 9, "end_hour": 17})
    service_info = oncall.get("services", {}).get(service_name, {})
    service_tz = service_info.get("timezone", "UTC")
    
    # Convert to service timezone for business hours calculation
    hour = now.astimezone().hour
    business_hours = bh["start_hour"] <= hour < bh["end_hour"]
    
    # Check for active incidents (prefer runtime incident registry, fall back to mocks)
    try:
        # Prefer runtime incident registry
        emergency_override = incidents.is_emergency_for_service(service_name)
    except Exception:
        # incident registry may not be available in some environments; fall back to mocks
        emergency_override = any(
            inc["service"] == service_name and inc["status"] == "investigating"
            for inc in (incidents_yaml.get("incidents", []) if isinstance(incidents_yaml, dict) else [])
            if isinstance(inc, dict)
        )
    
    # Get service criticality for temporal role
    criticality = service_info.get("service_criticality", "medium")
    escalation_delay = service_info.get("escalation_delay_minutes", 30)
    
    # Determine data freshness based on service criticality
    data_freshness_seconds = {
        "critical": 60,      # 1 minute for critical services
        "high": 300,         # 5 minutes for high priority
        "medium": 900,       # 15 minutes for medium
        "low": 3600          # 1 hour for low priority
    }.get(criticality, 900)
    
    # Create access window based on service policies
    access_window = None
    temporal_policies = oncall.get("global_policies", {}).get("temporal_access_windows", {})
    access_pattern = temporal_policies.get(criticality, "business_hours")
    
    if access_pattern == "24x7":
        # Critical services get 24/7 access
        pass  # No window restriction
    elif access_pattern == "business_hours_extended":
        # Extended hours: 2 hours before/after business hours
        extended_start = max(0, bh["start_hour"] - 2)
        extended_end = min(24, bh["end_hour"] + 2)
        access_window = TimeWindow(
            start=now.replace(hour=extended_start, minute=0, second=0, microsecond=0),
            end=now.replace(hour=extended_end, minute=0, second=0, microsecond=0)
        )
    elif access_pattern == "business_hours":
        # Standard business hours
        access_window = TimeWindow(
            start=now.replace(hour=bh["start_hour"], minute=0, second=0, microsecond=0),
            end=now.replace(hour=bh["end_hour"], minute=0, second=0, microsecond=0)
        )
    
    # Weekend handling
    is_weekend = now.weekday() >= 5  # Saturday = 5, Sunday = 6
    if is_weekend:
        weekend_support = bh.get("weekend_support", {})
        if weekend_support.get("critical_only", False) and criticality != "critical":
            business_hours = False
        elif "reduced_hours" in weekend_support:
            reduced = weekend_support["reduced_hours"]
            business_hours = reduced["start_hour"] <= hour < reduced["end_hour"]
    
    # Create temporal context. If an incident is active, set an incident-specific temporal role.
    role = None
    if emergency_override:
        try:
            role = incidents.get_incident_temporal_role_for_service(service_name)
        except Exception:
            role = "incident_responder"

    if not role:
        role = f"oncall_{criticality}"
    tc = TemporalContext(
        service_id=service_name,  # Add service reference for Neo4j
        timestamp=now,
        timezone=service_tz,
        business_hours=business_hours,
        emergency_override=emergency_override,
        access_window=access_window,
        data_freshness_seconds=data_freshness_seconds,
        situation=("EMERGENCY" if emergency_override else "NORMAL"),
        temporal_role=role,
            event_correlation=f"{service_name}_context_{escalation_delay}min",
            emergency_authorization_id=(f"INC-{service_name}" if emergency_override else None)
    )
    
    # Optionally save to Neo4j or Graphiti if manager provided
    if graphiti_manager:
        try:
            tc.save_to_graphiti(graphiti_manager)
        except Exception as e:
            # Log error but don't fail the enrichment
            logging.warning(f"Failed to save TemporalContext to Graphiti: {e}")
    elif neo4j_manager:
        try:
            tc.save_to_neo4j(neo4j_manager)
        except Exception as e:
            # Log error but don't fail the enrichment
            logging.warning(f"Failed to save TemporalContext to Neo4j: {e}")
    
    return tc


def build_temporal_context_from_graphiti(sender_id: str, 
                                        recipient_id: str, 
                                        data_type: str,
                                        timestamp: datetime = None) -> TemporalContext:
    """
    STEP 3: Build temporal context by calling Graphiti APIs with caching (STEP 5)
    
    This function queries Team B's Graphiti service to fetch organizational
    relationships and populates TemporalContext with that metadata.
    
    Cache behavior (STEP 5):
    - Key: (sender_id, recipient_id)
    - TTL: 120 seconds (configurable)
    - Auto-eviction: Expired entries removed on access
    
    Fallback behavior (STEP 6):
    - If Graphiti fails: Inject minimal TemporalContext
    - Mark decision as ALLOW_WITH_AUDIT for compliance
    - Log failure and track failure rate
    - Alert if >5% failures in 5 minutes
    
    Args:
        sender_id: Employee requesting access (e.g., "emp-5892")
        recipient_id: Employee owning the data (e.g., "emp-2109")
        data_type: Type of data being accessed (e.g., "payroll", "medical_record")
        timestamp: Optional timestamp for temporal role queries (default: now)
    
    Returns:
        TemporalContext enriched with Graphiti org metadata (cached if available)
        OR minimal fallback context on failure
    """
    timestamp = timestamp or datetime.now(timezone.utc)
    
    # STEP 5: Check cache first before making API calls
    cached_context = _graphiti_context_cache.get(sender_id, recipient_id)
    if cached_context is not None:
        logger.info(f"Using cached context for {sender_id} -> {recipient_id}")
        _graphiti_failure_tracker.record_success()
        return cached_context

    # Optional: Use Team B PrivacyFirewallAPI when GRAPHITI_MODE=team_b_api
    # 
    # ARCHITECTURAL NOTE: Team B runs as a separate FastAPI service to avoid
    # Python namespace collision (both projects have a 'core' package).
    # This is the correct microservice design - services communicate via HTTP APIs.
    #
    # To use Team B integration:
    # 1. Start Team B service: cd team_b_org_chart_codebase && uvicorn api.rest_api:app
    # 2. Set GRAPHITI_MODE=team_b_api
    # 3. Set TEAM_B_API_URL=http://localhost:8000 (or your Team B deployment URL)
    try:
        mode = os.getenv("GRAPHITI_MODE", "").lower()
        if mode == "team_b_api":
            import asyncio
            import httpx
            
            team_b_url = os.getenv("TEAM_B_API_URL", "http://localhost:8000")
            logger.info(f"Using Team B FastAPI service at {team_b_url}")

            async def _build_tc_team_b_http():
                """Build TemporalContext by calling Team B's REST API"""
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Call Team B's /api/v1/employee-context/{email} endpoint
                    try:
                        # Construct email from sender_id (assuming sender_id is username)
                        email = f"{sender_id}@company.com" if "@" not in sender_id else sender_id
                        
                        response = await client.get(
                            f"{team_b_url}/api/v1/employee-context/{email}"
                        )
                        response.raise_for_status()
                        employee_ctx = response.json()
                        
                        # Build TemporalContext from Team B's response
                        # Team B returns: employee_id, name, email, title, department, team,
                        # security_clearance, hierarchy_level, is_manager, working_hours, etc.
                        tc = TemporalContext(
                            timestamp=timestamp,
                            timezone=employee_ctx.get("working_hours", {}).get("timezone", "UTC"),
                            business_hours=True,  # TODO: check working_hours for current time
                            temporal_role="user",
                            situation="NORMAL",
                        )
                        
                        # Enrich with organizational data as extra fields
                        tc.user_id = sender_id
                        if employee_ctx.get("department"):
                            setattr(tc, "data_domain", employee_ctx["department"])
                        if employee_ctx.get("security_clearance"):
                            setattr(tc, "security_clearance", employee_ctx["security_clearance"])
                        if employee_ctx.get("is_manager"):
                            tc.temporal_role = "acting_manager"
                        
                        logger.info(f"Built temporal context via Team B FastAPI: {sender_id} ({employee_ctx.get('title', 'unknown')})")
                        return tc
                        
                    except httpx.HTTPStatusError as e:
                        logger.warning(f"Team B API returned error {e.response.status_code}: {e.response.text}")
                        raise
                    except httpx.HTTPError as e:
                        logger.warning(f"Team B API connection failed: {e}")
                        raise

            # Try to get running event loop, if exists use it (for tests), otherwise create new one
            try:
                loop = asyncio.get_running_loop()
                # Running in async context (e.g., pytest-asyncio), create task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    tc_team_b = pool.submit(asyncio.run, _build_tc_team_b_http()).result()
            except RuntimeError:
                # No event loop, safe to use asyncio.run() (normal sync context)
                tc_team_b = asyncio.run(_build_tc_team_b_http())
            
            _graphiti_context_cache.set(sender_id, recipient_id, tc_team_b)
            _graphiti_failure_tracker.record_success()
            return tc_team_b
            
    except Exception as e:
        logger.warning(f"Team B API integration unavailable, falling back to Graphiti HTTP client: {e}")

    # Fallback: Try Graphiti-core via GraphitiClient

    except Exception as e:
        logger.warning(f"Team B API integration unavailable, falling back to Graphiti HTTP client: {e}")

    # Fallback: Try Graphiti-core via GraphitiClient
    # Initialize Graphiti client
    try:
        from core.graphiti_client import GraphitiClient
        from core.graphiti_config import (
            GraphitiConfig,
            RelationshipReportingRequest,
            RelationshipDepartmentRequest,
            RelationshipProjectsRequest,
            RolesTemporalRequest,
        )
    except ImportError as e:
        error_msg = f"Graphiti client not available: {e}"
        logger.warning(error_msg)
        _graphiti_failure_tracker.record_failure(error_msg)
        
        # STEP 6: Fallback to minimal context
        fallback_context = _create_minimal_temporal_context(timestamp, error_msg)
        logger.warning(f"Returning fallback context (ALLOW_WITH_AUDIT) for {sender_id} -> {recipient_id}")
        return fallback_context
    
    # Create config from environment or defaults
    config = GraphitiConfig()
    client = GraphitiClient(config)
    
    # Initialize temporal context with defaults
    tc = TemporalContext(
        timestamp=timestamp,
        timezone="UTC",
        temporal_role="user",
        situation="NORMAL",
    )
    
    failures = []
    
    try:
        # 1. Query reporting relationship
        logger.debug(f"Fetching reporting relationship: {sender_id} -> {recipient_id}")

        reporting_req = RelationshipReportingRequest(
            employee_id=sender_id,
            manager_id=recipient_id
        )
        reporting = client.get_reporting_relationship(reporting_req)
        
        if reporting.is_direct_report:
            # sender reports to recipient = privileged access
            tc.temporal_role = "manager"
            logger.info(f"{sender_id} reports to {recipient_id}: elevated temporal role")
    
    except Exception as e:
        error_msg = f"Failed to get reporting relationship: {e}"
        logger.warning(error_msg)
        failures.append(error_msg)
        _graphiti_failure_tracker.record_failure(error_msg)
    
    try:
        # 2. Query department relationship
        logger.debug(f"Fetching department relationship: {sender_id} <-> {recipient_id}")
        dept_req = RelationshipDepartmentRequest(
            sender_id=sender_id,
            recipient_id=recipient_id
        )
        dept_response = client.get_department_relationship(dept_req)
        
        if dept_response.same_department:
            # Same department = lower risk, set context
            tc.data_domain = f"dept_{sender_id.split('-')[0]}"  # Extract dept prefix
            logger.info(f"{sender_id} and {recipient_id} share department: lower risk context")
    
    except Exception as e:
        error_msg = f"Failed to get department relationship: {e}"
        logger.warning(error_msg)
        failures.append(error_msg)
        _graphiti_failure_tracker.record_failure(error_msg)
    
    try:
        # 3. Query shared projects
        logger.debug(f"Fetching shared projects: {sender_id} <-> {recipient_id}")
        projects_req = RelationshipProjectsRequest(
            sender_id=sender_id,
            recipient_id=recipient_id
        )
        projects_response = client.get_shared_projects(projects_req)
        
        if projects_response.projects_ids:
            # Set project membership and use first project for event correlation
            tc.event_correlation = f"proj_{projects_response.projects_ids[0]}"
            logger.info(f"{sender_id} and {recipient_id} share {len(projects_response.projects_ids)} projects")
    
    except Exception as e:
        error_msg = f"Failed to get shared projects: {e}"
        logger.warning(error_msg)
        failures.append(error_msg)
        _graphiti_failure_tracker.record_failure(error_msg)
    
    try:
        # 4. Query temporal/acting roles
        logger.debug(f"Fetching temporal roles for {sender_id} at {timestamp.isoformat()}")
        roles_req = RolesTemporalRequest(person_id=sender_id)
        roles_response = client.get_temporal_roles(roles_req)
        
        if roles_response.temporary_roles:
            # If there are active/acting roles, override the temporal_role
            for role in roles_response.temporary_roles:
                if role.is_active_at(timestamp):
                    tc.temporal_role = f"acting_{role.role_name.lower().replace(' ', '_')}"
                    # Set access window from role dates if available
                    if role.start_date and role.end_date:
                        tc.access_window = TimeWindow(
                            start=role.start_date,
                            end=role.end_date,
                            window_type="emergency",
                            description=f"Acting role: {role.role_name}"
                        )
                    logger.info(f"{sender_id} has active acting role: {role.role_name}")
                    break  # Use first active role
    
    except Exception as e:
        error_msg = f"Failed to get temporal roles: {e}"
        logger.warning(error_msg)
        failures.append(error_msg)
        _graphiti_failure_tracker.record_failure(error_msg)
    
    finally:
        # Always clean up client connection
        try:
            client.close()
        except Exception:
            pass
    
    # STEP 6: Check if all queries failed - use fallback if necessary
    if len(failures) >= 4:
        # All 4 API calls failed - critical Graphiti outage
        logger.critical(f"All Graphiti API calls failed for {sender_id} -> {recipient_id}. Engaging fallback mode.")
        fallback_context = _create_minimal_temporal_context(
            timestamp,
            f"Complete Graphiti failure: {len(failures)}/4 calls failed"
        )
        return fallback_context
    elif len(failures) > 0:
        # Some failures - record success for partial success
        _graphiti_failure_tracker.record_success()
    else:
        # All calls succeeded
        _graphiti_failure_tracker.record_success()
    
    # STEP 5: Cache the enriched context for future requests
    _graphiti_context_cache.set(sender_id, recipient_id, tc)
    
    logger.info(f"Built temporal context for {sender_id}: role={tc.temporal_role}, domain={getattr(tc, 'data_domain', 'N/A')}")
    return tc



# STEP 5: Cache management functions
def get_graphiti_cache_stats() -> dict:
    """Get statistics about Graphiti context cache."""
    return _graphiti_context_cache.stats()


def clear_graphiti_cache() -> None:
    """Clear all cached Graphiti contexts."""
    _graphiti_context_cache.clear()


def set_graphiti_cache_ttl(ttl_seconds: int) -> None:
    """
    Configure cache TTL (time-to-live).
    
    Args:
        ttl_seconds: Cache expiration time in seconds (recommended: 60-180)
    """
    _graphiti_context_cache.ttl_seconds = ttl_seconds
    logger.info(f"Updated Graphiti cache TTL to {ttl_seconds} seconds")


# STEP 6: Failure tracking and fallback management functions
def get_graphiti_failure_stats() -> dict:
    """
    Get statistics about Graphiti API failures (STEP 6).
    
    Returns:
        Dict with failure tracking metrics:
        - window_seconds: Monitoring window (5 minutes)
        - failures: Count in current window
        - successes: Count in current window
        - total: Total requests in window
        - failure_rate_pct: Percentage failures
        - threshold_pct: Alert threshold
        - alert_active: True if failure rate exceeds threshold
    """
    return _graphiti_failure_tracker.get_stats()


def reset_graphiti_failure_tracker() -> None:
    """
    Reset the Graphiti failure tracker (STEP 6).
    
    Useful after maintenance or when implementing fixes.
    Logs final statistics before reset.
    """
    stats = _graphiti_failure_tracker.get_stats()
    logger.info(f"Resetting Graphiti failure tracker. Final stats: {stats}")
    _graphiti_failure_tracker.failure_times.clear()
    _graphiti_failure_tracker.success_times.clear()
    _graphiti_failure_tracker.alert_logged = False
