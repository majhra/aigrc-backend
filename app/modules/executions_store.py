from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas.executions import (
    ExecutedTestSchema, 
    ExecutedTestCreate, 
    ValidationEvent,
    PerformanceMetrics,
    ErrorDetails
)
from app.schemas import User

class ExecutedTestStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()
        self._test_to_executions_prefix = "test_to_executions:"

    def _get_test_to_executions_key(self, test_id: str) -> str:
        return f"{self._test_to_executions_prefix}{test_id}"

    def _update_indexes(self, execution_id: str, test_id: str, is_delete: bool = False) -> None:
        """Update both indexes when an execution is created or deleted."""
        # For SQL stores, we don't need custom indexing - the database handles relationships
        # For Redis stores, maintain the original indexing logic
        
        # Check if this is an SQL store by trying to use SQL-specific features
        try:
            # Try to check if the store has get_filtered method (SQL store specific)
            if hasattr(self._store, 'get_filtered'):
                # SQL store - no custom indexing needed, database handles relationships
                return
        except:
            pass
        
        # Redis store - use original indexing logic
        execution_id = str(execution_id)
        test_id = str(test_id)
        if is_delete:
            # Remove from test_to_executions index
            test_key = self._get_test_to_executions_key(test_id)
            data = self._store.get(test_key)
            if data:
                executions = set(data.get("executions", []))
                executions.discard(execution_id)
                if executions:
                    self._store.put(test_key, {"executions": list(executions)})
                else:
                    self._store.pop(test_key)
        else:
            # Add to test_to_executions index
            test_key = self._get_test_to_executions_key(test_id)
            data = self._store.get(test_key)
            executions = set(data.get("executions", []) if data else [])
            executions.add(execution_id)
            self._store.put(test_key, {"executions": list(executions)})

    def get_execution_ids_for_test(self, test_id: str) -> List[str]:
        """Get all execution IDs associated with a test ID."""
        # For SQL stores, query executions by test_id directly
        try:
            if hasattr(self._store, 'get_filtered'):
                # SQL store - use filter query
                executions = self._store.get_filtered({'test_id': test_id})
                return [exec_data.get('id') for exec_data in executions if exec_data.get('id')]
        except:
            pass
        
        # Redis store - use index
        data = self._store.get(self._get_test_to_executions_key(test_id))
        return data.get("executions", []) if data else []

    def get(self, execution_id: str) -> Optional[ExecutedTestSchema]:
        data = self._store.get(execution_id)
        if not data:
            return None
        
        # Fix None values for required string fields
        if data.get('prompt') is None:
            data['prompt'] = ""
        if data.get('response') is None:
            data['response'] = ""
        
        # Fix input_variables if it's an empty string or invalid type
        if data.get('input_variables') == "" or not isinstance(data.get('input_variables'), (dict, type(None))):
            data['input_variables'] = None
        
        # Fix error field if it's an empty string or invalid type
        if data.get('error') == "" or not isinstance(data.get('error'), (dict, type(None))):
            data['error'] = None
        
        try:
            return ExecutedTestSchema(**data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create ExecutedTestSchema from data: {e}")
            logger.error(f"Data that caused the error: {data}")
            raise

    def list(
        self,
        test_id: str,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        statuses: Optional[List[str]] = None,
        result: Optional[str] = None,
        has_errors: Optional[bool] = None,
    ) -> Tuple[List[ExecutedTestSchema], int]:
        # Get all keys
        keys = self._store.keys()

        if not keys:
            return [], 0

        # Get all executions
        executions = []
        for key in keys:
            # Skip index keys
            if key.startswith(self._test_to_executions_prefix):
                continue
                
            try:
                execution = self.get(key)
                if execution and str(execution.test_id) == test_id:
                    # Apply filters
                    if status and execution.validation_status != status:
                        continue
                    if statuses and execution.validation_status not in statuses:
                        continue
                    if result and not any(v.status == result for v in execution.validations):
                        continue
                    if has_errors is not None:
                        if has_errors and not execution.error:
                            continue
                        if not has_errors and execution.error:
                            continue
                    executions.append(execution)
            except Exception:
                # Skip keys that can't be deserialized as ExecutedTestSchema
                # This happens when the store contains other types of data (like tests)
                continue

        # Sort by executed_at descending
        executions.sort(key=lambda x: x.executed_at, reverse=True)

        # Calculate pagination
        total = len(executions)
        start = (page - 1) * limit
        end = start + limit
        paginated_executions = executions[start:end]

        return paginated_executions, total

    def create(
        self,
        test_id: str,
        execution: ExecutedTestCreate,
        user: User,
        prompt: str,
        response: str,
        benchmarks: Optional[Dict] = None,
        error: Optional[Dict] = None,
        test_group_id: Optional[str] = None,  # Pass group_id from test
    ) -> ExecutedTestSchema:
        now = datetime.now(timezone.utc)
        execution_id = str(uuid4())
        
        # If test_group_id not provided, try to get it from the test
        group_id = test_group_id
        if not group_id:
            # Try to get the test from the store to inherit its group_id
            try:
                from app.modules.tests_store import AITestStore
                test_store = AITestStore(self._store)
                test = test_store.get(test_id)
                if test:
                    group_id = test.group_id
            except Exception:
                # If we can't get the test, fall back to user's group
                group_id = user.group
        
        # Convert benchmarks dict to PerformanceMetrics object if provided
        benchmarks_obj = None
        if benchmarks:
            if isinstance(benchmarks, dict):
                benchmarks_obj = PerformanceMetrics(**benchmarks)
            else:
                # Already a PerformanceMetrics object
                benchmarks_obj = benchmarks
        
        # Convert error dict to ErrorDetails object if provided
        error_obj = None
        if error:
            if isinstance(error, dict):
                error_obj = ErrorDetails(**error)
            else:
                # Already an ErrorDetails object
                error_obj = error
        
        # Set validation status based on error presence
        validation_status = "ERROR" if error_obj else "PENDING"
        
        new_execution = ExecutedTestSchema(
            id=execution_id,
            test_id=test_id,
            executed_at=now,
            executed_by=user.id,
            group_id=group_id,  # Inherit group_id from test
            execution_environment=execution.execution_environment,
            input_variables=execution.input_variables,
            prompt=prompt,
            response=response,
            benchmarks=benchmarks_obj,
            error=error_obj,
            validation_status=validation_status,
            validations=[]
        )
        
        # Store the execution and update indexes
        self._store.put(execution_id, new_execution.model_dump())
        self._update_indexes(execution_id, test_id)
        return new_execution

    def add_validation(
        self,
        execution_id: str,
        validation: Dict
    ) -> Optional[ExecutedTestSchema]:
        execution = self.get(execution_id)

        if not execution:
            return None

        # Convert UUID objects to strings in validation data
        validation_copy = validation.copy()
        if 'validator_id' in validation_copy and hasattr(validation_copy['validator_id'], '__str__'):
            validation_copy['validator_id'] = str(validation_copy['validator_id'])

        # Add validation event
        execution.validations.append(ValidationEvent(**validation_copy))
        
        # Update validation status
        if len(execution.validations) > 0:
            execution.validation_status = "VALIDATED"
        
        # Convert the model to dict with proper UUID serialization
        execution_data = execution.model_dump(mode='json')
        self._store.put(execution_id, execution_data)
        return execution

    def list_outstanding_tasks(
        self,
        test_id: str,
        page: int = 1,
        limit: int = 10
    ) -> Tuple[List[ExecutedTestSchema], int]:
        """
        Get executions that need attention (PENDING or ERROR status).
        This is a convenience method for finding outstanding tasks.
        """
        return self.list(
            test_id=test_id,
            page=page,
            limit=limit,
            statuses=["PENDING", "ERROR"]
        )

    def delete(self, execution_id: str) -> bool:
        # Get test_id before deleting
        execution = self.get(execution_id)
        if execution is None:
            return False
            
        test_id = str(execution.test_id)
            
        # Delete the execution and update indexes
        data = self._store.pop(execution_id)
        if data is not None:
            self._update_indexes(execution_id, test_id, is_delete=True)
        return data is not None

    def clear(self) -> None:
        """Clear all executions and indexes from the store. Used for testing."""
        if isinstance(self._store, LocalStore):
            # Clear all execution records and indexes
            keys_to_delete = self._store.keys()
            for key in keys_to_delete:
                self._store.pop(key) 