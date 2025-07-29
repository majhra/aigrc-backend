from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.modules.store_interface import LocalStore, StoreProtocol
from app.schemas import User, UserInDB


class UserStore:
    def __init__(self, store: StoreProtocol = None):
        self._store = store or LocalStore()

    def _get_user_key(self, group_id: str, user_id: str) -> str:
        """Generate the Redis key for a user with group structure."""
        return f"{group_id}:{user_id}"

    def _parse_user_key(self, key: str) -> tuple[str, str]:
        """Parse a user key to extract group_id and user_id."""
        parts = key.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid user key format: {key}")
        return parts[0], parts[1]

    def get(self, group_id: str, user_id: str) -> Optional[User]:
        """Get a user by group ID and user ID."""
        # Check if this is an SQL store (has get_filtered method and is not a mock)
        is_sql_store = hasattr(self._store, 'get_filtered') and hasattr(self._store, 'session')
        
        if is_sql_store:
            # For SQL stores, try direct user ID lookup first
            try:
                data = self._store.get(user_id)
                if data:
                    user = User(**data)
                    # Verify the group matches if specified
                    if group_id and user.group != group_id:
                        return None
                    return user
            except Exception:
                pass
        
        # For Redis stores or when SQL lookup fails, use Redis-style key lookup
        key = self._get_user_key(group_id, user_id)
        data = self._store.get(key)
        if not data:
            return None
        return User(**data)

    def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email using the email index."""
        # The underlying store handles email indexing
        data = self._store.get_by_email(email.lower())
        if not data:
            return None
        return User(**data)

    def get_by_id_only(self, user_id: str) -> Optional[User]:
        """Get a user by ID only (searches across all groups)."""
        # Try to use efficient query() method first
        try:
            users = self._store.query(
                filters={"id": user_id},
                keys_only=False
            )
            
            if users:
                return User(**users[0])
            return None
            
        except (AttributeError, TypeError):
            # Fallback for stores without query() method
            return self._get_by_id_only_fallback(user_id)
    
    def _get_by_id_only_fallback(self, user_id: str) -> Optional[User]:
        """Fallback implementation for stores without query() method"""
        # Check if this is an SQL store (has get_filtered method and is not a mock)
        is_sql_store = hasattr(self._store, 'get_filtered') and hasattr(self._store, 'session')
        
        if is_sql_store:
            # For SQL stores, we can directly query by user ID
            try:
                data = self._store.get(user_id)
                if data:
                    return User(**data)
            except Exception:
                pass
        
        # For Redis stores or when SQL lookup fails, search through keys
        keys = self._store.keys()
        if not keys:
            return None

        for key in keys:
            try:
                group_id, stored_user_id = self._parse_user_key(key)
                if stored_user_id == user_id:
                    return self.get(group_id, user_id)
            except ValueError:
                # Skip keys that don't match the expected format
                continue
        return None

    def list(
        self,
        group_id: Optional[str] = None,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> tuple[List[User], int]:
        """List users with pagination and filtering."""
        # Try to use efficient query() method first
        try:
            # Build SQL-compatible filters
            filters = {}
            if group_id:
                filters["group_id"] = group_id
            
            # Add SQL text search using OR condition for email and full_name
            if search:
                search_pattern = f"%{search}%"
                filters["_or"] = [
                    {"email__ilike": search_pattern},
                    {"full_name__ilike": search_pattern}
                ]
            
            # Use efficient database pagination
            user_data_list, total_count = self._store.query(
                filters=filters,
                keys_only=False,
                page=page,
                limit=limit,
                order_by="created_at",
                order_direction="desc"
            )
            
            # Convert to User objects
            users = []
            for user_data in user_data_list:
                try:
                    user = User(**user_data)
                    users.append(user)
                except Exception:
                    continue
            
            return users, total_count
            
        except (AttributeError, TypeError):
            # Fallback to original implementation
            return self._list_fallback(group_id, page, limit, search)

    def create(self, user_data: User, group_id: str) -> User:
        """Create a new user in a specific group."""
        if not user_data.id:
            user_data.id = str(uuid4())

        # Ensure the user has the group_id
        user_data.group = group_id

        # Check if this is an SQL store (has get_filtered method and is not a mock)
        is_sql_store = hasattr(self._store, 'get_filtered') and hasattr(self._store, 'session')
        
        if is_sql_store:
            # For SQL stores, use user_id directly
            self._store.put(str(user_data.id), user_data.model_dump())
        else:
            # For Redis stores, use the key format
            key = self._get_user_key(group_id, str(user_data.id))
            self._store.put(key, user_data.model_dump())
        
        return user_data

    def update(self, group_id: str, user_id: str, user_update: Dict) -> Optional[User]:
        """Update an existing user."""
        existing_user = self.get(group_id, user_id)
        if not existing_user:
            return None

        # Update fields
        for field, value in user_update.items():
            if hasattr(existing_user, field):
                setattr(existing_user, field, value)

        # Check if this is an SQL store (has get_filtered method and is not a mock)
        is_sql_store = hasattr(self._store, 'get_filtered') and hasattr(self._store, 'session')
        
        if is_sql_store:
            # For SQL stores, use user_id directly
            self._store.put(user_id, existing_user.model_dump())
        else:
            # For Redis stores, use the key format
            key = self._get_user_key(group_id, user_id)
            self._store.put(key, existing_user.model_dump())
        
        return existing_user

    def delete(self, group_id: str, user_id: str) -> bool:
        """Delete a user."""
        existing_user = self.get(group_id, user_id)
        if not existing_user:
            return False

        # Check if this is an SQL store (has get_filtered method and is not a mock)
        is_sql_store = hasattr(self._store, 'get_filtered') and hasattr(self._store, 'session')
        
        if is_sql_store:
            # For SQL stores, use user_id directly
            self._store.pop(user_id)
        else:
            # For Redis stores, use the key format
            key = self._get_user_key(group_id, user_id)
            self._store.pop(key)
        
        return True

    def exists(self, group_id: str, user_id: str) -> bool:
        """Check if a user exists."""
        return self.get(group_id, user_id) is not None

    def get_user_uuid_by_email(self, email: str) -> Optional[str]:
        """Get a user's UUID by their email address."""
        user = self.get_by_email(email)
        if user:
            return str(user.id)
        return None 