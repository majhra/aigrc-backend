from typing import Annotated, List, Optional, Literal
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api import deps
from app.core.config import settings
from app.modules.store_interface import StoreProtocol, RedisStore
from app.modules.tests_store import AITestStore
from app.modules.ai_connection_service import AIConnectionService, AIConnectionError
from app.schemas import AITestSchema, AITestCreate, TestList, User, ConnectionConfig
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

class ConnectionTestRequest(BaseModel):
    connection_config: ConnectionConfig

class ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    response_time: Optional[float] = None

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
        prompt = test.prompt_template or ""
        logger.info(f"Using prompt for test {test_id}: {prompt}")

        # Initialize AI connection service
        ai_service = AIConnectionService(logger)
        
        # Execute the prompt using the AI connection service
        try:
            result = await ai_service.execute_prompt(
                connection_config=test.connection_config,
                prompt=prompt,
                input_variables=execution.input_variables
            )
            
            response = result["response"]
            benchmarks = result["benchmarks"]
            
            # Get the formatted prompt from the AI service
            formatted_prompt = ai_service._format_prompt(prompt, execution.input_variables or {})
            
        except AIConnectionError as ai_error:
            logger.error(f"AI connection error for test {test_id}: {str(ai_error)}")
            # Create execution record with AI error
            error_execution = execution_store.create(
                test_id=str(test_id),
                execution=execution,
                user=current_user,
                prompt=prompt,
                response="",
                error={
                    "code": "AI_CONNECTION_ERROR",
                    "message": str(ai_error)
                }
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI endpoint connection failed: {str(ai_error)}"
            )

        logger.info(f"Creating execution record for test {test_id}")
        # Create execution record (this will automatically update the indexes)
        execution_record = execution_store.create(
            test_id=str(test_id),
            execution=execution,
            user=current_user,
            prompt=formatted_prompt,
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
                prompt=prompt if 'prompt' in locals() else (test.prompt_template or ""),
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

@router.get("/{test_id}/executions", response_model=ExecutedTestList)
async def list_test_executions(
    test_id: UUID,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    execution_store: ExecutedTestStore = Depends(deps.get_execution_store),
    test_store: AITestStore = Depends(deps.get_test_store),
    logger: deps.TLogger = Depends(deps.get_logger),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page"),
    validation_status: Optional[str] = Query(None, description="Filter by validation status (PENDING, IN_PROGRESS, VALIDATED, ERROR)"),
    statuses: Optional[str] = Query(None, description="Filter by multiple validation statuses (comma-separated)"),
    result: Optional[str] = Query(None, description="Filter by validation result (PASS, FAIL)"),
    has_errors: Optional[bool] = Query(None, description="Filter by error presence"),
    outstanding: bool = Query(False, description="Get outstanding tasks (PENDING and ERROR executions)")
) -> ExecutedTestList:
    """
    List executions for a specific test with optional filtering.
    
    Useful for finding:
    - Outstanding tasks: Use outstanding=true
    - Pending executions: Use validation_status=PENDING  
    - Error executions: Use validation_status=ERROR
    - Multiple statuses: Use statuses=PENDING,ERROR
    """
    # Verify test exists and user has access
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
    
    # Handle outstanding tasks shortcut
    if outstanding:
        executions, total = execution_store.list_outstanding_tasks(
            test_id=str(test_id),
            page=page,
            limit=limit
        )
    else:
        # Parse comma-separated statuses if provided
        statuses_list = None
        if statuses:
            statuses_list = [s.strip().upper() for s in statuses.split(',')]
            # Validate statuses
            valid_statuses = {"PENDING", "IN_PROGRESS", "VALIDATED", "ERROR"}
            for s in statuses_list:
                if s not in valid_statuses:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status '{s}'. Valid statuses: {', '.join(valid_statuses)}"
                    )
        
        # Validate single status if provided
        if validation_status:
            status_upper = validation_status.upper()
            valid_statuses = {"PENDING", "IN_PROGRESS", "VALIDATED", "ERROR"}
            if status_upper not in valid_statuses:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid validation_status '{validation_status}'. Valid statuses: {', '.join(valid_statuses)}"
                )
            validation_status = status_upper
        
        # Validate result if provided
        if result:
            result_upper = result.upper()
            valid_results = {"PASS", "FAIL"}
            if result_upper not in valid_results:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid result '{result}'. Valid results: {', '.join(valid_results)}"
                )
            result = result_upper
        
        # Get filtered executions
        executions, total = execution_store.list(
            test_id=str(test_id),
            page=page,
            limit=limit,
            status=validation_status,
            statuses=statuses_list,
            result=result,
            has_errors=has_errors
        )
    
    logger.info(f"Retrieved {len(executions)} executions for test {test_id} (page {page}, total {total})")
    
    return ExecutedTestList(
        items=executions,
        total=total,
        page=page,
        limit=limit
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

@router.post("/test-connection", response_model=ConnectionTestResponse)
async def test_ai_connection(
    request: ConnectionTestRequest,
    current_user: Annotated[User, Depends(deps.get_current_active_user)],
    logger: deps.TLogger = Depends(deps.get_logger),
) -> ConnectionTestResponse:
    """
    Test the connection to an AI endpoint using the provided connection configuration.
    """
    try:
        # Initialize AI connection service
        ai_service = AIConnectionService(logger)
        
        # Test the connection
        success = await ai_service.test_connection(request.connection_config)
        
        if success:
            return ConnectionTestResponse(
                success=True,
                message="Connection test successful"
            )
        else:
            return ConnectionTestResponse(
                success=False,
                message="Connection test failed"
            )
            
    except AIConnectionError as ai_error:
        logger.error(f"AI connection test error: {str(ai_error)}")
        return ConnectionTestResponse(
            success=False,
            message=f"Connection test failed: {str(ai_error)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during connection test: {str(e)}")
        return ConnectionTestResponse(
            success=False,
            message=f"Unexpected error: {str(e)}"
        ) 