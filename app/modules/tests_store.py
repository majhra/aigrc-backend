from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas import AITestSchema, AITestCreate, User

class AITestStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def get(self, test_id: str) -> Optional[AITestSchema]:
        try:
            data = self._store.get(test_id)
        except Exception as e:
            # Handle database connection errors gracefully
            return None
            
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
        # Try efficient query() method first
        try:
            if hasattr(self._store, 'query'):
                # Build filters for database-level filtering
                filters = {}
                if status:
                    filters['status'] = status
                if risk_level:
                    filters['risk_level'] = risk_level
                if group_id:
                    filters['group_id'] = group_id
                
                # Add search filters if provided (SQL text search)
                if search:
                    search_pattern = f"%{search}%"
                    filters['_or'] = [
                        {'name__ilike': search_pattern},
                        {'description__ilike': search_pattern}
                    ]
                
                # Get filtered results with pagination
                test_data, total_count = self._store.query(
                    filters=filters,
                    keys_only=False,
                    page=page,
                    limit=limit,
                    order_by="created_at",
                    order_direction="desc"
                )
                
                # Convert to schema objects
                tests = []
                for data in test_data:
                    try:
                        # Ensure group_id field exists for backward compatibility
                        if 'group_id' not in data:
                            data['group_id'] = None
                        test = AITestSchema(**data)
                        tests.append(test)
                    except Exception:
                        continue
                
                # For search queries involving tags, we need post-processing
                # since tags are complex JSON arrays that require Python filtering
                if search and tests:
                    search_lower = search.lower()
                    filtered_tests = []
                    for test in tests:
                        # Check if already matched by name/description (keep it)
                        name_match = search_lower in test.name.lower()
                        desc_match = search_lower in test.description.lower()
                        tag_match = any(search_lower in tag.lower() for tag in test.tags)
                        
                        if name_match or desc_match or tag_match:
                            filtered_tests.append(test)
                    
                    return filtered_tests, len(filtered_tests)
                
                return tests, total_count
            else:
                # Fallback to old method for non-query supporting stores
                return self._list_fallback(page, limit, status, risk_level, search, group_id)
                
        except Exception:
            # Fallback to Redis-style approach
            return self._list_fallback(page, limit, status, risk_level, search, group_id)

    def _list_fallback(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> tuple[List[AITestSchema], int]:
        """Fallback method using the old Redis-style keys() approach."""
        keys = self._store.keys()
        if not keys:
            return [], 0

        # Get all tests
        try:
            tests = [self.get(key) for key in keys]
            tests = [t for t in tests if t is not None]  # Filter out None values
        except Exception:
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
        # Before deleting the test, we need to delete all related executions
        # to avoid foreign key constraint violations
        try:
            from app.modules.executions_store import ExecutedTestStore
            execution_store = ExecutedTestStore(self._store)
            
            # Get all executions for this test
            executions, _ = execution_store.list(test_id=test_id, page=1, limit=1000)
            
            # Delete all executions first
            for execution in executions:
                execution_store.delete(str(execution.id))
                
        except Exception as e:
            # If we can't delete executions, the test deletion will likely fail
            # Log the error but continue to attempt test deletion
            pass
        
        # Now delete the test
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
        try:
            if hasattr(self._store, 'query'):
                # Use efficient query method without pagination
                test_data = self._store.query(
                    filters={'group_id': group_id},
                    keys_only=False,
                    order_by="created_at",
                    order_direction="desc"
                )
                
                # Convert to schema objects
                tests = []
                for data in test_data:
                    try:
                        # Ensure group_id field exists for backward compatibility
                        if 'group_id' not in data:
                            data['group_id'] = None
                        test = AITestSchema(**data)
                        tests.append(test)
                    except Exception:
                        continue
                
                return tests
            else:
                # Fallback to paginated approach for non-query stores
                tests, _ = self.list(group_id=group_id, page=1, limit=1000)
                return tests
        except Exception:
            # Fallback to paginated approach
            tests, _ = self.list(group_id=group_id, page=1, limit=1000)
            return tests


    def clear(self) -> None:
        """Clear all tests from the store. Used for testing."""
        if isinstance(self._store, LocalStore):
            self._store.data.clear() 