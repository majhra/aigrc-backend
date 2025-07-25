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
        keys = self._store.keys()

        if not keys:
            return [], 0

        # Filter keys by group if specified
        if group_id:
            keys = [key for key in keys if key.startswith(f"{group_id}:")]

        # Get all users
        try:
            users = []
            for key in keys:
                try:
                    group_id, user_id = self._parse_user_key(key)
                    user = self.get(group_id, user_id)
                    if user:
                        users.append(user)
                except ValueError:
                    # Skip keys that don't match the expected format
                    continue
        except Exception as e:
            print(f"error: {e}")
            return [], 0

        # Apply search filter
        if search:
            search_lower = search.lower()
            users = [
                u for u in users
                if search_lower in u.email.lower()
                or (u.full_name and search_lower in u.full_name.lower())
            ]

        # Calculate pagination
        total = len(users)
        start = (page - 1) * limit
        end = start + limit
        paginated_users = users[start:end]

        return paginated_users, total

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