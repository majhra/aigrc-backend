import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.modules.tests_store import AITestStore
from app.modules.executions_store import ExecutedTestStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.schemas import AITestCreate, User, ExecutedTestCreate, ConnectionConfig, ValidationConfig, ValidationCriterion, GroupCreate

from app.api import deps
from app.core.config import settings


class TestAIConnection:
    """Test AI connection functionality."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def setup_stores(self):
        """Set up test stores and data."""
        user_store = UserStore(LocalStore())
        group_store = GroupStore(LocalStore())
        test_store = AITestStore(LocalStore())
        execution_store = ExecutedTestStore(LocalStore())
        
        # Create test group
        group_data = GroupCreate(name="Test Group", description="Test group for AI connection tests")
        group = group_store.create(group_data, "system")
        
        # Create test user
        test_user = User(
            id=uuid4(),
            email="goricoaico+stores@gmail.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group=str(group.id)
        )
        user_store.create(test_user, str(group.id))
        
        # Override dependencies
        app.dependency_overrides[deps.get_user_store] = lambda: user_store
        app.dependency_overrides[deps.get_group_store] = lambda: group_store
        app.dependency_overrides[deps.get_test_store] = lambda: test_store
        app.dependency_overrides[deps.get_execution_store] = lambda: execution_store
        app.dependency_overrides[deps.get_current_active_user] = lambda: test_user
        
        yield {
            "user_store": user_store,
            "group_store": group_store,
            "test_store": test_store,
            "execution_store": execution_store,
            "test_user": test_user,
            "group": group
        }
        
        # Clean up
        app.dependency_overrides.clear()
    
    def test_test_connection_success(self, client, setup_stores):
        """Test successful connection test."""
        connection_config = {
            "endpoint": "https://api.galdren.com/v1/chat/completions",
            "auth_type": "API_KEY",
            "auth_string": "test-api-key",
            "timeout": 30
        }
        
        with patch('app.modules.ai_connection_service.AIConnectionService.test_connection') as mock_test:
            mock_test.return_value = True
            
            response = client.post(
                f"{settings.API_V1_STR}/tests/test-connection",
                json={"connection_config": connection_config}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is True
            assert "Connection test successful" in data["message"]
    
    def test_test_connection_failure(self, client, setup_stores):
        """Test failed connection test."""
        connection_config = {
            "endpoint": "https://api.galdren.com/v1/chat/completions",
            "auth_type": "API_KEY",
            "auth_string": "invalid-key",
            "timeout": 30
        }
        
        with patch('app.modules.ai_connection_service.AIConnectionService.test_connection') as mock_test:
            mock_test.return_value = False
            
            response = client.post(
                f"{settings.API_V1_STR}/tests/test-connection",
                json={"connection_config": connection_config}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "Connection test failed" in data["message"]
    
    def test_test_connection_ai_error(self, client, setup_stores):
        """Test connection test with AI connection error."""
        connection_config = {
            "endpoint": "https://api.galdren.com/v1/chat/completions",
            "auth_type": "API_KEY",
            "auth_string": "invalid-key",
            "timeout": 30
        }
        
        with patch('app.modules.ai_connection_service.AIConnectionService.test_connection') as mock_test:
            from app.modules.ai_connection_service import AIConnectionError
            mock_test.side_effect = AIConnectionError("Invalid API key")
            
            response = client.post(
                f"{settings.API_V1_STR}/tests/test-connection",
                json={"connection_config": connection_config}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["success"] is False
            assert "Invalid API key" in data["message"]
    
    def test_test_connection_unauthorized(self, client):
        """Test connection test without authentication."""
        # Remove auth override
        app.dependency_overrides = {}
        
        connection_config = {
            "endpoint": "https://api.galdren.com/v1/chat/completions",
            "auth_type": "API_KEY",
            "auth_string": "test-api-key",
            "timeout": 30
        }
        
        response = client.post(
            f"{settings.API_V1_STR}/tests/test-connection",
            json={"connection_config": connection_config}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_execute_test_with_ai_connection_success(self, client, setup_stores):
        """Test successful test execution with AI connection."""
        # Create a test with AI connection config
        test_data = AITestCreate(
            name="Test AI Response",
            description="Test the AI's response to a simple prompt",
            prompt_template="What is 2+2?",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.galdren.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="test-api-key",
                timeout=30
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="accuracy",
                        name="Accuracy Check",
                        description="Verify the answer is correct",
                        type="EXACT_MATCH",
                        parameters={"expected": "4"}
                    )
                ]
            ),
            tags=["math", "basic"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # Create the test
        create_response = client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data.model_dump()
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        test_id = create_response.json()["id"]
        
        # Mock the AI connection service
        with patch('app.modules.ai_connection_service.AIConnectionService.execute_prompt') as mock_execute:
            mock_execute.return_value = {
                "response": "The answer is 4.",
                "benchmarks": {
                    "response_time": 150,
                    "total_time": 200,
                    "token_usage": {
                        "prompt": 8,
                        "completion": 4,
                        "total": 12
                    }
                },
                "raw_response": {"choices": [{"message": {"content": "The answer is 4."}}]}
            }
            
            # Execute the test
            execution_data = ExecutedTestCreate(
                input_variables={"name": "John"},
                execution_environment={
                    "environment_id": "test-env",
                    "version": "1.0.0"
                }
            )
            
            response = client.post(
                f"{settings.API_V1_STR}/tests/{test_id}/execute",
                json=execution_data.model_dump()
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify response structure
            assert data["test_id"] == test_id
            assert data["prompt"] == "What is 2+2?"
            assert data["response"] == "The answer is 4."
            assert data["benchmarks"]["response_time"] == 150
            assert data["benchmarks"]["total_time"] == 200
            assert data["benchmarks"]["token_usage"]["prompt"] == 8
            assert data["benchmarks"]["token_usage"]["completion"] == 4
            assert data["benchmarks"]["token_usage"]["total"] == 12
            assert data["error"] is None
    
    def test_execute_test_with_ai_connection_error(self, client, setup_stores):
        """Test test execution with AI connection error."""
        # Create a test with AI connection config
        test_data = AITestCreate(
            name="Test AI Response",
            description="Test the AI's response to a simple prompt",
            prompt_template="What is 2+2?",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.galdren.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="invalid-key",
                timeout=30
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="accuracy",
                        name="Accuracy Check",
                        description="Verify the answer is correct",
                        type="EXACT_MATCH",
                        parameters={"expected": "4"}
                    )
                ]
            ),
            tags=["math", "basic"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # Create the test
        create_response = client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data.model_dump()
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        test_id = create_response.json()["id"]
        
        # Mock the AI connection service to raise an error
        with patch('app.modules.ai_connection_service.AIConnectionService.execute_prompt') as mock_execute:
            from app.modules.ai_connection_service import AIConnectionError
            mock_execute.side_effect = AIConnectionError("Invalid API key")
            
            # Execute the test
            execution_data = ExecutedTestCreate(
                input_variables={"name": "John"},
                execution_environment={
                    "environment_id": "test-env",
                    "version": "1.0.0"
                }
            )
            
            response = client.post(
                f"{settings.API_V1_STR}/tests/{test_id}/execute",
                json=execution_data.model_dump()
            )
            
            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            data = response.json()
            assert "AI endpoint connection failed" in data["detail"]
            assert "Invalid API key" in data["detail"]
    
    def test_execute_test_with_prompt_variables(self, client, setup_stores):
        """Test test execution with prompt variables."""
        # Create a test with prompt template containing variables
        test_data = AITestCreate(
            name="Test AI Response",
            description="Test the AI's response with variables",
            prompt_template="Hello {name}, what is {question}?",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.galdren.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="test-api-key",
                timeout=30
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="accuracy",
                        name="Accuracy Check",
                        description="Verify the answer is correct",
                        type="EXACT_MATCH",
                        parameters={"expected": "4"}
                    )
                ]
            ),
            tags=["math", "basic"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # Create the test
        create_response = client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data.model_dump()
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        test_id = create_response.json()["id"]
        
        # Mock the AI connection service
        with patch('app.modules.ai_connection_service.AIConnectionService.execute_prompt') as mock_execute:
            mock_execute.return_value = {
                "response": "The answer is 4.",
                "benchmarks": {
                    "response_time": 150,
                    "total_time": 200,
                    "token_usage": {
                        "prompt": 8,
                        "completion": 4,
                        "total": 12
                    }
                },
                "raw_response": {"choices": [{"message": {"content": "The answer is 4."}}]}
            }
            
            # Execute the test with input variables
            execution_data = ExecutedTestCreate(
                input_variables={
                    "name": "John",
                    "question": "2+2"
                },
                execution_environment={
                    "environment_id": "test-env",
                    "version": "1.0.0"
                }
            )
            
            response = client.post(
                f"{settings.API_V1_STR}/tests/{test_id}/execute",
                json=execution_data.model_dump()
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            
            # Verify that the prompt was formatted with variables
            assert data["prompt"] == "Hello John, what is 2+2?"
            assert data["response"] == "The answer is 4."
    
    def test_execute_test_missing_prompt_variables(self, client, setup_stores):
        """Test test execution with missing prompt variables."""
        # Create a test with prompt template containing variables
        test_data = AITestCreate(
            name="Test AI Response",
            description="Test the AI's response with variables",
            prompt_template="Hello {name}, what is {question}?",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.galdren.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="test-api-key",
                timeout=30
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="accuracy",
                        name="Accuracy Check",
                        description="Verify the answer is correct",
                        type="EXACT_MATCH",
                        parameters={"expected": "4"}
                    )
                ]
            ),
            tags=["math", "basic"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # Create the test
        create_response = client.post(
            f"{settings.API_V1_STR}/tests",
            json=test_data.model_dump()
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        test_id = create_response.json()["id"]
        
        # Mock the AI connection service to raise an error for missing variables
        with patch('app.modules.ai_connection_service.AIConnectionService.execute_prompt') as mock_execute:
            from app.modules.ai_connection_service import AIConnectionError
            mock_execute.side_effect = AIConnectionError("Missing required input variable: question")
            
            # Execute the test with missing variables
            execution_data = ExecutedTestCreate(
                input_variables={
                    "name": "John"
                    # Missing 'question' variable
                },
                execution_environment={
                    "environment_id": "test-env",
                    "version": "1.0.0"
                }
            )
            
            response = client.post(
                f"{settings.API_V1_STR}/tests/{test_id}/execute",
                json=execution_data.model_dump()
            )
            
            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            data = response.json()
            assert "Missing required input variable" in data["detail"] 