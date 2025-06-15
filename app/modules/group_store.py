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
        # Get all groups and filter by name
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

        # Apply filters
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