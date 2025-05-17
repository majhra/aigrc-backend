import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.modules.tests_store import MyTestStore
from app.modules.executions_store import ExecutedTestStore
from app.schemas import MyTestCreate, User, ExecutedTestCreate

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
        status="ACTIVE"
    )

    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.test_store = MyTestStore()
        self.execution_store = ExecutedTestStore()
        #self.test_store.clear()  # Clear any existing tests

        # Override both the current user dependency and the test store dependency
        self.client.app.dependency_overrides[deps.get_current_active_user] = lambda: self.TEST_USER
        self.client.app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        self.client.app.dependency_overrides[deps.get_execution_store] = lambda: self.execution_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        self.test_store.clear()
        self.execution_store.clear()

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
        assert data["status"] == "ACTIVE"

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

    @pytest.mark.skip(reason="This test fails because the search is not implemented")
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

    def test_execute_test_success(self):
        """Test successful test execution"""
        # First create a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        # Execute the test
        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"},
            execution_environment={
                "environment_id": "test-env",
                "version": "1.0.0"
            }
        )
        
        response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Verify response structure
        assert UUID(data["id"])  # Valid UUID
        assert data["test_id"] == test_id
        assert data["executed_by"] == str(self.TEST_USER.id)
        assert data["validation_status"] == "PENDING"
        assert data["prompt"] == self.TEST_DATA.prompt_template
        assert data["response"] == "This is a mock response. AI endpoint integration pending."
        assert data["benchmarks"] is not None
        assert data["benchmarks"]["response_time"] == 100
        assert data["benchmarks"]["total_time"] == 150
        assert data["benchmarks"]["token_usage"]["prompt"] == 10
        assert data["benchmarks"]["token_usage"]["completion"] == 5
        assert data["benchmarks"]["token_usage"]["total"] == 15
        assert data["error"] is None
        assert len(data["validations"]) == 0

    def test_execute_test_not_found(self):
        """Test executing a non-existent test"""
        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        response = self.client.post(
            f"{settings.API_V1_STR}/tests/{uuid4()}/execute",
            json=execution_data.model_dump()
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Test not found"

    def test_execute_inactive_test(self):
        """Test executing an inactive test"""
        # Create a test with DRAFT status
        test_data = self.TEST_DATA.model_dump()
        test_data["status"] = "DRAFT"
        
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data
        )
        test_id = create_response.json()["id"]

        # Try to execute the test
        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Cannot execute test that is not active"

    @pytest.mark.skip(reason="Prompts do not handle variables, yet.")
    def test_execute_test_missing_variable(self):
        """Test executing a test with missing required variables"""
        # Create a test with a template requiring variables
        test_data = self.TEST_DATA.model_dump()
        test_data["prompt_template"] = "Hello {name}, how are you {time}?"
        
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data
        )
        test_id = create_response.json()["id"]

        # Try to execute with missing variable
        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}  # Missing 'time' variable
        )
        
        response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing required input variable" in response.json()["detail"]

    def test_execute_test_unauthorized(self):
        """Test executing a test without authentication"""
        # First create a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        # Remove auth override
        self.client.app.dependency_overrides = {}
        
        # Try to execute without auth
        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_execute_test_with_validation(self):
        """Test executing a test and adding validation"""
        # First create and execute a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Add validation
        validation = {
            "validator_id": str(self.TEST_USER.id),
            "validator_type": "HUMAN",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "PASS",
            "response": "This is a mock response.",
            "notes": "Overall good response",
            "confidence": 1.0
        }

        # Use the same execution store instance that was used for creation
        updated_execution = self.execution_store.add_validation(execution_id, validation)
        assert updated_execution is not None
        assert updated_execution.validation_status == "VALIDATED"
        assert len(updated_execution.validations) == 1
        assert updated_execution.validations[0].status == "PASS"
        assert updated_execution.validations[0].validator_id == self.TEST_USER.id

    def test_validate_execution_success(self):
        """Test successful validation submission"""
        # First create and execute a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Submit validation
        validation_data = {
            "validator_id": str(self.TEST_USER.id),
            "validator_type": "HUMAN",
            "status": "PASS",
            "response": "This is a mock response.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": "Overall good response",
            "confidence": 1.0
        }

        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{test_id}/{execution_id}/validate",
            json=validation_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify validation was added
        assert data["validation_status"] == "VALIDATED"
        assert len(data["validations"]) == 1
        validation = data["validations"][0]
        assert validation["validator_id"] == str(self.TEST_USER.id)
        assert validation["validator_type"] == "HUMAN"
        assert validation["status"] == "PASS"
        #assert validation["criteria_results"][0]["criterion_id"] == "accuracy"
        #assert validation["criteria_results"][0]["result"] is True
        assert validation["notes"] == "Overall good response"
        assert validation["confidence"] == 1.0

    def test_validate_execution_not_found(self):
        """Test validation for non-existent execution"""
        # Create a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        validation_data = {
            "validator_id": str(self.TEST_USER.id),
            "validator_type": "HUMAN",
            "status": "PASS",
            "response": "This is a mock response.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        fake_execution_id = uuid4()

        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{test_id}/{fake_execution_id}/validate",
            json=validation_data
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Execution not found"

    def test_validate_execution_wrong_test(self):
        """Test validation for execution from different test"""
        # Create two tests
        create_response1 = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id1 = create_response1.json()["id"]

        test_data2 = self.TEST_DATA.model_dump()
        test_data2["name"] = "Test 2"
        create_response2 = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data2
        )
        test_id2 = create_response2.json()["id"]

        # Execute test 1
        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id1}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Try to validate using test 2's ID
        validation_data = {
            "validator_id": str(self.TEST_USER.id),
            "validator_type": "HUMAN",
            "status": "PASS",
            "response": "This is a mock response.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{test_id2}/{execution_id}/validate",
            json=validation_data
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Execution does not belong to the specified test"

    def test_validate_execution_unauthorized(self):
        """Test validation without authentication"""
        # Create and execute a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Remove auth override
        self.client.app.dependency_overrides = {}
        
        validation_data = {
            "validator_id": str(self.TEST_USER.id),
            "validator_type": "HUMAN",
            "status": "PASS",
            "response": "This is a mock response.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{test_id}/{execution_id}/validate",
            json=validation_data
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(reason="Not implemented user checks")
    def test_validate_execution_wrong_validator(self):
        """Test validation with wrong validator ID"""
        # Create and execute a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Try to validate with different validator ID
        validation_data = {
            "validator_id": str(uuid4()),  # Different UUID
            "validator_type": "HUMAN",
            "status": "PASS",
            "response": "This is a mock response.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        response = self.client.put(
            f"{settings.API_V1_STR}/tests/{test_id}/{execution_id}/validate",
            json=validation_data
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.json()["detail"] == "Cannot submit validation for another user"

    def test_get_test_execution_success(self):
        """Test successful retrieval of test execution details"""
        # First create and execute a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Add a validation to make sure it's included in the response
        validation_data = {
            "validator_id": str(self.TEST_USER.id),
            "validator_type": "HUMAN",
            "status": "PASS",
            "response": "This is a mock response.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "notes": "Overall good response",
            "confidence": 1.0
        }
        self.execution_store.add_validation(execution_id, validation_data)

        # Get the test execution details
        response = self.client.get(
            f"{settings.API_V1_STR}/tests/{test_id}/{execution_id}"
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify test details
        assert data["test"]["id"] == test_id
        assert data["test"]["name"] == self.TEST_DATA.name
        assert data["test"]["description"] == self.TEST_DATA.description
        
        # Verify execution details
        assert data["execution"]["id"] == execution_id
        assert data["execution"]["test_id"] == test_id
        assert data["execution"]["executed_by"] == str(self.TEST_USER.id)
        assert data["execution"]["validation_status"] == "VALIDATED"
        
        # Verify validation details
        assert len(data["execution"]["validations"]) == 1
        validation = data["execution"]["validations"][0]
        assert validation["validator_id"] == str(self.TEST_USER.id)
        assert validation["validator_type"] == "HUMAN"
        assert validation["status"] == "PASS"
        assert validation["notes"] == "Overall good response"
        assert validation["confidence"] == 1.0

    def test_get_test_execution_not_found(self):
        """Test retrieval of non-existent test execution"""
        # Create a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        # Try to get non-existent execution
        non_existent_execution_id = str(uuid4())
        response = self.client.get(
            f"{settings.API_V1_STR}/tests/{test_id}/{non_existent_execution_id}"
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Execution not found"

    def test_get_test_execution_wrong_test(self):
        """Test retrieval of execution from different test"""
        # Create two tests
        create_response1 = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id1 = create_response1.json()["id"]

        test_data2 = self.TEST_DATA.model_dump()
        test_data2["name"] = "Test 2"
        create_response2 = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data2
        )
        test_id2 = create_response2.json()["id"]

        # Execute test 1
        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id1}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Try to get execution using test 2's ID
        response = self.client.get(
            f"{settings.API_V1_STR}/tests/{test_id2}/{execution_id}"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Execution does not belong to the specified test"

    def test_get_test_execution_test_not_found(self):
        """Test retrieval of execution with non-existent test"""
        # Create and execute a test
        create_response = self.client.post(
            f"{settings.API_V1_STR}/tests",
            json=self.TEST_DATA.model_dump()
        )
        test_id = create_response.json()["id"]

        execution_data = ExecutedTestCreate(
            input_variables={"name": "John"}
        )
        
        execute_response = self.client.post(
            f"{settings.API_V1_STR}/tests/{test_id}/execute",
            json=execution_data.model_dump()
        )
        execution_id = execute_response.json()["id"]

        # Try to get execution with non-existent test
        non_existent_test_id = str(uuid4())
        response = self.client.get(
            f"{settings.API_V1_STR}/tests/{non_existent_test_id}/{execution_id}"
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Test not found"