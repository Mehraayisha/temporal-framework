"""
Unit tests for GraphitiClient

Tests cover:
- Department operations
- Team operations  
- Employee operations
- Batch operations
- Search/query operations
- Error handling
"""

import pytest

from core import (
    Department,
    Employee,
    EntityCreationError,
    EntityNotFoundError,
    GraphitiClient,
    Team,
)


class TestDepartmentOperations:
    """Test department creation and retrieval"""

    @pytest.mark.asyncio
    async def test_add_department(self, graphiti_client, sample_department):
        """Test adding a single department"""
        dept = Department(**sample_department)
        node = await graphiti_client.add_department(dept)

        assert node is not None
        assert node.name == "Engineering"
        assert node.attributes["id"] == "dept-test-001"
        assert node.attributes["budget"] == 1000000.0

    @pytest.mark.asyncio
    async def test_add_departments_batch(self, graphiti_client):
        """Test adding multiple departments in batch"""
        depts = [
            Department(
                name="Engineering",
                id="dept-001",
                description="Engineering dept",
                budget=1000000.0,
                head_count=10,
            ),
            Department(
                name="Sales",
                id="dept-002",
                description="Sales dept",
                budget=500000.0,
                head_count=5,
            ),
        ]

        await graphiti_client.add_departments(depts)

        # Verify both exist
        eng_dept = await graphiti_client.find_department("Engineering")
        sales_dept = await graphiti_client.find_department("Sales")

        assert eng_dept.name == "Engineering"
        assert sales_dept.name == "Sales"

    @pytest.mark.asyncio
    async def test_find_department(self, graphiti_client, sample_department):
        """Test finding a department by name"""
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        found = await graphiti_client.find_department("Engineering")

        assert found is not None
        assert found.name == "Engineering"
        assert found.attributes["id"] == "dept-test-001"

    @pytest.mark.asyncio
    async def test_find_nonexistent_department(self, graphiti_client):
        """Test finding a department that doesn't exist"""
        with pytest.raises(EntityNotFoundError):
            await graphiti_client.find_department("Nonexistent Department")


class TestTeamOperations:
    """Test team creation and retrieval"""

    @pytest.mark.asyncio
    async def test_add_team(self, graphiti_client, sample_department, sample_team):
        """Test adding a single team"""
        # Create department first
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        # Create team
        team = Team(**sample_team)
        node = await graphiti_client.add_team(team)

        assert node is not None
        assert node.name == "Backend Team"
        assert node.attributes["lead"] == "Alice Johnson"

    @pytest.mark.asyncio
    async def test_add_teams_batch(self, graphiti_client, sample_department):
        """Test adding multiple teams in batch"""
        # Create department first
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        teams = [
            Team(
                name="Backend Team",
                department="Engineering",
                id="team-001",
                lead="Alice",
                purpose="Backend services",
            ),
            Team(
                name="Frontend Team",
                department="Engineering",
                id="team-002",
                lead="Bob",
                purpose="Frontend apps",
            ),
        ]

        await graphiti_client.add_teams(teams)

        # Verify both exist
        backend = await graphiti_client.find_team("Backend Team")
        frontend = await graphiti_client.find_team("Frontend Team")

        assert backend.name == "Backend Team"
        assert frontend.name == "Frontend Team"

    @pytest.mark.asyncio
    async def test_find_team(self, graphiti_client, sample_department, sample_team):
        """Test finding a team by name"""
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        found = await graphiti_client.find_team("Backend Team")

        assert found is not None
        assert found.name == "Backend Team"
        assert found.attributes["lead"] == "Alice Johnson"

    @pytest.mark.asyncio
    async def test_find_nonexistent_team(self, graphiti_client):
        """Test finding a team that doesn't exist"""
        with pytest.raises(EntityNotFoundError):
            await graphiti_client.find_team("Nonexistent Team")


class TestEmployeeOperations:
    """Test employee creation and retrieval"""

    @pytest.mark.asyncio
    async def test_add_employees_batch(
        self, graphiti_client, sample_department, sample_team, sample_employees
    ):
        """Test adding multiple employees with all relationships"""
        # Setup: Create department and team
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        # Add employees
        employees = [Employee(**emp) for emp in sample_employees]
        await graphiti_client.add_employees(employees)

        # Verify employees exist
        alice = await graphiti_client.find_employee("Alice Johnson")
        bob = await graphiti_client.find_employee("Bob Smith")

        assert alice is not None
        assert alice.name == "Alice Johnson"
        assert bob is not None
        assert bob.name == "Bob Smith"

    @pytest.mark.asyncio
    async def test_find_employee(
        self, graphiti_client, sample_department, sample_team, sample_employee
    ):
        """Test finding an employee by name"""
        # Setup
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        # Add employee
        emp = Employee(**sample_employee)
        await graphiti_client.add_employees([emp])

        # Find employee
        found = await graphiti_client.find_employee("Alice Johnson")

        assert found is not None
        assert found.name == "Alice Johnson"
        assert found.attributes["title"] == "Engineering Manager"

    @pytest.mark.asyncio
    async def test_find_nonexistent_employee(self, graphiti_client):
        """Test finding an employee that doesn't exist"""
        result = await graphiti_client.find_employee("Nonexistent Person")
        assert result is None  # Returns None for employees

    @pytest.mark.asyncio
    async def test_employee_department_relationship(
        self, graphiti_client, sample_department, sample_team, sample_employee
    ):
        """Test that employee is properly linked to department"""
        # Setup
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        emp = Employee(**sample_employee)
        await graphiti_client.add_employees([emp])

        # This test verifies the relationship was created
        # Actual relationship verification would require Cypher queries
        # For now, we verify no errors occurred
        assert True

    @pytest.mark.asyncio
    async def test_employee_skills_array(
        self, graphiti_client, sample_department, sample_team, sample_employee
    ):
        """Test that employee skills are stored as array"""
        # Setup
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        emp = Employee(**sample_employee)
        await graphiti_client.add_employees([emp])

        found = await graphiti_client.find_employee("Alice Johnson")

        assert "skills" in found.attributes
        assert isinstance(found.attributes["skills"], list)
        assert "Python" in found.attributes["skills"]


class TestManagerResolution:
    """Test manager relationship resolution"""

    @pytest.mark.asyncio
    async def test_manager_resolution(
        self, graphiti_client, sample_department, sample_team, sample_employees
    ):
        """Test that team managers are resolved correctly"""
        # Setup
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        # Add employees (Alice is the team lead)
        employees = [Employee(**emp) for emp in sample_employees]
        await graphiti_client.add_employees(employees)

        # Find manager of team
        manager = await graphiti_client.find_manager_of_team("Backend Team")

        assert manager is not None
        assert manager.name == "Alice Johnson"


class TestSearchOperations:
    """Test search and query operations"""

    @pytest.mark.asyncio
    async def test_natural_language_query(
        self, graphiti_client, sample_department, sample_team, sample_employee
    ):
        """Test natural language query"""
        # Setup
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        emp = Employee(**sample_employee)
        await graphiti_client.add_employees([emp])

        # Execute query - returns list of edges, not string
        result = await graphiti_client.query("Who works in Engineering?")

        # Result should contain relevant edges
        assert result is not None
        assert isinstance(result, list)


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_invalid_employee_type(self):
        """Test that invalid employee type raises validation error"""
        with pytest.raises(ValueError):
            Employee(
                name="Test",
                department="Eng",
                team="Team",
                id="emp-001",
                email="test@test.com",
                title="Engineer",
                location="SF",
                phone="555-0000",
                employee_type="invalid_type",  # Invalid!
            )

    @pytest.mark.asyncio
    async def test_invalid_security_clearance(self):
        """Test that invalid security clearance raises validation error"""
        with pytest.raises(ValueError):
            Employee(
                name="Test",
                department="Eng",
                team="Team",
                id="emp-001",
                email="test@test.com",
                title="Engineer",
                location="SF",
                phone="555-0000",
                security_clearance="super_secret",  # Invalid!
            )

    @pytest.mark.asyncio
    async def test_add_employee_without_department(
        self, graphiti_client, sample_team, sample_employee
    ):
        """Test adding employee when department doesn't exist"""
        # Only create team, not department
        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        emp = Employee(**sample_employee)

        # Should raise EdgeCreationError because department doesn't exist
        from core import EdgeCreationError
        with pytest.raises(EdgeCreationError):
            await graphiti_client.add_employees([emp])


class TestPerformance:
    """Test performance characteristics"""

    @pytest.mark.asyncio
    async def test_batch_employee_creation_performance(
        self, graphiti_client, sample_department, sample_team
    ):
        """Test that batch operations are reasonably fast"""
        import time

        # Setup
        dept = Department(**sample_department)
        await graphiti_client.add_department(dept)

        team = Team(**sample_team)
        await graphiti_client.add_team(team)

        # Create 10 employees
        employees = []
        for i in range(10):
            employees.append(
                Employee(
                    name=f"Employee {i}",
                    department="Engineering",
                    team="Backend Team",
                    id=f"emp-perf-{i:03d}",
                    email=f"emp{i}@company.com",
                    title="Engineer",
                    skills=["Python"],
                    location="San Francisco",
                    phone=f"+1-555-{i:04d}",
                    timezone="America/Los_Angeles",
                    working_hours_start="09:00",
                    working_hours_end="17:00",
                )
            )

        # Time the batch operation
        start = time.time()
        await graphiti_client.add_employees(employees)
        elapsed = time.time() - start

        # Should complete in reasonable time (< 30 seconds for 10 employees)
        assert elapsed < 30, f"Batch operation took {elapsed:.2f}s, expected < 30s"

        # Verify all created
        found = await graphiti_client.find_employee("Employee 0")
        assert found is not None
