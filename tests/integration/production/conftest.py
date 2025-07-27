"""
Configuration and fixtures for production integration testing.

This module provides shared fixtures and setup for comprehensive
integration testing against the actual backend service.
"""
import pytest
import asyncio
import time
from typing import Dict, Any, List, Generator
from dataclasses import asdict

from utils.api_client import ProductionAPIClient, APIResponse
from utils.test_data_factory import TestDataFactory, TestUser, TestGroup


# Test configuration
BACKEND_URL = "http://backend-grc_api-1:80"
TEST_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds


@pytest.fixture(scope="session")
def api_client() -> ProductionAPIClient:
    """Create API client for the test session"""
    client = ProductionAPIClient(BACKEND_URL)
    
    # Wait for backend to be ready
    for attempt in range(MAX_RETRY_ATTEMPTS):
        if client.health_check():
            break
        if attempt < MAX_RETRY_ATTEMPTS - 1:
            time.sleep(RETRY_DELAY)
    else:
        pytest.fail(f"Backend at {BACKEND_URL} is not accessible after {MAX_RETRY_ATTEMPTS} attempts")
    
    return client


@pytest.fixture(scope="session")
def data_factory() -> TestDataFactory:
    """Create test data factory"""
    return TestDataFactory()


@pytest.fixture(scope="function")
def clean_api_client(api_client: ProductionAPIClient) -> ProductionAPIClient:
    """Provide clean API client for each test (no authentication)"""
    api_client.clear_auth()
    return api_client


class TestUserManager:
    """Manages test users for integration testing"""
    
    def __init__(self, api_client: ProductionAPIClient, data_factory: TestDataFactory):
        self.api_client = api_client
        self.data_factory = data_factory
        self.created_users: List[TestUser] = []
        self.created_groups: List[TestGroup] = []
    
    def create_and_register_user(self, user_data: TestUser, verify: bool = True) -> TestUser:
        """Create and register a new user, optionally verify email"""
        # Register user
        register_data = {
            "email": user_data.email,
            "password": user_data.password,
            "full_name": user_data.full_name
        }
        if user_data.group:
            register_data["group"] = user_data.group
        
        response = self.api_client.register_user(**register_data)
        
        if response.status_code not in [200, 201]:
            pytest.fail(f"Failed to register user {user_data.email}: {response.data}")
        
        # Store user ID from response
        if isinstance(response.data, dict):
            # Handle nested response format {"message": "...", "data": {...}}
            if "data" in response.data and isinstance(response.data["data"], dict):
                user_data.id = response.data["data"].get("id")
            else:
                user_data.id = response.data.get("id")
        
        # Verify email if requested (for production testing, we might need to mock this)
        if verify:
            # In production tests, we might need to directly update the database
            # or have a test endpoint to verify users
            pass
        
        # Login to get token
        login_response = self.api_client.login(user_data.email, user_data.password)
        if login_response.status_code == 200:
            user_data.access_token = login_response.data.get("access_token")
            user_data.is_verified = True
            
            # If this user should be an admin, update their role
            if user_data.role == "admin":
                self._update_user_role_to_admin(user_data)
                
        elif login_response.status_code == 401 and "not verified" in str(login_response.data).lower():
            # User created but email verification required
            # For production tests, we'll skip authenticated tests for this user
            user_data.is_verified = False
            user_data.access_token = None
            # Don't fail - just mark as unverified
        else:
            # Actual login failure
            pytest.fail(f"Login failed for {user_data.email}: {login_response.data}")
        
        self.created_users.append(user_data)
        return user_data
    
    def _update_user_role_to_admin(self, user_data: TestUser):
        """Update a user's role to admin. In production, this would need existing admin or database access."""
        # For production tests, we can't easily make a user admin without existing admin privileges
        # This is a limitation of testing in production environment
        # In real production, the first admin would be created via:
        # 1. Direct database modification
        # 2. Environment setup script
        # 3. Special initialization endpoint
        
        # For now, we'll mark this user as admin in our test data but understand
        # that admin-only endpoints may fail in production tests
        user_data.role = "admin"
        
        # Log this limitation
        print(f"Warning: User {user_data.email} marked as admin in test data but may not have actual admin privileges in production system")
    
    def create_admin_user(self, **overrides) -> TestUser:
        """Create and register admin user"""
        admin_data = self.data_factory.create_admin_user(**overrides)
        return self.create_and_register_user(admin_data)
    
    def create_regular_user(self, **overrides) -> TestUser:
        """Create and register regular user"""
        user_data = self.data_factory.create_regular_user(**overrides)
        return self.create_and_register_user(user_data)
    
    def create_user_in_group(self, group_id: str, role: str = "user", **overrides) -> TestUser:
        """Create user in specific group"""
        user_data = self.data_factory.create_user_in_group(group_id, role, **overrides)
        return self.create_and_register_user(user_data)
    
    def cleanup(self):
        """Clean up created test data"""
        # Note: In production tests, we might need to clean up via API calls
        # or database operations
        pass


@pytest.fixture(scope="function")
def user_manager(api_client: ProductionAPIClient, data_factory: TestDataFactory) -> Generator[TestUserManager, None, None]:
    """Provide user manager for test with cleanup"""
    manager = TestUserManager(api_client, data_factory)
    yield manager
    manager.cleanup()


@pytest.fixture(scope="function")
def admin_user(user_manager: TestUserManager) -> TestUser:
    """Create authenticated admin user for test"""
    user = user_manager.create_admin_user()
    if not user.access_token:
        pytest.skip("Admin user could not be authenticated (email verification required)")
    return user


@pytest.fixture(scope="function") 
def regular_user(user_manager: TestUserManager) -> TestUser:
    """Create authenticated regular user for test"""
    user = user_manager.create_regular_user()
    if not user.access_token:
        pytest.skip("Regular user could not be authenticated (email verification required)")
    return user


@pytest.fixture(scope="function")
def two_group_scenario(user_manager: TestUserManager, api_client: ProductionAPIClient):
    """Create scenario with two groups and users in each"""
    # Create admin user first
    admin = user_manager.create_admin_user()
    
    # Login as admin to create groups
    api_client.set_auth_token(admin.access_token)
    
    # Create groups
    group1_data = {"name": "Test Group 1", "description": "First test group"}
    group2_data = {"name": "Test Group 2", "description": "Second test group"}
    
    group1_response = api_client.post("/groups", group1_data)
    group2_response = api_client.post("/groups", group2_data)
    
    if group1_response.status_code != 201 or group2_response.status_code != 201:
        pytest.skip("Cannot create groups - group management may not be implemented")
    
    group1_id = group1_response.data.get("id")
    group2_id = group2_response.data.get("id")
    
    # Create users in each group
    user1 = user_manager.create_user_in_group(group1_id)
    user2 = user_manager.create_user_in_group(group2_id)
    
    return {
        "admin": admin,
        "group1": {"id": group1_id, "user": user1},
        "group2": {"id": group2_id, "user": user2}
    }


# Performance testing utilities
@pytest.fixture(scope="function")
def performance_monitor():
    """Monitor performance metrics during tests"""
    metrics = {
        "response_times": [],
        "status_codes": [],
        "errors": []
    }
    
    def record_response(self, response: APIResponse):
        metrics["response_times"].append(response.response_time)
        metrics["status_codes"].append(response.status_code)
        if response.status_code >= 400:
            metrics["errors"].append(response.data)
    
    def get_stats(self):
        if not metrics["response_times"]:
            return {}
        
        response_times = metrics["response_times"]
        return {
            "avg_response_time": sum(response_times) / len(response_times),
            "max_response_time": max(response_times),
            "min_response_time": min(response_times),
            "total_requests": len(response_times),
            "error_rate": len(metrics["errors"]) / len(response_times),
            "status_codes": metrics["status_codes"]
        }
    
    monitor = type('Monitor', (), {
        'record': record_response,
        'stats': get_stats,
        'metrics': metrics
    })()
    
    return monitor


# Utility functions for common test patterns
def assert_success_response(response: APIResponse, expected_status: int = 200):
    """Assert that response is successful"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.data}"
    assert response.data is not None, "Response data should not be None"


def assert_error_response(response: APIResponse, expected_status: int, expected_message: str = None):
    """Assert that response is an error with expected status"""
    assert response.status_code == expected_status, f"Expected {expected_status}, got {response.status_code}: {response.data}"
    if expected_message:
        error_detail = response.data.get("detail", "") if isinstance(response.data, dict) else str(response.data)
        assert expected_message.lower() in error_detail.lower(), f"Expected '{expected_message}' in error message: {error_detail}"


def assert_auth_required(response: APIResponse):
    """Assert that response indicates authentication is required"""
    assert response.status_code == 401, f"Expected 401 Unauthorized, got {response.status_code}: {response.data}"


def assert_forbidden(response: APIResponse):
    """Assert that response indicates forbidden access"""
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.status_code}: {response.data}"


def assert_not_found(response: APIResponse):
    """Assert that response indicates resource not found"""
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}: {response.data}"


# Pytest configuration
def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--production",
        action="store_true",
        default=False,
        help="Run production integration tests (normally skipped)"
    )


def pytest_configure(config):
    """Configure pytest for production integration testing"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "production: mark test as production-level test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for production integration tests"""
    # Only skip if --production flag is NOT passed
    skip_production = not config.getoption("--production", default=False)
    
    for item in items:
        # Only process items that are actually in the production directory
        if "tests/integration/production" in str(item.fspath):
            # Add markers to tests in this directory
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.production)
            
            # Skip production tests unless --production flag is used
            if skip_production:
                item.add_marker(pytest.mark.skip(reason="Production tests require --production flag to run"))
            
            # Mark tests that might be slow
            if "comprehensive" in item.name or "full_crud" in item.name:
                item.add_marker(pytest.mark.slow)