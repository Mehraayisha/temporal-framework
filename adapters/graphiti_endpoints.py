"""
Team B Graphiti Endpoint Adapters
----------------------------------
This module provides adapters for Team B's Graphiti API endpoints.

Required environment variables:
  - TEAM_B_GRAPHITI_BASE_URL: Base URL for Graphiti (e.g., https://graphiti.team-b.internal)
  - TEAM_B_GRAPHITI_AUTH_TOKEN: Bearer token or API key for authentication

Endpoints:
  - /relationship/reporting?employee=E&manager=M
  - /relationship/department?sender=S&recipient=R
  - /relationship/projects?sender=S&recipient=R
  - /roles/temporal?person_id=P&time=T
"""

import os
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import requests

LOGGER = logging.getLogger(__name__)


class GraphitiConfig:
    """Configuration for Team B Graphiti endpoint access."""
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 10.0,
        verify_ssl: bool = True
    ):
        self.base_url = base_url or os.environ.get(
            "TEAM_B_GRAPHITI_BASE_URL",
            "http://localhost:8000"  # Fallback for local testing
        ).rstrip("/")
        self.auth_token = auth_token or os.environ.get("TEAM_B_GRAPHITI_AUTH_TOKEN", "")
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    def headers(self) -> Dict[str, str]:
        """Generate request headers with auth."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers


class GraphitiAdapter:
    """Adapter for Team B Graphiti endpoints."""

    def __init__(self, config: Optional[GraphitiConfig] = None):
        self.config = config or GraphitiConfig()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to Graphiti endpoint with error handling."""
        url = f"{self.config.base_url}{endpoint}"
        headers = self.config.headers()

        LOGGER.debug(
            "Graphiti %s %s params=%s",
            method.upper(),
            endpoint,
            params or {},
        )

        try:
            if method.lower() == "get":
                resp = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                )
            elif method.lower() == "post":
                resp = requests.post(
                    url,
                    json=json_body,
                    params=params,
                    headers=headers,
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            LOGGER.debug(
                "Graphiti %s %s -> status=%s",
                method.upper(),
                endpoint,
                resp.status_code,
            )

            resp.raise_for_status()
            return resp.json()

        except requests.Timeout as e:
            LOGGER.error("Graphiti timeout on %s %s: %s", method.upper(), endpoint, e)
            raise RuntimeError(f"Graphiti timeout: {e}") from e
        except requests.HTTPError as e:
            LOGGER.error(
                "Graphiti HTTP error on %s %s: %s (body: %s)",
                method.upper(),
                endpoint,
                e,
                resp.text if hasattr(e, "response") else "N/A",
            )
            raise RuntimeError(f"Graphiti HTTP error: {e}") from e
        except requests.RequestException as e:
            LOGGER.error("Graphiti connection error on %s %s: %s", method.upper(), endpoint, e)
            raise RuntimeError(f"Graphiti connection error: {e}") from e

    def get_reporting_relationship(
        self,
        employee: str,
        manager: str,
    ) -> Dict[str, Any]:
        """
        Get reporting relationship between employee and manager.

        Endpoint: GET /relationship/reporting?employee=E&manager=M

        Args:
            employee: Employee ID or email
            manager: Manager ID or email

        Returns:
            JSON response with reporting relationship details
        """
        params = {
            "employee": employee,
            "manager": manager,
        }
        return self._request("GET", "/relationship/reporting", params=params)

    def get_department_relationship(
        self,
        sender: str,
        recipient: str,
    ) -> Dict[str, Any]:
        """
        Get department-level relationship between sender and recipient.

        Endpoint: GET /relationship/department?sender=S&recipient=R

        Args:
            sender: Sender ID or email
            recipient: Recipient ID or email

        Returns:
            JSON response with department relationship details
        """
        params = {
            "sender": sender,
            "recipient": recipient,
        }
        return self._request("GET", "/relationship/department", params=params)

    def get_projects_relationship(
        self,
        sender: str,
        recipient: str,
    ) -> Dict[str, Any]:
        """
        Get shared projects between sender and recipient.

        Endpoint: GET /relationship/projects?sender=S&recipient=R

        Args:
            sender: Sender ID or email
            recipient: Recipient ID or email

        Returns:
            JSON response with shared projects list
        """
        params = {
            "sender": sender,
            "recipient": recipient,
        }
        return self._request("GET", "/relationship/projects", params=params)

    def get_temporal_roles(
        self,
        person_id: str,
        time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get active temporal roles for a person at a given time.

        Endpoint: GET /roles/temporal?person_id=P&time=T

        Args:
            person_id: Person ID or email
            time: Timestamp (ISO format). Defaults to current UTC time.

        Returns:
            JSON response with list of active temporal roles
        """
        if time is None:
            time = datetime.now(timezone.utc)

        # Ensure ISO format
        if isinstance(time, datetime):
            time_str = time.isoformat()
        else:
            time_str = str(time)

        params = {
            "person_id": person_id,
            "time": time_str,
        }
        return self._request("GET", "/roles/temporal", params=params)

    def health_check(self) -> bool:
        """Check if Graphiti endpoint is reachable."""
        try:
            resp = requests.head(
                self.config.base_url,
                headers=self.config.headers(),
                timeout=2.0,
                verify=self.config.verify_ssl,
            )
            return resp.status_code < 500
        except Exception as e:
            LOGGER.warning("Graphiti health check failed: %s", e)
            return False
