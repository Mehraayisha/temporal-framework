#!/usr/bin/env python3
"""
Production Integration Examples

This module demonstrates real-world integration patterns and production
scenarios for the Temporal Framework. Use these examples as templates
for implementing the framework in your production systems.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from core.tuples import TimeWindow, TemporalContext, EnhancedContextualIntegrityTuple
from core.policy_engine import TemporalPolicyEngine
from core.evaluator import TemporalEvaluator
from core.enricher import TemporalEnricher
from core.neo4j_manager import TemporalNeo4jManager
from core.graphiti_manager import TemporalGraphitiManager
from core.logging_config import setup_logging

# Configure production-grade logging
setup_logging(level="INFO", enable_audit=True, enable_security=True)
logger = logging.getLogger(__name__)

class ProductionTemporalFramework:
    """
    Production-ready temporal framework with comprehensive integration.
    
    This class demonstrates how to integrate the temporal framework
    into production systems with proper error handling, monitoring,
    and performance optimization.
    """
    
    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        graphiti_server_url: Optional[str] = None,
        graphiti_api_key: Optional[str] = None,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 300
    ):
        """
        Initialize production framework with all integrations.
        
        Args:
            neo4j_uri: Neo4j database connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            graphiti_server_url: Optional Graphiti server URL
            graphiti_api_key: Optional Graphiti API key
            enable_caching: Enable policy decision caching
            cache_ttl_seconds: Cache time-to-live in seconds
        """
        self.neo4j_manager = TemporalNeo4jManager(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password
        )
        
        self.graphiti_manager = None
        if graphiti_server_url and graphiti_api_key:
            self.graphiti_manager = TemporalGraphitiManager(
                server_url=graphiti_server_url,
                api_key=graphiti_api_key
            )
        
        self.enricher = TemporalEnricher(
            neo4j_manager=self.neo4j_manager,
            graphiti_manager=self.graphiti_manager,
            enable_caching=enable_caching,
            cache_ttl_seconds=cache_ttl_seconds
        )
        
        self.policy_engine = TemporalPolicyEngine(
            neo4j_manager=self.neo4j_manager,
            graphiti_manager=self.graphiti_manager,
            enable_caching=enable_caching,
            cache_ttl_seconds=cache_ttl_seconds
        )
        
        self.evaluator = TemporalEvaluator(
            policy_engine=self.policy_engine,
            enricher=self.enricher,
            enable_audit=True
        )
        
        logger.info("Initialized production temporal framework")
    
    async def initialize(self) -> None:
        """Initialize async components."""
        if self.graphiti_manager:
            await self.graphiti_manager.initialize()
            logger.info("Initialized Graphiti integration")
    
    async def evaluate_access_request(
        self,
        request: Dict[str, any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Evaluate access request with comprehensive logging and error handling.
        
        Args:
            request: Access request dictionary
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Dictionary containing decision and metadata
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create 6-tuple from request
            access_tuple = self._create_tuple_from_request(request)
            
            # Add correlation ID if provided
            if correlation_id:
                access_tuple.correlation_id = correlation_id
            
            # Log request received
            logger.info(
                f"Processing access request",
                extra={
                    "request_id": access_tuple.request_id,
                    "correlation_id": correlation_id,
                    "data_type": access_tuple.data_type,
                    "sender": access_tuple.data_sender,
                    "recipient": access_tuple.data_recipient,
                    "risk_level": access_tuple.risk_level
                }
            )
            
            # Evaluate request
            result = self.evaluator.evaluate(access_tuple)
            
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Create response
            response = {
                "decision": {
                    "allowed": result.decision.allowed,
                    "reason": result.decision.reason,
                    "confidence": result.decision.confidence,
                    "risk_level": result.decision.risk_level
                },
                "metadata": {
                    "request_id": access_tuple.request_id,
                    "correlation_id": correlation_id,
                    "processing_time_seconds": processing_time,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "framework_version": "1.0.0"
                },
                "audit": {
                    "enriched": result.enriched,
                    "applied_rules": result.decision.applied_rules,
                    "graph_queries_executed": result.graph_queries_count if hasattr(result, 'graph_queries_count') else 0
                }
            }
            
            # Log successful evaluation
            logger.info(
                f"Access request evaluated successfully",
                extra={
                    "request_id": access_tuple.request_id,
                    "correlation_id": correlation_id,
                    "decision": result.decision.allowed,
                    "confidence": result.decision.confidence,
                    "processing_time": processing_time
                }
            )
            
            # Security audit log for sensitive decisions
            if access_tuple.audit_required or result.decision.risk_level in ["HIGH", "CRITICAL"]:
                security_logger = logging.getLogger("security")
                security_logger.info(
                    f"High-risk access decision",
                    extra={
                        "request_id": access_tuple.request_id,
                        "data_subject": access_tuple.data_subject,
                        "decision": result.decision.allowed,
                        "risk_level": result.decision.risk_level,
                        "emergency_override": access_tuple.temporal_context.emergency_override
                    }
                )
            
            return response
            
        except Exception as e:
            # Calculate error processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Log error
            logger.error(
                f"Failed to evaluate access request: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time": processing_time
                },
                exc_info=True
            )
            
            # Return error response
            return {
                "decision": {
                    "allowed": False,
                    "reason": f"evaluation_error: {type(e).__name__}",
                    "confidence": 0.0,
                    "risk_level": "CRITICAL"
                },
                "metadata": {
                    "correlation_id": correlation_id,
                    "processing_time_seconds": processing_time,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": True,
                    "error_message": str(e)
                }
            }
    
    def _create_tuple_from_request(self, request: Dict[str, any]) -> EnhancedContextualIntegrityTuple:
        """
        Create EnhancedContextualIntegrityTuple from request dictionary.
        
        This method demonstrates how to transform external API requests
        into the framework's internal data structures.
        """
        # Extract temporal context data
        context_data = request.get("temporal_context", {})
        
        # Create time windows
        time_windows = []
        for tw_data in context_data.get("time_windows", []):
            time_window = TimeWindow(
                start=datetime.fromisoformat(tw_data["start"]) if tw_data.get("start") else None,
                end=datetime.fromisoformat(tw_data["end"]) if tw_data.get("end") else None,
                window_type=tw_data.get("window_type", "access_window"),
                description=tw_data.get("description")
            )
            time_windows.append(time_window)
        
        # Create temporal context
        temporal_context = TemporalContext(
            service_id=context_data.get("service_id", "unknown"),
            user_id=context_data.get("user_id", "unknown"),
            location=context_data.get("location", "unknown"),
            timezone=context_data.get("timezone", "UTC"),
            time_windows=time_windows,
            emergency_override=context_data.get("emergency_override", False),
            situation=context_data.get("situation", "NORMAL"),
            temporal_role=context_data.get("temporal_role")
        )
        
        # Create enhanced tuple
        access_tuple = EnhancedContextualIntegrityTuple(
            data_type=request["data_type"],
            data_subject=request["data_subject"],
            data_sender=request["data_sender"],
            data_recipient=request["data_recipient"],
            transmission_principle=request["transmission_principle"],
            temporal_context=temporal_context,
            risk_level=request.get("risk_level", "MEDIUM"),
            audit_required=request.get("audit_required", False),
            compliance_tags=request.get("compliance_tags", []),
            session_id=request.get("session_id"),
            data_classification=request.get("data_classification"),
            purpose_limitation=request.get("purpose_limitation")
        )
        
        return access_tuple
    
    async def health_check(self) -> Dict[str, any]:
        """
        Perform comprehensive health check of all components.
        
        Returns:
            Health status dictionary
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {}
        }
        
        try:
            # Check Neo4j connection
            neo4j_healthy = self.neo4j_manager.health_check()
            health_status["components"]["neo4j"] = {
                "status": "healthy" if neo4j_healthy else "unhealthy",
                "response_time_ms": 0  # Add actual timing
            }
        except Exception as e:
            health_status["components"]["neo4j"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Check Graphiti connection
        if self.graphiti_manager:
            try:
                graphiti_healthy = await self.graphiti_manager.health_check()
                health_status["components"]["graphiti"] = {
                    "status": "healthy" if graphiti_healthy else "unhealthy"
                }
            except Exception as e:
                health_status["components"]["graphiti"] = {
                    "status": "error", 
                    "error": str(e)
                }
        
        # Check policy engine
        try:
            rule_count = len(self.policy_engine.rules)
            health_status["components"]["policy_engine"] = {
                "status": "healthy",
                "active_rules": rule_count
            }
        except Exception as e:
            health_status["components"]["policy_engine"] = {
                "status": "error",
                "error": str(e)
            }
        
        # Determine overall status
        component_statuses = [comp["status"] for comp in health_status["components"].values()]
        if "error" in component_statuses:
            health_status["status"] = "error"
        elif "unhealthy" in component_statuses:
            health_status["status"] = "degraded"
        
        return health_status
    
    async def get_metrics(self) -> Dict[str, any]:
        """
        Get performance and usage metrics.
        
        Returns:
            Metrics dictionary
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "policy_engine": {
                "total_evaluations": getattr(self.policy_engine, '_evaluation_count', 0),
                "cache_hit_rate": getattr(self.policy_engine, '_cache_hit_rate', 0.0),
                "average_evaluation_time_ms": getattr(self.policy_engine, '_avg_eval_time_ms', 0.0)
            },
            "enricher": {
                "total_enrichments": getattr(self.enricher, '_enrichment_count', 0),
                "cache_hit_rate": getattr(self.enricher, '_cache_hit_rate', 0.0)
            },
            "database": {
                "neo4j_query_count": getattr(self.neo4j_manager, '_query_count', 0),
                "graphiti_query_count": getattr(self.graphiti_manager, '_query_count', 0) if self.graphiti_manager else 0
            }
        }
    
    async def close(self) -> None:
        """Clean up resources."""
        if self.neo4j_manager:
            self.neo4j_manager.close()
        
        if self.graphiti_manager:
            await self.graphiti_manager.close()
        
        logger.info("Closed production temporal framework")


# FastAPI Integration Example
try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    
    class AccessRequest(BaseModel):
        """FastAPI request model for access evaluation."""
        data_type: str
        data_subject: str
        data_sender: str
        data_recipient: str
        transmission_principle: str
        temporal_context: Dict[str, any]
        risk_level: str = "MEDIUM"
        audit_required: bool = False
        compliance_tags: List[str] = []
        session_id: Optional[str] = None
        
    # Initialize FastAPI app
    app = FastAPI(
        title="Temporal Framework API",
        description="Production API for temporal contextual integrity",
        version="1.0.0"
    )
    
    # Global framework instance
    framework: Optional[ProductionTemporalFramework] = None
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize framework on startup."""
        global framework
        framework = ProductionTemporalFramework(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password"
        )
        await framework.initialize()
        logger.info("FastAPI application started with temporal framework")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up on shutdown."""
        if framework:
            await framework.close()
        logger.info("FastAPI application shutdown complete")
    
    @app.post("/evaluate")
    async def evaluate_access(
        request: AccessRequest,
        req: Request
    ) -> JSONResponse:
        """Evaluate access request."""
        if not framework:
            raise HTTPException(status_code=503, detail="Framework not initialized")
        
        correlation_id = req.headers.get("x-correlation-id")
        
        try:
            result = await framework.evaluate_access_request(
                request.dict(),
                correlation_id=correlation_id
            )
            
            status_code = 200 if result["decision"]["allowed"] else 403
            return JSONResponse(content=result, status_code=status_code)
            
        except Exception as e:
            logger.error(f"API evaluation error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal evaluation error")
    
    @app.get("/health")
    async def health_check() -> JSONResponse:
        """Health check endpoint."""
        if not framework:
            return JSONResponse(
                content={"status": "error", "message": "Framework not initialized"},
                status_code=503
            )
        
        health = await framework.health_check()
        status_code = 200 if health["status"] == "healthy" else 503
        return JSONResponse(content=health, status_code=status_code)
    
    @app.get("/metrics")
    async def get_metrics() -> JSONResponse:
        """Metrics endpoint."""
        if not framework:
            raise HTTPException(status_code=503, detail="Framework not initialized")
        
        metrics = await framework.get_metrics()
        return JSONResponse(content=metrics)

except ImportError:
    logger.warning("FastAPI not available - skipping API integration example")


# Example usage functions
async def example_medical_emergency_scenario():
    """
    Demonstrate emergency medical access scenario.
    
    This example shows how the framework handles time-critical
    medical access requests with emergency overrides.
    """
    print("\n🚨 Emergency Medical Access Scenario")
    print("="*50)
    
    # Initialize framework (would be done once in production)
    framework = ProductionTemporalFramework(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j", 
        neo4j_password="password"
    )
    
    try:
        await framework.initialize()
        
        # Emergency access request (2 AM, outside business hours)
        emergency_request = {
            "data_type": "critical_patient_vitals",
            "data_subject": "patient_trauma_001",
            "data_sender": "dr_emergency_oncall",
            "data_recipient": "trauma_response_team",
            "transmission_principle": "life_safety_emergency",
            "temporal_context": {
                "service_id": "emergency_medical_system",
                "user_id": "dr_emergency_oncall",
                "location": "emergency_department_trauma_bay",
                "timezone": "UTC",
                "emergency_override": True,
                "situation": "EMERGENCY",
                "temporal_role": "emergency_physician",
                "time_windows": [{
                    "window_type": "emergency",
                    "description": "24/7 emergency access"
                }]
            },
            "risk_level": "HIGH",
            "audit_required": True,
            "compliance_tags": ["HIPAA", "emergency_care", "life_safety"]
        }
        
        # Evaluate request
        result = await framework.evaluate_access_request(
            emergency_request,
            correlation_id="emergency_001"
        )
        
        print(f"📋 Request: {emergency_request['data_type']}")
        print(f"🏥 Context: {emergency_request['temporal_context']['situation']}")
        print(f"⚡ Emergency Override: {emergency_request['temporal_context']['emergency_override']}")
        print(f"\n✅ Decision: {'ALLOWED' if result['decision']['allowed'] else 'DENIED'}")
        print(f"📝 Reason: {result['decision']['reason']}")
        print(f"📊 Confidence: {result['decision']['confidence']:.2f}")
        print(f"⚠️  Risk Level: {result['decision']['risk_level']}")
        print(f"⏱️  Processing Time: {result['metadata']['processing_time_seconds']:.3f}s")
        
        print(f"\n🔍 Audit Information:")
        print(f"   Request ID: {result['metadata']['request_id']}")
        print(f"   Correlation ID: {result['metadata']['correlation_id']}")
        print(f"   Context Enriched: {result['audit']['enriched']}")
        print(f"   Applied Rules: {', '.join(result['audit']['applied_rules'])}")
        
    finally:
        await framework.close()


async def example_business_hours_scenario():
    """
    Demonstrate standard business hours access scenario.
    
    This example shows normal access control during business hours
    with standard validation and audit trails.
    """
    print("\n🏢 Business Hours Access Scenario")
    print("="*50)
    
    framework = ProductionTemporalFramework(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    )
    
    try:
        await framework.initialize()
        
        # Business hours request
        business_request = {
            "data_type": "patient_appointment_history",
            "data_subject": "patient_alice_smith",
            "data_sender": "dr_regular_physician", 
            "data_recipient": "medical_records_system",
            "transmission_principle": "routine_patient_care",
            "temporal_context": {
                "service_id": "medical_records_system",
                "user_id": "dr_regular_physician",
                "location": "clinic_station_3",
                "timezone": "UTC",
                "emergency_override": False,
                "situation": "NORMAL", 
                "temporal_role": "physician",
                "time_windows": [{
                    "start": datetime.now(timezone.utc).replace(hour=9).isoformat(),
                    "end": datetime.now(timezone.utc).replace(hour=17).isoformat(),
                    "window_type": "business_hours",
                    "description": "Regular clinic hours"
                }]
            },
            "risk_level": "MEDIUM",
            "audit_required": False,
            "compliance_tags": ["HIPAA", "routine_care"],
            "session_id": "session_12345"
        }
        
        result = await framework.evaluate_access_request(
            business_request,
            correlation_id="business_001"
        )
        
        print(f"📋 Request: {business_request['data_type']}")
        print(f"🏥 Context: {business_request['temporal_context']['situation']}")
        print(f"👩‍⚕️ Role: {business_request['temporal_context']['temporal_role']}")
        print(f"\n✅ Decision: {'ALLOWED' if result['decision']['allowed'] else 'DENIED'}")
        print(f"📝 Reason: {result['decision']['reason']}")
        print(f"📊 Confidence: {result['decision']['confidence']:.2f}")
        print(f"⚠️  Risk Level: {result['decision']['risk_level']}")
        print(f"⏱️  Processing Time: {result['metadata']['processing_time_seconds']:.3f}s")
        
    finally:
        await framework.close()


async def example_health_monitoring():
    """
    Demonstrate health monitoring and metrics collection.
    """
    print("\n📊 Health Monitoring & Metrics")
    print("="*50)
    
    framework = ProductionTemporalFramework(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password"
    )
    
    try:
        await framework.initialize()
        
        # Health check
        health = await framework.health_check()
        print(f"Overall Status: {health['status'].upper()}")
        print(f"Timestamp: {health['timestamp']}")
        print(f"\nComponent Status:")
        
        for component, status in health['components'].items():
            print(f"  {component}: {status['status']}")
            if 'error' in status:
                print(f"    Error: {status['error']}")
        
        # Metrics
        metrics = await framework.get_metrics()
        print(f"\n📈 Performance Metrics:")
        print(f"  Policy Evaluations: {metrics['policy_engine']['total_evaluations']}")
        print(f"  Cache Hit Rate: {metrics['policy_engine']['cache_hit_rate']:.2%}")
        print(f"  Avg Evaluation Time: {metrics['policy_engine']['average_evaluation_time_ms']:.2f}ms")
        
    finally:
        await framework.close()


# Main demonstration function
async def main():
    """
    Run all production integration examples.
    """
    print("🚀 Production Integration Examples")
    print("="*60)
    print("""
These examples demonstrate how to integrate the Temporal Framework
into production systems with proper error handling, monitoring,
and performance optimization.
    """)
    
    try:
        await example_medical_emergency_scenario()
        await example_business_hours_scenario() 
        await example_health_monitoring()
        
        print(f"\n🎯 Production Integration Complete!")
        print(f"""
Next steps for production deployment:
1. Configure environment variables for your infrastructure
2. Set up monitoring and alerting for health endpoints
3. Implement proper authentication and authorization
4. Configure load balancing and scaling policies
5. Set up comprehensive logging and audit trails
        """)
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")
        logger.error(f"Production example error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())