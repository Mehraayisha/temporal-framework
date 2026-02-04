"""
Tests for Team B Graphiti endpoint adapters.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from adapters.graphiti_endpoints import GraphitiConfig, GraphitiAdapter


class TestGraphitiConfig:
    """Tests for GraphitiConfig."""

    def test_config_defaults(self):
        """Config should use environment variables or sensible defaults."""
        config = GraphitiConfig()
        assert config.base_url == "http://localhost:8000"
        assert config.timeout == 10.0
        assert config.verify_ssl is True

    def test_config_from_env(self):
        """Config should read from environment variables."""
        import os
        with patch.dict(os.environ, {
            "TEAM_B_GRAPHITI_BASE_URL": "https://graphiti.team-b.internal",
            "TEAM_B_GRAPHITI_AUTH_TOKEN": "secret-token-123"
        }):
            config = GraphitiConfig()
            assert config.base_url == "https://graphiti.team-b.internal"
            assert config.auth_token == "secret-token-123"

    def test_config_headers_with_auth(self):
        """Headers should include Bearer token when auth is provided."""
        config = GraphitiConfig(auth_token="test-token")
        headers = config.headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"

    def test_config_headers_without_auth(self):
        """Headers should work without auth token."""
        config = GraphitiConfig()
        headers = config.headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"


class TestGraphitiAdapter:
    """Tests for GraphitiAdapter."""

    @pytest.fixture
    def adapter(self):
        config = GraphitiConfig(base_url="http://localhost:8000")
        return GraphitiAdapter(config)

    def test_get_reporting_relationship(self, adapter):
        """Should call /relationship/reporting endpoint."""
        with patch("adapters.graphiti_endpoints.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "employee": "alice@example.com",
                "manager": "bob@example.com",
                "is_direct_report": True,
            }
            mock_get.return_value = mock_resp

            result = adapter.get_reporting_relationship(
                employee="alice@example.com",
                manager="bob@example.com"
            )

            assert result["is_direct_report"] is True
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            # Params should pass raw email values; requests handles URL encoding internally
            assert call_args[1]["params"]["employee"] == "alice@example.com"
            assert call_args[1]["params"]["manager"] == "bob@example.com"

    def test_get_department_relationship(self, adapter):
        """Should call /relationship/department endpoint."""
        with patch("adapters.graphiti_endpoints.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "sender_dept": "Engineering",
                "recipient_dept": "Engineering",
                "same_department": True,
            }
            mock_get.return_value = mock_resp

            result = adapter.get_department_relationship(
                sender="alice@example.com",
                recipient="bob@example.com"
            )

            assert result["same_department"] is True

    def test_get_projects_relationship(self, adapter):
        """Should call /relationship/projects endpoint."""
        with patch("adapters.graphiti_endpoints.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "shared_projects": ["proj-alpha", "proj-beta"],
                "count": 2,
            }
            mock_get.return_value = mock_resp

            result = adapter.get_projects_relationship(
                sender="alice@example.com",
                recipient="bob@example.com"
            )

            assert result["count"] == 2
            assert len(result["shared_projects"]) == 2

    def test_get_temporal_roles(self, adapter):
        """Should call /roles/temporal endpoint."""
        with patch("adapters.graphiti_endpoints.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            now = datetime.now(timezone.utc)
            mock_resp.json.return_value = {
                "person_id": "alice@example.com",
                "time": now.isoformat(),
                "roles": ["user", "oncall_medium", "acting_manager"],
                "active": True,
            }
            mock_get.return_value = mock_resp

            result = adapter.get_temporal_roles(
                person_id="alice@example.com",
                time=now
            )

            assert len(result["roles"]) == 3
            assert "acting_manager" in result["roles"]

    def test_temporal_roles_defaults_to_now(self, adapter):
        """get_temporal_roles should default time to current UTC."""
        with patch("adapters.graphiti_endpoints.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"roles": []}
            mock_get.return_value = mock_resp

            adapter.get_temporal_roles(person_id="alice@example.com")

            call_params = mock_get.call_args[1]["params"]
            assert "time" in call_params

    def test_health_check_success(self, adapter):
        """Health check should return True when endpoint is reachable."""
        with patch("adapters.graphiti_endpoints.requests.head") as mock_head:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_head.return_value = mock_resp

            result = adapter.health_check()

            assert result is True

    def test_health_check_failure(self, adapter):
        """Health check should return False on connection error."""
        with patch("adapters.graphiti_endpoints.requests.head") as mock_head:
            mock_head.side_effect = Exception("Connection refused")

            result = adapter.health_check()

            assert result is False

    def test_timeout_handling(self, adapter):
        """Should raise RuntimeError on timeout."""
        import requests
        with patch("adapters.graphiti_endpoints.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("Request timed out")

            with pytest.raises(RuntimeError, match="Graphiti timeout"):
                adapter.get_reporting_relationship(
                    employee="alice@example.com",
                    manager="bob@example.com"
                )

    def test_http_error_handling(self, adapter):
        """Should raise RuntimeError on HTTP error."""
        import requests
        with patch("adapters.graphiti_endpoints.requests.get") as mock_get:
            mock_resp = Mock()
            mock_resp.status_code = 404
            mock_resp.text = "Not found"
            mock_resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
            mock_get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="Graphiti HTTP error"):
                adapter.get_reporting_relationship(
                    employee="alice@example.com",
                    manager="bob@example.com"
                )

    def test_team_b_integration_smoke(self):
        """End-to-end smoke: uses Team B config to hit health endpoint with auth headers."""
        config = GraphitiConfig(
            base_url="https://graphiti.team-b.internal",
            auth_token="team-b-token",
            timeout=5.0,
        )
        adapter = GraphitiAdapter(config)

        with patch("adapters.graphiti_endpoints.requests.head") as mock_head:
            mock_resp = Mock()
            mock_resp.status_code = 200
            mock_head.return_value = mock_resp

            result = adapter.health_check()

            assert result is True
            mock_head.assert_called_once()
            call_args = mock_head.call_args
            # Validate Team B base URL and headers are used
            # Health check should target the Team B base URL
            assert call_args[0][0].startswith("https://graphiti.team-b.internal")
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer team-b-token"
            assert headers["Content-Type"] == "application/json"
