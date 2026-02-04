# Quick Start Guide# 🚀 QUICK START GUIDE - Privacy Firewall Integration



This guide will help you set up and run the resource-based access control system.**Last Updated:** October 25, 2025  

**Status:** CRITICAL - Integration Testing Phase

---

---

## Prerequisites

## ✅ STEP 1: Verify Environment (5 minutes)

- **Docker Desktop** installed and running

- **Python 3.11+** installed### Check Neo4j is Running

```bash

---cd /home/christo/Desktop/Skyber\ Work/team_b_org_chart

docker ps | grep neo4j

## Step 1: Environment Setup```



Create a `.env` file from the example:**Expected:** Container `team_b_neo4j` should be running and healthy



```bash**If not running:**

cp .env.example .env```bash

```docker-compose up -d

docker ps  # Wait for "healthy" status

The `.env` file contains Neo4j credentials:```



```### Check Python Environment

NEO4J_URI=bolt://localhost:7687```bash

NEO4J_USER=neo4jpython3 --version  # Should be 3.10+

NEO4J_PASSWORD=password123pip3 list | grep -E "graphiti|neo4j|deal"

``````



------



## Step 2: Start Neo4j Database## ✅ STEP 2: Load Data into Neo4j (10-15 minutes)



Start the Neo4j container using Docker Compose:### Run Data Ingestion

```bash

```bashpython3 data/ingestion.py

docker-compose up -d```

```

**Expected Output:**

Verify the container is running:```

✅ Ingested 6 departments

```bash✅ Ingested 12 teams  

docker ps✅ Ingested 45 employees

```✅ Performance target met (<120s)

```

**Neo4j Browser Access:**

- URL: http://localhost:7474**If ingestion fails:**

- Username: `neo4j`1. Check Neo4j is running

- Password: `password123`2. Check `.env` file has correct credentials

3. Look at error logs in terminal

---

---

## Step 3: Install Python Dependencies

## ✅ STEP 3: Test Privacy Firewall Queries (15 minutes)

Create a virtual environment and install dependencies:

### Run PRD Validation Tests

```bash```bash

python -m venv .venvpython3 examples/test_privacy_queries.py

source .venv/bin/activate  # On Windows: .venv\Scripts\activate```

pip install -r requirements.txt

```**What This Tests:**

- ✓ Manager accessing team member's PTO (SCENARIO 1)

---- ✓ Cross-functional project data sharing (SCENARIO 2)

- ✓ Contractor data access restrictions (SCENARIO 3)

## Step 4: Load Organizational Data- ✓ Same department checks

- ✓ Employee context retrieval

Run the data ingestion script to populate the graph:- ✓ System health



```bash**Expected:**

python data/ingestion.pyAll scenarios should pass with ✓ marks

```

**If tests fail:**

**Expected Output:**1. Check data ingestion completed

```2. Review error messages

✓ Connected to Neo4j successfully3. Verify Neo4j connection

✓ Loaded 45 employees

✓ Loaded 6 departments---

✓ Loaded 13 teams

✓ Created relationships...## ✅ STEP 4: Integration with Team A (Critical)

```

### Your API Interface

---

Team A calls these functions from your code:

## Step 5: Test the System

```python

Run the comprehensive demo:from api.privacy_api import PrivacyFirewallAPI



```bash# Initialize once

python demo_final.pyapi = PrivacyFirewallAPI()

```

# Main access check (what Team A calls)

This will run 12 test scenarios demonstrating all access control policies.result = await api.check_access_permission(

    requester_id="emp-001",

Or test the API endpoints:    target_id="emp-002", 

    resource_type="pto_calendar",

```bash    timestamp=datetime.now()

python test_api_complete.py)

```

# Returns:

This tests the 5 main API operations.{

    "allowed": True/False,

---    "reason": "Access granted - manager relationship",

    "context": {

## Architecture Overview        "relationship": "manager",

        "department_match": True,

```        ...

┌─────────────────────────────────────────────────┐    }

│  API Layer (api/privacy_api.py)                 │}

│  - check_access()                               │

│  - get_accessible_resources()                   │# Get employee temporal context

│  - get_resource_viewers()                       │context = await api.get_temporal_context(

└────────────────┬────────────────────────────────┘    employee_id="emp-001",

                 │    timestamp=datetime.now()

                 ▼)

┌─────────────────────────────────────────────────┐

│  Policy Engine (core/policy_engine_v2.py)       │# Returns full employee org context

│  - 43 YAML-driven policies                      │```

│  - Priority-based matching (10 tiers)           │

└────────────────┬────────────────────────────────┘### API Contract Document

                 │

                 ▼Share this with Team A:

┌─────────────────────────────────────────────────┐

│  Privacy Queries (core/privacy_queries.py)      │**File:** `docs/TEAM_A_INTEGRATION_CONTRACT.md` (create this)

│  - get_employee_context()                       │

│  - Cypher query generation                      │**Endpoints:**

└────────────────┬────────────────────────────────┘1. `check_access_permission(requester_id, target_id, resource_type, timestamp)` → access decision

                 │2. `get_temporal_context(employee_id, timestamp)` → employee org context

                 ▼3. `check_organizational_relationship(user_a, user_b, relationship_type)` → boolean

┌─────────────────────────────────────────────────┐

│  Neo4j Graph Database                           │---

│  - 45 employees, 6 departments, 13 teams        │

│  - REPORTS_TO, MEMBER_OF, WORKS_ON relationships│## 🔍 TROUBLESHOOTING

└─────────────────────────────────────────────────┘

```### Problem: Data not loading

```bash

---# Check Neo4j logs

docker logs team_b_neo4j

## Access Control Policies

# Verify Neo4j is accessible

The system implements 43 policies across 10 priority tiers:curl http://localhost:7474



1. **Executive Override** (Priority 98-100) - CEO/Executive universal access# Check environment variables

2. **Absolute Denials** (Priority 95-97) - Security clearance, expired contractorscat .env | grep NEO4J

3. **Hierarchy-Based** (Priority 80-89) - Manager-report relationships```

4. **Project-Based** (Priority 70-79) - Shared project membership

5. **Department/Team** (Priority 60-69) - Same dept/team access### Problem: Tests failing

6. **Public/Internal** (Priority 50-59) - Classification-based access```bash

7. **Time-Based** (Priority 40-49) - Business hours, temporal roles# Check database has data

8. **Role-Based** (Priority 30-39) - Job function permissions# Open Neo4j Browser: http://localhost:7474

9. **Special Cases** (Priority 20-29) - Cross-dept collaboration# Run query: MATCH (n) RETURN labels(n), count(*)

10. **Fallback Denials** (Priority 1-10) - Default deny

# Expected:

See `POLICY_CATALOG.md` for full policy details.# Employee: 45

# Department: 6

---# Team: 12

```

## Configuration Files

### Problem: Import errors

- `config/resource_policies.yaml` - 43 access control policies```bash

- `config/database.yaml` - Neo4j connection settings# Reinstall dependencies

- `data/org_data.json` - Organizational structure (45 employees, 6 depts, 13 teams)pip3 install -r requirements.txt



---# Check Python path

python3 -c "import sys; print('\n'.join(sys.path))"

## Clearance Levels```



Security clearances (lowest to highest):---

1. **basic** - Public information only

2. **standard** - Internal documents## 📋 CRITICAL CHECKLIST

3. **elevated** - Confidential data

4. **restricted** - Sensitive informationBefore calling integration "complete":

5. **top_secret** - Highly classified

6. **executive** - CEO-level access- [ ] Neo4j running and healthy

- [ ] 45 employees loaded (verify with query)

Resource classifications match clearance levels (public → internal → confidential → restricted → secret → top_secret).- [ ] 6 departments loaded

- [ ] 12 teams loaded

---- [ ] REPORTS_TO relationships created (check `emp-005` → `emp-004`)

- [ ] MEMBER_OF relationships created (employees → departments)

## Example Usage- [ ] MEMBER_OF relationships created (employees → teams)

- [ ] `test_privacy_queries.py` passes all tests

### Check Access Permission- [ ] Performance <100ms per query (test with benchmarks)

- [ ] Team A has API documentation

```python- [ ] Example test scenarios documented

from api.privacy_api import check_access

---

result = check_access(

    employee_email="sarah.chen@acme.com",## 🎯 CURRENT PRIORITIES

    resource_id="RES-001",

    resource_classification="confidential"### TODAY (Oct 25):

)1. ✅ Run data ingestion

2. ✅ Test privacy queries

print(result['access_granted'])  # True/False3. ⏳ Fix any failing tests

print(result['reason'])          # Policy that granted/denied access4. ⏳ Document API for Team A

```

### TOMORROW (Oct 26):

### Get Accessible Resources1. Performance testing

2. Create Project nodes (for project membership queries)

```python3. Team A integration testing

from api.privacy_api import get_accessible_resources4. Bug fixes



resources = get_accessible_resources(---

    employee_email="john.smith@acme.com",

    classification="confidential"## 📞 NEED HELP?

)

### Common Issues:

for resource in resources:

    print(f"{resource['id']} - {resource['reason']}")**Q: "Employee not found" errors**  

```A: Check employee IDs match exactly (e.g., "emp-004" not "4")



### Get Resource Viewers**Q: "No relationship found" but should exist**  

A: Verify relationships in Neo4j Browser:

```python```cypher

from api.privacy_api import get_resource_viewersMATCH (e:Employee {id: 'emp-005'})-[r:REPORTS_TO]->(m:Employee)

RETURN e.name, type(r), m.name

viewers = get_resource_viewers(```

    resource_id="RES-EXEC-001",

    resource_classification="top_secret"**Q: "Projects not found"**  

)A: Project nodes need to be created separately (Phase 2)



for viewer in viewers:---

    print(f"{viewer['email']} - {viewer['reason']}")

```## 🚀 YOU'RE READY!



---If all checkboxes above are ✅, you have:

- ✅ Working Neo4j database with org data

## Troubleshooting- ✅ Privacy Firewall queries passing PRD requirements

- ✅ API ready for Team A integration

### Neo4j Connection Issues- ✅ Test scenarios validating functionality



**Problem:** `Failed to connect to Neo4j`**Next:** Coordinate with Team A for integration testing!

**Solution:** 
- Ensure Docker is running: `docker ps`
- Restart container: `docker-compose restart`
- Check port 7687: `lsof -i :7687`

### Empty Query Results

**Problem:** No employees found
**Solution:**
- Re-run data ingestion: `python data/ingestion.py`
- Verify in Neo4j Browser: `MATCH (e:Employee) RETURN count(e)`

### Policy Not Matching

**Problem:** Unexpected access denial/grant
**Solution:**
- Check policy priority in `config/resource_policies.yaml`
- Review employee clearance level
- Verify resource classification matches clearance hierarchy

---

## Running Tests

Run all tests:

```bash
pytest tests/ -v
```

Run demo scenarios:

```bash
python demo_final.py
```

Run API tests:

```bash
python test_api_complete.py
```

---

**You're all set!** 🎉

Run `python demo_final.py` to see the system in action.
