# core/enricher.py
import logging
import yaml
from datetime import datetime, timezone
from pathlib import Path
from core.tuples import TemporalContext, TimeWindow

MOCK_DIR = Path(__file__).resolve().parent.parent / "mocks"

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
    incidents = load_yaml("incidents.yaml")
    
    # Enhanced business hours detection with timezone awareness
    bh = oncall.get("business_hours", {"start_hour": 9, "end_hour": 17})
    service_info = oncall.get("services", {}).get(service_name, {})
    service_tz = service_info.get("timezone", "UTC")
    
    # Convert to service timezone for business hours calculation
    hour = now.astimezone().hour
    business_hours = bh["start_hour"] <= hour < bh["end_hour"]
    
    # Check for active incidents (investigating status)
    emergency_override = any(
        inc["service"] == service_name and inc["status"] == "investigating" 
        for inc in incidents.get("incidents", [])
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
    
    # Create temporal context
    tc = TemporalContext(
        service_id=service_name,  # Add service reference for Neo4j
        timestamp=now,
        timezone=service_tz,
        business_hours=business_hours,
        emergency_override=emergency_override,
        access_window=access_window,
        data_freshness_seconds=data_freshness_seconds,
        situation="EMERGENCY" if emergency_override else "NORMAL",
        temporal_role=f"oncall_{criticality}",
        event_correlation=f"{service_name}_context_{escalation_delay}min"
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
