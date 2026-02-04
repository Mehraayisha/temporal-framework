# Resource-Based Access Control System

**Status:** ✅ Ready for Handoff  
**Version:** 2.0  
**Last Updated:** November 2, 2025

---

## Overview

Resource-based access control system using Neo4j graph database. Enforces 43 YAML-driven policies across organizational hierarchy, projects, departments, time restrictions, and security clearances.

**Key Features:**
- 🔐 **Resource-Based Access Control:** Employee → Resource permissions
- 📋 **43 YAML Policies:** Priority-based matching (10 tiers)
- �� **Organizational Graph:** 45 employees, 6 departments, 13 teams
- ⏰ **Time-Aware:** Business hours, seasonal access, temporal roles
- 🧪 **100% Test Coverage:** All tests passing (36/36)

---

## Quick Start

See **[QUICK_START.md](QUICK_START.md)** for detailed setup.

```bash
# 1. Start Neo4j
docker-compose up -d

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Load organizational data
python data/ingestion.py

# 5. Run demo
python demo_final.py
```

---

## Architecture

```
API Layer (api/privacy_api.py)
    ↓
Policy Engine (core/policy_engine_v2.py)
    ↓
Privacy Queries (core/privacy_queries.py)
    ↓
Neo4j Graph Database
```

**4-Layer Architecture:**
1. **API Layer** - check_access(), get_accessible_resources(), get_resource_viewers()
2. **Policy Engine** - 43 YAML policies with priority-based matching
3. **Privacy Queries** - Cypher query generation with employee context
4. **Neo4j Database** - Graph of employees, departments, teams, projects

---

## Access Control Policies

43 policies across 10 priority tiers:

| Tier | Priority | Category |
|------|----------|----------|
| 1 | 98-100 | Executive Override |
| 2 | 95-97 | Absolute Denials |
| 3 | 80-89 | Hierarchy-Based |
| 4 | 70-79 | Project-Based |
| 5 | 60-69 | Department/Team |
| 6 | 50-59 | Public/Internal |
| 7 | 40-49 | Time-Based |
| 8 | 30-39 | Role-Based |
| 9 | 20-29 | Special Cases |
| 10 | 1-10 | Fallback Denials |

See **[POLICY_CATALOG.md](POLICY_CATALOG.md)** for complete policy details.

---

## Example Usage

```python
from api.privacy_api import check_access

# Check if employee can access resource
result = check_access(
    employee_email="sarah.chen@acme.com",
    resource_id="RES-001",
    resource_classification="confidential"
)

print(result['access_granted'])  # True/False
print(result['reason'])          # Policy that matched
```

```python
from api.privacy_api import get_accessible_resources

# Get all resources employee can access
resources = get_accessible_resources(
    employee_email="john.smith@acme.com",
    classification="confidential"
)
```

```python
from api.privacy_api import get_resource_viewers

# Get all employees who can view a resource
viewers = get_resource_viewers(
    resource_id="RES-EXEC-001",
    resource_classification="top_secret"
)
```

---

## Data Model

### Neo4j Graph Structure

**Nodes:**
- `Employee` (45) - name, email, title, department, clearance_level, hierarchy_level
- `Department` (6) - name
- `Team` (13) - name, department
- `Project` (5) - project_id, name, status

**Relationships:**
- `REPORTS_TO` (44) - Manager-employee hierarchy
- `MEMBER_OF` (45) - Team membership
- `BELONGS_TO` (13) - Team-department mapping
- `WORKS_ON` (28) - Project assignments

### Clearance Levels

Security clearances (lowest to highest):
1. basic
2. standard
3. elevated
4. restricted
5. top_secret
6. executive

Resource classifications match clearance hierarchy.

---

## Configuration Files

- `config/resource_policies.yaml` - 43 access control policies
- `config/database.yaml` - Neo4j connection settings
- `config/temporal.yaml` - Time-based policy configuration
- `data/org_data.json` - Organizational structure (45 employees, 6 depts, 13 teams)

---

## Testing

**Test Coverage:** 100% (36/36 tests passing)

```bash
# Run all tests
pytest tests/ -v

# Run API tests
python test_api_complete.py

# Run demo scenarios
python demo_final.py
```

---

## Project Structure

```
team_b_org_chart/
├── api/
│   └── privacy_api.py           # API endpoints
├── core/
│   ├── graphiti_client.py       # Neo4j wrapper
│   ├── policy_engine_v2.py      # YAML policy engine
│   ├── privacy_queries.py       # Query generation
│   └── models.py                # Data models
├── config/
│   ├── resource_policies.yaml   # 43 policies
│   ├── database.yaml            # Neo4j config
│   └── temporal.yaml            # Time rules
├── data/
│   ├── ingestion.py             # Data loader
│   └── org_data.json            # Org structure
├── tests/
│   ├── conftest.py              # Test fixtures
│   └── test_graphiti_client.py  # Unit tests
├── demo_final.py                # 12 demo scenarios
├── test_api_complete.py         # 5 API tests
└── docker-compose.yml           # Neo4j container
```

---

## Environment Setup

Create `.env` file from `.env.example`:

```
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

---

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - Setup and installation guide
- **[POLICY_CATALOG.md](POLICY_CATALOG.md)** - Complete policy reference

---

## Notes

- **No REST API:** Python-only implementation (no HTTP endpoints)
- **No Authentication:** Assumes employee identity verified upstream
- **No Audit Logging:** Access decisions not persisted
- **Static Policies:** Requires restart to reload YAML changes

---

**Ready to use!** Run `python demo_final.py` to see the system in action.
