# Integration Guide for Privacy Firewall

This guide helps integrate the Privacy Firewall into other projects.

## 🎯 **What You Get**

This package provides:
- **Organizational relationship detection** (manager/peer/subordinate)
- **Policy-based access control** (43 YAML rules)
- **REST API endpoints** (8 endpoints for integration)
- **High-performance caching** (80% hit rate)
- **Audit logging** (compliance-ready)
- **Visual testing tool** (demo and validation)

## 🚀 **Quick Integration (5 minutes)**

### Option A: Use As-Is with Sample Data
```bash
# 1. Extract the project zip
unzip privacy-firewall.zip
cd team_b_org_chart

# 2. Install dependencies
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Start services
docker-compose up -d
python data/ingestion.py  # Load sample org data
python -m uvicorn api.rest_api:app --port 8000

# 4. Test integration
curl http://localhost:8000/api/v1/health
```

### Option B: Use with Your Own Data
```bash
# 1-3. Same as Option A

# 4. Replace org data
# Edit data/org_data.json with your employees/departments/teams
python data/ingestion.py  # Load your data

# 5. Customize policies (optional)
# Edit config/resource_policies.yaml

# 6. Start API
python -m uvicorn api.rest_api:app --port 8000
```

## 📡 **API Integration**

### Main Endpoints
```python
# Check if employee can access another employee's data
POST /api/v1/check-employee-access
{
  "requester_email": "manager@company.com",
  "target_email": "employee@company.com", 
  "resource_type": "pto_calendar"
}

# Get employee organizational context
GET /api/v1/employee-context/{email}

# Get audit trail
GET /api/v1/audit-trail?employee_email=user@company.com
```

### Python SDK Usage
```python
import requests

# Check access permission
def check_employee_access(requester, target, resource_type):
    response = requests.post(
        "http://localhost:8000/api/v1/check-employee-access",
        params={
            "requester_email": requester,
            "target_email": target,
            "resource_type": resource_type
        }
    )
    return response.json()

# Example usage
result = check_employee_access(
    "priya.patel@company.com", 
    "emily.zhang@company.com", 
    "pto_calendar"
)
print(f"Access: {result['access_granted']}")
print(f"Reason: {result['reason']}")
```

## 🔧 **Customization**

### 1. **Adding Your Organization Data**
Edit `data/org_data.json`:
```json
{
  "company_name": "Your Company Name",
  "employees": [
    {
      "name": "Your CEO",
      "email": "ceo@yourcompany.com",
      "title": "Chief Executive Officer",
      "department": "Executive",
      "security_clearance": "executive",
      "reports_to": null
    }
  ],
  "departments": [
    {"name": "Engineering", "data_classification": "confidential"}
  ]
}
```

### 2. **Customizing Access Policies**
Edit `config/resource_policies.yaml`:
```yaml
- id: custom-001
  name: Department Manager Access
  conditions:
    - requester.is_manager == true
    - requester.department == target.department
    - resource_type in ["team_calendar", "project_docs"]
  action: ALLOW
  priority: 80
```

### 3. **Environment Configuration**
Copy `.env.example` to `.env` and update:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your_neo4j_password
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## 🔌 **Embedding in Existing Applications**

### Flask Integration
```python
from flask import Flask, request, jsonify
import asyncio
from api.privacy_api import check_access

app = Flask(__name__)

@app.route('/check-access', methods=['POST'])
def check_access_endpoint():
    data = request.json
    
    # Use your privacy firewall
    result = asyncio.run(check_access(
        data['employee_email'],
        data['resource_id'], 
        data['classification']
    ))
    
    return jsonify(result)
```

### FastAPI Integration
```python
from fastapi import FastAPI
from api.privacy_api import PrivacyFirewallAPI

app = FastAPI()
privacy_api = PrivacyFirewallAPI()

@app.middleware("http")
async def privacy_middleware(request, call_next):
    # Check access for protected routes
    if request.url.path.startswith('/protected/'):
        user_email = request.headers.get('X-User-Email')
        resource_id = request.path_params.get('resource_id')
        
        access_check = await privacy_api.check_resource_access(
            user_email, resource_id, "confidential", "document"
        )
        
        if not access_check['allowed']:
            return JSONResponse(
                status_code=403,
                content={"error": access_check['reason']}
            )
    
    return await call_next(request)
```

## 📊 **Performance Tuning**

### Cache Configuration
Adjust cache TTL in `core/cache.py`:
```python
class PrivacyFirewallCache:
    EMPLOYEE_CONTEXT_TTL = 300  # 5 minutes
    POLICY_RESULT_TTL = 60      # 1 minute  
    RELATIONSHIP_TTL = 180      # 3 minutes
```

### Database Optimization
For large organizations (1000+ employees):
```yaml
# docker-compose.yml
services:
  neo4j:
    environment:
      - NEO4J_dbms_memory_heap_initial__size=2G
      - NEO4J_dbms_memory_heap_max__size=4G
      - NEO4J_dbms_memory_pagecache_size=1G
```

## 🧪 **Testing Your Integration**

### 1. **Use the Visual Tool**
```bash
cd visual-tool
./start.sh
# Open http://localhost:8501
```

### 2. **Run Unit Tests**
```bash
pytest tests/ -v
python test_api_complete.py
```

### 3. **API Health Check**
```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/cache-stats
```

## 🚨 **Troubleshooting**

### Common Issues

**"Neo4j connection failed"**
```bash
docker ps  # Check if neo4j container is running
docker logs team_b_neo4j  # Check for errors
```

**"Employee not found"**
```bash
# Check if data is loaded
docker exec team_b_neo4j cypher-shell -u neo4j -p password \
  "MATCH (e:Entity:Employee) RETURN count(e)"
```

**"Import errors"**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate
pip install -r requirements.txt
```

**"Port conflicts"**
```bash
# Change ports in docker-compose.yml and API startup
python -m uvicorn api.rest_api:app --port 8001
```

## 📞 **Support**

This system provides:
- ✅ **Organizational relationship detection**
- ✅ **Policy-based access decisions** 
- ✅ **High-performance caching**
- ✅ **Complete audit trail**
- ✅ **REST API for integration**
- ✅ **Visual testing interface**

For additional customization or questions about integration with specific frameworks, refer to the code documentation or extend the existing patterns.

## 📝 **What to Modify for Different Organizations**

| Component | File | What to Change |
|-----------|------|----------------|
| **Employee Data** | `data/org_data.json` | Replace with your org structure |
| **Access Policies** | `config/resource_policies.yaml` | Add/modify business rules |
| **Security Levels** | `core/models.py` | Adjust clearance hierarchy |
| **API Endpoints** | `api/rest_api.py` | Add custom endpoints |
| **Database Config** | `docker-compose.yml` | Adjust memory/performance |

The core logic in `core/privacy_queries.py` and `api/privacy_api.py` should work with any organizational structure without modification.