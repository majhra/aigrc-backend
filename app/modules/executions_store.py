from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas.executions import ExecutedTestSchema, ExecutedTestCreate, ValidationEvent
from app.schemas import User

class ExecutedTestStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()
        self._test_to_executions_prefix = "test_to_executions:"

    def _get_test_to_executions_key(self, test_id: str) -> str:
        return f"{self._test_to_executions_prefix}{test_id}"

    def _update_indexes(self, execution_id: str, test_id: str, is_delete: bool = False) -> None:
        """Update both indexes when an execution is created or deleted."""
        # hard force this to string, sometimes might be UUID
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
        data = self._store.get(self._get_test_to_executions_key(test_id))
        return data.get("executions", []) if data else []

    def get(self, execution_id: str) -> Optional[ExecutedTestSchema]:
        data = self._store.get(execution_id)
        if not data:
            return None
        return ExecutedTestSchema(**data)

    def list(
        self,
        test_id: str,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        result: Optional[str] = None,
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
                
            execution = self.get(key)
            if execution and str(execution.test_id) == test_id:
                # Apply filters
                if status and execution.validation_status != status:
                    continue
                if result and not any(v.status == result for v in execution.validations):
                    continue
                executions.append(execution)

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
    ) -> ExecutedTestSchema:
        now = datetime.now(timezone.utc)
        execution_id = str(uuid4())
        
        new_execution = ExecutedTestSchema(
            id=execution_id,
            test_id=test_id,
            executed_at=now,
            executed_by=user.id,
            execution_environment=execution.execution_environment,
            input_variables=execution.input_variables,
            prompt=prompt,
            response=response,
            benchmarks=benchmarks,
            error=error,
            validation_status="PENDING",
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

        # Add validation event
        execution.validations.append(ValidationEvent(**validation))
        
        # Update validation status
        if len(execution.validations) > 0:
            execution.validation_status = "VALIDATED"
        self._store.put(execution_id, execution.model_dump())
        return execution

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