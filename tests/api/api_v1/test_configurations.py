import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone
from uuid import uuid4

from app.main import app
from app.modules.configurations_store import AIConfigurationStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.schemas import User, GroupCreate
from app.api import deps
from app.core.config import settings

@pytest.fixture
def sample_openai_config():
    return {
        "name": "Test OpenAI Config",
        "description": "A test OpenAI configuration",
        "provider": "openai",
        "endpoint_url": "https://api.openai.com/v1/chat/completions",
        "auth_type": "api_key",
        "model_name": "gpt-3.5-turbo",
        "api_key": "sk-test123456789",
        "timeout_seconds": 30,
        "max_retries": 3,
        "tags": ["test", "openai"]
    }

@pytest.fixture
def sample_anthropic_config():
    return {
        "name": "Test Anthropic Config",
        "description": "A test Anthropic configuration",
        "provider": "anthropic",
        "endpoint_url": "https://api.anthropic.com/v1/messages",
        "auth_type": "api_key",
        "model_name": "claude-3-sonnet-20240229",
        "api_key": "sk-ant-test123456789",
        "timeout_seconds": 30,
        "max_retries": 3,
        "tags": ["test", "anthropic"]
    }

class TestAIConfigurations:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.config_store = AIConfigurationStore(LocalStore())
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        
        # Create a test group
        group_data = GroupCreate(name="Test Group", description="Test group for configs")
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
        self.client.app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear config store by accessing underlying store
        if isinstance(self.config_store._store, LocalStore):
            self.config_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_create_openai_configuration(self, sample_openai_config):
        response = self.client.post(
            "/api/v1.0/configurations/",
            json=sample_openai_config
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_openai_config["name"]
        assert data["provider"] == "openai"
        assert data["model_name"] == sample_openai_config["model_name"]
        assert data["status"] == "testing"  # Default status
        assert "id" in data
        assert "created_at" in data
        # Sensitive data should not be in response
        assert "api_key" not in data
    
    def test_create_anthropic_configuration(self, sample_anthropic_config):
        response = self.client.post(
            "/api/v1.0/configurations/",
            json=sample_anthropic_config
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["provider"] == "anthropic"
        assert data["model_name"] == sample_anthropic_config["model_name"]
    
    def test_get_configurations(self):
        response = self.client.get(
            "/api/v1.0/configurations/"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
    
    def test_get_configuration_by_id(self, sample_openai_config):
        # First create a configuration
        create_response = self.client.post(
            "/api/v1.0/configurations/",
            json=sample_openai_config
        )
        config_id = create_response.json()["id"]
        
        # Then retrieve it
        response = self.client.get(
            f"/api/v1.0/configurations/{config_id}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == config_id
        assert data["name"] == sample_openai_config["name"]
    
    def test_update_configuration(self, sample_openai_config):
        # First create a configuration
        create_response = self.client.post(
            "/api/v1.0/configurations/",
            json=sample_openai_config
        )
        config_id = create_response.json()["id"]
        
        # Update it
        update_data = {
            "name": "Updated OpenAI Config",
            "status": "active"
        }
        response = self.client.put(
            f"/api/v1.0/configurations/{config_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated OpenAI Config"
        assert data["status"] == "active"
    
    def test_delete_configuration(self, sample_openai_config):
        # First create a configuration
        create_response = self.client.post(
            "/api/v1.0/configurations/",
            json=sample_openai_config
        )
        config_id = create_response.json()["id"]
        
        # Delete it
        response = self.client.delete(
            f"/api/v1.0/configurations/{config_id}"
        )
        
        assert response.status_code == 204
        
        # Verify it's gone
        get_response = self.client.get(
            f"/api/v1.0/configurations/{config_id}"
        )
        assert get_response.status_code == 404

class TestConfigurationProviders:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.config_store = AIConfigurationStore(LocalStore())
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        
        # Create a test group
        group_data = GroupCreate(name="Test Group", description="Test group for configs")
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
        self.client.app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear config store by accessing underlying store
        if isinstance(self.config_store._store, LocalStore):
            self.config_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_get_ai_providers(self):
        response = self.client.get(
            "/api/v1.0/configurations/providers/list"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        
        providers = data["providers"]
        assert len(providers) > 0
        
        # Check that we have expected providers
        provider_names = [p["provider"] for p in providers]
        assert "openai" in provider_names
        assert "anthropic" in provider_names
        assert "azure_openai" in provider_names
        
        # Check provider structure
        openai_provider = next(p for p in providers if p["provider"] == "openai")
        assert "display_name" in openai_provider
        assert "description" in openai_provider
        assert "auth_types" in openai_provider
        assert "required_fields" in openai_provider
        assert "api_key" in openai_provider["auth_types"]
    
    def test_get_configuration_templates(self):
        response = self.client.get(
            "/api/v1.0/configurations/templates/list"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        
        templates = data["templates"]
        assert len(templates) > 0
        
        # Check template structure
        template = templates[0]
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "provider" in template
        assert "template_config" in template
        assert "required_user_inputs" in template
    
    def test_filter_templates_by_provider(self):
        response = self.client.get(
            "/api/v1.0/configurations/templates/list?provider=openai"
        )
        
        assert response.status_code == 200
        data = response.json()
        templates = data["templates"]
        
        # All templates should be for OpenAI
        for template in templates:
            assert template["provider"] == "openai"

class TestConfigurationValidation:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.config_store = AIConfigurationStore(LocalStore())
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        
        # Create a test group
        group_data = GroupCreate(name="Test Group", description="Test group for configs")
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
        self.client.app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear config store by accessing underlying store
        if isinstance(self.config_store._store, LocalStore):
            self.config_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_validate_valid_openai_config(self):
        validation_data = {
            "provider": "openai",
            "endpoint_url": "https://api.openai.com/v1/chat/completions",
            "auth_type": "api_key",
            "model_name": "gpt-3.5-turbo",
            "api_key": "sk-test123456789"  # Required field for OpenAI
        }
        
        response = self.client.post(
            "/api/v1.0/configurations/validate",
            json=validation_data
        )
        
        assert response.status_code == 200
        data = response.json()
        print(data)
        assert data["is_valid"] is True
        assert len(data["errors"]) == 0
    
    def test_validate_invalid_config_missing_fields(self):
        validation_data = {
            "provider": "openai",
            "auth_type": "api_key"
            # Missing required fields
        }
        
        response = self.client.post(
            "/api/v1.0/configurations/validate",
            json=validation_data
        )
        
        assert response.status_code == 422
        # This test validates that FastAPI correctly rejects requests missing required schema fields
    
    def test_validate_unsupported_provider(self):
        validation_data = {
            "provider": "unsupported_provider",
            "endpoint_url": "https://example.com/api",
            "auth_type": "api_key",
            "model_name": "some-model"
        }
        
        response = self.client.post(
            "/api/v1.0/configurations/validate",
            json=validation_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_valid"] is False
        assert "Unsupported provider" in data["errors"][0]

class TestConfigurationTesting:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.config_store = AIConfigurationStore(LocalStore())
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        
        # Create a test group
        group_data = GroupCreate(name="Test Group", description="Test group for configs")
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
        self.client.app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear config store by accessing underlying store
        if isinstance(self.config_store._store, LocalStore):
            self.config_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_test_configuration_endpoint_exists(self, sample_openai_config):
        # Create a configuration first
        create_response = self.client.post(
            "/api/v1.0/configurations/",
            json=sample_openai_config
        )
        config_id = create_response.json()["id"]
        
        # Test the configuration (this will likely fail due to invalid API key, but endpoint should exist)
        test_data = {
            "test_prompt": "Hello, world!",
            "max_tokens": 50,
            "temperature": 0.7
        }
        
        response = self.client.post(
            f"/api/v1.0/configurations/{config_id}/test",
            json=test_data
        )
        
        # Should return 200 even if test fails (failure is about the AI service, not our API)
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "response_time_ms" in data
        assert "test_timestamp" in data
        # Since we're using a fake API key, this should fail
        assert data["success"] is False
        assert data["error_message"] is not None

class TestConfigurationFiltering:
    def setup_method(self, method):
        """Setup test environment before each test"""
        self.client = TestClient(app)
        self.config_store = AIConfigurationStore(LocalStore())
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        
        # Create a test group
        group_data = GroupCreate(name="Test Group", description="Test group for configs")
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
        self.client.app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        self.client.app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        self.client.app.dependency_overrides[deps.get_group_store] = lambda: self.group_store

    def teardown_method(self, method):
        """Clean up after each test"""
        self.client.app.dependency_overrides = {}
        # Clear config store by accessing underlying store
        if isinstance(self.config_store._store, LocalStore):
            self.config_store._store.data.clear()
        # Clear user and group stores
        if isinstance(self.user_store._store, LocalStore):
            self.user_store._store.data.clear()
        if isinstance(self.group_store._store, LocalStore):
            self.group_store._store.data.clear()

    def test_filter_by_status(self):
        response = self.client.get(
            "/api/v1.0/configurations/?status=active"
        )
        
        assert response.status_code == 200
        data = response.json()
        for config in data["items"]:
            assert config["status"] == "active"
    
    def test_filter_by_provider(self):
        response = self.client.get(
            "/api/v1.0/configurations/?provider=openai"
        )
        
        assert response.status_code == 200
        data = response.json()
        for config in data["items"]:
            assert config["provider"] == "openai"
    
    def test_search_configurations(self):
        response = self.client.get(
            "/api/v1.0/configurations/?search=test"
        )
        
        assert response.status_code == 200
        # Response should be valid even if no results found
        data = response.json()
        assert "items" in data
    
    def test_my_configurations_filter(self):
        response = self.client.get(
            "/api/v1.0/configurations/?my_configs=true"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_pagination(self):
        response = self.client.get(
            "/api/v1.0/configurations/?page=1&limit=5"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["limit"] == 5
        assert len(data["items"]) <= 5