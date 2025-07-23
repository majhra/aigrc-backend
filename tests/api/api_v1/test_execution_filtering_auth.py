import pytest
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.modules.store_interface import LocalStore
from app.modules.tests_store import AITestStore
from app.modules.executions_store import ExecutedTestStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.schemas import (
    AITestCreate, User, ConnectionConfig, ValidationConfig, ValidationCriterion,
    ExecutedTestCreate, GroupCreate
)

client = TestClient(app)


class TestExecutionFilteringAuth:
    """Test suite for execution filtering endpoint authentication and authorization."""
    
    def setup_method(self):
        """Set up test fixtures for each test."""
        # Use fresh stores for each test
        self.store = LocalStore()
        self.user_store = UserStore(self.store)
        self.group_store = GroupStore(self.store)
        self.tests_store = AITestStore(self.store)
        self.executions_store = ExecutedTestStore(self.store)
        
        # Create test group
        self.group = self.group_store.create(
            GroupCreate(name="Test Group", description="Test group"),
            User(id=str(uuid4()), email="admin@example.com")
        )
        
        # Create regular user
        self.regular_user = User(
            id=str(uuid4()),
            email="goricoaico+regular@gmail.com",
            full_name="Regular User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",  # Regular user role
            group=str(self.group.id)
        )
        
        # Create admin user
        self.admin_user = User(
            id=str(uuid4()),
            email="goricoaico+admin@gmail.com",
            full_name="Admin User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",  # Admin role
            group=str(self.group.id)
        )
        
        # Create user from different group
        self.other_group = self.group_store.create(
            GroupCreate(name="Other Group", description="Other group"),
            self.admin_user
        )
        
        self.other_user = User(
            id=str(uuid4()),
            email="goricoaico+other@gmail.com",
            full_name="Other User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group=str(self.other_group.id)
        )
        
        # Note: We don't need to store users in UserStore for this test
        # We'll mock the authentication to return our test users directly
        
        # Create test
        self.test_data = AITestCreate(
            name="Auth Test",
            description="A test for auth testing",
            prompt_template="Test {input}",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="test-api-key"
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="criterion1",
                        name="Test Criterion",
                        description="A test criterion",
                        type="exact_match"
                    )
                ]
            ),
            tags=["test"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        self.test = self.tests_store.create(self.test_data, self.regular_user)
        
        # Create an execution
        self.execution = self.executions_store.create(
            test_id=str(self.test.id),
            execution=ExecutedTestCreate(),
            user=self.regular_user,
            prompt="Test prompt",
            response="Test response"
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.store.data.clear()

    def test_admin_role_check_bug_prevention(self):
        """Test that prevents the is_admin AttributeError bug."""
        # This test ensures we don't accidentally use current_user.is_admin
        # which doesn't exist on the User model
        
        # Mock the get_current_active_user dependency to return our test users
        with patch('app.api.deps.get_current_active_user') as mock_get_user:
            # Test with regular user - should work for own group's test
            mock_get_user.return_value = self.regular_user
            
            response = client.get(
                f"/api/v1.0/tests/{self.test.id}/executions",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should succeed (user can access own group's test)
            assert response.status_code == 200
            
            # Test with admin user - should work for any test
            mock_get_user.return_value = self.admin_user
            
            response = client.get(
                f"/api/v1.0/tests/{self.test.id}/executions",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should succeed (admin can access any test)
            assert response.status_code == 200

    def test_user_role_attribute_exists(self):
        """Test that User objects have the correct role attribute."""
        # Verify that our User objects have the 'role' attribute
        assert hasattr(self.regular_user, 'role')
        assert hasattr(self.admin_user, 'role')
        assert hasattr(self.other_user, 'role')
        
        # Verify role values
        assert self.regular_user.role == "user"
        assert self.admin_user.role == "admin"
        assert self.other_user.role == "user"
        
        # Verify that is_admin attribute does NOT exist (this is the bug)
        assert not hasattr(self.regular_user, 'is_admin')
        assert not hasattr(self.admin_user, 'is_admin')
        assert not hasattr(self.other_user, 'is_admin')

    def test_admin_access_pattern_consistency(self):
        """Test that admin access checking is consistent across the codebase."""
        # This test verifies the correct admin checking pattern
        
        with patch('app.api.deps.get_current_active_user') as mock_get_user:
            # Test admin user accessing different group's test
            other_test = self.tests_store.create(self.test_data, self.other_user)
            
            # Admin should be able to access tests from other groups
            mock_get_user.return_value = self.admin_user
            
            response = client.get(
                f"/api/v1.0/tests/{other_test.id}/executions",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should succeed because admin can access any group's tests
            assert response.status_code == 200
            
            # Regular user should NOT be able to access other group's test
            mock_get_user.return_value = self.regular_user
            
            response = client.get(
                f"/api/v1.0/tests/{other_test.id}/executions",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should fail with 403 Forbidden
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]

    def test_role_based_authorization_edge_cases(self):
        """Test edge cases in role-based authorization."""
        
        with patch('app.api.deps.get_current_active_user') as mock_get_user:
            # Test user with None role
            user_no_role = User(
                id=str(uuid4()),
                email="goricoaico+norole@gmail.com",
                full_name="No Role User",
                disabled=False,
                created_at=datetime.now(timezone.utc),
                is_verified=True,
                role=None,  # No role
                group=str(self.group.id)
            )
            self.user_store.create_user(user_no_role)
            
            mock_get_user.return_value = user_no_role
            
            response = client.get(
                f"/api/v1.0/tests/{self.test.id}/executions",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should still work for same group (None != "admin" is True)
            assert response.status_code == 200
            
            # Test user with empty string role
            user_empty_role = User(
                id=str(uuid4()),
                email="goricoaico+emptyrole@gmail.com",
                full_name="Empty Role User",
                disabled=False,
                created_at=datetime.now(timezone.utc),
                is_verified=True,
                role="",  # Empty role
                group=str(self.group.id)
            )
            self.user_store.create_user(user_empty_role)
            
            mock_get_user.return_value = user_empty_role
            
            response = client.get(
                f"/api/v1.0/tests/{self.test.id}/executions",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should still work for same group ("" != "admin" is True)
            assert response.status_code == 200

    def test_case_sensitive_admin_role_check(self):
        """Test that admin role checking is case sensitive."""
        
        with patch('app.api.deps.get_current_active_user') as mock_get_user:
            # Test user with different case admin role
            user_admin_caps = User(
                id=str(uuid4()),
                email="goricoaico+admincaps@gmail.com",
                full_name="Admin Caps User",
                disabled=False,
                created_at=datetime.now(timezone.utc),
                is_verified=True,
                role="ADMIN",  # Uppercase admin
                group=str(self.group.id)
            )
            self.user_store.create_user(user_admin_caps)
            
            # Create test in different group
            other_test = self.tests_store.create(self.test_data, self.other_user)
            
            mock_get_user.return_value = user_admin_caps
            
            response = client.get(
                f"/api/v1.0/tests/{other_test.id}/executions",
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Should fail because "ADMIN" != "admin" (case sensitive)
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]

    def test_multiple_filter_combinations_with_auth(self):
        """Test various filter combinations work correctly with auth."""
        
        with patch('app.api.deps.get_current_active_user') as mock_get_user:
            mock_get_user.return_value = self.regular_user
            
            # Test different filter combinations
            filter_combinations = [
                "?status=PENDING",
                "?statuses=PENDING,ERROR",
                "?result=PASS",
                "?has_errors=true",
                "?outstanding=true",
                "?page=1&limit=5",
                "?status=VALIDATED&result=PASS"
            ]
            
            for filters in filter_combinations:
                response = client.get(
                    f"/api/v1.0/tests/{self.test.id}/executions{filters}",
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # All should succeed with proper auth
                assert response.status_code == 200, f"Failed for filters: {filters}"
                
                # Verify response structure
                data = response.json()
                assert "items" in data
                assert "total" in data
                assert "page" in data
                assert "limit" in data

    def test_admin_check_consistency_across_endpoints(self):
        """Test that admin checking is consistent across different test endpoints."""
        
        with patch('app.api.deps.get_current_active_user') as mock_get_user:
            # Create test in different group
            other_test = self.tests_store.create(self.test_data, self.other_user)
            
            # Test admin access to various endpoints
            admin_endpoints = [
                f"/api/v1.0/tests/{other_test.id}",  # Get test details
                f"/api/v1.0/tests/{other_test.id}/executions",  # List executions (our new endpoint)
                f"/api/v1.0/tests/{other_test.id}/{self.execution.id}",  # Get specific execution
            ]
            
            # Test with admin user
            mock_get_user.return_value = self.admin_user
            
            for endpoint in admin_endpoints:
                response = client.get(
                    endpoint,
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Admin should be able to access all endpoints
                # Note: Some might return 404 if execution doesn't belong to test, but not 403
                assert response.status_code in [200, 400, 404], f"Admin access failed for {endpoint}: {response.status_code}"
            
            # Test with regular user from different group  
            mock_get_user.return_value = self.regular_user
            
            for endpoint in admin_endpoints:
                response = client.get(
                    endpoint,
                    headers={"Authorization": "Bearer test-token"}
                )
                
                # Regular user should get 403 Forbidden for cross-group access
                assert response.status_code == 403, f"Expected 403 for {endpoint}, got {response.status_code}"

    def test_attribute_error_prevention_direct(self):
        """Direct test to prevent AttributeError: 'User' object has no attribute 'is_admin'."""
        
        # This test directly tries to access is_admin to ensure it fails gracefully
        users = [self.regular_user, self.admin_user, self.other_user]
        
        for user in users:
            # Verify is_admin attribute doesn't exist
            with pytest.raises(AttributeError, match="'User' object has no attribute 'is_admin'"):
                _ = user.is_admin
            
            # Verify role attribute does exist and works correctly
            assert hasattr(user, 'role')
            role = user.role
            
            # Test the correct admin check pattern
            is_admin_correct = (role == "admin")
            
            # Verify expected results
            if user == self.admin_user:
                assert is_admin_correct is True
            else:
                assert is_admin_correct is False