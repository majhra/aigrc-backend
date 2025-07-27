"""
Setup Verification Tests

Simple tests to verify that the production integration test setup
is working correctly before running the full test suite.
"""
import pytest

from utils.api_client import ProductionAPIClient
from utils.test_data_factory import TestDataFactory


class TestSetupVerification:
    """Verify that the test setup is working correctly"""
    
    def test_imports_work(self):
        """Test that all imports are working correctly"""
        # If we get here, all imports worked
        assert True
    
    def test_api_client_creation(self):
        """Test that API client can be created"""
        client = ProductionAPIClient()
        assert client is not None
        assert client.base_url is not None
        assert client.api_base is not None
    
    def test_data_factory_creation(self):
        """Test that data factory can be created"""
        factory = TestDataFactory()
        assert factory is not None
        
        # Test creating sample data
        user = factory.create_regular_user()
        assert user.email is not None
        assert user.password is not None
        assert user.full_name is not None
    
    def test_backend_connectivity(self, api_client: ProductionAPIClient):
        """Test that we can connect to the backend"""
        # This will be automatically checked by the api_client fixture
        # If we get here, the backend is accessible
        assert api_client.health_check()
    
    @pytest.mark.skip(reason="Optional test for backend API docs")
    def test_backend_api_docs_accessible(self, api_client: ProductionAPIClient):
        """Test that backend API documentation is accessible"""
        import requests
        
        try:
            docs_url = f"{api_client.base_url}/docs"
            response = requests.get(docs_url, timeout=10)
            assert response.status_code == 200
        except requests.exceptions.RequestException:
            pytest.skip("Backend API docs not accessible")
    
    def test_basic_public_endpoint(self, clean_api_client: ProductionAPIClient):
        """Test access to a basic public endpoint"""
        # Try to access the models endpoint (should be public)
        response = clean_api_client.get("/simulation/v1/models")
        
        # Should not require authentication (might return empty list, but not 401)
        assert response.status_code != 401, "Public endpoint should not require authentication"
        
        # Should return some response (200 or other valid status)
        assert response.status_code in [200, 404, 405, 422], f"Unexpected status: {response.status_code}"
    
    def test_protected_endpoint_requires_auth(self, clean_api_client: ProductionAPIClient):
        """Test that a protected endpoint requires authentication"""
        response = clean_api_client.get("/user/me")
        
        # Should require authentication
        assert response.status_code == 401, f"Protected endpoint should require auth, got {response.status_code}"
    
    def test_data_factory_scenarios(self, data_factory: TestDataFactory):
        """Test that data factory can create various scenarios"""
        
        # Test user creation
        admin = data_factory.create_admin_user()
        user = data_factory.create_regular_user()
        
        assert admin.role == "admin"
        assert user.role == "user"
        assert admin.email != user.email
        
        # Test other data creation
        category = data_factory.create_prompt_category()
        prompt = data_factory.create_prompt()
        config = data_factory.create_ai_configuration()
        test = data_factory.create_ai_test()
        
        assert category.name is not None
        assert prompt.template is not None
        assert config.endpoint is not None
        assert test.prompt_template is not None
    
    def test_performance_monitoring(self, performance_monitor):
        """Test that performance monitoring works"""
        
        # Create a mock response to test monitoring
        from utils.api_client import APIResponse
        
        mock_response = APIResponse(
            status_code=200,
            data={"test": "data"},
            headers={"Content-Type": "application/json"},
            response_time=0.5,
            raw_response=None
        )
        
        performance_monitor.record(mock_response)
        stats = performance_monitor.stats()
        
        assert stats["total_requests"] == 1
        assert stats["avg_response_time"] == 0.5
        assert stats["error_rate"] == 0.0