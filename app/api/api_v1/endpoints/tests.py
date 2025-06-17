from typing import Annotated, List, Optional, Literal
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api import deps
from app.core.config import settings
from app.modules.store_interface import StoreProtocol, RedisStore
from app.modules.tests_store import AITestStore
from app.schemas import AITestSchema, AITestCreate, TestList, User
from app.schemas.executions import (
    ExecutedTestCreate, 
    ExecutedTestSchema, 
    ExecutedTestList,
    ValidationEvent
)
from app.modules.executions_store import ExecutedTestStore

router = APIRouter()

# New model for the combined test and execution response
class TestExecutionDetail(BaseModel):
    test: AITestSchema
    execution: ExecutedTestSchema

class TestWithExecutions(BaseModel):
    test: AITestSchema
    execution_ids: List[UUID]

@router.get("", response_model=TestList)
async def list_tests(
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: AITestStore = Depends(deps.get_test_store),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None, pattern="^(DRAFT|ACTIVE|ARCHIVED)$"),
    risk_level: Optional[str] = Query(None, pattern="^(LOW|MEDIUM|HIGH)$"),
    search: Optional[str] = None,
    logger: deps.TLogger = Depends(deps.get_logger),
) -> TestList:
    """
    List all tests with pagination and filtering.
    Users can only see tests from their own group unless they are admin.
    """
    # Filter tests by user's group unless user is admin
    group_filter = None
    if current_user.role != "admin":
        group_filter = current_user.group
        # If user has no group, they can see tests with no group_id (legacy tests)
        if not group_filter:
            group_filter = "default"
    
    tests, total = test_store.list(
        page=page,
        limit=limit,
        status=status,
        risk_level=risk_level,
        search=search,
        group_id=group_filter
    )
    
    return TestList(
        items=tests,
        total=total,
        page=page,
        limit=limit
    )

@router.get("/{test_id}", response_model=TestWithExecutions)
async def get_test(
    test_id: UUID,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: AITestStore = Depends(deps.get_test_store),
    execution_store: ExecutedTestStore = Depends(deps.get_execution_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> TestWithExecutions:
    """
    Get test details by ID along with associated execution IDs.
    Users can only access tests from their own group unless they are admin.
    """
    logger.info(f"Getting test with ID: {test_id}")
    test = test_store.get(str(test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check group ownership unless user is admin
    if current_user.role != "admin" and test.group_id != current_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Test does not belong to your group"
        )
    
    # Get execution IDs for this test
    execution_ids = execution_store.get_execution_ids_for_test(str(test_id))
    if not execution_ids:
        execution_ids = []
    
    return TestWithExecutions(
        test=test,
        execution_ids=[exec_id for exec_id in execution_ids]
    )

@router.post("", response_model=AITestSchema, status_code=status.HTTP_201_CREATED)
async def create_test(
    test: AITestCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: AITestStore = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> AITestSchema:
    """
    Create a new test.
    """
    return test_store.create(test, current_user)

@router.put("/{test_id}", response_model=AITestSchema)
async def update_test(
    test_id: UUID,
    test: AITestCreate,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: AITestStore = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> AITestSchema:
    """
    Update an existing test.
    Users can only update tests from their own group unless they are admin.
    """
    # Get the test and check ownership
    existing_test = test_store.get(str(test_id))
    if not existing_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check group ownership unless user is admin
    if current_user.role != "admin" and existing_test.group_id != current_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Test does not belong to your group"
        )
    
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
    test_store: AITestStore = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> None:
    """
    Delete a test.
    Users can only delete tests from their own group unless they are admin.
    """
    # Get the test and check ownership
    existing_test = test_store.get(str(test_id))
    if not existing_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    # Check group ownership unless user is admin
    if current_user.role != "admin" and existing_test.group_id != current_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Test does not belong to your group"
        )
    
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
    test_store: AITestStore = Depends(deps.get_test_store),
    execution_store: ExecutedTestStore = Depends(deps.get_execution_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> ExecutedTestSchema:
    """
    Execute a test with the given input variables.
    Creates a new execution record and establishes the test-execution relationship.
    Users can only execute tests from their own group unless they are admin.
    """
    # Get the test and check ownership
    test = test_store.get(str(test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    # Check group ownership unless user is admin
    if current_user.role != "admin" and test.group_id != current_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Test does not belong to your group"
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

        logger.info(f"Creating execution record for test {test_id}")
        # Create execution record (this will automatically update the indexes)
        execution_record = execution_store.create(
            test_id=str(test_id),
            execution=execution,
            user=current_user,
            prompt=prompt,
            response=response,
            benchmarks=benchmarks
        )
        
        # Verify the execution was properly indexed
        logger.info(f"Execution record: {execution_record}")
        if execution_record.test_id != test_id:
            logger.error(f"Execution {execution_record.id} was not properly indexed for test {test_id}")
            # Clean up the execution if indexing failed
            execution_store.delete(execution_record.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to establish test-execution relationship"
            )

        logger.info(f"Successfully created and indexed execution {execution_record.id} for test {test_id}")

        # Update test's last run time and latest execution
        test_store.update(
            str(test_id),
            AITestCreate(
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

    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Error executing test {test_id}: {str(e)}")
        # Create execution record with error
        try:
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
            # Clean up the error execution if it was created but indexing failed
            if error_execution:
                if execution_record["test_id"] != str(test_id):
                    execution_store.delete(error_execution.id)
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup of failed execution: {str(cleanup_error)}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing test: {str(e)}"
        )

@router.post("/{test_id}/{execution_id}/validate", response_model=ExecutedTestSchema)
async def validate_execution(
    test_id: UUID,
    execution_id: UUID,
    validation: ValidationEvent,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: AITestStore = Depends(deps.get_test_store),
    execution_store: ExecutedTestStore = Depends(deps.get_execution_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> ExecutedTestSchema:
    """
    Submit validation for a test execution.
    """

    raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Not implemented"
        )

    #The remainder of this code is waiting for finalisation of validations. Keeping it for the moment. 
    # Get the test
    execution = execution_store.get(str(execution_id))
    if not execution:
        logger.warning(f"Execution {execution_id} for {test_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    logger.info(f"Recorded execution {execution_id} base test {test_id}")

    # Get the latest execution for this test
    executions = execution_store.get_execution_ids_for_test(str(test_id))
    logger.info(f"Recorded test {test_id} base test {executions}")
    if not executions or not executions[0]:
        logger.warning(f"No executions found for this test {test_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No execution found for this test"
        )

    # Verify validator has permission to validate this test
    if validation.validator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot submit validation for another user"
        )

    # Add timestamp to validation
    validation_dict = validation.model_dump()
    validation_dict["timestamp"] = datetime.now(timezone.utc)

    logger.info(f"Recorded test {test_id} validation {validation_dict}")

    try:
        # Add validation to execution
        updated_execution = execution_store.add_validation(str(execution.id), validation_dict)
        if not updated_execution:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add validation"
            )

        logger.info(f"Added validation to execution {execution.id} by user {current_user.id}")
        return updated_execution

    except Exception as e:
        logger.error(f"Error adding validation to execution {execution.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding validation: {str(e)}"
        )

@router.put("/{test_id}/{execution_id}/validate", response_model=ExecutedTestSchema)
async def validate_execution(
    test_id: UUID,
    execution_id: UUID,
    validation: ValidationEvent,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: AITestStore = Depends(deps.get_test_store),
    execution_store: ExecutedTestStore = Depends(deps.get_execution_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> ExecutedTestSchema:
    """
    Add a new validation to an existing test execution.
    The execution must exist and belong to the specified test.
    Users can only validate executions for tests from their own group unless they are admin.
    """
    # Get the test and check ownership
    test = test_store.get(str(test_id))
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    # Check group ownership unless user is admin
    if current_user.role != "admin" and test.group_id != current_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Test does not belong to your group"
        )

    # Verify the execution exists and belongs to this test
    execution_test_id = execution_store.get(str(execution_id))
    if not execution_test_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    if execution_test_id.test_id != test_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution does not belong to the specified test"
        )

    # Create validation event with current user's ID
    validation_dict = validation.model_dump()
    validation_dict.update({
        "validator_id": current_user.id,
        "timestamp": datetime.now(timezone.utc)
    })

    logger.info(f"Adding validation {validation_dict} to execution {execution_id} for test {test_id}")

    try:
        # Add validation to execution
        updated_execution = execution_store.add_validation(str(execution_id), validation_dict)
        if not updated_execution:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add validation"
            )

        logger.info(f"Added validation to execution {execution_id} by user {current_user.id}")
        return updated_execution

    except Exception as e:
        logger.error(f"Error adding validation to execution {execution_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding validation: {str(e)}"
        )

@router.get("/{test_id}/{execution_id}", response_model=TestExecutionDetail)
async def get_test_execution(
    test_id: UUID,
    execution_id: UUID,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    test_store: AITestStore = Depends(deps.get_test_store),
    execution_store: ExecutedTestStore = Depends(deps.get_execution_store),
    logger: deps.TLogger = Depends(deps.get_logger),
) -> TestExecutionDetail:
    """
    Get detailed information about a specific test execution, including:
    - The test details
    - The execution record
    - All validations for this execution
    Users can only access executions for tests from their own group unless they are admin.
    """
    # Get the test and check ownership
    test = test_store.get(str(test_id))
    if not test:
        logger.warning(f"Test {test_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )

    # Check group ownership unless user is admin
    if current_user.role != "admin" and test.group_id != current_user.group:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Test does not belong to your group"
        )

    # Verify the execution exists and belongs to this test
    execution_test_id = execution_store.get(str(execution_id))
    if not execution_test_id:
        logger.warning(f"Execution {execution_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found"
        )
    
    if execution_test_id.test_id != test_id:
        logger.warning(f"Execution {execution_id} does not belong to test {test_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Execution does not belong to the specified test"
        )

    # Get the execution details
    execution = execution_store.get(str(execution_id))
    if not execution:
        logger.warning(f"Execution {execution_id} details not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution details not found"
        )

    logger.info(f"Retrieved execution {execution_id} for test {test_id}")
    return TestExecutionDetail(test=test, execution=execution) 