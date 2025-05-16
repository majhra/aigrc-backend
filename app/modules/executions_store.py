from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas.executions import ExecutedTestSchema, ExecutedTestCreate, ValidationEvent
from app.schemas import User

class ExecutedTestStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()
        self._prefix = "execution:"

    def _get_key(self, execution_id: str) -> str:
        return f"{self._prefix}{execution_id}"

    def get(self, execution_id: str) -> Optional[ExecutedTestSchema]:
        data = self._store.get(self._get_key(execution_id))
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
        # Get all keys with prefix
        keys = [k for k in self._store.keys() if k.startswith(self._prefix)]

        if not keys:
            return [], 0

        # Get all executions
        executions = []
        for key in keys:
            execution = self.get(key[len(self._prefix):])
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
        
        self._store.put(self._get_key(execution_id), new_execution.model_dump())
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
        
        self._store.put(self._get_key(execution_id), execution.model_dump())
        return execution

    def delete(self, execution_id: str) -> bool:
        data = self._store.pop(self._get_key(execution_id))
        return data is not None

    def clear(self) -> None:
        """Clear all executions from the store. Used for testing."""
        if isinstance(self._store, LocalStore):
            keys_to_delete = [k for k in self._store.keys() if k.startswith(self._prefix)]
            for key in keys_to_delete:
                self._store.pop(key) 