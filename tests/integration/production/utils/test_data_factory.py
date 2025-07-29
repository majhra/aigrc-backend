"""
Test Data Factory for Production Integration Testing

Provides utilities for creating realistic test data that can be used
across multiple test scenarios.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ProductionTestUser:
    """Test user data structure"""
    email: str
    password: str
    full_name: str
    role: str = "user"
    group: Optional[str] = None
    is_verified: bool = False
    id: Optional[str] = None
    access_token: Optional[str] = None


@dataclass
class ProductionTestGroup:
    """Test group data structure"""
    name: str
    description: str
    id: Optional[str] = None


@dataclass
class ProductionTestPrompt:
    """Test prompt data structure"""
    name: str
    description: str
    template: str
    category_id: Optional[str] = None
    tags: List[str] = None
    id: Optional[str] = None


@dataclass
class ProductionTestPromptCategory:
    """Test prompt category data structure"""
    name: str
    description: str
    id: Optional[str] = None


@dataclass
class ProductionTestConfiguration:
    """Test AI configuration data structure"""
    name: str
    description: str
    endpoint: str
    auth_type: str = "API_KEY"
    auth_string: str = "test-api-key"
    provider: str = "openai"
    model: str = "gpt-3.5-turbo"
    id: Optional[str] = None


@dataclass
class ProductionTestAITest:
    """Test AI test data structure"""
    name: str
    description: str
    prompt_template: str
    interface_type: str = "DIRECT_LLM"
    connection_config: Optional[Dict] = None
    validation_config: Optional[Dict] = None
    tags: List[str] = None
    risk_level: str = "LOW"
    status: str = "ACTIVE"
    id: Optional[str] = None


class ProductionDataFactory:
    """Factory for creating test data with realistic values"""
    
    def __init__(self):
        self._counter = 0
    
    def _get_unique_id(self) -> str:
        """Generate unique identifier for test data"""
        self._counter += 1
        return f"test_{self._counter}_{uuid.uuid4().hex[:8]}"
    
    def _get_unique_email(self, prefix: str = "test") -> str:
        """Generate unique email for testing"""
        unique_id = self._get_unique_id()
        return f"goricoaico+{prefix}_{unique_id}@gmail.com"
    
    # User creation methods
    def create_admin_user(self, **overrides) -> ProductionTestUser:
        """Create admin user with default values"""
        defaults = {
            "email": self._get_unique_email("admin"),
            "password": "AdminPass123!",
            "full_name": "Admin User",
            "role": "admin"
        }
        defaults.update(overrides)
        return ProductionTestUser(**defaults)
    
    def create_regular_user(self, **overrides) -> ProductionTestUser:
        """Create regular user with default values"""
        defaults = {
            "email": self._get_unique_email("user"),
            "password": "UserPass123!",
            "full_name": "Regular User",
            "role": "user"
        }
        defaults.update(overrides)
        return ProductionTestUser(**defaults)
    
    def create_user_in_group(self, group_id: str, role: str = "user", **overrides) -> ProductionTestUser:
        """Create user in specific group"""
        defaults = {
            "group": group_id,
            "role": role
        }
        defaults.update(overrides)
        
        if role == "admin":
            return self.create_admin_user(**defaults)
        else:
            return self.create_regular_user(**defaults)
    
    # Group creation methods
    def create_group(self, **overrides) -> ProductionTestGroup:
        """Create test group with default values"""
        unique_id = self._get_unique_id()
        defaults = {
            "name": f"Test Group {unique_id}",
            "description": f"Test group for integration testing {unique_id}"
        }
        defaults.update(overrides)
        return ProductionTestGroup(**defaults)
    
    # Prompt and category creation methods
    def create_prompt_category(self, **overrides) -> ProductionTestPromptCategory:
        """Create test prompt category"""
        unique_id = self._get_unique_id()
        defaults = {
            "name": f"Test Category {unique_id}",
            "description": f"Test category for integration testing {unique_id}"
        }
        defaults.update(overrides)
        return ProductionTestPromptCategory(**defaults)
    
    def create_prompt(self, **overrides) -> ProductionTestPrompt:
        """Create test prompt"""
        unique_id = self._get_unique_id()
        defaults = {
            "name": f"Test Prompt {unique_id}",
            "description": f"Test prompt for integration testing {unique_id}",
            "template": f"Test prompt template {unique_id}: {{input_variable}}",
            "tags": ["integration", "test"]
        }
        defaults.update(overrides)
        return ProductionTestPrompt(**defaults)
    
    # Configuration creation methods
    def create_ai_configuration(self, **overrides) -> ProductionTestConfiguration:
        """Create test AI configuration"""
        unique_id = self._get_unique_id()
        defaults = {
            "name": f"Test Config {unique_id}",
            "description": f"Test AI configuration {unique_id}",
            "endpoint": f"https://api.example.com/v1/test_{unique_id}",
            "auth_type": "API_KEY",
            "auth_string": f"test-key-{unique_id}",
            "provider": "openai",
            "model": "gpt-3.5-turbo"
        }
        defaults.update(overrides)
        return ProductionTestConfiguration(**defaults)
    
    # AI Test creation methods
    def create_ai_test(self, **overrides) -> ProductionTestAITest:
        """Create test AI test"""
        unique_id = self._get_unique_id()
        
        # Default connection config
        default_connection_config = {
            "endpoint": f"https://api.example.com/v1/test_{unique_id}",
            "auth_type": "API_KEY",
            "auth_string": f"test-key-{unique_id}",
            "provider": "openai",
            "model": "gpt-3.5-turbo"
        }
        
        # Default validation config
        default_validation_config = {
            "validator_type": "HUMAN",
            "validation_criteria": [{
                "id": f"criterion_{unique_id}",
                "name": f"Test Criterion {unique_id}",
                "description": f"Test validation criterion {unique_id}",
                "type": "exact_match"
            }]
        }
        
        defaults = {
            "name": f"Test AI Test {unique_id}",
            "description": f"AI test for integration testing {unique_id}",
            "prompt_template": f"Test prompt: {{input}} - {unique_id}",
            "interface_type": "DIRECT_LLM",
            "connection_config": default_connection_config,
            "validation_config": default_validation_config,
            "tags": ["integration", "test"],
            "risk_level": "LOW",
            "status": "ACTIVE"
        }
        defaults.update(overrides)
        return ProductionTestAITest(**defaults)
    
    # Execution data
    def create_execution_data(self, **overrides) -> Dict[str, Any]:
        """Create test execution data"""
        defaults = {
            "input_variables": {"input": "test input"},
            "execution_environment": {
                "environment_id": "integration_test",
                "version": "1.0.0",
                "parameters": {
                    "source": "integration_test",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
        }
        defaults.update(overrides)
        return defaults
    
    # Validation data
    def create_validation_data(self, validator_id: str, **overrides) -> Dict[str, Any]:
        """Create test validation data"""
        defaults = {
            "validator_id": validator_id,
            "validator_type": "HUMAN",
            "status": "PASS",
            "notes": "Integration test validation",
            "confidence": 0.95
        }
        defaults.update(overrides)
        return defaults
    
    # Utility methods
    def to_api_format(self, obj) -> Dict[str, Any]:
        """Convert dataclass object to API-compatible dictionary"""
        if hasattr(obj, '__dict__'):
            data = asdict(obj)
            # Remove None values and internal fields
            result = {k: v for k, v in data.items() if v is not None and not k.startswith('_')}
            
            # Handle ProductionTestPrompt specific conversions
            if isinstance(obj, ProductionTestPrompt):
                # Convert 'template' field to 'content' for API
                if 'template' in result:
                    result['content'] = result.pop('template')
                
                # Note: category_id should be provided by the test or will need to be created first
                # The hardcoded category_id approach doesn't work in production tests
            
            # Handle ProductionTestConfiguration specific conversions
            elif isinstance(obj, ProductionTestConfiguration):
                # Convert field names to match API schema
                if 'endpoint' in result:
                    result['endpoint_url'] = result.pop('endpoint')
                if 'model' in result:
                    result['model_name'] = result.pop('model')
                if 'auth_string' in result:
                    # Convert auth_string to appropriate auth field based on auth_type
                    auth_type = result.get('auth_type', 'api_key').lower()
                    if auth_type in ['api_key', 'API_KEY']:
                        result['api_key'] = result.pop('auth_string')
                    elif auth_type in ['bearer_token', 'BEARER_TOKEN']:
                        result['bearer_token'] = result.pop('auth_string')
                    else:
                        result.pop('auth_string', None)
                
                # Ensure auth_type is lowercase
                if 'auth_type' in result:
                    result['auth_type'] = result['auth_type'].lower().replace('_', '_')
            
            return result
        return obj
    
    def create_test_scenario(self, name: str = "default") -> Dict[str, Any]:
        """Create a complete test scenario with all related data"""
        unique_id = self._get_unique_id()
        
        # Create groups
        group1 = self.create_group(name=f"Group 1 {unique_id}")
        group2 = self.create_group(name=f"Group 2 {unique_id}")
        
        # Create users
        admin = self.create_admin_user(group=None)  # Admin has access to all groups
        user1 = self.create_regular_user(group="group1_id")  # Will be updated with actual group ID
        user2 = self.create_regular_user(group="group2_id")  # Will be updated with actual group ID
        
        # Create prompt categories
        category1 = self.create_prompt_category(name=f"Category 1 {unique_id}")
        category2 = self.create_prompt_category(name=f"Category 2 {unique_id}")
        
        # Create prompts
        prompt1 = self.create_prompt(name=f"Prompt 1 {unique_id}")
        prompt2 = self.create_prompt(name=f"Prompt 2 {unique_id}")
        
        # Create configurations
        config1 = self.create_ai_configuration(name=f"Config 1 {unique_id}")
        config2 = self.create_ai_configuration(name=f"Config 2 {unique_id}")
        
        # Create AI tests
        test1 = self.create_ai_test(name=f"AI Test 1 {unique_id}")
        test2 = self.create_ai_test(name=f"AI Test 2 {unique_id}")
        
        return {
            "name": name,
            "groups": [group1, group2],
            "users": {
                "admin": admin,
                "user1": user1,
                "user2": user2
            },
            "prompt_categories": [category1, category2],
            "prompts": [prompt1, prompt2],
            "configurations": [config1, config2],
            "ai_tests": [test1, test2]
        }