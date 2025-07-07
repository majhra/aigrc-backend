import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4

from app.main import app
from app.schemas import PromptVariable, User, GroupCreate
from app.modules.prompts_store import PromptCategoryStore, PromptStore, PromptSetStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.api import deps
from app.core.config import settings

@pytest.fixture
def sample_category_data():
    return {
        "name": "Test Category",
        "description": "A test category for prompts",
        "category_type": "CUSTOM",
        "priority": "MEDIUM",
        "tags": ["test", "category"]
    }

@pytest.fixture
def sample_prompt_data():
    return {
        "name": "Test Prompt",
        "description": "A test prompt template",
        "content": "Hello {{name}}, how are you today?",
        "category_id": str(uuid4()),
        "variables": [
            {
                "name": "name",
                "description": "The person's name",
                "type": "text",
                "required": True
            }
        ],
        "tags": ["greeting", "test"],
        "risk_level": "LOW"
    }

class TestPromptCategories:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.category_store = PromptCategoryStore(LocalStore())
        self.prompt_store = PromptStore(LocalStore())
        self.prompt_set_store = PromptSetStore(LocalStore())
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

        # Override dependencies
        self.client.app.dependency_overrides[deps.get_current_active_user] = lambda: self.TEST_USER
        self.client.app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        self.client.app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        self.client.app.dependency_overrides[deps.get_prompt_set_store] = lambda: self.prompt_set_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear prompt stores by accessing underlying store
        if isinstance(self.category_store._store, LocalStore):
            self.category_store._store.data.clear()
        if isinstance(self.prompt_store._store, LocalStore):
            self.prompt_store._store.data.clear()
        if isinstance(self.prompt_set_store._store, LocalStore):
            self.prompt_set_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_create_category(self, sample_category_data):
        response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=sample_category_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_category_data["name"]
        assert data["description"] == sample_category_data["description"]
        assert data["category_type"] == sample_category_data["category_type"]
        assert "id" in data
        assert "created_at" in data
    
    def test_get_categories(self):
        response = self.client.get(
            "/api/v1.0/prompts/categories"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
    
    def test_get_category_by_id(self, sample_category_data):
        # First create a category
        create_response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=sample_category_data
        )
        category_id = create_response.json()["id"]
        
        # Then retrieve it
        response = self.client.get(
            f"/api/v1.0/prompts/categories/{category_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == category_id
        assert data["name"] == sample_category_data["name"]
    
    def test_update_category(self, sample_category_data):
        # First create a category
        create_response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=sample_category_data
        )
        category_id = create_response.json()["id"]
        
        # Update it
        update_data = {"name": "Updated Category Name"}
        response = self.client.put(
            f"/api/v1.0/prompts/categories/{category_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Category Name"
    
    def test_delete_category(self, sample_category_data):
        # First create a category
        create_response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=sample_category_data
        )
        category_id = create_response.json()["id"]
        
        # Delete it
        response = self.client.delete(
            f"/api/v1.0/prompts/categories/{category_id}"
        )
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = self.client.get(
            f"/api/v1.0/prompts/categories/{category_id}"
        )
        assert get_response.status_code == 404

class TestPrompts:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.category_store = PromptCategoryStore(LocalStore())
        self.prompt_store = PromptStore(LocalStore())
        self.prompt_set_store = PromptSetStore(LocalStore())
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

        # Override dependencies
        self.client.app.dependency_overrides[deps.get_current_active_user] = lambda: self.TEST_USER
        self.client.app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        self.client.app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        self.client.app.dependency_overrides[deps.get_prompt_set_store] = lambda: self.prompt_set_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear prompt stores by accessing underlying store
        if isinstance(self.category_store._store, LocalStore):
            self.category_store._store.data.clear()
        if isinstance(self.prompt_store._store, LocalStore):
            self.prompt_store._store.data.clear()
        if isinstance(self.prompt_set_store._store, LocalStore):
            self.prompt_set_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_create_prompt(self, sample_prompt_data):
        # First create a category
        category_data = {
            "name": "Test Category",
            "description": "A test category",
            "category_type": "CUSTOM"
        }
        category_response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=category_data
        )
        category_id = category_response.json()["id"]
        
        # Update prompt data with valid category_id
        sample_prompt_data["category_id"] = category_id
        
        response = self.client.post(
            "/api/v1.0/prompts/",
            json=sample_prompt_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_prompt_data["name"]
        assert data["content"] == sample_prompt_data["content"]
        assert "id" in data
        assert "version" in data
    
    def test_get_prompts(self):
        response = self.client.get(
            "/api/v1.0/prompts/"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
    
    def test_validate_prompt_template(self):
        validation_data = {
            "content": "Hello {{name}}, your age is {{age}}",
            "variables": [
                {
                    "name": "name",
                    "description": "The person's name",
                    "type": "text",
                    "required": True
                },
                {
                    "name": "age",
                    "description": "The person's age",
                    "type": "number",
                    "required": True
                }
            ]
        }
        
        response = self.client.post(
            "/api/v1.0/prompts/validate",
            json=validation_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is True
        assert "variable_placeholders" in data
        assert "name" in data["variable_placeholders"]
        assert "age" in data["variable_placeholders"]
    
    def test_preview_prompt(self):
        preview_data = {
            "content": "Hello {{name}}, you are {{age}} years old",
            "variable_values": {
                "name": "John",
                "age": "30"
            }
        }
        
        response = self.client.post(
            "/api/v1.0/prompts/preview",
            json=preview_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["rendered_content"] == "Hello John, you are 30 years old"
        assert data["is_valid"] is True
    
    def test_invalid_prompt_template(self):
        # Test with missing required variable
        validation_data = {
            "content": "Hello {{name}}, your age is {{age}}",
            "variables": [
                {
                    "name": "name",
                    "description": "The person's name",
                    "type": "text",
                    "required": True
                }
                # Missing 'age' variable definition
            ]
        }
        
        response = self.client.post(
            "/api/v1.0/prompts/validate",
            json=validation_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert len(data["errors"]) > 0

class TestPromptSets:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.category_store = PromptCategoryStore(LocalStore())
        self.prompt_store = PromptStore(LocalStore())
        self.prompt_set_store = PromptSetStore(LocalStore())
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

        # Override dependencies
        self.client.app.dependency_overrides[deps.get_current_active_user] = lambda: self.TEST_USER
        self.client.app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        self.client.app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        self.client.app.dependency_overrides[deps.get_prompt_set_store] = lambda: self.prompt_set_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear prompt stores by accessing underlying store
        if isinstance(self.category_store._store, LocalStore):
            self.category_store._store.data.clear()
        if isinstance(self.prompt_store._store, LocalStore):
            self.prompt_store._store.data.clear()
        if isinstance(self.prompt_set_store._store, LocalStore):
            self.prompt_set_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_create_prompt_set(self):
        # First create a category
        category_data = {
            "name": "Test Category",
            "description": "A test category",
            "category_type": "CUSTOM"
        }
        category_response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=category_data
        )
        category_id = category_response.json()["id"]
        
        # Create a prompt
        prompt_data = {
            "name": "Test Prompt",
            "description": "A test prompt",
            "content": "Hello {{name}}",
            "category_id": category_id,
            "variables": [
                {
                    "name": "name",
                    "description": "Person's name",
                    "type": "text",
                    "required": True
                }
            ]
        }
        prompt_response = self.client.post(
            "/api/v1.0/prompts/",
            json=prompt_data
        )
        prompt_id = prompt_response.json()["id"]
        
        # Create prompt set
        set_data = {
            "name": "Test Prompt Set",
            "description": "A collection of test prompts",
            "category_id": category_id,
            "prompt_ids": [prompt_id],
            "tags": ["test", "collection"]
        }
        
        response = self.client.post(
            "/api/v1.0/prompts/sets",
            json=set_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == set_data["name"]
        assert prompt_id in data["prompt_ids"]
    
    def test_get_prompt_sets(self):
        response = self.client.get(
            "/api/v1.0/prompts/sets"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data

class TestPromptFiltering:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.category_store = PromptCategoryStore(LocalStore())
        self.prompt_store = PromptStore(LocalStore())
        self.prompt_set_store = PromptSetStore(LocalStore())
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

        # Override dependencies
        self.client.app.dependency_overrides[deps.get_current_active_user] = lambda: self.TEST_USER
        self.client.app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        self.client.app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        self.client.app.dependency_overrides[deps.get_prompt_set_store] = lambda: self.prompt_set_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear prompt stores by accessing underlying store
        if isinstance(self.category_store._store, LocalStore):
            self.category_store._store.data.clear()
        if isinstance(self.prompt_store._store, LocalStore):
            self.prompt_store._store.data.clear()
        if isinstance(self.prompt_set_store._store, LocalStore):
            self.prompt_set_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_filter_prompts_by_status(self):
        response = self.client.get(
            "/api/v1.0/prompts/?status=ACTIVE"
        )
        
        assert response.status_code == 200
        data = response.json()
        for prompt in data["items"]:
            assert prompt["status"] == "ACTIVE"
    
    def test_search_prompts(self):
        response = self.client.get(
            "/api/v1.0/prompts/?search=test"
        )
        
        assert response.status_code == 200
        # Response should be valid even if no results found
        data = response.json()
        assert "items" in data
    
    def test_pagination(self):
        response = self.client.get(
            "/api/v1.0/prompts/?page=1&limit=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 5
        assert len(data["items"]) <= 5