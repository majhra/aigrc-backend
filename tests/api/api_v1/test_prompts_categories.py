import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api import deps
from app.core.config import settings
from app.schemas import User

class TestPromptsCategories:
    # Test data
    TEST_CATEGORY_ID = uuid4()
    TEST_CATEGORY = {
        "id": TEST_CATEGORY_ID,
        "name": "Test Category",
        "description": "Test Description",
        "category": "COMPLIANCE",
        "subcategory": "Test Subcategory",
        "priority": "HIGH",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "tags": ["test", "category"]
    }

    def setup_method(self, method):
        """Setup test user in local store before each test"""
        # Create test user
        test_user = User(
            email="goricoaico+testcategories0@gmail.com",
            password=self.valid_passwords[0],
            is_verified=True,
            disabled=False
        )
        # Use the underlying store to put the user directly
        self.user_store._store.put(str(test_user.id), test_user.model_dump())

        # Override the current user dependency in the Auth: current_user: Annotated[User, Depends(deps.get_current_active_user)] dependency
    
        self.app.dependency_overrides[deps.get_current_active_user] = lambda: test_user

    def teardown_method(self, method):
        """Clean up after each test"""
        self.app.dependency_overrides = {}
        #self.user_store.clear()

    def test_get_categories_list(self):
        """Test getting list of categories"""
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert response.status_code == status.HTTP_200_OK
        
        categories = response.json()
        assert isinstance(categories, list)
        assert len(categories) > 0
        
        # Verify first category structure
        first_category = categories[0]
        assert "id" in first_category
        assert "name" in first_category
        assert "description" in first_category
        assert "category" in first_category
        assert first_category["category"] in ["SAFETY", "ACCURACY", "COMPLIANCE"]

    def test_get_categories_unauthorized(self):
        """Test getting categories without auth"""
        # Remove the auth override
        self.app.dependency_overrides = {}
        
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_category_by_id(self):
        """Test getting a specific category by ID"""
        # First get the list to get a valid ID
        list_response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert list_response.status_code == status.HTTP_200_OK
        category_id = list_response.json()[0]["id"]
        
        # Then get the specific category
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories/{category_id}")
        assert response.status_code == status.HTTP_200_OK
        
        category = response.json()
        assert category["id"] == category_id
        assert "name" in category
        assert "description" in category
        assert "category" in category

    def test_get_category_not_found(self):
        """Test getting a non-existent category"""
        non_existent_id = uuid4()
        response = self.client.get(f"{settings.API_V1_STR}/prompts/categories/{non_existent_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "Test category not found"

    def test_update_category(self):
        """Test updating a category"""
        # First get the list to get a valid ID
        list_response = self.client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert list_response.status_code == status.HTTP_200_OK
        category_id = list_response.json()[0]["id"]
        
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
        category_id = list_response.json()[0]["id"]
        
        # Invalid update data (invalid category type)
        update_data = {
            "category": "INVALID_CATEGORY"  # Not one of SAFETY, ACCURACY, COMPLIANCE
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
        assert response.json()["detail"] == "Test category not found"

    def test_update_category_unauthorized(self):
        """Test updating a category without auth"""
        # Remove the auth override
        self.app.dependency_overrides = {}
        
        category_id = uuid4()
        update_data = {
            "name": "Updated Name"
        }
        
        response = self.client.put(
            f"{settings.API_V1_STR}/prompts/categories/{category_id}",
            json=update_data
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED 