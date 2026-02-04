# Privacy Firewall Visual Demo Tool

Simple Streamlit app to test and validate your organizational chart logic.

## Quick Start

1. **Install dependencies:**
   ```bash
   cd visual-tool
   pip install -r requirements.txt
   ```

2. **Make sure your Privacy Firewall API is running:**
   ```bash
   cd .. # Go back to main project
   python -m uvicorn api.rest_api:app --reload --port 8000
   ```

3. **Start the visual tool:**
   ```bash
   cd visual-tool
   streamlit run app.py
   ```

4. **Open in browser:** http://localhost:8501

## Features

### 🧪 Access Request Tester
- Test predefined scenarios (Manager→Report, Cross-dept, etc.)
- Custom access requests
- See real-time decisions from your API
- View relationship analysis

### 👥 Employee Explorer  
- Look up any employee by email
- See their organizational context
- View manager, reports, projects, teams

### 📊 System Stats
- Cache performance metrics
- API health status
- Hit rate visualizations

## Demo Scenarios

The tool includes these test scenarios:

1. **Manager → Direct Report (PTO)**: Should ALLOW
2. **Cross-Department (Salary)**: Should DENY  
3. **Same Team (Code Access)**: Should ALLOW
4. **CEO → Anyone**: Should ALLOW

## Troubleshooting

- **"API not running"**: Start your FastAPI server first
- **"Employee not found"**: Check email format (should be `@techflow.com`)
- **"Connection Error"**: Make sure both Neo4j and API are running

## What This Validates

This tool proves your organizational chart logic works by:
- ✅ Testing manager-subordinate relationships
- ✅ Validating cross-department access controls  
- ✅ Showing real-time policy decisions
- ✅ Demonstrating relationship detection accuracy