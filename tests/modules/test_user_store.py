import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.modules.user_store import UserStore
from app.modules.store_interface import LocalStore
from app.schemas import User
import pytest


class TestUserStore(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        self.user_store = UserStore(self.mock_store)
        
        # Create test user data
        self.test_user = User(
            id=str(uuid4()),
            email="goricoaico+user_store@gmail.com",
            full_name="Test User",
            password="hashed_password",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        self.test_group_id = "test_group"
        self.test_user_id = str(self.test_user.id)

    def test_get_user_key(self):
        """Test that user keys are generated correctly."""
        key = self.user_store._get_user_key(self.test_group_id, self.test_user_id)
        expected_key = f"{self.test_group_id}:{self.test_user_id}"
        self.assertEqual(key, expected_key)

    def test_parse_user_key(self):
        """Test that user keys are parsed correctly."""
        key = f"{self.test_group_id}:{self.test_user_id}"
        group_id, user_id = self.user_store._parse_user_key(key)
        self.assertEqual(group_id, self.test_group_id)
        self.assertEqual(user_id, self.test_user_id)

    def test_parse_user_key_invalid_format(self):
        """Test that invalid key formats raise ValueError."""
        invalid_keys = ["invalid", "too:many:colons", ""]
        for key in invalid_keys:
            with self.assertRaises(ValueError):
                self.user_store._parse_user_key(key)

    def test_get_success(self):
        """Test successful user retrieval by group and user ID."""
        # Mock the underlying store to return user data
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        result = self.user_store.get(self.test_group_id, self.test_user_id)
        
        # Verify the store was called with the correct key
        expected_key = f"{self.test_group_id}:{self.test_user_id}"
        self.mock_store.get.assert_called_once_with(expected_key)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.email, self.test_user.email)
        self.assertEqual(result.id, self.test_user.id)

    def test_get_not_found(self):
        """Test user retrieval when user doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.user_store.get(self.test_group_id, self.test_user_id)
        
        self.assertIsNone(result)

    def test_get_by_email_success(self):
        """Test successful user retrieval by email."""
        # Mock the underlying store to return user data
        self.mock_store.get_by_email.return_value = self.test_user.model_dump()
        
        result = self.user_store.get_by_email(self.test_user.email)
        
        # Verify the store was called with the correct email
        self.mock_store.get_by_email.assert_called_once_with(self.test_user.email.lower())
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.email, self.test_user.email)

    def test_get_by_email_not_found(self):
        """Test user retrieval by email when user doesn't exist."""
        self.mock_store.get_by_email.return_value = None
        
        result = self.user_store.get_by_email(self.test_user.email)
        
        self.assertIsNone(result)

    def test_get_by_id_only_success(self):
        """Test successful user retrieval by ID only."""
        # Mock the store to return keys and user data
        test_key = f"{self.test_group_id}:{self.test_user_id}"
        self.mock_store.keys.return_value = [test_key]
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        result = self.user_store.get_by_id_only(self.test_user_id)
        
        # Verify the store was called correctly
        self.mock_store.keys.assert_called_once()
        self.mock_store.get.assert_called_once_with(test_key)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.test_user.id)

    def test_get_by_id_only_not_found(self):
        """Test user retrieval by ID when user doesn't exist."""
        self.mock_store.keys.return_value = []
        
        result = self.user_store.get_by_id_only(self.test_user_id)
        
        self.assertIsNone(result)

    def test_get_by_id_only_invalid_keys(self):
        """Test user retrieval by ID with invalid keys in store."""
        # Mock the store to return some invalid keys
        invalid_keys = ["invalid_key", "another:invalid:key", f"{self.test_group_id}:{self.test_user_id}"]
        self.mock_store.keys.return_value = invalid_keys
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        result = self.user_store.get_by_id_only(self.test_user_id)
        
        # Should still find the valid key
        self.assertIsNotNone(result)
        self.assertEqual(result.id, self.test_user.id)

    def test_create_success(self):
        """Test successful user creation."""
        # Mock the store
        self.mock_store.put.return_value = None
        
        result = self.user_store.create(self.test_user, self.test_group_id)
        
        # Verify the store was called with the correct key and data
        expected_key = f"{self.test_group_id}:{self.test_user_id}"
        self.mock_store.put.assert_called_once_with(expected_key, self.test_user.model_dump())
        
        # Verify the result
        self.assertEqual(result, self.test_user)
        self.assertEqual(result.group, self.test_group_id)

    @pytest.mark.filterwarnings(r"ignore:Pydantic serializer warnings:UserWarning")
    def test_create_without_id(self):
        """Test user creation when user doesn't have an ID."""
        user_without_id = User(
            email="goricoaico+new@gmail.com",
            full_name="New User",
            password="hashed_password",
            group=self.test_group_id
        )
        
        self.mock_store.put.return_value = None
        
        result = self.user_store.create(user_without_id, self.test_group_id)
        
        # Verify an ID was generated
        self.assertIsNotNone(result.id)
        self.assertEqual(result.group, self.test_group_id)

    def test_update_success(self):
        """Test successful user update."""
        # Mock the store to return existing user
        self.mock_store.get.return_value = self.test_user.model_dump()
        self.mock_store.put.return_value = None
        
        update_data = {"full_name": "Updated Name"}
        result = self.user_store.update(self.test_group_id, self.test_user_id, update_data)
        
        # Verify the store was called correctly
        expected_key = f"{self.test_group_id}:{self.test_user_id}"
        self.mock_store.get.assert_called_once_with(expected_key)
        self.mock_store.put.assert_called_once()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.full_name, "Updated Name")

    def test_update_user_not_found(self):
        """Test user update when user doesn't exist."""
        self.mock_store.get.return_value = None
        
        update_data = {"full_name": "Updated Name"}
        result = self.user_store.update(self.test_group_id, self.test_user_id, update_data)
        
        self.assertIsNone(result)

    def test_delete_success(self):
        """Test successful user deletion."""
        # Mock the store to return existing user
        self.mock_store.get.return_value = self.test_user.model_dump()
        self.mock_store.pop.return_value = self.test_user.model_dump()
        
        result = self.user_store.delete(self.test_group_id, self.test_user_id)
        
        # Verify the store was called correctly
        expected_key = f"{self.test_group_id}:{self.test_user_id}"
        self.mock_store.get.assert_called_once_with(expected_key)
        self.mock_store.pop.assert_called_once_with(expected_key)
        
        # Verify the result
        self.assertTrue(result)

    def test_delete_user_not_found(self):
        """Test user deletion when user doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.user_store.delete(self.test_group_id, self.test_user_id)
        
        self.assertFalse(result)

    def test_exists_true(self):
        """Test user existence check when user exists."""
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        result = self.user_store.exists(self.test_group_id, self.test_user_id)
        
        self.assertTrue(result)

    def test_exists_false(self):
        """Test user existence check when user doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.user_store.exists(self.test_group_id, self.test_user_id)
        
        self.assertFalse(result)

    def test_get_user_uuid_by_email_success(self):
        """Test getting user UUID by email when user exists."""
        self.mock_store.get_by_email.return_value = self.test_user.model_dump()
        
        result = self.user_store.get_user_uuid_by_email(self.test_user.email)
        
        self.assertEqual(result, str(self.test_user.id))

    def test_get_user_uuid_by_email_not_found(self):
        """Test getting user UUID by email when user doesn't exist."""
        self.mock_store.get_by_email.return_value = None
        
        result = self.user_store.get_user_uuid_by_email(self.test_user.email)
        
        self.assertIsNone(result)

    def test_list_users_success(self):
        """Test successful user listing."""
        # Mock the store to return keys and user data
        test_keys = [f"{self.test_group_id}:{self.test_user_id}"]
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        users, total = self.user_store.list(page=1, limit=10)
        
        # Verify the result
        self.assertEqual(len(users), 1)
        self.assertEqual(total, 1)
        self.assertEqual(users[0].email, self.test_user.email)

    def test_list_users_with_group_filter(self):
        """Test user listing with group filter."""
        # Mock the store to return keys for different groups
        test_keys = [
            f"{self.test_group_id}:{self.test_user_id}",
            "other_group:other_user",
            f"{self.test_group_id}:another_user"
        ]
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        users, total = self.user_store.list(group_id=self.test_group_id, page=1, limit=10)
        
        # Should only return users from the specified group
        self.assertEqual(len(users), 2)
        self.assertEqual(total, 2)

    def test_list_users_with_search(self):
        """Test user listing with search filter."""
        # Mock the store to return keys and user data
        test_keys = [f"{self.test_group_id}:{self.test_user_id}"]
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        users, total = self.user_store.list(search="test", page=1, limit=10)
        
        # Should return users matching the search
        self.assertEqual(len(users), 1)
        self.assertEqual(total, 1)

    def test_list_users_empty(self):
        """Test user listing when no users exist."""
        self.mock_store.keys.return_value = []
        
        users, total = self.user_store.list(page=1, limit=10)
        
        self.assertEqual(len(users), 0)
        self.assertEqual(total, 0)

    def test_list_users_pagination(self):
        """Test user listing with pagination."""
        # Mock the store to return multiple keys
        test_keys = [f"{self.test_group_id}:user{i}" for i in range(5)]
        self.mock_store.keys.return_value = test_keys
        self.mock_store.get.return_value = self.test_user.model_dump()
        
        users, total = self.user_store.list(page=1, limit=3)
        
        # Should return paginated results
        self.assertEqual(len(users), 3)
        self.assertEqual(total, 5)


if __name__ == '__main__':
    unittest.main() 