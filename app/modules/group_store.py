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
        # Try using the optimized query() method for SQL stores
        try:
            if hasattr(self._store, 'query'):
                # First try exact case-sensitive match
                groups = self._store.query(
                    filters={'name': name},
                    keys_only=False
                )
                if groups:
                    try:
                        return Group(**groups[0])
                    except Exception:
                        pass
                
                # If exact match failed, fall back to case-insensitive search with ILIKE
                groups = self._store.query(
                    filters={'name__ilike': name},
                    keys_only=False
                )
                if groups:
                    try:
                        return Group(**groups[0])
                    except Exception:
                        pass
                return None
            else:
                # Fallback for stores that don't support query()
                return self._get_by_name_fallback(name)
        except Exception:
            # Fallback to Redis-style approach
            return self._get_by_name_fallback(name)

    def list(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Group], int]:
        """List groups with pagination and filtering."""
        # Try using the optimized query() method for SQL stores
        try:
            if hasattr(self._store, 'query'):
                # Build filters for SQL query
                filters = {}
                if status:
                    filters['status'] = status
                
                # Handle search with OR conditions
                if search:
                    search_term = f"%{search}%"
                    filters['_or'] = [
                        {'name__ilike': search_term},
                        {'description__ilike': search_term}
                    ]
                
                # Use query() method for efficient single-query retrieval
                group_data, total_count = self._store.query(
                    filters=filters,
                    keys_only=False,
                    page=page,
                    limit=limit,
                    order_by="name",
                    order_direction="asc"
                )
                
                # Convert to schema objects
                groups = []
                for data in group_data:
                    try:
                        group = Group(**data)
                        groups.append(group)
                    except Exception:
                        continue
                
                return groups, total_count
            else:
                # Fallback for stores that don't support query()
                return self._list_fallback(page, limit, status, search)
                
        except Exception:
            # Fallback to Redis-style approach
            return self._list_fallback(page, limit, status, search)

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
    
    def _get_by_name_fallback(self, name: str) -> Optional[Group]:
        """Fallback implementation for stores that don't support query() method."""
        keys = self._store.keys()
        if not keys:
            return None

        for key in keys:
            group = self.get(key)
            if group and group.name.lower() == name.lower():
                return group
        return None
    
    def _list_fallback(
        self,
        page: int = 1,
        limit: int = 10,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> tuple[List[Group], int]:
        """Fallback implementation for stores that don't support query() method."""
        keys = self._store.keys()

        if not keys:
            return [], 0

        # Get all groups
        try:
            groups = [self.get(key) for key in keys]
            groups = [g for g in groups if g is not None]  # Filter out None values
        except Exception:
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

        # Sort by name (ascending)
        groups.sort(key=lambda x: x.name.lower())

        # Calculate pagination
        total = len(groups)
        start = (page - 1) * limit
        end = start + limit
        paginated_groups = groups[start:end]

        return paginated_groups, total