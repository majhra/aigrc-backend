from typing import Annotated, List, Optional
from datetime import datetime, timezone
import asyncio
import aiohttp
import time

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.api import deps
from app.modules.tlogger import TLogger
from app.modules.configurations_store import AIConfigurationStore, AIProviderService
from app.modules.store_interface import RedisStore
from app.schemas import (
    User,
    AIEndpointConfig, AIEndpointConfigCreate, AIEndpointConfigUpdate, AIEndpointConfigList,
    ConfigTestRequest, ConfigTestResponse,
    AIProviderInfo, AIProviderList, ConfigTemplate, ConfigTemplateList,
    ConfigValidationRequest, ConfigValidationResponse
)

from pydantic import UUID4

router = APIRouter()


# AI CONFIGURATION ENDPOINTS

@router.get("/", response_model=AIEndpointConfigList)
async def get_configurations(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(active|inactive|testing)$"),
    provider: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    my_configs: bool = Query(False, description="Show only configurations created by current user"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of AI endpoint configurations with pagination and filtering.
    """
    logger.info(f"Retrieving AI configurations - page: {page}, limit: {limit}")
    
    created_by = str(current_user.id) if my_configs else None
    
    configurations, total = config_store.list(
        page=page,
        limit=limit,
        status=status,
        provider=provider,
        search=search,
        created_by=created_by,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    return AIEndpointConfigList(
        items=configurations,
        total=total,
        page=page,
        limit=limit
    )

@router.get("/{config_id}", response_model=AIEndpointConfig)
async def get_configuration(
    config_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get a specific AI endpoint configuration by ID.
    """
    logger.info(f"Retrieving AI configuration: {config_id}")
    
    configuration = config_store.get(str(config_id))
    if not configuration:
        logger.error(f"Configuration not found: {config_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )
    
    return configuration

@router.post("/", response_model=AIEndpointConfig, status_code=status.HTTP_201_CREATED)
async def create_configuration(
    config_create: AIEndpointConfigCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Create a new AI endpoint configuration.
    """
    logger.info(f"Creating AI configuration: {config_create.name}")
    
    # Validate the configuration
    validation = AIProviderService.validate_configuration(
        config_create.provider,
        config_create.model_dump()
    )
    
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration: {', '.join(validation['errors'])}"
        )
    
    configuration = config_store.create(config_create, current_user)
    
    # Log warnings if any
    if validation["warnings"]:
        logger.warning(f"Configuration warnings: {', '.join(validation['warnings'])}")
    
    return configuration

@router.put("/{config_id}", response_model=AIEndpointConfig)
async def update_configuration(
    config_id: UUID4,
    config_update: AIEndpointConfigUpdate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Update an AI endpoint configuration by ID.
    """
    logger.info(f"Updating AI configuration: {config_id}")
    
    configuration = config_store.update(str(config_id), config_update)
    if not configuration:
        logger.error(f"Configuration not found: {config_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )
    
    return configuration

@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_configuration(
    config_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Delete an AI endpoint configuration by ID.
    """
    logger.info(f"Deleting AI configuration: {config_id}")
    
    success = config_store.delete(str(config_id))
    if not success:
        logger.error(f"Configuration not found: {config_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )

# CONFIGURATION TESTING

@router.post("/{config_id}/test", response_model=ConfigTestResponse)
async def test_configuration(
    config_id: UUID4,
    test_request: ConfigTestRequest,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    config_store: AIConfigurationStore = Depends(deps.get_config_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Test an AI endpoint configuration with a sample request.
    """
    logger.info(f"Testing AI configuration: {config_id}")
    
    # Get configuration
    configuration = config_store.get(str(config_id))
    if not configuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI configuration not found"
        )
    
    # Get sensitive data
    sensitive_data = config_store.get_sensitive_data(str(config_id))
    
    # Perform the test
    test_result = await _test_ai_endpoint(configuration, sensitive_data, test_request, logger)
    
    # Update configuration with test results
    config_store.update_test_result(str(config_id), test_result)
    
    return test_result

# PROVIDER INFORMATION

@router.get("/providers/list", response_model=AIProviderList)
async def get_ai_providers(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of supported AI providers and their configurations.
    """
    logger.info("Retrieving supported AI providers")
    
    providers = AIProviderService.get_supported_providers()
    
    return AIProviderList(providers=providers)

@router.get("/templates/list", response_model=ConfigTemplateList)
async def get_configuration_templates(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    provider: Optional[str] = Query(None, description="Filter templates by provider"),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of configuration templates for quick setup.
    """
    logger.info("Retrieving configuration templates")
    
    templates = AIProviderService.get_provider_templates()
    
    if provider:
        templates = [t for t in templates if t.provider == provider]
    
    return ConfigTemplateList(templates=templates)

# CONFIGURATION VALIDATION

@router.post("/validate", response_model=ConfigValidationResponse)
async def validate_configuration(
    validation_request: ConfigValidationRequest,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Validate a configuration without saving it.
    """
    logger.info(f"Validating configuration for provider: {validation_request.provider}")
    
    validation_result = AIProviderService.validate_configuration(
        validation_request.provider,
        validation_request.model_dump()
    )
    
    return ConfigValidationResponse(**validation_result)

# HELPER FUNCTIONS

async def _test_ai_endpoint(
    config: AIEndpointConfig,
    sensitive_data: dict,
    test_request: ConfigTestRequest,
    logger: TLogger
) -> ConfigTestResponse:
    """Test an AI endpoint configuration"""
    start_time = time.time()
    
    try:
        # Prepare headers
        headers = {"Content-Type": "application/json"}
        
        # Add authentication
        if config.auth_type == "api_key":
            api_key = sensitive_data.get("api_key")
            if not api_key:
                raise ValueError("API key not found for configuration")
            
            if config.provider == "openai":
                headers["Authorization"] = f"Bearer {api_key}"
            elif config.provider == "anthropic":
                headers["x-api-key"] = api_key
            elif config.provider == "azure_openai":
                headers["api-key"] = api_key
            else:
                headers["Authorization"] = f"Bearer {api_key}"
        
        elif config.auth_type == "bearer_token":
            bearer_token = sensitive_data.get("bearer_token")
            if not bearer_token:
                raise ValueError("Bearer token not found for configuration")
            headers["Authorization"] = f"Bearer {bearer_token}"
        
        # Add custom headers
        headers.update(config.custom_headers)
        
        # Prepare request payload based on provider
        if config.provider == "openai":
            payload = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": test_request.test_prompt}],
                "max_tokens": test_request.max_tokens,
                "temperature": test_request.temperature
            }
        elif config.provider == "anthropic":
            payload = {
                "model": config.model_name,
                "max_tokens": test_request.max_tokens,
                "messages": [{"role": "user", "content": test_request.test_prompt}]
            }
        elif config.provider == "azure_openai":
            payload = {
                "model": config.model_name,
                "messages": [{"role": "user", "content": test_request.test_prompt}],
                "max_tokens": test_request.max_tokens,
                "temperature": test_request.temperature
            }
        else:
            # Generic payload for custom providers
            payload = {
                "model": config.model_name,
                "prompt": test_request.test_prompt,
                "max_tokens": test_request.max_tokens,
                "temperature": test_request.temperature
            }
        
        # Make the request
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=config.timeout_seconds)) as session:
            async with session.post(config.endpoint_url, json=payload, headers=headers) as response:
                response_time_ms = int((time.time() - start_time) * 1000)
                
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Extract response content based on provider
                    if config.provider in ["openai", "azure_openai"]:
                        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        token_usage = response_data.get("usage", {})
                    elif config.provider == "anthropic":
                        content = response_data.get("content", [{}])[0].get("text", "")
                        token_usage = response_data.get("usage", {})
                    else:
                        content = str(response_data)
                        token_usage = None
                    
                    return ConfigTestResponse(
                        success=True,
                        response_time_ms=response_time_ms,
                        response_content=content,
                        token_usage=token_usage,
                        test_timestamp=datetime.now(timezone.utc)
                    )
                else:
                    error_text = await response.text()
                    return ConfigTestResponse(
                        success=False,
                        response_time_ms=response_time_ms,
                        error_message=f"HTTP {response.status}: {error_text}",
                        test_timestamp=datetime.now(timezone.utc)
                    )
    
    except asyncio.TimeoutError:
        response_time_ms = int((time.time() - start_time) * 1000)
        return ConfigTestResponse(
            success=False,
            response_time_ms=response_time_ms,
            error_message="Request timeout",
            test_timestamp=datetime.now(timezone.utc)
        )
    
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error testing configuration: {str(e)}")
        return ConfigTestResponse(
            success=False,
            response_time_ms=response_time_ms,
            error_message=str(e),
            test_timestamp=datetime.now(timezone.utc)
        )