from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas import Group, GroupCreate, GroupUpdate


class GroupStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def get(self, group_id: str) -> Optional[Group]:
        """Get a group by ID."""
        data = self._store.get(group_id)
        if not data:
            return None
        return Group(**data)

    def get_by_name(self, name: str) -> Optional[Group]:
        """Get a group by name."""
        # For SQL stores, use more efficient filtered queries when possible
        try:
            if hasattr(self._store, 'get_filtered'):
                # Use SQL filtering by name
                group_data = self._store.get_filtered({'name': name})
                if group_data:
                    try:
                        return Group(**group_data[0])
                    except Exception:
                        pass
                
                # If exact match failed, fall back to case-insensitive search
                all_data = self._store.get_filtered({})
                for data in all_data:
                    try:
                        group = Group(**data)
                        if group.name.lower() == name.lower():
                            return group
                    except Exception:
                        continue
                return None
            else:
                raise Exception("Not an SQL store")
        except Exception:
            # Fallback to Redis-style approach
            keys = self._store.keys()
            if not keys:
                return None

            for key in keys:
                group = self.get(key)
                if group and group.name.lower() == name.lower():
                    return group
            return None

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Group], int]:
        """List groups with pagination and filtering."""
        sql_filtered = False  # Track if SQL filtering was used
        
        # For SQL stores, use more efficient filtered queries when possible
        try:
            if hasattr(self._store, 'get_filtered'):
                # Build filters for SQL query
                filters = {}
                if status:
                    filters['status'] = status
                
                # Get filtered results from SQL
                if filters:
                    sql_filtered = True
                    group_data = self._store.get_filtered(filters)
                    groups = []
                    for data in group_data:
                        try:
                            group = Group(**data)
                            groups.append(group)
                        except Exception:
                            continue
                else:
                    # No filters were applied, fall back to keys() approach for SQL stores
                    keys = self._store.keys()
                    if keys:
                        groups = [self.get(key) for key in keys]
                        groups = [g for g in groups if g is not None]
                    else:
                        groups = []
            else:
                raise Exception("Not an SQL store")
        except Exception:
            # Fallback to Redis-style approach
            keys = self._store.keys()

            if not keys:
                return [], 0

            # Get all groups
            try:
                groups = [self.get(key) for key in keys]
                groups = [g for g in groups if g is not None]  # Filter out None values
            except Exception as e:
                print(f"error: {e}")
                return [], 0

        # Apply filters only if SQL filtering wasn't used
        if not sql_filtered:
            if status:
                groups = [g for g in groups if g.status == status]
        if search:
            search_lower = search.lower()
            groups = [
                g for g in groups
                if search_lower in g.name.lower()
                or (g.description and search_lower in g.description.lower())
            ]

        # Calculate pagination
        total = len(groups)
        start = (page - 1) * limit
        end = start + limit
        paginated_groups = groups[start:end]

        return paginated_groups, total

    def create(self, group_data: GroupCreate, created_by: str) -> Group:
        """Create a new group."""
        group_id = str(uuid4())
        
        group = Group(
            id=group_id,
            name=group_data.name,
            description=group_data.description,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            status="ACTIVE",
            settings=group_data.settings or {}
        )

        self._store.put(group_id, group.model_dump())
        return group

    def update(self, group_id: str, group_update: GroupUpdate) -> Optional[Group]:
        """Update an existing group."""
        existing_group = self.get(group_id)
        if not existing_group:
            return None

        # Update fields
        update_data = group_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_group, field, value)
        
        # Always update the updated_at timestamp
        existing_group.updated_at = datetime.now(timezone.utc)

        self._store.put(group_id, existing_group.model_dump())
        return existing_group

    def delete(self, group_id: str) -> bool:
        """Delete a group."""
        existing_group = self.get(group_id)
        if not existing_group:
            return False

        self._store.pop(group_id)
        return True

    def exists(self, group_id: str) -> bool:
        """Check if a group exists."""
        return self.get(group_id) is not None 