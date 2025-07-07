from typing import Annotated, List, Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app.api import deps
from app.modules.tlogger import TLogger
from app.modules.prompts_store import PromptCategoryStore, PromptStore, PromptSetStore, PromptTemplateEngine
from app.modules.store_interface import RedisStore
from app.schemas import (
    User, 
    PromptCategory, PromptCategoryCreate, PromptCategoryUpdate, PromptCategoryList,
    Prompt, PromptCreate, PromptUpdate, PromptList,
    PromptSet, PromptSetCreate, PromptSetUpdate, PromptSetList,
    PromptValidationRequest, PromptValidationResponse,
    PromptPreviewRequest, PromptPreviewResponse
)

from pydantic import UUID4

router = APIRouter()



# PROMPT CATEGORIES ENDPOINTS

@router.get("/categories", response_model=PromptCategoryList)
async def get_prompt_categories(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(ACTIVE|ARCHIVED)$"),
    category_type: Optional[str] = Query(None, pattern="^(COMPLIANCE|SAFETY|ACCURACY|CUSTOM)$"),
    search: Optional[str] = Query(None),
    category_store: PromptCategoryStore = Depends(deps.get_category_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of prompt categories with pagination and filtering.
    """
    logger.info(f"Retrieving prompt categories - page: {page}, limit: {limit}")
    
    categories, total = category_store.list(
        page=page,
        limit=limit,
        status=status,
        category_type=category_type,
        search=search
    )
    
    return PromptCategoryList(
        items=categories,
        total=total,
        page=page,
        limit=limit
    )

@router.get("/categories/{category_id}", response_model=PromptCategory)
async def get_prompt_category(
    category_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    category_store: PromptCategoryStore = Depends(deps.get_category_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get a specific prompt category by ID.
    """
    logger.info(f"Retrieving prompt category: {category_id}")
    
    category = category_store.get(str(category_id))
    if not category:
        logger.error(f"Category not found: {category_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt category not found"
        )
    
    return category

@router.post("/categories", response_model=PromptCategory, status_code=status.HTTP_201_CREATED)
async def create_prompt_category(
    category_create: PromptCategoryCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    category_store: PromptCategoryStore = Depends(deps.get_category_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Create a new prompt category.
    """
    logger.info(f"Creating prompt category: {category_create.name}")
    
    category = category_store.create(category_create, current_user)
    
    return category

@router.put("/categories/{category_id}", response_model=PromptCategory)
async def update_prompt_category(
    category_id: UUID4,
    category_update: PromptCategoryUpdate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    category_store: PromptCategoryStore = Depends(deps.get_category_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Update a prompt category by ID.
    """
    logger.info(f"Updating prompt category: {category_id}")
    
    category = category_store.update(str(category_id), category_update)
    if not category:
        logger.error(f"Category not found: {category_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt category not found"
        )
    
    return category

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_category(
    category_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    category_store: PromptCategoryStore = Depends(deps.get_category_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Delete a prompt category by ID.
    """
    logger.info(f"Deleting prompt category: {category_id}")
    
    success = category_store.delete(str(category_id))
    if not success:
        logger.error(f"Category not found: {category_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt category not found"
        )

# PROMPTS ENDPOINTS

@router.get("/", response_model=PromptList)
async def get_prompts(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(DRAFT|ACTIVE|ARCHIVED)$"),
    category_id: Optional[UUID4] = Query(None),
    risk_level: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    search: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    prompt_store: PromptStore = Depends(deps.get_prompt_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of prompts with pagination and filtering.
    """
    logger.info(f"Retrieving prompts - page: {page}, limit: {limit}")
    
    prompts, total = prompt_store.list(
        page=page,
        limit=limit,
        status=status,
        category_id=str(category_id) if category_id else None,
        risk_level=risk_level,
        search=search,
        tags=tags
    )
    
    return PromptList(
        items=prompts,
        total=total,
        page=page,
        limit=limit
    )

# PROMPT SETS ENDPOINTS

@router.get("/sets", response_model=PromptSetList)
async def get_prompt_sets(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(ACTIVE|ARCHIVED)$"),
    category_id: Optional[UUID4] = Query(None),
    search: Optional[str] = Query(None),
    prompt_set_store: PromptSetStore = Depends(deps.get_prompt_set_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of prompt sets with pagination and filtering.
    """
    logger.info(f"Retrieving prompt sets - page: {page}, limit: {limit}")
    
    sets, total = prompt_set_store.list(
        page=page,
        limit=limit,
        status=status,
        category_id=str(category_id) if category_id else None,
        search=search
    )
    
    return PromptSetList(
        items=sets,
        total=total,
        page=page,
        limit=limit
    )

@router.get("/sets/{set_id}", response_model=PromptSet)
async def get_prompt_set(
    set_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_set_store: PromptSetStore = Depends(deps.get_prompt_set_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get a specific prompt set by ID.
    """
    logger.info(f"Retrieving prompt set: {set_id}")
    
    prompt_set = prompt_set_store.get(str(set_id))
    if not prompt_set:
        logger.error(f"Prompt set not found: {set_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt set not found"
        )
    
    return prompt_set

@router.post("/sets", response_model=PromptSet, status_code=status.HTTP_201_CREATED)
async def create_prompt_set(
    set_create: PromptSetCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_set_store: PromptSetStore = Depends(deps.get_prompt_set_store),
    prompt_store: PromptStore = Depends(deps.get_prompt_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Create a new prompt set.
    """
    logger.info(f"Creating prompt set: {set_create.name}")
    
    # Validate that all prompt IDs exist
    for prompt_id in set_create.prompt_ids:
        prompt = prompt_store.get(str(prompt_id))
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt not found: {prompt_id}"
            )
    
    prompt_set = prompt_set_store.create(set_create, current_user)
    
    return prompt_set

@router.put("/sets/{set_id}", response_model=PromptSet)
async def update_prompt_set(
    set_id: UUID4,
    set_update: PromptSetUpdate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_set_store: PromptSetStore = Depends(deps.get_prompt_set_store),
    prompt_store: PromptStore = Depends(deps.get_prompt_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Update a prompt set by ID.
    """
    logger.info(f"Updating prompt set: {set_id}")
    
    # Validate that all prompt IDs exist (if prompt_ids are being updated)
    if set_update.prompt_ids is not None:
        for prompt_id in set_update.prompt_ids:
            prompt = prompt_store.get(str(prompt_id))
            if not prompt:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Prompt not found: {prompt_id}"
                )
    
    prompt_set = prompt_set_store.update(str(set_id), set_update)
    if not prompt_set:
        logger.error(f"Prompt set not found: {set_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt set not found"
        )
    
    return prompt_set

@router.delete("/sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt_set(
    set_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_set_store: PromptSetStore = Depends(deps.get_prompt_set_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Delete a prompt set by ID.
    """
    logger.info(f"Deleting prompt set: {set_id}")
    
    success = prompt_set_store.delete(str(set_id))
    if not success:
        logger.error(f"Prompt set not found: {set_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt set not found"
        )

# INDIVIDUAL PROMPT ENDPOINTS

@router.get("/{prompt_id}", response_model=Prompt)
async def get_prompt(
    prompt_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_store: PromptStore = Depends(deps.get_prompt_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get a specific prompt by ID.
    """
    logger.info(f"Retrieving prompt: {prompt_id}")
    
    prompt = prompt_store.get(str(prompt_id))
    if not prompt:
        logger.error(f"Prompt not found: {prompt_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    return prompt

@router.post("/", response_model=Prompt, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_create: PromptCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_store: PromptStore = Depends(deps.get_prompt_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Create a new prompt.
    """
    logger.info(f"Creating prompt: {prompt_create.name}")
    
    # Validate the prompt template
    validation = PromptTemplateEngine.validate_prompt(
        prompt_create.content, 
        prompt_create.variables
    )
    
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid prompt template: {', '.join(validation.errors)}"
        )
    
    prompt = prompt_store.create(prompt_create, current_user)
    
    return prompt

@router.put("/{prompt_id}", response_model=Prompt)
async def update_prompt(
    prompt_id: UUID4,
    prompt_update: PromptUpdate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_store: PromptStore = Depends(deps.get_prompt_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Update a prompt by ID.
    """
    logger.info(f"Updating prompt: {prompt_id}")
    
    # If content or variables are being updated, validate the template
    if prompt_update.content is not None or prompt_update.variables is not None:
        # Get current prompt to merge with update
        current_prompt = prompt_store.get(str(prompt_id))
        if not current_prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        
        content = prompt_update.content or current_prompt.content
        variables = prompt_update.variables or current_prompt.variables
        
        validation = PromptTemplateEngine.validate_prompt(content, variables)
        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid prompt template: {', '.join(validation.errors)}"
            )
    
    prompt = prompt_store.update(str(prompt_id), prompt_update)
    if not prompt:
        logger.error(f"Prompt not found: {prompt_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    return prompt

@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    prompt_store: PromptStore = Depends(deps.get_prompt_store),
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Delete a prompt by ID.
    """
    logger.info(f"Deleting prompt: {prompt_id}")
    
    success = prompt_store.delete(str(prompt_id))
    if not success:
        logger.error(f"Prompt not found: {prompt_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )

# PROMPT VALIDATION AND PREVIEW ENDPOINTS

@router.post("/validate", response_model=PromptValidationResponse)
async def validate_prompt(
    validation_request: PromptValidationRequest,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Validate a prompt template without saving it.
    """
    logger.info("Validating prompt template")
    
    validation = PromptTemplateEngine.validate_prompt(
        validation_request.content,
        validation_request.variables
    )
    
    return validation

@router.post("/preview", response_model=PromptPreviewResponse)
async def preview_prompt(
    preview_request: PromptPreviewRequest,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Preview a prompt template with variable substitution.
    """
    logger.info("Previewing prompt template")
    
    preview = PromptTemplateEngine.render_prompt(
        preview_request.content,
        preview_request.variable_values
    )
    
    return preview
