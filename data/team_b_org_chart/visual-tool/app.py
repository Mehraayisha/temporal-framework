"""
Simple Visual Tool for Privacy Firewall Demo

Validates that your organizational chart logic is working correctly.
"""

import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional

# Configure page
st.set_page_config(
    page_title="Privacy Firewall Demo",
    page_icon="🛡️",
    layout="wide"
)

# API Configuration
API_BASE = "http://localhost:8000"

class APIClient:
    """Simple client to test your privacy firewall API"""
    
    @staticmethod
    def test_connection():
        """Test if API is running"""
        try:
            response = requests.get(f"{API_BASE}/api/v1/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    @staticmethod
    def get_employee_context(email: str):
        """Get employee details"""
        try:
            response = requests.get(f"{API_BASE}/api/v1/employee-context/{email}")
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    @staticmethod
    def get_all_employees():
        """Get list of all employees from Neo4j"""
        try:
            import neo4j
            driver = neo4j.GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
            with driver.session() as session:
                result = session.run(
                    "MATCH (e:Entity:Employee) RETURN e.name as name, e.email as email, e.title as title ORDER BY e.name"
                )
                employees = [{"name": record["name"], "email": record["email"], "title": record["title"]} 
                           for record in result]
            driver.close()
            return employees
        except Exception as e:
            st.error(f"Could not fetch employees: {e}")
            return []
    
    @staticmethod
    def check_access(requester_email: str, target_email: str, resource_type: str = "employee_data"):
        """Test access control"""
        try:
            response = requests.post(
                f"{API_BASE}/api/v1/check-employee-access",
                params={
                    "requester_email": requester_email,
                    "target_email": target_email,
                    "resource_type": resource_type
                }
            )
            if response.status_code == 200:
                return response.json()
            return {"error": f"API Error: {response.status_code}"}
        except Exception as e:
            return {"error": f"Connection Error: {str(e)}"}
    
    @staticmethod
    def get_cache_stats():
        """Get performance metrics"""
        try:
            response = requests.get(f"{API_BASE}/api/v1/cache-stats")
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

def main():
    st.title("🛡️ Privacy Firewall Demo Tool")
    st.markdown("**Simple interface to validate your organizational chart logic**")
    
    # Check API connection
    if not APIClient.test_connection():
        st.error("❌ Privacy Firewall API not running!")
        st.markdown("**Start your API first:**")
        st.code("cd /home/christo/Desktop/Skyber Work/team_b_org_chart")
        st.code("python -m uvicorn api.rest_api:app --reload --port 8000")
        return
    
    st.success("✅ Connected to Privacy Firewall API")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a demo page:",
        ["🧪 Access Request Tester", "👥 Employee Explorer", "📊 System Stats"]
    )
    
    if page == "🧪 Access Request Tester":
        access_request_tester()
    elif page == "👥 Employee Explorer":
        employee_explorer()
    elif page == "📊 System Stats":
        system_stats()

def access_request_tester():
    """Main testing interface"""
    st.header("🧪 Access Request Tester")
    st.markdown("Test if your organizational logic is working correctly")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Setup Request")
        
        # Get employee list for dropdowns
        all_employees = APIClient.get_all_employees()
        employee_emails = [emp['email'] for emp in all_employees] if all_employees else [
            "sarah.chen@techflow.com", "priya.patel@techflow.com", "emily.zhang@techflow.com",
            "carlos.martinez@techflow.com", "lisa.kumar@techflow.com", "alex.kim@techflow.com"
        ]
        
        # Predefined test cases
        test_scenarios = {
            "Manager → Direct Report (PTO)": {
                "requester": "priya.patel@techflow.com",
                "target": "emily.zhang@techflow.com",
                "resource": "pto_calendar",
                "expected": "ALLOW"
            },
            "Cross-Department (Salary)": {
                "requester": "lisa.kumar@techflow.com", 
                "target": "carlos.martinez@techflow.com",
                "resource": "salary_info",
                "expected": "DENY"
            },
            "Same Team (Code Access)": {
                "requester": "alex.kim@techflow.com",
                "target": "emily.zhang@techflow.com", 
                "resource": "source_code",
                "expected": "ALLOW"
            },
            "CEO → Anyone": {
                "requester": "sarah.chen@techflow.com",
                "target": "priya.patel@techflow.com",
                "resource": "performance_review",
                "expected": "ALLOW"
            }
        }
        
        scenario = st.selectbox("Quick Test Scenarios:", ["Custom"] + list(test_scenarios.keys()))
        
        if scenario != "Custom":
            test_data = test_scenarios[scenario]
            requester_email = test_data["requester"]
            target_email = test_data["target"] 
            resource_type = test_data["resource"]
            st.info(f"Expected Result: **{test_data['expected']}**")
        else:
            # Custom scenario with dropdowns
            col1a, col1b = st.columns(2)
            with col1a:
                requester_email = st.selectbox("Requester:", employee_emails, index=1)  # Default to Priya
            with col1b:
                target_email = st.selectbox("Target:", employee_emails, index=2)  # Default to Emily
                
            resource_type = st.selectbox(
                "Resource Type:",
                ["pto_calendar", "salary_info", "source_code", "performance_review", "department_docs"]
            )
        
        if st.button("🚀 Test Access Request", type="primary"):
            if requester_email and target_email:
                with st.spinner("Checking access..."):
                    result = APIClient.check_access(requester_email, target_email, resource_type)
                    
                    # Store result in session state for display
                    st.session_state['last_result'] = result
                    st.session_state['last_requester'] = requester_email
                    st.session_state['last_target'] = target_email
                    st.session_state['last_resource'] = resource_type
    
    with col2:
        st.subheader("Access Decision")
        
        if 'last_result' in st.session_state:
            result = st.session_state['last_result']
            
            if "error" in result:
                st.error(f"❌ Error: {result['error']}")
            else:
                # Show decision
                if result.get('access_granted', False):
                    st.success("✅ **ACCESS GRANTED**")
                else:
                    st.error("❌ **ACCESS DENIED**")
                
                # Show reason
                st.markdown(f"**Reason:** {result.get('reason', 'No reason provided')}")
                
                # Show relationship context
                if 'relationship_context' in result:
                    context = result['relationship_context']
                    st.markdown("**Relationship Analysis:**")
                    
                    relationship_data = []
                    if 'department_match' in context:
                        relationship_data.append({"Check": "Same Department", "Result": "✅ Yes" if context['department_match'] else "❌ No"})
                    if 'is_manager' in result.get('requester', {}):
                        relationship_data.append({"Check": "Is Manager", "Result": "✅ Yes" if result['requester']['is_manager'] else "❌ No"})
                    
                    if relationship_data:
                        df = pd.DataFrame(relationship_data)
                        st.dataframe(df, use_container_width=True)
                
                # Show raw response (collapsible)
                with st.expander("🔍 Raw API Response"):
                    st.json(result)

def employee_explorer():
    """Explore employee data and relationships"""
    st.header("👥 Employee Explorer") 
    st.markdown("Explore the organizational chart data")
    
    # Get all employees for dropdown
    with st.spinner("Loading employee list..."):
        all_employees = APIClient.get_all_employees()
    
    if all_employees:
        # Create dropdown with employee options
        employee_options = ["Type email manually..."] + [f"{emp['name']} ({emp['email']})" for emp in all_employees]
        
        selected_option = st.selectbox("Select Employee:", employee_options)
        
        if selected_option == "Type email manually...":
            email = st.text_input("Employee Email:", "priya.patel@techflow.com")
        else:
            # Extract email from selection
            email = selected_option.split("(")[1].split(")")[0]
            st.info(f"Selected: {email}")
        
        # Show employee list in sidebar
        with st.sidebar:
            st.subheader("All Employees")
            st.caption(f"Total: {len(all_employees)} employees")
            for emp in all_employees[:10]:  # Show first 10
                st.write(f"• **{emp['name']}** - {emp['title']}")
            if len(all_employees) > 10:
                st.caption(f"... and {len(all_employees) - 10} more")
    else:
        st.warning("Could not load employee list. Using manual entry.")
        email = st.text_input("Employee Email:", "priya.patel@techflow.com")
    
    if st.button("Get Employee Info"):
        with st.spinner("Loading employee data..."):
            employee_data = APIClient.get_employee_context(email)
            
            if employee_data:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Basic Info")
                    st.write(f"**Name:** {employee_data.get('name', 'Unknown')}")
                    st.write(f"**Title:** {employee_data.get('title', 'Unknown')}")
                    st.write(f"**Department:** {employee_data.get('department', 'Unknown')}")
                    st.write(f"**Team:** {employee_data.get('team', 'Unknown')}")
                    st.write(f"**Security Clearance:** {employee_data.get('security_clearance', 'Unknown')}")
                
                with col2:
                    st.subheader("Relationships")
                    
                    # Manager
                    if employee_data.get('reports_to'):
                        manager = employee_data['reports_to']
                        st.write(f"**Manager:** {manager.get('name', 'Unknown')} ({manager.get('email', 'Unknown')})")
                    else:
                        st.write("**Manager:** None (Top-level)")
                    
                    # Direct reports
                    reports = employee_data.get('direct_reports', [])
                    if reports:
                        st.write(f"**Direct Reports ({len(reports)}):**")
                        for report in reports[:5]:  # Show first 5
                            st.write(f"• {report.get('name', 'Unknown')} - {report.get('title', 'Unknown')}")
                        if len(reports) > 5:
                            st.write(f"• ... and {len(reports) - 5} more")
                    else:
                        st.write("**Direct Reports:** None")
                    
                    # Projects
                    projects = employee_data.get('projects', [])
                    if projects:
                        st.write(f"**Projects ({len(projects)}):**")
                        for project in projects[:3]:  # Show first 3
                            st.write(f"• {project.get('name', 'Unknown')}")
                        if len(projects) > 3:
                            st.write(f"• ... and {len(projects) - 3} more")
                    else:
                        st.write("**Projects:** None assigned")
                
                # Additional info
                col3, col4 = st.columns(2)
                with col3:
                    st.subheader("Employment Info")
                    st.write(f"**Type:** {employee_data.get('employment_type', 'Unknown')}")
                    st.write(f"**Hierarchy Level:** {employee_data.get('hierarchy_level', 'Unknown')}")
                    st.write(f"**Location:** {employee_data.get('location', 'Unknown')}")
                
                with col4:
                    st.subheader("Access Level")
                    st.write(f"**Is Manager:** {'✅ Yes' if employee_data.get('is_manager') else '❌ No'}")
                    st.write(f"**Is Executive:** {'✅ Yes' if employee_data.get('is_executive') else '❌ No'}")
                    st.write(f"**Is CEO:** {'✅ Yes' if employee_data.get('is_ceo') else '❌ No'}")
                
                # Raw data
                with st.expander("🔍 Raw Employee Data"):
                    st.json(employee_data)
            else:
                st.error(f"❌ Employee not found: {email}")
                st.info("💡 **Tip:** Try one of these emails:")
                if all_employees:
                    for emp in all_employees[:5]:
                        st.code(emp['email'])
                else:
                    st.code("sarah.chen@techflow.com")
                    st.code("priya.patel@techflow.com")
                    st.code("emily.zhang@techflow.com")

def system_stats():
    """Show system performance and stats"""
    st.header("📊 System Statistics")
    
    # Get cache stats
    cache_stats = APIClient.get_cache_stats()
    
    if cache_stats:
        st.subheader("Cache Performance")
        
        # Overall hit rate
        hit_rate = cache_stats.get('overall_hit_rate', 0)
        st.metric("Overall Hit Rate", f"{hit_rate:.1%}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            emp_cache = cache_stats.get('employee_context_cache', {})
            st.metric("Employee Context", f"{emp_cache.get('hit_rate', 0):.1%}")
            st.caption(f"Size: {emp_cache.get('size', 0)}")
        
        with col2:
            policy_cache = cache_stats.get('policy_cache', {})
            st.metric("Policy Results", f"{policy_cache.get('hit_rate', 0):.1%}")
            st.caption(f"Size: {policy_cache.get('size', 0)}")
        
        with col3:
            rel_cache = cache_stats.get('relationship_cache', {})
            st.metric("Relationships", f"{rel_cache.get('hit_rate', 0):.1%}")
            st.caption(f"Size: {rel_cache.get('size', 0)}")
        
        # Performance chart
        if hit_rate > 0:
            cache_data = {
                'Cache Type': ['Employee Context', 'Policy Results', 'Relationships'],
                'Hit Rate': [
                    emp_cache.get('hit_rate', 0),
                    policy_cache.get('hit_rate', 0), 
                    rel_cache.get('hit_rate', 0)
                ]
            }
            
            fig = px.bar(
                x=cache_data['Cache Type'],
                y=cache_data['Hit Rate'],
                title="Cache Hit Rates by Type"
            )
            fig.update_layout(yaxis_title="Hit Rate", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ Could not fetch cache statistics")
    
    st.subheader("API Health")
    if APIClient.test_connection():
        st.success("✅ API is healthy and responding")
    else:
        st.error("❌ API is not responding")

if __name__ == "__main__":
    main()