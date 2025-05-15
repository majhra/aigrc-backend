import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.modules.tests_store import MyTestStore
from app.schemas import MyTestCreate, User

from app.api import deps
from app.core.config import settings


class TestTests:
    # Test data
    TEST_USER = User(
        id=uuid4(),
        email="test@example.com",
        is_active=True,
        is_superuser=False
    )

    TEST_DATA = MyTestCreate(
        name="Test AI Response",
        description="Test the AI's response to a simple prompt",
        prompt_template="What is 2+2?",
        interface_type="DIRECT_LLM",
        connection_config={
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "auth_type": "API_KEY",
            "timeout": 30
        },
        validation_config={
            "validator_type": "HUMAN",
            "validation_criteria": [
                {
                    "id": "accuracy",
                    "name": "Accuracy Check",
                    "description": "Verify the answer is correct",
                    "type": "EXACT_MATCH",
                    "parameters": {"expected": "4"}
                }
            ]
        },
        tags=["math", "basic"],
        risk_level="LOW",
        status="DRAFT"
    )

    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.test_store = MyTestStore()
        #self.test_store.clear()  # Clear any existing tests

        # Override both the current user dependency and the test store dependency
        self.client.app.dependency_overrides[deps.get_current_active_user] = lambda: self.TEST_USER
        self.client.app.dependency_overrides[deps.get_test_store] = lambda: self.test_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        self.test_store.clear()

    def test_create_test(self):
        """Test creating a new test"""
        response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == self.TEST_DATA.name
        assert data["description"] == self.TEST_DATA.description
        assert UUID(data["id"])  # Verify it's a valid UUID
        assert data["created_by"] == str(self.TEST_USER.id)
        assert data["status"] == "DRAFT"

    def test_create_test_unauthorized(self):
        """Test creating a test without auth"""
        self.client.app.dependency_overrides = {}
        response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_test(self):
        """Test getting a specific test"""
        # First create a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        # Then get it
        response = self.client.get(f"{settings.API_V1_STR}/tests/{test_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_id
        assert data["name"] == self.TEST_DATA.name

    def test_get_test_not_found(self):
        """Test getting a non-existent test"""
        response = self.client.get(f"{settings.API_V1_STR}/tests/{uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Test not found"

    def test_get_test_unauthorized(self):
        """Test getting a test without auth"""
        self.client.app.dependency_overrides = {}
        response = self.client.get(f"{settings.API_V1_STR}/tests/{uuid4()}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_tests(self):
        """Test listing all tests"""
        # Create multiple tests
        for i in range(3):
            test_data = self.TEST_DATA.model_dump()
            test_data["name"] = f"Test {i}"
            self.client.post(f"{settings.API_V1_STR}/tests", json=test_data)
        
        response = self.client.get(f"{settings.API_V1_STR}/tests")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["limit"] == 10

    def test_list_tests_with_filters(self):
        """Test listing tests with filters"""
        # Create tests with different statuses
        test_data = self.TEST_DATA.model_dump()
        test_data["status"] = "DRAFT"
        self.client.post(f"{settings.API_V1_STR}/tests", json=test_data)
        
        test_data["status"] = "ACTIVE"
        self.client.post(f"{settings.API_V1_STR}/tests", json=test_data)
        
        response = self.client.get(f"{settings.API_V1_STR}/tests?status=ACTIVE")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "ACTIVE"

    def test_update_test(self):
        """Test updating a test"""
        # First create a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]
        
        # Update it
        update_data = self.TEST_DATA.model_dump()
        update_data["name"] = "Updated Test Name"
        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{test_id}",
            json=update_data
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Test Name"
        assert data["id"] == test_id

    def test_update_test_not_found(self):
        """Test updating a non-existent test"""
        update_data = self.TEST_DATA.model_dump()
        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{uuid4()}",
            json=update_data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Test not found"

    def test_update_test_unauthorized(self):
        """Test updating a test without auth"""
        self.client.app.dependency_overrides = {}
        update_data = self.TEST_DATA.model_dump()
        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{uuid4()}",
            json=update_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_test(self):
        """Test deleting a test"""
        # First create a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]
        
        # Delete it
        response = self.client.delete(f"{settings.API_V1_STR}/tests/{test_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's gone
        get_response = self.client.get(f"{settings.API_V1_STR}/tests/{test_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_test_not_found(self):
        """Test deleting a non-existent test"""
        response = self.client.delete(f"{settings.API_V1_STR}/tests/{uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Test not found"

    def test_delete_test_unauthorized(self):
        """Test deleting a test without auth"""
        self.client.app.dependency_overrides = {}
        response = self.client.delete(f"{settings.API_V1_STR}/tests/{uuid4()}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_tests_pagination(self):
        """Test test listing pagination"""
        # Create 15 tests
        for i in range(15):
            test_data = self.TEST_DATA.model_dump()
            test_data["name"] = f"Test {i}"
            self.client.post(f"{settings.API_V1_STR}/tests", json=test_data)
        
        # Test first page
        response = self.client.get(f"{settings.API_V1_STR}/tests?page=1&limit=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 10
        assert data["total"] == 15
        assert data["page"] == 1
        assert data["limit"] == 10
        
        # Test second page
        response = self.client.get(f"{settings.API_V1_STR}/tests?page=2&limit=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 5
        assert data["total"] == 15
        assert data["page"] == 2
        assert data["limit"] == 10

    def test_list_tests_search(self):
        """Test test listing search functionality"""
        # Create tests with different names
        test_data = self.TEST_DATA.model_dump()
        test_data["name"] = "Math Test"
        self.client.post(f"{settings.API_V1_STR}/tests", json=test_data)
        
        test_data["name"] = "Science Test"
        self.client.post(f"{settings.API_V1_STR}/tests", json=test_data)
        
        # Search for "math"
        response = self.client.get(f"{settings.API_V1_STR}/tests?search=math")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["name"] == "Math Test"

    def test_create_test_validation(self):
        """Test test creation validation"""
        # Test with invalid status
        invalid_data = {
            "name": "Invalid Test",
            "description": "Test with invalid status",
            "prompt_template": "Test",
            "interface_type": "DIRECT_LLM",
            "connection_config": {
                "endpoint": "https://api.example.com",
                "auth_type": "API_KEY"
            },
            "validation_config": {
                "validator_type": "HUMAN",
                "validation_criteria": []
            },
            "tags": [],
            "risk_level": "LOW",
            "status": "INVALID_STATUS"  # Invalid status
        }
        
        response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=invalid_data
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY 