import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.modules.tests_store import AITestStore
from app.modules.executions_store import ExecutedTestStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.schemas import (
    AITestCreate, User, ExecutedTestCreate, ConnectionConfig, ValidationConfig, ValidationCriterion,
    ExecutionEnvironment, PerformanceMetrics, TokenUsage, GroupCreate
)

from app.api import deps
from app.core.config import settings


class TestReports:
    # Test data
    TEST_DATA = AITestCreate(
        name="Test AI Response",
        description="Test the AI's response to a simple prompt",
        prompt_template="What is 2+2?",
        interface_type="DIRECT_LLM",
        connection_config=ConnectionConfig(
            endpoint="https://api.openai.com/v1/chat/completions",
            auth_type="API_KEY",
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

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def test_user(self):
        return User(
            id=str(uuid4()),
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )

    @pytest.fixture
    def authenticated_headers(self, test_user):
        # Mock the authentication dependency
        def mock_get_current_active_user():
            return test_user
        
        # Create a shared LocalStore instance for all stores
        from app.modules.reports_store import ReportsStore
        from app.modules.tests_store import AITestStore
        from app.modules.executions_store import ExecutedTestStore
        from app.modules.store_interface import LocalStore
        
        # Create a single shared store instance
        shared_store = LocalStore()
        
        def mock_get_reports_store():
            tests_store = AITestStore(shared_store)
            executions_store = ExecutedTestStore(shared_store)
            return ReportsStore(tests_store, executions_store, shared_store)
        
        def mock_get_test_store():
            return AITestStore(shared_store)
        
        def mock_get_execution_store():
            return ExecutedTestStore(shared_store)
        
        app.dependency_overrides[deps.get_current_active_user] = mock_get_current_active_user
        app.dependency_overrides[deps.get_reports_store] = mock_get_reports_store
        app.dependency_overrides[deps.get_test_store] = mock_get_test_store
        app.dependency_overrides[deps.get_execution_store] = mock_get_execution_store
        return {"Authorization": "Bearer test-token"}

    def test_get_summary_report_success(self, client, authenticated_headers, test_user):
        """Test successful summary report retrieval."""
        response = client.get(f"{settings.API_V1_STR}/reports/summary", headers=authenticated_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "test_metrics" in data
        assert "execution_metrics" in data
        assert "generated_at" in data
        
        # Verify test metrics structure
        test_metrics = data["test_metrics"]
        assert "total_tests" in test_metrics
        assert "active_tests" in test_metrics
        assert "draft_tests" in test_metrics
        assert "archived_tests" in test_metrics
        assert "high_risk_tests" in test_metrics
        assert "medium_risk_tests" in test_metrics
        assert "low_risk_tests" in test_metrics
        
        # Verify execution metrics structure
        execution_metrics = data["execution_metrics"]
        assert "total_executions" in execution_metrics
        assert "pending_validations" in execution_metrics
        assert "validated_executions" in execution_metrics
        assert "acceptance_rate" in execution_metrics
        assert "executions_last_7_days" in execution_metrics
        assert "executions_last_30_days" in execution_metrics

    def test_get_execution_trends_success(self, client, authenticated_headers, test_user):
        """Test successful execution trends retrieval."""
        response = client.get(f"{settings.API_V1_STR}/reports/trends", headers=authenticated_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "trends" in data
        assert "period_days" in data
        assert "generated_at" in data
        
        # Verify trends structure
        trends = data["trends"]
        assert isinstance(trends, list)
        assert len(trends) == 30  # Default 30 days
        
        if trends:
            trend = trends[0]
            assert "date" in trend
            assert "executions" in trend
            assert "validations" in trend
            assert "passed" in trend

    def test_get_execution_trends_with_custom_days(self, client, authenticated_headers, test_user):
        """Test execution trends with custom number of days."""
        response = client.get(
            f"{settings.API_V1_STR}/reports/trends?days=7",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["period_days"] == 7
        assert len(data["trends"]) == 7

    def test_get_execution_trends_invalid_days(self, client, authenticated_headers, test_user):
        """Test execution trends with invalid days parameter."""
        response = client.get(
            f"{settings.API_V1_STR}/reports/trends?days=0",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_performance_report_success(self, client, authenticated_headers, test_user):
        """Test successful performance report retrieval."""
        response = client.get(f"{settings.API_V1_STR}/reports/performance", headers=authenticated_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "performance_metrics" in data
        assert "generated_at" in data
        
        # Verify performance metrics structure
        performance_metrics = data["performance_metrics"]
        assert isinstance(performance_metrics, list)
        
        if performance_metrics:
            metric = performance_metrics[0]
            assert "test_id" in metric
            assert "test_name" in metric
            assert "total_executions" in metric
            assert "success_rate" in metric
            assert "avg_response_time" in metric
            assert "avg_cost" in metric
            assert "last_executed" in metric

    def test_reports_endpoints_require_authentication(self, client):
        """Test that reports endpoints require authentication."""
        endpoints = [
            f"{settings.API_V1_STR}/reports/summary",
            f"{settings.API_V1_STR}/reports/trends",
            f"{settings.API_V1_STR}/reports/performance"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_individual_test_trends_success(self, client, authenticated_headers, test_user):
        """Test successful individual test trends retrieval."""
        # Create a test first
        test_data = self.TEST_DATA
        test_response = client.post(
            f"{settings.API_V1_STR}/tests/",
            json=test_data.model_dump(),
            headers=authenticated_headers
        )
        assert test_response.status_code == status.HTTP_201_CREATED
        test_id = test_response.json()["id"]
        
        # Test individual trends endpoint
        response = client.get(
            f"{settings.API_V1_STR}/reports/trends/{test_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "test_id" in data
        assert "test_name" in data
        assert "trends" in data
        assert "period_days" in data
        assert "generated_at" in data
        
        # Verify test-specific data
        assert data["test_id"] == test_id
        assert data["test_name"] == test_data.name
        assert data["period_days"] == 30  # Default
        
        # Verify trends structure
        trends = data["trends"]
        assert isinstance(trends, list)
        assert len(trends) == 30  # Default 30 days
        
        if trends:
            trend = trends[0]
            assert "date" in trend
            assert "executions" in trend
            assert "validations" in trend
            assert "passed" in trend

    def test_get_individual_test_trends_with_custom_days(self, client, authenticated_headers, test_user):
        """Test individual test trends with custom number of days."""
        # Create a test first
        test_data = self.TEST_DATA
        test_response = client.post(
            f"{settings.API_V1_STR}/tests/",
            json=test_data.model_dump(),
            headers=authenticated_headers
        )
        assert test_response.status_code == status.HTTP_201_CREATED
        test_id = test_response.json()["id"]
        
        # Test with custom days
        response = client.get(
            f"{settings.API_V1_STR}/reports/trends/{test_id}?days=7",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["period_days"] == 7
        assert len(data["trends"]) == 7

    def test_get_individual_test_trends_invalid_days(self, client, authenticated_headers, test_user):
        """Test individual test trends with invalid days parameter."""
        # Create a test first
        test_data = self.TEST_DATA
        test_response = client.post(
            f"{settings.API_V1_STR}/tests/",
            json=test_data.model_dump(),
            headers=authenticated_headers
        )
        assert test_response.status_code == status.HTTP_201_CREATED
        test_id = test_response.json()["id"]
        
        # Test with invalid days
        response = client.get(
            f"{settings.API_V1_STR}/reports/trends/{test_id}?days=0",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_individual_test_trends_test_not_found(self, client, authenticated_headers, test_user):
        """Test individual test trends with non-existent test ID."""
        non_existent_test_id = str(uuid4())
        
        response = client.get(
            f"{settings.API_V1_STR}/reports/trends/{non_existent_test_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in response.json()["detail"].lower()

    def test_get_individual_test_performance_success(self, client, authenticated_headers, test_user):
        """Test successful individual test performance retrieval."""
        # Create a test first
        test_data = self.TEST_DATA
        test_response = client.post(
            f"{settings.API_V1_STR}/tests/",
            json=test_data.model_dump(),
            headers=authenticated_headers
        )
        assert test_response.status_code == status.HTTP_201_CREATED
        test_id = test_response.json()["id"]
        
        # Test individual performance endpoint
        response = client.get(
            f"{settings.API_V1_STR}/reports/performance/{test_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "test_id" in data
        assert "test_name" in data
        assert "performance_metrics" in data
        assert "generated_at" in data
        
        # Verify test-specific data
        assert data["test_id"] == test_id
        assert data["test_name"] == test_data.name
        
        # Verify performance metrics structure
        performance_metrics = data["performance_metrics"]
        assert "test_id" in performance_metrics
        assert "test_name" in performance_metrics
        assert "total_executions" in performance_metrics
        assert "success_rate" in performance_metrics
        assert "avg_response_time" in performance_metrics
        assert "avg_cost" in performance_metrics
        assert "last_executed" in performance_metrics

    def test_get_individual_test_performance_test_not_found(self, client, authenticated_headers, test_user):
        """Test individual test performance with non-existent test ID."""
        non_existent_test_id = str(uuid4())
        
        response = client.get(
            f"{settings.API_V1_STR}/reports/performance/{non_existent_test_id}",
            headers=authenticated_headers
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in response.json()["detail"].lower()

    def test_individual_test_endpoints_require_authentication(self, client):
        """Test that individual test endpoints require authentication."""
        test_id = str(uuid4())
        endpoints = [
            f"{settings.API_V1_STR}/reports/trends/{test_id}",
            f"{settings.API_V1_STR}/reports/performance/{test_id}"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_reports_endpoints_accept_query_parameters(self, client, authenticated_headers, test_user):
        """Test that reports endpoints properly handle query parameters."""
        # Test trends endpoint with days parameter
        response = client.get(
            f"{settings.API_V1_STR}/reports/trends?days=14",
            headers=authenticated_headers
        )
        assert response.status_code == status.HTTP_200_OK 