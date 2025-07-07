import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.api import deps
from app.core.config import settings
from app.schemas import User, GroupCreate
from app.modules.prompts_store import PromptCategoryStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore

class TestPromptsCategories:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.category_store = PromptCategoryStore(LocalStore())
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        
        # Create a test group
        group_data = GroupCreate(name="Test Group", description="Test group for prompts")
        self.test_group = self.group_store.create(group_data, "system")
        
        # Create a test user with the group
        self.TEST_USER = User(
            id=uuid4(),
            email="test@example.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group=str(self.test_group.id)
        )
        
        # Store the user
        self.user_store.create(self.TEST_USER, str(self.test_group.id))
        
        # Create some test categories in the store
        self._create_test_categories()

        # Override dependencies
        self.client.app.dependency_overrides[deps.get_current_active_user] = lambda: self.TEST_USER
        self.client.app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def _create_test_categories(self):
        """Create test categories for testing"""
        from app.schemas.prompts import PromptCategoryCreate
        
        test_categories = [
            PromptCategoryCreate(
                name="Safety Category",
                description="Safety testing prompts",
                category_type="SAFETY",
                priority="HIGH",
                tags=["safety", "test"]
            ),
            PromptCategoryCreate(
                name="Compliance Category", 
                description="Compliance testing prompts",
                category_type="COMPLIANCE",
                priority="MEDIUM",
                tags=["compliance", "test"]
            ),
            PromptCategoryCreate(
                name="Accuracy Category",
                description="Accuracy testing prompts", 
                category_type="ACCURACY",
                priority="LOW",
                tags=["accuracy", "test"]
            )
        ]
        
        for category_data in test_categories:
            self.category_store.create(category_data, self.TEST_USER)

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear stores by accessing underlying store
        if isinstance(self.category_store._store, LocalStore):
            self.category_store._store.data.clear()
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_get_categories_list(self):
        """Test getting list of categories"""
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        
        categories = data["items"]
        assert isinstance(categories, list)
        assert len(categories) >= 3  # We created 3 test categories
        
        # Verify first category structure
        first_category = categories[0]
        assert "id" in first_category
        assert "name" in first_category
        assert "description" in first_category
        assert "category_type" in first_category
        assert first_category["category_type"] in ["SAFETY", "ACCURACY", "COMPLIANCE"]

    def test_get_categories_unauthorized(self):
        """Test getting categories without auth"""
        # Remove the auth override
        self.client.app.dependency_overrides = {}
        
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_category_by_id(self):
        """Test getting a specific category by ID"""
        # First get the list to get a valid ID
        list_response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert list_response.status_code == status.HTTP_200_OK
        category_id = list_response.json()["items"][0]["id"]
        
        # Then get the specific category
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories/{category_id}")
        assert response.status_code == status.HTTP_200_OK
        
        category = response.json()
        assert category["id"] == category_id
        assert "name" in category
        assert "description" in category
        assert "category_type" in category

    def test_get_category_not_found(self):
        """Test getting a non-existent category"""
        non_existent_id = uuid4()
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories/{non_existent_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_update_category(self):
        """Test updating a category"""
        # First get the list to get a valid ID
        list_response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert list_response.status_code == status.HTTP_200_OK
        category_id = list_response.json()["items"][0]["id"]
        
        # Update data
        update_data = {
            "name": "Updated Category Name",
            "description": "Updated Description",
            "priority": "HIGH",
            "tags": ["updated", "test"]
        }
        
        response = self.client.put(
            f"{settings.API_V1_STR}/prompts/categories/{category_id}",
            json=update_data
        )
        assert response.status_code == status.HTTP_200_OK
        
        updated_category = response.json()
        assert updated_category["id"] == category_id
        assert updated_category["name"] == update_data["name"]
        assert updated_category["description"] == update_data["description"]
        assert updated_category["priority"] == update_data["priority"]
        assert updated_category["tags"] == update_data["tags"]

    def test_update_category_invalid_data(self):
        """Test updating a category with invalid data"""
        # First get the list to get a valid ID
        list_response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert list_response.status_code == status.HTTP_200_OK
        category_id = list_response.json()["items"][0]["id"]
        
        # Invalid update data (invalid category type)
        update_data = {
            "category_type": "INVALID_CATEGORY"  # Not one of SAFETY, ACCURACY, COMPLIANCE
        }
        
        response = self.client.put(
            f"{settings.API_V1_STR}/prompts/categories/{category_id}",
            json=update_data
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_category_not_found(self):
        """Test updating a non-existent category"""
        non_existent_id = uuid4()
        update_data = {
            "name": "Updated Name"
        }
        
        response = self.client.put(
            f"{settings.API_V1_STR}/prompts/categories/{non_existent_id}",
            json=update_data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_update_category_unauthorized(self):
        """Test updating a category without auth"""
        # Remove the auth override
        self.client.app.dependency_overrides = {}
        
        category_id = uuid4()
        update_data = {
            "name": "Updated Name"
        }
        
        response = self.client.put(
            f"{settings.API_V1_STR}/prompts/categories/{category_id}",
            json=update_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED 