"""
Graphiti HTTP Client - Execute requests to Team B's Graphiti API

This module implements the actual HTTP client that calls Graphiti endpoints
using the configuration and schemas defined in graphiti_config.py.
"""

import requests
from typing import Optional, Dict, Any
import logging
import time
from datetime import datetime

from core.graphiti_config import (
    GraphitiConfig,
    RelationshipReportingRequest,
    RelationshipReportingResponse,
    RelationshipDepartmentRequest,
    RelationshipDepartmentResponse,
    RelationshipProjectsRequest,
    RelationshipProjectsResponse,
    RolesTemporalRequest,
    RolesTemporalResponse,
    GraphitiAPIError,
    GraphitiConnectionError,
    GraphitiAuthError,
    GraphitiRateLimitError,
    GraphitiNotFoundError,
    GraphitiValidationError,
    HTTP_ERROR_MAP,
)

logger = logging.getLogger(__name__)


class GraphitiClient:
    """HTTP client for calling Graphiti API endpoints"""
    
    def __init__(self, config: GraphitiConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)
        self._request_count = 0
        self._last_reset = time.time()
    
    def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting"""
        now = time.time()
        elapsed = now - self._last_reset
        
        # Reset counter every minute
        if elapsed >= 60:
            self._request_count = 0
            self._last_reset = now
        
        # Check if we've exceeded limit
        if self._request_count >= self.config.max_requests_per_minute:
            wait_time = 60 - elapsed
            logger.warning(f"Rate limit approaching; wait {wait_time:.1f}s before next request")
            raise GraphitiRateLimitError(f"Rate limit exceeded. Retry after {wait_time:.1f}s")
        
        self._request_count += 1
    
    def _handle_response(self, response: requests.Response, endpoint: str) -> Dict[str, Any]:
        """Handle HTTP response and map errors"""
        if response.status_code < 300:
            return response.json()
        
        # Map status code to exception
        error_class = HTTP_ERROR_MAP.get(response.status_code, GraphitiAPIError)
        error_msg = f"{endpoint}: HTTP {response.status_code} - {response.text[:200]}"
        logger.error(error_msg)
        raise error_class(error_msg)
    
    def _retry_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Execute request with retry logic"""
        for attempt in range(self.config.max_retries):
            try:
                self._check_rate_limit()
                
                if method.upper() == "GET":
                    response = self.session.get(url, timeout=self.config.request_timeout, **kwargs)
                elif method.upper() == "POST":
                    response = self.session.post(url, timeout=self.config.request_timeout, **kwargs)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Success
                if response.status_code < 500:
                    return response
                
                # Server error - retry
                if attempt < self.config.max_retries - 1:
                    wait = self.config.retry_backoff_seconds * (2 ** attempt)
                    logger.warning(f"Server error; retrying in {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                else:
                    return response
            
            except requests.exceptions.Timeout as e:
                if attempt < self.config.max_retries - 1:
                    wait = self.config.retry_backoff_seconds * (2 ** attempt)
                    logger.warning(f"Timeout; retrying in {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                else:
                    raise GraphitiConnectionError(f"Connection timeout after {self.config.max_retries} retries")
            
            except requests.exceptions.ConnectionError as e:
                if attempt < self.config.max_retries - 1:
                    wait = self.config.retry_backoff_seconds * (2 ** attempt)
                    logger.warning(f"Connection error; retrying in {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                else:
                    raise GraphitiConnectionError(f"Connection failed after {self.config.max_retries} retries: {e}")
        
        return response
    
    def get_reporting_relationship(self, req: RelationshipReportingRequest) -> RelationshipReportingResponse:
        """GET /relationship/reporting - Query reporting relationship between two people"""
        url = f"{self.config.api_url}{self.config.relationship_reporting_path}"
        
        try:
            response = self._retry_request("GET", url, params=req.to_query_params())
            data = self._handle_response(response, "get_reporting_relationship")
            return RelationshipReportingResponse.from_json(data)
        except GraphitiAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_reporting_relationship: {e}")
            raise GraphitiAPIError(f"Failed to get reporting relationship: {e}")
    
    def get_department_relationship(self, req: RelationshipDepartmentRequest) -> RelationshipDepartmentResponse:
        """GET /relationship/department - Query department relationship between two people"""
        url = f"{self.config.api_url}{self.config.relationship_department_path}"
        
        try:
            response = self._retry_request("GET", url, params=req.to_query_params())
            data = self._handle_response(response, "get_department_relationship")
            return RelationshipDepartmentResponse.from_json(data)
        except GraphitiAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_department_relationship: {e}")
            raise GraphitiAPIError(f"Failed to get department relationship: {e}")
    
    def get_shared_projects(self, req: RelationshipProjectsRequest) -> RelationshipProjectsResponse:
        """GET /relationship/projects - Query shared projects between two people"""
        url = f"{self.config.api_url}{self.config.relationship_projects_path}"
        
        try:
            response = self._retry_request("GET", url, params=req.to_query_params())
            data = self._handle_response(response, "get_shared_projects")
            return RelationshipProjectsResponse.from_json(data)
        except GraphitiAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_shared_projects: {e}")
            raise GraphitiAPIError(f"Failed to get shared projects: {e}")
    
    def get_temporal_roles(self, req: RolesTemporalRequest) -> RolesTemporalResponse:
        """GET /roles/temporal - Query temporary/acting roles for a person"""
        url = f"{self.config.api_url}{self.config.roles_temporal_path}"
        
        try:
            response = self._retry_request("GET", url, params=req.to_query_params())
            data = self._handle_response(response, "get_temporal_roles")
            return RolesTemporalResponse.from_json(data)
        except GraphitiAPIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_temporal_roles: {e}")
            raise GraphitiAPIError(f"Failed to get temporal roles: {e}")
    
    def close(self) -> None:
        """Close the session"""
        self.session.close()


if __name__ == "__main__":
    # Example usage
    config = GraphitiConfig(
        base_url="https://graphiti-staging.internal.example.com",
        auth_token="demo-token",
        service_identity="temporal-engine"
    )
    
    client = GraphitiClient(config)
    
    try:
        # Example: Get reporting relationship
        req = RelationshipReportingRequest(
            employee_id="emp-123",
            manager_id="mgr-456"
        )
        print(f"Querying: {req.to_query_params()}")
        # result = client.get_reporting_relationship(req)
        # print(f"Result: {result}")
    except GraphitiAPIError as e:
        print(f"API Error: {e}")
    finally:
        client.close()
