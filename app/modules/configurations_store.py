from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4
import json

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas import (
    AIEndpointConfig, AIEndpointConfigCreate, AIEndpointConfigUpdate,
    ConfigTestResponse, AIProviderInfo, ConfigTemplate,
    User
)

class AIConfigurationStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def get(self, config_id: str) -> Optional[AIEndpointConfig]:
        data = self._store.get(config_id)
        if not data:
            return None
        
        try:
            # Remove encrypted fields that are not part of the AIEndpointConfig schema
            cleaned_data = data.copy()
            encrypted_fields = ['api_key_encrypted', 'bearer_token_encrypted', 'azure_client_secret_encrypted']
            for field in encrypted_fields:
                cleaned_data.pop(field, None)
            
            # Fix empty string values that should be None for proper Pydantic validation
            nullable_fields = ['last_test_status', 'last_test_error', 'avg_response_time_ms', 'last_tested_at']
            for field in nullable_fields:
                if field in cleaned_data and cleaned_data[field] == '':
                    cleaned_data[field] = None
            
            # Convert avg_response_time_ms to float if it's a valid number string
            if 'avg_response_time_ms' in cleaned_data and cleaned_data['avg_response_time_ms'] is not None:
                try:
                    cleaned_data['avg_response_time_ms'] = float(cleaned_data['avg_response_time_ms'])
                except (ValueError, TypeError):
                    cleaned_data['avg_response_time_ms'] = None
            
            return AIEndpointConfig(**cleaned_data)
        except Exception as e:
            return None

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        provider: Optional[str] = None,
        search: Optional[str] = None,
        group_id: Optional[str] = None,  # INTERNAL USE ONLY - NOT FROM CLIENT
        created_by: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[List[AIEndpointConfig], int]:
        sql_filtered = False  # Track if SQL filtering was used
        
        # For SQL stores, use more efficient filtered queries when possible
        try:
            if hasattr(self._store, 'get_filtered'):
                # Build filters for SQL query
                filters = {}
                if status:
                    filters['status'] = status
                if provider:
                    filters['provider'] = provider
                if group_id:
                    filters['group_id'] = group_id
                if created_by:
                    filters['created_by'] = created_by
                
                # Get filtered results from SQL
                if filters:
                    sql_filtered = True
                    config_data = self._store.get_filtered(filters)
                    configs = []
                    for data in config_data:
                        try:
                            # Clean and validate data like in get() method
                            cleaned_data = data.copy()
                            encrypted_fields = ['api_key_encrypted', 'bearer_token_encrypted', 'azure_client_secret_encrypted']
                            for field in encrypted_fields:
                                cleaned_data.pop(field, None)
                            
                            # Fix empty string values that should be None
                            nullable_fields = ['last_test_status', 'last_test_error', 'avg_response_time_ms', 'last_tested_at']
                            for field in nullable_fields:
                                if field in cleaned_data and cleaned_data[field] == '':
                                    cleaned_data[field] = None
                            
                            # Convert avg_response_time_ms to float if needed
                            if 'avg_response_time_ms' in cleaned_data and cleaned_data['avg_response_time_ms'] is not None:
                                try:
                                    cleaned_data['avg_response_time_ms'] = float(cleaned_data['avg_response_time_ms'])
                                except (ValueError, TypeError):
                                    cleaned_data['avg_response_time_ms'] = None
                            
                            config = AIEndpointConfig(**cleaned_data)
                            configs.append(config)
                        except Exception:
                            continue
                else:
                    # No filters were applied, fall back to keys() approach for SQL stores
                    keys = self._store.keys()
                    if keys:
                        configs = [self.get(key) for key in keys]
                        configs = [c for c in configs if c is not None]
                    else:
                        configs = []
            else:
                raise Exception("Not an SQL store")
        except Exception:
            # Fallback to Redis-style approach
            keys = self._store.keys()
            if not keys:
                return [], 0

            try:
                configs = [self.get(key) for key in keys]
                configs = [c for c in configs if c is not None]
            except Exception as e:
                return [], 0

        # Apply filters only if SQL filtering wasn't used
        if not sql_filtered:
            if status:
                configs = [c for c in configs if c.status == status]
            if provider:
                configs = [c for c in configs if c.provider == provider]
            if group_id:
                configs = [c for c in configs if str(c.group_id) == str(group_id)]
            if created_by:
                configs = [c for c in configs if str(c.created_by) == str(created_by)]
        if search:
            search_lower = search.lower()
            configs = [
                c for c in configs
                if search_lower in c.name.lower()
                or search_lower in c.description.lower()
                or search_lower in c.model_name.lower()
                or any(search_lower in tag.lower() for tag in c.tags)
            ]

        # Sort by the specified field and order
        reverse_sort = sort_order.lower() == "desc"
        
        # Handle different sort fields
        if sort_by == "created_at":
            configs.sort(key=lambda x: x.created_at, reverse=reverse_sort)
        elif sort_by == "updated_at":
            configs.sort(key=lambda x: x.updated_at, reverse=reverse_sort)
        elif sort_by == "name":
            configs.sort(key=lambda x: x.name.lower(), reverse=reverse_sort)
        elif sort_by == "provider":
            configs.sort(key=lambda x: x.provider, reverse=reverse_sort)
        elif sort_by == "status":
            configs.sort(key=lambda x: x.status, reverse=reverse_sort)
        else:
            # Default to created_at if sort_by is not recognized
            configs.sort(key=lambda x: x.created_at, reverse=reverse_sort)

        # Calculate pagination
        total = len(configs)
        start = (page - 1) * limit
        end = start + limit
        paginated_configs = configs[start:end]

        return paginated_configs, total

    def create(self, config: AIEndpointConfigCreate, user: User) -> AIEndpointConfig:
        now = datetime.now(timezone.utc)
        config_id = str(uuid4())
        
        # Prepare config data
        config_data = config.model_dump()
        
        # Extract sensitive data for encrypted storage
        sensitive_data = {
            "api_key": config_data.pop("api_key", None),
            "bearer_token": config_data.pop("bearer_token", None),
            "azure_client_secret": config_data.pop("azure_client_secret", None),
        }
        
        # Extract fields that go into connection_config JSON
        connection_config_fields = [
            "azure_deployment_name", "azure_tenant_id", "azure_client_id", 
            "azure_api_version", "timeout_seconds", "max_retries", 
            "rate_limit_rpm", "huggingface_task"
        ]
        
        connection_config = {}
        for field in connection_config_fields:
            if field in config_data:
                value = config_data.pop(field)
                if value is not None:  # Only store non-null values
                    connection_config[field] = value
        
        # Create the configuration object
        new_config = AIEndpointConfig(
            id=config_id,
            created_by=user.id,
            group_id=user.group,
            created_at=now,
            updated_at=now,
            connection_config=connection_config,
            **config_data
        )
        
        # Add sensitive data to the configuration for SQL storage
        config_dict = new_config.model_dump()
        config_dict.update({
            "api_key_encrypted": sensitive_data.get("api_key"),
            "bearer_token_encrypted": sensitive_data.get("bearer_token"),
            "azure_client_secret_encrypted": sensitive_data.get("azure_client_secret"),
        })
        
        # Store the configuration
        self._store.put(config_id, config_dict)
        
        return new_config

    def update(self, config_id: str, config: AIEndpointConfigUpdate) -> Optional[AIEndpointConfig]:
        existing_data = self._store.get(config_id)
        if not existing_data:
            return None
            
        existing_config = AIEndpointConfig(**existing_data)
        now = datetime.now(timezone.utc)
        
        # Update only provided fields
        update_data = config.model_dump(exclude_unset=True)
        
        # Handle sensitive data separately
        sensitive_updates = {}
        for field in ["api_key", "bearer_token", "azure_client_secret"]:
            if field in update_data:
                sensitive_updates[field] = update_data.pop(field)
        
        # Handle connection_config fields
        connection_config_fields = [
            "azure_deployment_name", "azure_tenant_id", "azure_client_id", 
            "azure_api_version", "timeout_seconds", "max_retries", 
            "rate_limit_rpm", "huggingface_task"
        ]
        
        connection_config_updates = {}
        for field in connection_config_fields:
            if field in update_data:
                value = update_data.pop(field)
                if value is not None:
                    connection_config_updates[field] = value
        
        # Update connection_config if there are updates
        if connection_config_updates:
            current_connection_config = existing_config.connection_config or {}
            current_connection_config.update(connection_config_updates)
            existing_config.connection_config = current_connection_config
        
        # Update remaining configuration fields
        for field, value in update_data.items():
            setattr(existing_config, field, value)
        
        existing_config.updated_at = now
        
        # Update sensitive data if provided
        if sensitive_updates:
            for field, value in sensitive_updates.items():
                encrypted_field = f"{field}_encrypted"
                setattr(existing_config, encrypted_field, value)
        
        # Store updated configuration
        self._store.put(config_id, existing_config.model_dump())
        
        return existing_config

    def delete(self, config_id: str) -> bool:
        existing_data = self._store.get(config_id)
        if not existing_data:
            return False
        
        # Delete main config
        self._store.pop(config_id)
        
        return True

    def get_sensitive_data(self, config_id: str) -> Dict[str, str]:
        """Get sensitive authentication data for a configuration"""
        config_data = self._store.get(config_id)
        if not config_data:
            return {}
        
        return {
            "api_key": config_data.get("api_key_encrypted"),
            "bearer_token": config_data.get("bearer_token_encrypted"),
            "azure_client_secret": config_data.get("azure_client_secret_encrypted"),
        }

    def update_test_result(self, config_id: str, test_response: ConfigTestResponse) -> Optional[AIEndpointConfig]:
        """Update configuration with test results"""
        existing_data = self._store.get(config_id)
        if not existing_data:
            return None
            
        existing_config = AIEndpointConfig(**existing_data)
        
        # Update test status
        existing_config.last_tested_at = test_response.test_timestamp
        existing_config.last_test_status = "success" if test_response.success else "failed"
        existing_config.last_test_error = test_response.error_message
        
        # Update statistics
        existing_config.total_requests += 1
        if test_response.success:
            existing_config.successful_requests += 1
            # Update average response time
            if existing_config.avg_response_time_ms is None:
                existing_config.avg_response_time_ms = float(test_response.response_time_ms)
            else:
                # Simple moving average
                total_time = existing_config.avg_response_time_ms * (existing_config.successful_requests - 1)
                existing_config.avg_response_time_ms = (total_time + test_response.response_time_ms) / existing_config.successful_requests
        else:
            existing_config.failed_requests += 1
        
        existing_config.updated_at = datetime.now(timezone.utc)
        
        self._store.put(config_id, existing_config.model_dump())
        return existing_config

    def belongs_to_group(self, config_id: str, group_id: str) -> bool:
        """Check if a configuration belongs to a specific group."""
        config = self.get(config_id)
        if not config:
            return False
        return str(config.group_id) == str(group_id)

    def get_configs_by_group(self, group_id: str) -> List[AIEndpointConfig]:
        """Get all configurations belonging to a specific group."""
        configs, _ = self.list(group_id=group_id, page=1, limit=1000)
        return configs


class AIProviderService:
    """Service for managing AI provider information and templates"""
    
    @staticmethod
    def get_supported_providers() -> List[AIProviderInfo]:
        """Get list of supported AI providers"""
        providers = [
            AIProviderInfo(
                provider="openai",
                display_name="OpenAI",
                description="OpenAI GPT models including GPT-4, GPT-3.5",
                auth_types=["api_key"],
                required_fields=["api_key", "model_name"],
                optional_fields=["endpoint_url"],
                supported_models=["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"],
                documentation_url="https://platform.openai.com/docs"
            ),
            AIProviderInfo(
                provider="anthropic",
                display_name="Anthropic",
                description="Anthropic Claude models",
                auth_types=["api_key"],
                required_fields=["api_key", "model_name"],
                optional_fields=["endpoint_url"],
                supported_models=["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
                documentation_url="https://docs.anthropic.com"
            ),
            AIProviderInfo(
                provider="azure_openai",
                display_name="Azure OpenAI",
                description="Microsoft Azure OpenAI Service",
                auth_types=["api_key", "azure_ad"],
                required_fields=["endpoint_url", "api_key", "azure_deployment_name", "azure_api_version"],
                optional_fields=["azure_tenant_id", "azure_client_id", "azure_client_secret"],
                supported_models=["gpt-4", "gpt-35-turbo"],
                documentation_url="https://docs.microsoft.com/en-us/azure/cognitive-services/openai/"
            ),
            AIProviderInfo(
                provider="google",
                display_name="Google AI",
                description="Google Gemini and PaLM models",
                auth_types=["api_key"],
                required_fields=["api_key", "model_name"],
                optional_fields=["endpoint_url"],
                supported_models=["gemini-pro", "gemini-pro-vision"],
                documentation_url="https://ai.google.dev/docs"
            ),
            AIProviderInfo(
                provider="huggingface",
                display_name="Hugging Face",
                description="Hugging Face Inference API",
                auth_types=["api_key", "bearer_token"],
                required_fields=["model_name"],
                optional_fields=["endpoint_url", "huggingface_task"],
                supported_models=["gpt2", "distilbert-base-uncased", "t5-base"],
                documentation_url="https://huggingface.co/docs/api-inference"
            ),
            AIProviderInfo(
                provider="custom",
                display_name="Custom API",
                description="Custom AI API endpoint",
                auth_types=["api_key", "bearer_token", "oauth"],
                required_fields=["endpoint_url"],
                optional_fields=["custom_headers"],
                supported_models=[],
                documentation_url=None
            )
        ]
        
        return providers
    
    @staticmethod
    def get_provider_templates() -> List[ConfigTemplate]:
        """Get configuration templates for different providers"""
        templates = [
            ConfigTemplate(
                id="openai_gpt4",
                name="OpenAI GPT-4",
                description="Standard OpenAI GPT-4 configuration",
                provider="openai",
                template_config={
                    "endpoint_url": "https://api.openai.com/v1/chat/completions",
                    "model_name": "gpt-4",
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "rate_limit_rpm": 500
                },
                required_user_inputs=["api_key", "name", "description"]
            ),
            ConfigTemplate(
                id="anthropic_claude",
                name="Anthropic Claude",
                description="Standard Anthropic Claude configuration",
                provider="anthropic",
                template_config={
                    "endpoint_url": "https://api.anthropic.com/v1/messages",
                    "model_name": "claude-3-sonnet-20240229",
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "rate_limit_rpm": 100
                },
                required_user_inputs=["api_key", "name", "description"]
            ),
            ConfigTemplate(
                id="azure_openai_gpt4",
                name="Azure OpenAI GPT-4",
                description="Azure OpenAI Service GPT-4 configuration",
                provider="azure_openai",
                template_config={
                    "model_name": "gpt-4",
                    "azure_api_version": "2023-12-01-preview",
                    "timeout_seconds": 30,
                    "max_retries": 3
                },
                required_user_inputs=["endpoint_url", "api_key", "azure_deployment_name", "name", "description"]
            )
        ]
        
        return templates
    
    @staticmethod
    def validate_configuration(provider: str, config_data: dict) -> dict:
        """Validate configuration for a specific provider"""
        providers = {p.provider: p for p in AIProviderService.get_supported_providers()}
        
        if provider not in providers:
            return {
                "is_valid": False,
                "errors": [f"Unsupported provider: {provider}"],
                "warnings": [],
                "suggestions": []
            }
        
        provider_info = providers[provider]
        errors = []
        warnings = []
        suggestions = []
        
        # Check required fields
        for field in provider_info.required_fields:
            if field not in config_data or not config_data[field]:
                errors.append(f"Required field missing: {field}")
        
        # Provider-specific validations
        if provider == "openai":
            if config_data.get("endpoint_url") and "openai.com" not in config_data["endpoint_url"]:
                warnings.append("Endpoint URL does not appear to be an OpenAI endpoint")
        
        elif provider == "azure_openai":
            if not config_data.get("azure_deployment_name"):
                errors.append("Azure deployment name is required for Azure OpenAI")
            if not config_data.get("azure_api_version"):
                suggestions.append("Consider using the latest API version: 2023-12-01-preview")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions
        }