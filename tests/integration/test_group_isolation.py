"""
Integration tests to verify group isolation across all entities.

These tests ensure that:
1. Users can only see entities from their own group (unless admin)
2. Users cannot access entities from other groups
3. Admin users can access entities across all groups
4. Group_id cannot be overridden by client requests
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
    PromptCategoryCreate, PromptCreate, PromptSetCreate, PromptVariable
)
from app.modules.tests_store import AITestStore
from app.modules.configurations_store import AIConfigurationStore
from app.modules.prompts_store import PromptCategoryStore, PromptStore, PromptSetStore
from app.modules.executions_store import ExecutedTestStore
from app.modules.user_store import UserStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.core.config import settings
from app.api import deps


class TestGroupIsolation:
    """Test group isolation across all entities in the system."""

    def setup_method(self):
        """Set up test fixtures with multiple groups and users."""
        # Initialize stores
        self.user_store = UserStore(LocalStore())
        self.group_store = GroupStore(LocalStore())
        self.test_store = AITestStore(LocalStore())
        self.config_store = AIConfigurationStore(LocalStore())
        self.category_store = PromptCategoryStore(LocalStore())
        self.prompt_store = PromptStore(LocalStore())
        self.prompt_set_store = PromptSetStore(LocalStore())
        self.execution_store = ExecutedTestStore(LocalStore())
        
        # Create test groups
        from app.schemas import GroupCreate
        group1_data = GroupCreate(name="Engineering Team", description="Engineering group")
        group2_data = GroupCreate(name="QA Team", description="QA group")
        group3_data = GroupCreate(name="Security Team", description="Security group")
        
        self.group1 = self.group_store.create(group1_data, "system")
        self.group2 = self.group_store.create(group2_data, "system")
        self.group3 = self.group_store.create(group3_data, "system")
        
        # Create test users for each group
        self.eng_user = User(
            id=uuid4(),
            email="goricoaico+eng@gmail.com",
            full_name="Engineering User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group=str(self.group1.id)
        )
        
        self.qa_user = User(
            id=uuid4(),
            email="goricoaico+qa@gmail.com",
            full_name="QA User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group=str(self.group2.id)
        )
        
        self.sec_user = User(
            id=uuid4(),
            email="goricoaico+sec@gmail.com",
            full_name="Security User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="user",
            group=str(self.group3.id)
        )
        
        self.admin_user = User(
            id=uuid4(),
            email="goricoaico+admin@gmail.com",
            full_name="Admin User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            role="admin",
            group=str(self.group1.id)  # Admin belongs to group1 but can access all
        )
        
        # Store users
        self.user_store.create(self.eng_user, str(self.group1.id))
        self.user_store.create(self.qa_user, str(self.group2.id))
        self.user_store.create(self.sec_user, str(self.group3.id))
        self.user_store.create(self.admin_user, str(self.group1.id))
        
        # Create test data templates
        self.test_template = AITestCreate(
            name="Security Test",
            description="Test for security validation",
            prompt_template="Analyze this code for security issues: {code}",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.openai.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="dummy-key"
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="security_check",
                        name="Security Check",
                        description="Check for security vulnerabilities",
                        type="manual_review"
                    )
                ]
            ),
            tags=["security", "validation"],
            risk_level="HIGH",
            status="ACTIVE"
        )
        
        self.config_template = AIEndpointConfigCreate(
            name="OpenAI GPT-4 Config",
            description="GPT-4 configuration for testing",
            provider="openai",
            model_name="gpt-4",
            endpoint_url="https://api.openai.com/v1/chat/completions",
            auth_type="api_key",
            api_key="dummy-key"
        )
        
        self.category_template = PromptCategoryCreate(
            name="Security Prompts",
            description="Prompts for security analysis",
            category_type="SAFETY",
            priority="HIGH",
            tags=["security", "analysis"]
        )

    def test_configurations_group_isolation(self, request):
        """Test that configurations are properly isolated by group."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create configs for different groups
        eng_config = self.config_store.create(self.config_template, self.eng_user)
        qa_config_data = self.config_template.model_dump()
        qa_config_data["name"] = "QA OpenAI Config"
        qa_config_data["description"] = "QA team GPT-4 configuration"
        qa_config = self.config_store.create(AIEndpointConfigCreate(**qa_config_data), self.qa_user)
        
        # Test eng_user can only see their group's configs
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.eng_user
        
        response = client.get(f"{settings.API_V1_STR}/configurations")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(eng_config.id)
        assert data["items"][0]["group_id"] == str(self.group1.id)
        
        # Test qa_user can only see their group's configs
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.qa_user
        
        response = client.get(f"{settings.API_V1_STR}/configurations")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(qa_config.id)
        assert data["items"][0]["group_id"] == str(self.group2.id)
        
        # Test admin can see all configs
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.admin_user
        
        response = client.get(f"{settings.API_V1_STR}/configurations")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 2
        config_ids = [item["id"] for item in data["items"]]
        assert str(eng_config.id) in config_ids
        assert str(qa_config.id) in config_ids

    def test_cross_group_configuration_access_denied(self, request):
        """Test that users cannot access configurations from other groups."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create config for eng_user
        eng_config = self.config_store.create(self.config_template, self.eng_user)
        
        # Test qa_user cannot access eng_user's config
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.qa_user
        
        response = client.get(f"{settings.API_V1_STR}/configurations/{eng_config.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied: Configuration does not belong to your group" in response.json()["detail"]
        
        # Test qa_user cannot update eng_user's config
        update_data = {"name": "Hacked Config"}
        response = client.put(f"{settings.API_V1_STR}/configurations/{eng_config.id}", json=update_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Test qa_user cannot delete eng_user's config
        response = client.delete(f"{settings.API_V1_STR}/configurations/{eng_config.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_prompt_categories_group_isolation(self, request):
        """Test that prompt categories are properly isolated by group."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create categories for different groups
        eng_category = self.category_store.create(self.category_template, self.eng_user)
        qa_category_data = self.category_template.model_dump()
        qa_category_data["name"] = "QA Testing Prompts"
        qa_category = self.category_store.create(PromptCategoryCreate(**qa_category_data), self.qa_user)
        
        # Test eng_user can only see their group's categories
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.eng_user
        
        response = client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(eng_category.id)
        assert data["items"][0]["group_id"] == str(self.group1.id)
        
        # Test qa_user can only see their group's categories
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.qa_user
        
        response = client.get(f"{settings.API_V1_STR}/prompts/categories")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(qa_category.id)
        assert data["items"][0]["group_id"] == str(self.group2.id)

    def test_prompts_group_isolation(self, request):
        """Test that prompts are properly isolated by group."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create categories first
        eng_category = self.category_store.create(self.category_template, self.eng_user)
        qa_category_data = self.category_template.model_dump()
        qa_category_data["name"] = "QA Category"
        qa_category = self.category_store.create(PromptCategoryCreate(**qa_category_data), self.qa_user)
        
        # Create prompts for different groups
        prompt_template = PromptCreate(
            name="Security Analysis Prompt",
            description="Analyze code for security vulnerabilities",
            content="Review this code and identify security issues: {{code}}",
            category_id=UUID(str(eng_category.id)),
            variables=[
                PromptVariable(
                    name="code",
                    description="Code to analyze",
                    type="text",
                    required=True
                )
            ],
            tags=["security", "analysis"],
            risk_level="HIGH"
        )
        
        eng_prompt = self.prompt_store.create(prompt_template, self.eng_user)
        
        qa_prompt_data = prompt_template.model_dump()
        qa_prompt_data["name"] = "QA Test Prompt"
        qa_prompt_data["category_id"] = UUID(str(qa_category.id))
        qa_prompt = self.prompt_store.create(PromptCreate(**qa_prompt_data), self.qa_user)
        
        # Test eng_user can only see their group's prompts
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.eng_user
        
        response = client.get(f"{settings.API_V1_STR}/prompts/")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(eng_prompt.id)
        assert data["items"][0]["group_id"] == str(self.group1.id)

    def test_group_id_cannot_be_overridden_in_requests(self, request):
        """Test that users cannot override group_id in their requests."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Test with eng_user trying to create config for a different group
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.eng_user
        
        # Try to create config with different group_id in payload (should be ignored)
        malicious_config_data = self.config_template.model_dump()
        malicious_config_data["group_id"] = str(self.group2.id)  # Try to set different group
        
        response = client.post(f"{settings.API_V1_STR}/configurations", json=malicious_config_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify the group_id was set from the user's group, not the request
        data = response.json()
        assert data["group_id"] == str(self.group1.id)  # Should be eng_user's group
        assert data["group_id"] != str(self.group2.id)  # Should NOT be the malicious group

    def test_admin_cross_group_access(self, request):
        """Test that admin users can access entities across all groups."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create entities in different groups
        eng_config = self.config_store.create(self.config_template, self.eng_user)
        qa_category = self.category_store.create(self.category_template, self.qa_user)
        
        # Test admin can access eng_user's config
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.admin_user
        
        response = client.get(f"{settings.API_V1_STR}/configurations/{eng_config.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["group_id"] == str(self.group1.id)
        
        # Test admin can access qa_user's category
        response = client.get(f"{settings.API_V1_STR}/prompts/categories/{qa_category.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["group_id"] == str(self.group2.id)
        
        # Test admin can update entities from other groups
        update_data = {"description": "Updated by admin"}
        response = client.put(f"{settings.API_V1_STR}/configurations/{eng_config.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["description"] == "Updated by admin"

    def test_test_execution_inherits_group_from_test(self, request):
        """Test that test executions inherit group_id from their parent test."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_execution_store] = lambda: self.execution_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a test for eng_user
        test = self.test_store.create(self.test_template, self.eng_user)
        assert test.group_id == str(self.group1.id)
        
        # Test eng_user executing their own test
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.eng_user
        
        execution_data = {
            "execution_environment": {
                "environment_id": "test",
                "version": "1.0",
                "parameters": {}
            },
            "input_variables": {"code": "test code"}
        }
        
        # Mock AI service to avoid external calls
        from unittest.mock import MagicMock, patch, AsyncMock
        with patch('app.api.api_v1.endpoints.tests.AIConnectionService') as mock_ai_service:
            mock_instance = MagicMock()
            mock_instance.execute_prompt = AsyncMock(return_value={
                "response": "Test response",
                "benchmarks": {
                    "response_time": 1.5,
                    "total_time": 2.0,
                    "token_usage": {
                        "prompt": 10,
                        "completion": 20,
                        "total": 30
                    }
                }
            })
            mock_instance._format_prompt.return_value = "Formatted prompt"
            mock_ai_service.return_value = mock_instance
            
            response = client.post(f"{settings.API_V1_STR}/tests/{test.id}/execute", json=execution_data)
            assert response.status_code == status.HTTP_201_CREATED
            
            # Verify execution inherited group_id from test
            execution_data = response.json()
            assert execution_data["group_id"] == str(self.group1.id)
            assert execution_data["test_id"] == str(test.id)

    def test_user_cannot_execute_tests_from_other_groups(self, request):
        """Test that users cannot execute tests from other groups."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_execution_store] = lambda: self.execution_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Create a test for eng_user
        test = self.test_store.create(self.test_template, self.eng_user)
        
        # Test qa_user cannot execute eng_user's test
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.qa_user
        
        execution_data = {
            "execution_environment": {
                "environment_id": "test",
                "version": "1.0",
                "parameters": {}
            },
            "input_variables": {"code": "malicious code"}
        }
        
        # Since the access control happens before AI execution, we don't need to mock AI service here
        response = client.post(f"{settings.API_V1_STR}/tests/{test.id}/execute", json=execution_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "Access denied: Test does not belong to your group" in response.json()["detail"]

    def test_comprehensive_entity_creation_sets_correct_group(self, request):
        """Test that all entity creation sets correct group_id from user."""
        app = request.instance.app
        client = request.instance.client
        
        # Set up dependency overrides for all stores
        app.dependency_overrides[deps.get_config_store] = lambda: self.config_store
        app.dependency_overrides[deps.get_category_store] = lambda: self.category_store
        app.dependency_overrides[deps.get_prompt_store] = lambda: self.prompt_store
        app.dependency_overrides[deps.get_prompt_set_store] = lambda: self.prompt_set_store
        app.dependency_overrides[deps.get_test_store] = lambda: self.test_store
        app.dependency_overrides[deps.get_user_store] = lambda: self.user_store
        app.dependency_overrides[deps.get_group_store] = lambda: self.group_store
        
        # Test with sec_user (group3)
        app.dependency_overrides[deps.get_current_active_user] = lambda: self.sec_user
        
        # Create configuration
        config_data = self.config_template.model_dump()
        response = client.post(f"{settings.API_V1_STR}/configurations", json=config_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["group_id"] == str(self.group3.id)
        
        # Create category
        response = client.post(f"{settings.API_V1_STR}/prompts/categories", json=self.category_template.model_dump())
        assert response.status_code == status.HTTP_201_CREATED
        category_data = response.json()
        assert category_data["group_id"] == str(self.group3.id)
        
        # Create prompt
        prompt_data = {
            "name": "Security Prompt",
            "description": "Security analysis prompt",
            "content": "Analyze: {{input}}",
            "category_id": category_data["id"],
            "variables": [
                {
                    "name": "input",
                    "description": "Input to analyze",
                    "type": "text",
                    "required": True
                }
            ],
            "risk_level": "HIGH"
        }
        response = client.post(f"{settings.API_V1_STR}/prompts/", json=prompt_data)
        assert response.status_code == status.HTTP_201_CREATED
        prompt_response = response.json()
        assert prompt_response["group_id"] == str(self.group3.id)
        
        # Create prompt set
        prompt_set_data = {
            "name": "Security Prompt Set",
            "description": "Collection of security prompts",
            "category_id": category_data["id"],
            "prompt_ids": [prompt_response["id"]]
        }
        response = client.post(f"{settings.API_V1_STR}/prompts/sets", json=prompt_set_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["group_id"] == str(self.group3.id)
        
        # Create test
        response = client.post(f"{settings.API_V1_STR}/tests", json=self.test_template.model_dump())
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["group_id"] == str(self.group3.id)