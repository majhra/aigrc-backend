from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas import AITestSchema, AITestCreate, User

class AITestStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def get(self, test_id: str) -> Optional[AITestSchema]:
        data = self._store.get(test_id)
        if not data:
            return None
        
        # Handle missing group_id field in existing data
        if 'group_id' not in data:
            data['group_id'] = None
        
        try:
            return AITestSchema(**data)
        except Exception as e:
            return None

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> tuple[List[AITestSchema], int]:
        # Get all keys
        keys = self._store.keys()

        if not keys:
            return [], 0

        # Get all tests
        try:
            tests = [self.get(key) for key in keys]
            tests = [t for t in tests if t is not None]  # Filter out None values
        except Exception as e:
            return [], 0

        # Apply filters
        if status:
            tests = [t for t in tests if t.status == status]
        if risk_level:
            tests = [t for t in tests if t.risk_level == risk_level]
        if group_id:  # Filter by group ownership
            # Handle None group_id values - treat them as belonging to a default group
            # Convert both group_id values to strings for comparison
            tests = [t for t in tests if (t.group_id is None and group_id == "default") or str(t.group_id) == str(group_id)]
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

    def create(self, test: AITestCreate, user: User) -> AITestSchema:
        now = datetime.now(timezone.utc)
        test_id = str(uuid4())
        
        new_test = AITestSchema(
            id=test_id,
            created_by=user.id,
            group_id=user.group,
            created_at=now,
            updated_at=now,
            **test.model_dump()
        )
        
        self._store.put(test_id, new_test.model_dump())
        return new_test

    def update(self, test_id: str, test: AITestCreate) -> Optional[AITestSchema]:
        existing_data = self._store.get(test_id)
        if not existing_data:
            return None
            
        existing_test = AITestSchema(**existing_data)
        now = datetime.now(timezone.utc)
        
        updated_test = AITestSchema(
            id=test_id,
            created_by=existing_test.created_by,
            group_id=existing_test.group_id,
            created_at=existing_test.created_at,
            updated_at=now,
            **test.model_dump()
        )
        
        self._store.put(test_id, updated_test.model_dump())
        return updated_test

    def delete(self, test_id: str) -> bool:
        data = self._store.pop(test_id)
        return data is not None

    def belongs_to_group(self, test_id: str, group_id: str) -> bool:
        """Check if a test belongs to a specific group."""
        test = self.get(test_id)
        if not test:
            return False
        return str(test.group_id) == str(group_id)

    def get_tests_by_group(self, group_id: str) -> List[AITestSchema]:
        """Get all tests belonging to a specific group."""
        tests, _ = self.list(group_id=group_id, page=1, limit=1000)  # Get all tests for the group
        return tests


    def clear(self) -> None:
        """Clear all tests from the store. Used for testing."""
        if isinstance(self._store, LocalStore):
            self._store.data.clear() 