from typing import Literal, List, Optional, Dict, Any, Union
from pydantic import BaseModel, UUID4, Field, field_validator, ConfigDict
from datetime import datetime
from uuid import UUID

# AI Provider Types
class AIProviderType(BaseModel):
    provider: Literal["openai", "anthropic", "azure_openai", "google", "huggingface", "custom"]
    display_name: str
    description: str
    auth_types: List[Literal["api_key", "bearer_token", "oauth", "azure_ad"]]
    required_fields: List[str]
    optional_fields: List[str] = Field(default_factory=list)

# Configuration Base Models
class AIEndpointConfigBase(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    provider: Literal["openai", "anthropic", "azure_openai", "google", "huggingface", "custom"]
    endpoint_url: str = Field(..., min_length=1)
    auth_type: Literal["api_key", "bearer_token", "oauth", "azure_ad"]
    model_name: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)

class AIEndpointConfigCreate(AIEndpointConfigBase):
    model_config = ConfigDict(protected_namespaces=())
    # Sensitive authentication data
    api_key: str | None = Field(None, min_length=1)
    bearer_token: str | None = Field(None, min_length=1)
    azure_tenant_id: str | None = Field(None, min_length=1)
    azure_client_id: str | None = Field(None, min_length=1)
    azure_client_secret: str | None = Field(None, min_length=1)
    
    # Provider-specific configuration
    azure_api_version: str | None = None
    azure_deployment_name: str | None = None
    huggingface_task: str | None = None
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    
    # Request configuration
    timeout_seconds: int = Field(30, ge=1, le=300)
    max_retries: int = Field(3, ge=0, le=10)
    rate_limit_rpm: int | None = Field(None, ge=1, le=10000)  # Requests per minute
    
    @field_validator('api_key', 'bearer_token', 'azure_client_secret')
    @classmethod
    def validate_sensitive_fields(cls, v, info):
        if v is not None and len(v.strip()) == 0:
            raise ValueError(f"{info.field_name} cannot be empty if provided")
        return v

class AIEndpointConfigUpdate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1, max_length=500)
    endpoint_url: str | None = Field(None, min_length=1)
    model_name: str | None = Field(None, min_length=1)
    tags: List[str] | None = None
    
    # Auth updates (sensitive)
    api_key: str | None = None
    bearer_token: str | None = None
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_client_secret: str | None = None
    
    # Provider-specific updates
    azure_api_version: str | None = None
    azure_deployment_name: str | None = None
    huggingface_task: str | None = None
    custom_headers: Dict[str, str] | None = None
    
    # Request configuration updates
    timeout_seconds: int | None = Field(None, ge=1, le=300)
    max_retries: int | None = Field(None, ge=0, le=10)
    rate_limit_rpm: int | None = Field(None, ge=1, le=10000)
    
    status: Literal["active", "inactive", "testing"] | None = None

class AIEndpointConfig(AIEndpointConfigBase):
    model_config = ConfigDict(protected_namespaces=())
    id: UUID4
    status: Literal["active", "inactive", "testing"] = "testing"
    created_by: UUID4
    group_id: Optional[Union[str, UUID]] = None
    created_at: datetime
    updated_at: datetime
    last_tested_at: datetime | None = None
    last_test_status: Literal["success", "failed", "pending"] | None = None
    last_test_error: str | None = None
    
    # Connection configuration (stored as JSON in DB)
    connection_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Non-sensitive headers
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    
    # Usage statistics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float | None = None
    
    # Computed properties for backward compatibility
    @property
    def azure_api_version(self) -> str | None:
        return self.connection_config.get("azure_api_version")
    
    @property
    def azure_deployment_name(self) -> str | None:
        return self.connection_config.get("azure_deployment_name")
    
    @property
    def azure_tenant_id(self) -> str | None:
        return self.connection_config.get("azure_tenant_id")
    
    @property
    def azure_client_id(self) -> str | None:
        return self.connection_config.get("azure_client_id")
    
    @property
    def huggingface_task(self) -> str | None:
        return self.connection_config.get("huggingface_task")
    
    @property
    def timeout_seconds(self) -> int:
        return self.connection_config.get("timeout_seconds", 30)
    
    @property
    def max_retries(self) -> int:
        return self.connection_config.get("max_retries", 3)
    
    @property
    def rate_limit_rpm(self) -> int | None:
        return self.connection_config.get("rate_limit_rpm")
    
    # Field validators
    @field_validator('group_id', mode='before')
    @classmethod
    def convert_group_id_to_string(cls, v):
        if v is None:
            return None
        return str(v)
    
    # NOTE: Sensitive auth data is NOT included in the response model

# Configuration Testing
class ConfigTestRequest(BaseModel):
    test_prompt: str = Field("Hello, this is a test message.", min_length=1)
    max_tokens: int | None = Field(100, ge=1, le=4000)
    temperature: float | None = Field(0.7, ge=0.0, le=2.0)

class ConfigTestResponse(BaseModel):
    success: bool
    response_time_ms: int
    response_content: str | None = None
    error_message: str | None = None
    token_usage: Dict[str, int] | None = None
    test_timestamp: datetime

# Response Models with Pagination
class AIEndpointConfigList(BaseModel):
    items: List[AIEndpointConfig]
    total: int
    page: int
    limit: int

# AI Provider Information
class AIProviderInfo(BaseModel):
    provider: str
    display_name: str
    description: str
    auth_types: List[str]
    required_fields: List[str]
    optional_fields: List[str]
    supported_models: List[str] = Field(default_factory=list)
    documentation_url: str | None = None

class AIProviderList(BaseModel):
    providers: List[AIProviderInfo]

# Configuration Templates
class ConfigTemplate(BaseModel):
    id: str
    name: str
    description: str
    provider: str
    template_config: Dict[str, Any]
    required_user_inputs: List[str]

class ConfigTemplateList(BaseModel):
    templates: List[ConfigTemplate]

# Configuration Validation
class ConfigValidationRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    provider: str
    endpoint_url: str
    auth_type: str
    model_name: str
    api_key: str | None = None
    # Additional fields for validation without saving

class ConfigValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)