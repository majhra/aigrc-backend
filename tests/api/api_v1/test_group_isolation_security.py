"""
API-level security tests for group isolation.

These tests focus on security boundary testing and edge cases:
1. Attempting to override group_id parameters
2. Testing with malformed group_id values
3. Testing privilege escalation attempts
4. Testing boundary conditions and edge cases
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas import (
    User, 
    AITestCreate, ConnectionConfig, ValidationConfig, ValidationCriterion,
    AIEndpointConfigCreate, 
    PromptCategoryCreate, PromptCreate, PromptVariable
)
from app.modules.tests_store import AITestStore
from app.modules.configurations_store import AIConfigurationStore
from app.modules.prompts_store import PromptCategoryStore, PromptStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.core.config import settings
from app.api import deps


class TestGroupIsolationSecurity:
    """Security-focused tests for group isolation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Initialize stores
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        self.config_store = AIConfigurationStore(LocalStore())
        self.category_store = PromptCategoryStore(LocalStore())
        self.prompt_store = PromptStore(LocalStore())
        self.test_store = AITestStore(LocalStore())
        
        # Create test groups
        from app.schemas import GroupCreate
        group1_data = GroupCreate(name="Secure Group", description="Secure group")
        group2_data = GroupCreate(name="Public Group", description="Public group")
        
        self.secure_group = self.group_store.create(group1_data, "system")
        self.public_group = self.group_store.create(group2_data, "system")
        
        # Create test users
        self.secure_user = User(
            id=uuid4(),
            email="goricoaico+secure@gmail.com",
            full_name="Secure User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group=str(self.secure_group.id)
        )
        
        self.public_user = User(
            id=uuid4(),
            email="goricoaico+public@gmail.com",
            full_name="Public User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group=str(self.public_group.id)
        )
        
        self.no_group_user = User(
            id=uuid4(),
            email="goricoaico+nogroup@gmail.com",
            full_name="No Group User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group=None  # User with no group
        )
        
        # Store users
        self.user_store.create(self.secure_user, str(self.secure_group.id))
        self.user_store.create(self.public_user, str(self.public_group.id))
        self.user_store.create(self.no_group_user, "default")

    def test_group_id_injection_attempt_in_configuration_creation(self, request):
        """Test that group_id cannot be injected in configuration creation requests."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.public_user
        
        # Attempt to create configuration with injected group_id
        malicious_data = {
            "name": "Injected Config",
            "description": "Malicious config with injected group",
            "provider": "openai",
            "model_name": "gpt-4",
            "endpoint_url": "https://api.openai.com/v1/chat/completions",
            "auth_type": "api_key",
            "api_key": "dummy-key",
            "group_id": str(self.secure_group.id),  # Attempt to inject different group
            "created_by": str(self.secure_user.id)  # Attempt to spoof creator
        }
        
        response = client.post(f"{settings.API_V1_STR}/configurations", json=malicious_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify the group_id was set from the authenticated user, not the request
        data = response.json()
        assert data["group_id"] == str(self.public_group.id)  # Should be public_user's group
        assert data["created_by"] == str(self.public_user.id)  # Should be authenticated user
        assert data["group_id"] != str(self.secure_group.id)  # Should NOT be injected group

    def test_malformed_group_id_in_requests(self, request):
        """Test handling of malformed group_id values in requests."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.secure_user
        
        # Test with various malformed group_id values
        malformed_values = [
            "invalid-uuid",
            "00000000-0000-0000-0000-000000000000",
            "' OR 1=1 --",  # SQL injection attempt
            "<script>alert('xss')</script>",  # XSS attempt
            "../../../etc/passwd",  # Path traversal attempt
            None,
            "",
            123,
            {"nested": "object"}
        ]
        
        for malformed_value in malformed_values:
            category_data = {
                "name": f"Test Category {malformed_value}",
                "description": "Test category",
                "category_type": "CUSTOM",
                "group_id": malformed_value  # Malformed group_id
            }
            
            response = client.post(f"{settings.API_V1_STR}/prompts/categories", json=category_data)
            
            if response.status_code == status.HTTP_201_CREATED:
                # If creation succeeds, verify group_id was set correctly
                data = response.json()
                assert data["group_id"] == str(self.secure_group.id)  # Should be user's group
            # If it fails, that's also acceptable (request validation)

    def test_privilege_escalation_via_admin_endpoints(self, request):
        """Test that regular users cannot escalate privileges via admin endpoints."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a config in secure group
        secure_config = self.config_store.create(
            AIEndpointConfigCreate(
                name="Secure Config",
                description="Secure configuration for testing",
                provider="openai",
                model_name="gpt-4",
                endpoint_url="https://api.openai.com/v1/chat/completions",
                auth_type="api_key",
                api_key="dummy-key"
            ),
            self.secure_user
        )
        
        # Test public_user trying to access secure config by manipulating request
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.public_user
        
        # Attempt various privilege escalation techniques
        escalation_attempts = [
            # Try to add admin headers
            {"X-Admin-Override": "true"},
            {"X-Group-Override": str(self.secure_group.id)},
            {"Authorization": "Bearer admin-token"},
            # Try various URL manipulations
        ]
        
        for headers in escalation_attempts:
            response = client.get(
                f"{settings.API_V1_STR}/configurations/{secure_config.id}",
                headers=headers
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_user_with_no_group_access_patterns(self, request):
        """Test access patterns for users with no group assigned."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.no_group_user
        
        # Test creating entities with no group user
        config_data = {
            "name": "No Group Config",
            "description": "Configuration for user with no group",
            "provider": "openai",
            "model_name": "gpt-4",
            "endpoint_url": "https://api.openai.com/v1/chat/completions",
            "auth_type": "api_key",
            "api_key": "dummy-key"
        }
        
        response = client.post(f"{settings.API_V1_STR}/configurations", json=config_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify group_id is set to default for users with no group
        data = response.json()
        assert data["group_id"] == "default"
        
        # Test listing - user should only see their own entities
        response = client.get(f"{settings.API_V1_STR}/configurations")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["group_id"] == "default"

    def test_concurrent_access_attempt_race_condition(self, request):
        """Test for race conditions in group access control."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a config as secure_user
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.secure_user
        
        config_data = {
            "name": "Race Condition Test Config",
            "description": "Configuration for race condition testing",
            "provider": "openai",
            "model_name": "gpt-4",
            "endpoint_url": "https://api.openai.com/v1/chat/completions",
            "auth_type": "api_key",
            "api_key": "dummy-key"
        }
        
        response = client.post(f"{settings.API_V1_STR}/configurations", json=config_data)
        assert response.status_code == status.HTTP_201_CREATED
        config_id = response.json()["id"]
        
        # Rapidly switch users and attempt access (simulating race condition)
        for i in range(10):
            if i % 2 == 0:
                app.dependency_overrides[deps.get_current_active_user] = lambda: self.secure_user
                expected_status = status.HTTP_200_OK
            else:
                app.dependency_overrides[deps.get_current_active_user] = lambda: self.public_user
                expected_status = status.HTTP_403_FORBIDDEN
            
            response = client.get(f"{settings.API_V1_STR}/configurations/{config_id}")
            assert response.status_code == expected_status

    def test_group_id_parameter_sanitization(self, request):
        """Test that group_id parameters are properly sanitized and validated."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.secure_user
        
        # Create a category first
        category_data = {
            "name": "Test Category",
            "description": "Test category",
            "category_type": "CUSTOM"
        }
        response = client.post(f"{settings.API_V1_STR}/prompts/categories", json=category_data)
        assert response.status_code == status.HTTP_201_CREATED
        category_id = response.json()["id"]
        
        # Test creating prompt with various group_id injection attempts
        injection_attempts = [
            {"group_id": "'; DROP TABLE configurations; --"},
            {"group_id": {"$ne": None}},  # NoSQL injection
            {"group_id": ["array", "injection"]},
            {"group_id": f"'{self.public_group.id}' UNION SELECT * FROM users --"}
        ]
        
        for attempt in injection_attempts:
            prompt_data = {
                "name": "Injection Test Prompt",
                "description": "Test prompt for injection",
                "content": "Test content: {{input}}",
                "category_id": category_id,
                "variables": [
                    {
                        "name": "input",
                        "description": "Test input",
                        "type": "text",
                        "required": True
                    }
                ],
                "risk_level": "LOW",
                **attempt  # Add injection attempt
            }
            
            response = client.post(f"{settings.API_V1_STR}/prompts/", json=prompt_data)
            
            if response.status_code == status.HTTP_201_CREATED:
                # If creation succeeds, verify group_id was set correctly
                data = response.json()
                assert data["group_id"] == str(self.secure_group.id)

    def test_cross_group_reference_validation(self, request):
        """Test validation of cross-group references in entity relationships."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create category in secure group
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.secure_user
        
        category_data = {
            "name": "Secure Category",
            "description": "Secure category",
            "category_type": "SAFETY"
        }
        response = client.post(f"{settings.API_V1_STR}/prompts/categories", json=category_data)
        assert response.status_code == status.HTTP_201_CREATED
        secure_category_id = response.json()["id"]
        
        # Switch to public user and attempt to create prompt referencing secure category
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.public_user
        
        prompt_data = {
            "name": "Cross Group Reference Attempt",
            "description": "Attempting to reference secure category",
            "content": "Test content: {{input}}",
            "category_id": secure_category_id,  # Reference to secure group's category
            "variables": [
                {
                    "name": "input",
                    "description": "Test input",
                    "type": "text",
                    "required": True
                }
            ],
            "risk_level": "LOW"
        }
        
        response = client.post(f"{settings.API_V1_STR}/prompts/", json=prompt_data)
        
        # This should either:
        # 1. Fail with 400/403 due to invalid category reference, OR
        # 2. Succeed but create prompt in public user's group with correct group_id
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["group_id"] == str(self.public_group.id)  # Should be in public group
        else:
            # Failure is also acceptable - indicates proper validation
            assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]

    def test_url_parameter_manipulation(self, request):
        """Test manipulation of URL parameters to access other groups' resources."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create config in secure group
        secure_config = self.config_store.create(
            AIEndpointConfigCreate(
                name="URL Manipulation Test",
                description="Configuration for URL manipulation testing",
                provider="openai",
                model_name="gpt-4",
                endpoint_url="https://api.openai.com/v1/chat/completions",
                auth_type="api_key",
                api_key="dummy-key"
            ),
            self.secure_user
        )
        
        # Test public_user trying various URL manipulations
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.public_user
        
        manipulation_attempts = [
            # Standard access (should fail)
            f"{settings.API_V1_STR}/configurations/{secure_config.id}",
            # Path traversal attempts
            f"{settings.API_V1_STR}/configurations/../configurations/{secure_config.id}",
            f"{settings.API_V1_STR}/configurations/./../configurations/{secure_config.id}",
            # Encoding attempts
            f"{settings.API_V1_STR}/configurations/%2e%2e%2fconfigurations/{secure_config.id}",
        ]
        
        for url in manipulation_attempts:
            response = client.get(url)
            # All attempts should fail with 403 or 404
            assert response.status_code in [
                status.HTTP_403_FORBIDDEN, 
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY  # For malformed URLs
            ]