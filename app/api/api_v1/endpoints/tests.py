from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api import deps
from app.core.config import settings
from app.modules.store_interface import StoreProtocol, RedisStore
from app.schemas import TestSchema, MyTestCreate, TestList, User
from app.modules.tests_store import MyTestStore

router = APIRouter()

@router.get("", response_model=TestList)
async def list_tests(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: StoreProtocol = Depends(deps.get_test_store),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(DRAFT|ACTIVE|ARCHIVED)$"),
    risk_level: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    search: Optional[str] = None,
    logger: deps.TLogger = Depends(deps.get_logger),
) -> TestList:
    """
    List all tests with pagination and filtering.
    """
    tests, total = test_store.list(
        page=page,
        limit=limit,
        status=status,
        risk_level=risk_level,
        search=search
    )
    
    return TestList(
        items=tests,
        total=total,
        page=page,
        limit=limit
    )

@router.get("/{test_id}", response_model=TestSchema)
async def get_test(
    test_id: UUID,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: StoreProtocol = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> TestSchema:
    """
    Get test details by ID.
    """
    logger.info(f"Getting test with ID: {test_id}")
    test = test_store.get(str(test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    return test

@router.post("", response_model=TestSchema, status_code=status.HTTP_201_CREATED)
async def create_test(
    test: MyTestCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: StoreProtocol = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> TestSchema:
    """
    Create a new test.
    """
    return test_store.create(test, current_user)

@router.put("/{test_id}", response_model=TestSchema)
async def update_test(
    test_id: UUID,
    test: MyTestCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: StoreProtocol = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> TestSchema:
    """
    Update an existing test.
    """
    updated_test = test_store.update(str(test_id), test)
    if not updated_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    return updated_test

@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: UUID,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: StoreProtocol = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> None:
    """
    Delete a test.
    """
    if not test_store.delete(str(test_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        ) 