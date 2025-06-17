import pytest
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas import User, AITestCreate, ConnectionConfig, ValidationConfig, ValidationCriterion
from app.modules.tests_store import AITestStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.core.config import settings
from app.api import deps


class TestTestsAPIGroupOwnership:
    """Test group ownership validation in API endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        self.test_store = AITestStore(LocalStore())
        
        # Create test groups
        from app.schemas import GroupCreate
        group1_data = GroupCreate(name="Group 1", description="Test group 1")
        group2_data = GroupCreate(name="Group 2", description="Test group 2")
        
        self.group1 = self.group_store.create(group1_data, "system")
        self.group2 = self.group_store.create(group2_data, "system")
        
        # Create test users
        self.user1 = User(
            id=uuid4(),
            email="gorocoaico+TestTestsAPIGroupOwnership1@gmail.com",
            full_name="User 1",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group=str(self.group1.id)
        )
        
        self.user2 = User(
            id=uuid4(),
            email="gorocoaico+TestTestsAPIGroupOwnership2@gmail.com",
            full_name="User 2",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group=str(self.group2.id)
        )
        
        self.admin_user = User(
            id=uuid4(),
            email="gorocoaico+TestTestsAPIGroupOwnershipadmin@gmail.com",
            full_name="Admin User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group=str(self.group1.id)
        )
        
        # Store users
        self.user_store.create(self.user1, str(self.group1.id))
        self.user_store.create(self.user2, str(self.group2.id))
        self.user_store.create(self.admin_user, str(self.group1.id))
        
        # Create test data
        self.test_data = AITestCreate(
            name="Test Test",
            description="A test test",
            prompt_template="Hello {name}",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com",
                auth_type="API_KEY"
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

    def test_list_tests_filters_by_user_group(self, request):
        """Test that listing tests filters by user's group."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create tests for different groups
        test1 = self.test_store.create(self.test_data, self.user1)
        
        test_data2 = self.test_data.model_dump()
        test_data2["name"] = "Test 2"
        test2 = self.test_store.create(AITestCreate(**test_data2), self.user2)
        
        # Mock user1 as current user
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user1
        
        # User1 should only see tests from group1
        response = client.get(f"{settings.API_V1_STR}/tests")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(test1.id)
        
        # Mock user2 as current user
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user2
        
        # User2 should only see tests from group2
        response = client.get(f"{settings.API_V1_STR}/tests")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(test2.id)

    def test_admin_can_see_all_tests(self, request):
        """Test that admin users can see all tests."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create tests for different groups
        test1 = self.test_store.create(self.test_data, self.user1)
        
        test_data2 = self.test_data.model_dump()
        test_data2["name"] = "Test 2"
        test2 = self.test_store.create(AITestCreate(**test_data2), self.user2)
        
        # Mock admin user as current user
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.admin_user
        
        # Admin should see all tests
        response = client.get(f"{settings.API_V1_STR}/tests")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 2
        test_ids = [item["id"] for item in data["items"]]
        assert str(test1.id) in test_ids
        assert str(test2.id) in test_ids

    def test_get_test_group_ownership_validation(self, request):
        """Test that getting a test validates group ownership."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a mock execution store
        from unittest.mock import MagicMock
        mock_execution_store = MagicMock()
        mock_execution_store.get_execution_ids_for_test.return_value = []
        app.dependency_overrides[deps.get_execution_store] = lambda: mock_execution_store
        
        # Create a test for user1
        test = self.test_store.create(self.test_data, self.user1)
        
        # Mock user1 as current user - should succeed
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user1
        
        response = client.get(f"{settings.API_V1_STR}/tests/{test.id}")
        assert response.status_code == status.HTTP_200_OK
        
        # Mock user2 as current user - should fail
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user2
        
        response = client.get(f"{settings.API_V1_STR}/tests/{test.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied: Test does not belong to your group" in response.json()["detail"]

    def test_admin_can_access_any_test(self, request):
        """Test that admin users can access any test."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a mock execution store
        from unittest.mock import MagicMock
        mock_execution_store = MagicMock()
        mock_execution_store.get_execution_ids_for_test.return_value = []
        app.dependency_overrides[deps.get_execution_store] = lambda: mock_execution_store
        
        # Create a test for user1
        test = self.test_store.create(self.test_data, self.user1)
        
        # Mock admin user as current user - should succeed
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.admin_user
        
        response = client.get(f"{settings.API_V1_STR}/tests/{test.id}")
        assert response.status_code == status.HTTP_200_OK

    def test_update_test_group_ownership_validation(self, request):
        """Test that updating a test validates group ownership."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a test for user1
        test = self.test_store.create(self.test_data, self.user1)
        
        # Mock user1 as current user - should succeed
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user1
        
        update_data = self.test_data.model_dump()
        update_data["name"] = "Updated Test"
        
        response = client.put(f"{settings.API_V1_STR}/tests/{test.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Updated Test"
        
        # Mock user2 as current user - should fail
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user2
        
        response = client.put(f"{settings.API_V1_STR}/tests/{test.id}", json=update_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied: Test does not belong to your group" in response.json()["detail"]

    def test_delete_test_group_ownership_validation(self, request):
        """Test that deleting a test validates group ownership."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a test for user1
        test = self.test_store.create(self.test_data, self.user1)
        
        # Mock user1 as current user - should succeed
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user1
        
        response = client.delete(f"{settings.API_V1_STR}/tests/{test.id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify test was deleted
        assert self.test_store.get(str(test.id)) is None
        
        # Create another test for user1
        test2 = self.test_store.create(self.test_data, self.user1)
        
        # Mock user2 as current user - should fail
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user2
        
        response = client.delete(f"{settings.API_V1_STR}/tests/{test2.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied: Test does not belong to your group" in response.json()["detail"]
        
        # Verify test was not deleted
        assert self.test_store.get(str(test2.id)) is not None

    def test_create_test_sets_group_id_from_user(self, request):
        """Test that creating a test sets the group_id from the user's group."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Mock user1 as current user
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user1
        
        response = client.post(f"{settings.API_V1_STR}/tests", json=self.test_data.model_dump())
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert data["group_id"] == str(self.group1.id)
        assert data["created_by"] == str(self.user1.id)

    def test_non_existent_test_returns_404(self, request):
        """Test that accessing a non-existent test returns 404."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        app.dependency_overrides[deps.get_execution_store] = lambda: None  # Mock execution store
        
        # Mock user1 as current user
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.user1
        
        non_existent_id = str(uuid4())
        response = client.get(f"{settings.API_V1_STR}/tests/{non_existent_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Test not found" 