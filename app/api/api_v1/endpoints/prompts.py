import json
from os.path import join
from typing import Annotated, List
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api import deps
from app.modules.tlogger import TLogger
from app.schemas import TestParams, User, TestCategory, TestCategoryUpdate

from pydantic import UUID4

router = APIRouter()

MODELS_DIR: str = join("app", "assets", "ai_models")

# Sample test categories for MVP
SAMPLE_CATEGORIES = [
    {
        "id": uuid4(),
        "name": "Financial Compliance",
        "description": "Tests for financial regulatory compliance and reporting accuracy",
        "category": "COMPLIANCE",
        "subcategory": "Financial Reporting",
        "priority": "HIGH",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "tags": ["finance", "compliance", "reporting"]
    },
    {
        "id": uuid4(),
        "name": "Data Privacy",
        "description": "Tests for handling of personal and sensitive information",
        "category": "SAFETY",
        "subcategory": "Privacy",
        "priority": "HIGH",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "tags": ["privacy", "data-protection", "gdpr"]
    },
    {
        "id": uuid4(),
        "name": "Factual Accuracy",
        "description": "Tests for factual correctness and information accuracy",
        "category": "ACCURACY",
        "subcategory": "Fact Checking",
        "priority": "MEDIUM",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "tags": ["accuracy", "fact-checking", "verification"]
    }
]

@router.get("/categories", response_model=List[TestCategory])
async def get_test_categories(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get list of test categories.
    """
    logger.info("Retrieving test categories")
    
    # Convert sample data to TestCategory models
    categories = [TestCategory.model_validate(cat) for cat in SAMPLE_CATEGORIES]
    
    return JSONResponse(
        content=[category.model_dump(mode="json") for category in categories]
    )

@router.get("/categories/{category_id}", response_model=TestCategory)
async def get_test_category(
    category_id: UUID4,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Get a specific test category by ID.
    """
    logger.info(f"Retrieving test category: {category_id}")
    
    # Find the category in our sample data
    category = next(
        (cat for cat in SAMPLE_CATEGORIES if cat["id"] == category_id),
        None
    )
    
    if not category:
        logger.error(f"Category not found: {category_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test category not found"
        )
    
    # Convert to TestCategory model and return
    return JSONResponse(
        content=TestCategory.model_validate(category).model_dump(mode="json")
    )

@router.put("/categories/{category_id}", response_model=TestCategory)
async def update_test_category(
    category_id: UUID4,
    category_update: TestCategoryUpdate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: TLogger = Depends(deps.get_logger),
):
    """
    Update a test category by ID.
    """
    logger.info(f"Updating test category: {category_id}")
    
    # Find the category in our sample data
    category_index = next(
        (i for i, cat in enumerate(SAMPLE_CATEGORIES) if cat["id"] == category_id),
        None
    )
    
    if category_index is None:
        logger.error(f"Category not found: {category_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test category not found"
        )
    
    # Get current category
    current_category = SAMPLE_CATEGORIES[category_index]
    
    # Update only the fields that were provided
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        current_category[field] = value
    
    # Update the timestamp
    current_category["updated_at"] = datetime.now(timezone.utc)
    
    # Convert to TestCategory model and return
    return JSONResponse(
        content=TestCategory.model_validate(current_category).model_dump(mode="json")
    )
