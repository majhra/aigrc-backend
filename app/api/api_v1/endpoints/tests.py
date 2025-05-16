from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api import deps
from app.core.config import settings
from app.modules.store_interface import StoreProtocol, RedisStore
from app.schemas import TestSchema, MyTestCreate, TestList, User
from app.schemas.executions import ExecutedTestCreate, ExecutedTestSchema, ExecutedTestList
from app.modules.tests_store import MyTestStore
from app.modules.executions_store import ExecutedTestStore

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

@router.post("/{test_id}/execute", response_model=ExecutedTestSchema, status_code=status.HTTP_201_CREATED)
async def execute_test(
    test_id: UUID,
    execution: ExecutedTestCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: StoreProtocol = Depends(deps.get_test_store),
    execution_store: ExecutedTestStore = Depends(deps.get_execution_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> ExecutedTestSchema:
    """
    Execute a test with the given input variables.
    """
    # Get the test
    test = test_store.get(str(test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    # Check if test is active
    if test.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot execute test that is not active"
        )

    try:
        # Use prompt template directly without variable formatting
        prompt = test.prompt_template
        logger.info(f"Using prompt for test {test_id}: {prompt}")

        # TODO: Implement actual AI endpoint call
        # For now, return a mock response
        response = "This is a mock response. AI endpoint integration pending."
        benchmarks = {
            "response_time": 100,
            "total_time": 150,
            "token_usage": {
                "prompt": 10,
                "completion": 5,
                "total": 15
            }
        }

        logger.info(f"Recording test {test_id}")
        # Create execution record
        execution_record = execution_store.create(
            test_id=str(test_id),
            execution=execution,
            user=current_user,
            prompt=prompt,
            response=response,
            benchmarks=benchmarks
        )
        
        logger.info(f"Recorded test {test_id} execution {execution_record}")

        # Update test's last run time and latest execution
        test_store.update(
            str(test_id),
            MyTestCreate(
                name=test.name,
                description=test.description,
                prompt_template=test.prompt_template,
                interface_type=test.interface_type,
                connection_config=test.connection_config,
                validation_config=test.validation_config,
                tags=test.tags,
                risk_level=test.risk_level,
                status=test.status
            )
        )

        return execution_record

    except Exception as e:
        logger.error(f"Error executing test {test_id}: {(e)}")
        # Create execution record with error
        error_execution = execution_store.create(
            test_id=str(test_id),
            execution=execution,
            user=current_user,
            prompt=prompt if 'prompt' in locals() else test.prompt_template,
            response="",
            error={
                "code": "EXECUTION_ERROR",
                "message": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing test: {str(e)}"
        ) 