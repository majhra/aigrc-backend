from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas import TestSchema, MyTestCreate, User

class MyTestStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def get(self, test_id: str) -> Optional[TestSchema]:
        data = self._store.get(test_id)
        if not data:
            return None
        return TestSchema(**data)

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[TestSchema], int]:
        # Get all keys
        keys = self._store.keys()
        if not keys:
            return [], 0

        # Get all tests
        tests = [self.get(key) for key in keys]
        tests = [t for t in tests if t is not None]  # Filter out None values

        # Apply filters
        if status:
            tests = [t for t in tests if t.status == status]
        if risk_level:
            tests = [t for t in tests if t.risk_level == risk_level]
        if search:
            search_lower = search.lower()
            tests = [
                t for t in tests
                if search_lower in t.name.lower()
                or search_lower in t.description.lower()
                or any(search_lower in tag.lower() for tag in t.tags)
            ]

        # Calculate pagination
        total = len(tests)
        start = (page - 1) * limit
        end = start + limit
        paginated_tests = tests[start:end]

        return paginated_tests, total

    def create(self, test: MyTestCreate, user: User) -> TestSchema:
        now = datetime.now(timezone.utc).isoformat()
        test_id = str(uuid4())
        
        new_test = TestSchema(
            id=test_id,
            created_by=user.id,
            created_at=now,
            updated_at=now,
            **test.model_dump()
        )
        
        self._store.put(test_id, new_test.model_dump())
        return new_test

    def update(self, test_id: str, test: MyTestCreate) -> Optional[TestSchema]:
        existing_data = self._store.get(test_id)
        if not existing_data:
            return None
            
        existing_test = TestSchema(**existing_data)
        now = datetime.now(timezone.utc).isoformat()
        
        updated_test = TestSchema(
            id=test_id,
            created_by=existing_test.created_by,
            created_at=existing_test.created_at,
            updated_at=now,
            **test.model_dump()
        )
        
        self._store.put(test_id, updated_test.model_dump())
        return updated_test

    def delete(self, test_id: str) -> bool:
        data = self._store.pop(test_id)
        return data is not None

    def clear(self) -> None:
        """Clear all tests from the store. Used for testing."""
        if isinstance(self._store, LocalStore):
            self._store.data.clear() 