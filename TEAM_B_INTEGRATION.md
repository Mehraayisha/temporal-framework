# Team B Integration Guide

## Architecture Overview

The temporal-framework can integrate with **Team B's organizational chart API** via HTTP/REST endpoints. Team B runs as a **separate, independent FastAPI service** and is not embedded in the temporal-framework repository.

This microservice architecture provides:
- ✅ **Clean separation of concerns** - each service has its own codebase and deployment
- ✅ **Independent deployment** - update Team B without touching temporal-framework
- ✅ **Language agnostic** - Team B can be written in any language
- ✅ **Clear API contracts** - HTTP/JSON integration
- ✅ **Easy scaling** - run multiple Team B instances independently

## When to Use Team B Integration

Use Team B's API when you need:
- **Organizational hierarchy queries** - department, manager, direct reports
- **Employee context enrichment** - security clearance, employment type, location
- **Access control policies** - role-based decisions
- **Temporal organizational data** - working hours, contract details

Otherwise, use the default **Graphiti-based integration** (Graphiti provides similar org chart functionality).

## Setup Instructions

### 1. Start Team B Service (Separate)

Team B runs independently. To start it:

```bash
# Clone/pull Team B repository (from your Team B repo, not this one)
cd /path/to/team_b_org_chart_codebase

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI service
uvicorn api.rest_api:app --host 0.0.0.0 --port 8000

# Service will be available at http://localhost:8000
# Check health: curl http://localhost:8000/docs
```

### 2. Configure Temporal Framework

In your temporal-framework `.env` file:

```bash
# Enable Team B integration
GRAPHITI_MODE="team_b_api"

# Point to running Team B service
TEAM_B_API_URL="http://localhost:8000"
```

If you want to use Graphiti instead (default):
```bash
GRAPHITI_MODE="graphiti"
```

### 3. Run Temporal Framework

```bash
python main.py
```

The enricher will automatically:
1. Check `GRAPHITI_MODE` environment variable
2. If `team_b_api`: call Team B's HTTP API at `TEAM_B_API_URL`
3. If `graphiti` (default): use Graphiti-core HTTP client
4. Build `TemporalContext` from whichever service responds

## Team B API Endpoints

The temporal-framework only calls:

### GET /api/v1/employee-context/{email}
Returns complete organizational context for an employee.

**Parameters:**
- `{email}`: Employee email address (e.g., john.doe@company.com)

**Response:**
```json
{
  "employee_id": "EMP-001",
  "name": "John Doe",
  "email": "john.doe@company.com",
  "title": "Senior Engineer",
  "department": "Engineering",
  "team": "Backend",
  "security_clearance": "confidential",
  "employment_type": "full_time",
  "hierarchy_level": 3,
  "is_manager": true,
  "is_executive": false,
  "is_ceo": false,
  "reports_to": {"employee_id": "EMP-002", "name": "Engineering Lead"},
  "direct_reports": [{"employee_id": "EMP-003", "name": "Junior Engineer"}],
  "projects": [{"project_id": "PROJ-001", "name": "Core Platform"}],
  "working_hours": {"timezone": "America/New_York", "start": "08:00", "end": "18:00"},
  "location": "San Francisco",
  "phone": "+1-555-0123",
  "is_active": true,
  "contract_end_date": null
}
```

## Field Mapping

Team B response fields are mapped to `TemporalContext`:

| Team B Field | TemporalContext Field | Notes |
|--------------|----------------------|-------|
| `working_hours.timezone` | `timezone` | User's timezone for business hours |
| `is_manager` | `temporal_role` | If `true`, maps to `"acting_manager"` else `"user"` |
| `department` | `data_domain` | Extra field (allowed by pydantic config) |
| `security_clearance` | `security_clearance` | Extra field for audit tracking |
| - | `business_hours` | TODO: parse `working_hours` for current time |
| - | `situation` | Defaults to `"NORMAL"` |
| - | `timestamp` | Set to current datetime |

**Example mapping:**
```python
# Team B response
{
  "employee_id": "EMP-SMITH",
  "is_manager": True,
  "department": "Emergency Medicine",
  "security_clearance": "confidential",
  "working_hours": {"timezone": "America/New_York"}
}

# Becomes TemporalContext
TemporalContext(
  timestamp=datetime.now(timezone.utc),
  timezone="America/New_York",
  temporal_role="acting_manager",  # because is_manager=True
  data_domain="Emergency Medicine",  # extra field
  security_clearance="confidential",  # extra field
  situation="NORMAL",
  user_id="dr_smith"
)
```

## Fallback Behavior

If Team B is unreachable:

1. **Log warning**: "Team B API integration unavailable, falling back to Graphiti HTTP client"
2. **Try Graphiti**: Continue to Graphiti-core GraphitiClient
3. **If Graphiti fails**: Return minimal TemporalContext with `situation="INCIDENT"`
4. **Audit trail**: All failures logged for troubleshooting

## Troubleshooting

### "Team B API integration unavailable"
**Causes:**
- Team B service not running
- Wrong `TEAM_B_API_URL` in `.env`
- Network/firewall blocking connection
- Team B service crashed

**Solutions:**
```bash
# 1. Check Team B is running
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Mac/Linux

# 2. Test endpoint manually
curl http://localhost:8000/api/v1/employee-context/test@company.com

# 3. Check logs
# Review temporal-framework logs for detailed error message
# Review Team B service logs
```

### "404 Employee not found"
- Employee email doesn't exist in Team B's database
- Email format mismatch (check Team B's data format)
- Team B's database not initialized with test data

### Connection timeout
- Team B service is slow or overloaded
- Network latency issues
- Increase timeout in `enricher.py` line ~419

## Architecture Decision: Why HTTP, Not Direct Imports?

Both temporal-framework and Team B have a `core/` Python package. Direct imports create namespace collisions:

```python
# This fails:
from core.privacy_queries import ...  # Which core? Ours or Team B's?
```

**Solution: HTTP microservices**
- Clean service boundaries
- No shared Python code
- Independent scaling
- Language-independent integration

See README.md for more on microservice architecture.

## Performance Considerations

**Current implementation:**
- Timeout: 10 seconds per API call
- No caching (each request calls Team B)
- No retry logic (fail-fast fallback)

**Future improvements:**
- [ ] Add response caching with TTL
- [ ] Implement retry logic with exponential backoff
- [ ] Circuit breaker pattern for degraded mode
- [ ] Async HTTP requests to reduce latency
- [ ] Metrics/monitoring for API response times

## Testing

### Unit Tests
```bash
# Tests use httpx mocks - no actual Team B service needed
python -m pytest tests/test_team_b_integration.py -v
```

### Integration Tests (Requires Team B running)
```bash
# Start Team B service first
cd /path/to/team_b_org_chart_codebase
uvicorn api.rest_api:app --port 8000

# In another terminal
export GRAPHITI_MODE=team_b_api
export TEAM_B_API_URL=http://localhost:8000
python main.py
```

## Summary

✅ **Temporal-framework calls Team B via HTTP only**  
✅ **Team B runs independently**  
✅ **Clean microservice boundary**  
✅ **Automatic fallback to Graphiti if Team B unavailable**  

For Team B development, see Team B's own repository documentation.
