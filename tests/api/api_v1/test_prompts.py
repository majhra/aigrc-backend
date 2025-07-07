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
            email="goricoaico+prompts@gmail.com",
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
            email="goricoaico+prompts@gmail.com",
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
    
    def test_get_prompt_by_id(self, sample_prompt_data):
        """Test getting a specific prompt by ID"""
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
        
        # Create the prompt
        create_response = self.client.post(
            "/api/v1.0/prompts/",
            json=sample_prompt_data
        )
        prompt_id = create_response.json()["id"]
        
        # Get the prompt by ID
        response = self.client.get(f"/api/v1.0/prompts/{prompt_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == prompt_id
        assert data["name"] == sample_prompt_data["name"]
        assert data["content"] == sample_prompt_data["content"]
    
    def test_update_prompt(self, sample_prompt_data):
        """Test updating a prompt"""
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
        
        # Create the prompt
        create_response = self.client.post(
            "/api/v1.0/prompts/",
            json=sample_prompt_data
        )
        prompt_id = create_response.json()["id"]
        
        # Update the prompt
        update_data = {
            "name": "Updated Prompt Name",
            "description": "Updated description",
            "content": "Hello {{name}}, how are you feeling today?"
        }
        response = self.client.put(
            f"/api/v1.0/prompts/{prompt_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Prompt Name"
        assert data["description"] == "Updated description"
        assert data["content"] == "Hello {{name}}, how are you feeling today?"
        assert data["id"] == prompt_id
    
    def test_delete_prompt(self, sample_prompt_data):
        """Test deleting a prompt"""
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
        
        # Create the prompt
        create_response = self.client.post(
            "/api/v1.0/prompts/",
            json=sample_prompt_data
        )
        prompt_id = create_response.json()["id"]
        
        # Delete the prompt
        response = self.client.delete(f"/api/v1.0/prompts/{prompt_id}")
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = self.client.get(f"/api/v1.0/prompts/{prompt_id}")
        assert get_response.status_code == 404

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
            email="goricoaico+prompts@gmail.com",
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
    
    def test_get_prompt_set_by_id(self):
        """Test getting a specific prompt set by ID"""
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
        
        create_response = self.client.post(
            "/api/v1.0/prompts/sets",
            json=set_data
        )
        set_id = create_response.json()["id"]
        
        # Get the prompt set by ID
        response = self.client.get(f"/api/v1.0/prompts/sets/{set_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == set_id
        assert data["name"] == set_data["name"]
        assert data["description"] == set_data["description"]
        assert prompt_id in data["prompt_ids"]
    
    def test_update_prompt_set(self):
        """Test updating a prompt set"""
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
        
        create_response = self.client.post(
            "/api/v1.0/prompts/sets",
            json=set_data
        )
        set_id = create_response.json()["id"]
        
        # Update the prompt set
        update_data = {
            "name": "Updated Prompt Set",
            "description": "Updated description",
            "tags": ["updated", "test"]
        }
        response = self.client.put(
            f"/api/v1.0/prompts/sets/{set_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Prompt Set"
        assert data["description"] == "Updated description"
        assert "updated" in data["tags"]
        assert data["id"] == set_id
    
    def test_delete_prompt_set(self):
        """Test deleting a prompt set"""
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
        
        create_response = self.client.post(
            "/api/v1.0/prompts/sets",
            json=set_data
        )
        set_id = create_response.json()["id"]
        
        # Delete the prompt set
        response = self.client.delete(f"/api/v1.0/prompts/sets/{set_id}")
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = self.client.get(f"/api/v1.0/prompts/sets/{set_id}")
        assert get_response.status_code == 404

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
            email="goricoaico+prompts@gmail.com",
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

class TestPromptAuthentication:
    """Test authentication and authorization for prompt endpoints"""
    
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}

    def test_get_categories_unauthorized(self):
        """Test that unauthenticated users cannot access categories"""
        response = self.client.get("/api/v1.0/prompts/categories")
        assert response.status_code == 401

    def test_create_category_unauthorized(self):
        """Test that unauthenticated users cannot create categories"""
        category_data = {
            "name": "Test Category",
            "description": "A test category",
            "category_type": "CUSTOM"
        }
        response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=category_data
        )
        assert response.status_code == 401

    def test_get_category_by_id_unauthorized(self):
        """Test that unauthenticated users cannot get specific categories"""
        category_id = str(uuid4())
        response = self.client.get(f"/api/v1.0/prompts/categories/{category_id}")
        assert response.status_code == 401

    def test_update_category_unauthorized(self):
        """Test that unauthenticated users cannot update categories"""
        category_id = str(uuid4())
        update_data = {"name": "Updated Category"}
        response = self.client.put(
            f"/api/v1.0/prompts/categories/{category_id}",
            json=update_data
        )
        assert response.status_code == 401

    def test_delete_category_unauthorized(self):
        """Test that unauthenticated users cannot delete categories"""
        category_id = str(uuid4())
        response = self.client.delete(f"/api/v1.0/prompts/categories/{category_id}")
        assert response.status_code == 401

    def test_get_prompts_unauthorized(self):
        """Test that unauthenticated users cannot access prompts"""
        response = self.client.get("/api/v1.0/prompts/")
        assert response.status_code == 401

    def test_create_prompt_unauthorized(self):
        """Test that unauthenticated users cannot create prompts"""
        prompt_data = {
            "name": "Test Prompt",
            "description": "A test prompt",
            "content": "Hello {{name}}",
            "category_id": str(uuid4()),
            "variables": []
        }
        response = self.client.post(
            "/api/v1.0/prompts/",
            json=prompt_data
        )
        assert response.status_code == 401

    def test_get_prompt_by_id_unauthorized(self):
        """Test that unauthenticated users cannot get specific prompts"""
        prompt_id = str(uuid4())
        response = self.client.get(f"/api/v1.0/prompts/{prompt_id}")
        assert response.status_code == 401

    def test_update_prompt_unauthorized(self):
        """Test that unauthenticated users cannot update prompts"""
        prompt_id = str(uuid4())
        update_data = {"name": "Updated Prompt"}
        response = self.client.put(
            f"/api/v1.0/prompts/{prompt_id}",
            json=update_data
        )
        assert response.status_code == 401

    def test_delete_prompt_unauthorized(self):
        """Test that unauthenticated users cannot delete prompts"""
        prompt_id = str(uuid4())
        response = self.client.delete(f"/api/v1.0/prompts/{prompt_id}")
        assert response.status_code == 401

    def test_get_prompt_sets_unauthorized(self):
        """Test that unauthenticated users cannot access prompt sets"""
        response = self.client.get("/api/v1.0/prompts/sets")
        assert response.status_code == 401

    def test_create_prompt_set_unauthorized(self):
        """Test that unauthenticated users cannot create prompt sets"""
        set_data = {
            "name": "Test Set",
            "description": "A test set",
            "category_id": str(uuid4()),
            "prompt_ids": [str(uuid4())]
        }
        response = self.client.post(
            "/api/v1.0/prompts/sets",
            json=set_data
        )
        assert response.status_code == 401

    def test_get_prompt_set_by_id_unauthorized(self):
        """Test that unauthenticated users cannot get specific prompt sets"""
        set_id = str(uuid4())
        response = self.client.get(f"/api/v1.0/prompts/sets/{set_id}")
        assert response.status_code == 401

    def test_update_prompt_set_unauthorized(self):
        """Test that unauthenticated users cannot update prompt sets"""
        set_id = str(uuid4())
        update_data = {"name": "Updated Set"}
        response = self.client.put(
            f"/api/v1.0/prompts/sets/{set_id}",
            json=update_data
        )
        assert response.status_code == 401

    def test_delete_prompt_set_unauthorized(self):
        """Test that unauthenticated users cannot delete prompt sets"""
        set_id = str(uuid4())
        response = self.client.delete(f"/api/v1.0/prompts/sets/{set_id}")
        assert response.status_code == 401

    def test_validate_prompt_unauthorized(self):
        """Test that unauthenticated users cannot validate prompts"""
        validation_data = {
            "content": "Hello {{name}}",
            "variables": [
                {
                    "name": "name",
                    "description": "Person's name",
                    "type": "text",
                    "required": True
                }
            ]
        }
        response = self.client.post(
            "/api/v1.0/prompts/validate",
            json=validation_data
        )
        assert response.status_code == 401

    def test_preview_prompt_unauthorized(self):
        """Test that unauthenticated users cannot preview prompts"""
        preview_data = {
            "content": "Hello {{name}}",
            "variable_values": {"name": "John"}
        }
        response = self.client.post(
            "/api/v1.0/prompts/preview",
            json=preview_data
        )
        assert response.status_code == 401

class TestPromptErrorCases:
    """Test error cases and validation for prompt endpoints"""
    
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
            email="goricoaico+prompts@gmail.com",
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
        # Clear stores
        if isinstance(self.category_store._store, LocalStore):
            self.category_store._store.data.clear()
        if isinstance(self.prompt_store._store, LocalStore):
            self.prompt_store._store.data.clear()
        if isinstance(self.prompt_set_store._store, LocalStore):
            self.prompt_set_store._store.data.clear()
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_get_category_not_found(self):
        """Test getting a category that doesn't exist"""
        non_existent_id = str(uuid4())
        response = self.client.get(f"/api/v1.0/prompts/categories/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_prompt_not_found(self):
        """Test getting a prompt that doesn't exist"""
        non_existent_id = str(uuid4())
        response = self.client.get(f"/api/v1.0/prompts/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_prompt_set_not_found(self):
        """Test getting a prompt set that doesn't exist"""
        non_existent_id = str(uuid4())
        response = self.client.get(f"/api/v1.0/prompts/sets/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_update_category_not_found(self):
        """Test updating a category that doesn't exist"""
        non_existent_id = str(uuid4())
        update_data = {"name": "Updated Category"}
        response = self.client.put(
            f"/api/v1.0/prompts/categories/{non_existent_id}",
            json=update_data
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_update_prompt_not_found(self):
        """Test updating a prompt that doesn't exist"""
        non_existent_id = str(uuid4())
        update_data = {"name": "Updated Prompt"}
        response = self.client.put(
            f"/api/v1.0/prompts/{non_existent_id}",
            json=update_data
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_update_prompt_set_not_found(self):
        """Test updating a prompt set that doesn't exist"""
        non_existent_id = str(uuid4())
        update_data = {"name": "Updated Set"}
        response = self.client.put(
            f"/api/v1.0/prompts/sets/{non_existent_id}",
            json=update_data
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_category_not_found(self):
        """Test deleting a category that doesn't exist"""
        non_existent_id = str(uuid4())
        response = self.client.delete(f"/api/v1.0/prompts/categories/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_prompt_not_found(self):
        """Test deleting a prompt that doesn't exist"""
        non_existent_id = str(uuid4())
        response = self.client.delete(f"/api/v1.0/prompts/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_delete_prompt_set_not_found(self):
        """Test deleting a prompt set that doesn't exist"""
        non_existent_id = str(uuid4())
        response = self.client.delete(f"/api/v1.0/prompts/sets/{non_existent_id}")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_create_prompt_invalid_category_id(self):
        """Test creating a prompt with invalid category ID"""
        prompt_data = {
            "name": "Test Prompt",
            "description": "A test prompt",
            "content": "Hello {{name}}",
            "category_id": str(uuid4()),  # Non-existent category
            "variables": [
                {
                    "name": "name",
                    "description": "Person's name",
                    "type": "text",
                    "required": True
                }
            ]
        }
        response = self.client.post(
            "/api/v1.0/prompts/",
            json=prompt_data
        )
        # NOTE: Current implementation allows creation with non-existent category_id
        # This test verifies the current behavior - in production this might need validation
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == prompt_data["name"]

    def test_create_prompt_set_invalid_prompt_ids(self):
        """Test creating a prompt set with invalid prompt IDs"""
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

        set_data = {
            "name": "Test Set",
            "description": "A test set",
            "category_id": category_id,
            "prompt_ids": [str(uuid4())]  # Non-existent prompt
        }
        response = self.client.post(
            "/api/v1.0/prompts/sets",
            json=set_data
        )
        # This should fail due to invalid prompt reference
        assert response.status_code == 400
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_invalid_uuid_parameters(self):
        """Test endpoints with invalid UUID parameters"""
        invalid_id = "not-a-uuid"
        
        # Test various endpoints with invalid UUIDs
        endpoints = [
            f"/api/v1.0/prompts/categories/{invalid_id}",
            f"/api/v1.0/prompts/{invalid_id}",
            f"/api/v1.0/prompts/sets/{invalid_id}"
        ]
        
        for endpoint in endpoints:
            for method in ["GET", "PUT", "DELETE"]:
                if method == "GET":
                    response = self.client.get(endpoint)
                elif method == "PUT":
                    response = self.client.put(endpoint, json={"name": "test"})
                else:  # DELETE
                    response = self.client.delete(endpoint)
                
                assert response.status_code == 422  # Validation error

    def test_create_prompt_missing_required_fields(self):
        """Test creating prompt with missing required fields"""
        incomplete_prompt = {
            "name": "Incomplete Prompt"
            # Missing description, content, category_id, variables
        }
        response = self.client.post(
            "/api/v1.0/prompts/",
            json=incomplete_prompt
        )
        assert response.status_code == 422  # Validation error

    def test_create_category_missing_required_fields(self):
        """Test creating category with missing required fields"""
        incomplete_category = {
            "name": "Incomplete Category"
            # Missing description, category_type
        }
        response = self.client.post(
            "/api/v1.0/prompts/categories",
            json=incomplete_category
        )
        assert response.status_code == 422  # Validation error