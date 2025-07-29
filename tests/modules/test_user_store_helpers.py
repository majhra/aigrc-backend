import unittest
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone
import uuid

from app.modules.user_store import UserStore
from app.modules.store_interface import LocalStore
from app.schemas import User


class TestUserStoreHelpers(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.store = LocalStore()
        self.user_store = UserStore(self.store)
        
        # Sample test data
        self.user_uuid1 = str(uuid.uuid4())
        self.user_uuid2 = str(uuid.uuid4())
        self.user_uuid3 = str(uuid.uuid4())
        self.group_id = "test-group"
        self.other_group_id = "other-group"
        
        # Sample users
        self.user_data1 = {
            'id': self.user_uuid1,
            'email': 'goricoaico+test1@gmail.com',
            'full_name': 'Test User One',
            'password': 'hashed_password1',
            'disabled': False,
            'is_verified': True,
            'role': 'user',
            'group': self.group_id,
            'created_at': datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        }
        
        self.user_data2 = {
            'id': self.user_uuid2,
            'email': 'goricoaico+test2@gmail.com',
            'full_name': 'Test User Two',
            'password': 'hashed_password2',
            'disabled': False,
            'is_verified': True,
            'role': 'admin',
            'group': self.group_id,
            'created_at': datetime(2023, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
        }
        
        self.user_data3 = {
            'id': self.user_uuid3,
            'email': 'goricoaico+other@gmail.com',
            'full_name': 'Other User',
            'password': 'hashed_password3',
            'disabled': False,
            'is_verified': True,
            'role': 'user',
            'group': self.other_group_id,
            'created_at': datetime(2023, 1, 3, 10, 0, 0, tzinfo=timezone.utc)
        }

    def test_get_by_id_only_fallback_found_user(self):
        """Test _get_by_id_only_fallback() finds existing user"""
        # Add users to store using Redis-style keys
        redis_key1 = f"{self.group_id}:{self.user_uuid1}"
        redis_key2 = f"{self.other_group_id}:{self.user_uuid3}"
        
        self.store.put(redis_key1, self.user_data1)
        self.store.put(redis_key2, self.user_data3)
        
        # Test finding user in first group
        result = self.user_store._get_by_id_only_fallback(self.user_uuid1)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, User)
        self.assertEqual(str(result.id), self.user_uuid1)
        self.assertEqual(result.email, 'goricoaico+test1@gmail.com')
        self.assertEqual(result.group, self.group_id)

    def test_get_by_id_only_fallback_found_user_different_group(self):
        """Test _get_by_id_only_fallback() finds user in different group"""
        # Add users to store using Redis-style keys
        redis_key = f"{self.other_group_id}:{self.user_uuid3}"
        self.store.put(redis_key, self.user_data3)
        
        # Test finding user in other group
        result = self.user_store._get_by_id_only_fallback(self.user_uuid3)
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, User)
        self.assertEqual(str(result.id), self.user_uuid3)
        self.assertEqual(result.email, 'goricoaico+other@gmail.com')
        self.assertEqual(result.group, self.other_group_id)

    def test_get_by_id_only_fallback_user_not_found(self):
        """Test _get_by_id_only_fallback() returns None when user not found"""
        # Add some users but not the one we're looking for
        redis_key = f"{self.group_id}:{self.user_uuid1}"
        self.store.put(redis_key, self.user_data1)
        
        nonexistent_uuid = str(uuid.uuid4())
        result = self.user_store._get_by_id_only_fallback(nonexistent_uuid)
        
        self.assertIsNone(result)

    def test_get_by_id_only_fallback_empty_store(self):
        """Test _get_by_id_only_fallback() with empty store"""
        result = self.user_store._get_by_id_only_fallback(self.user_uuid1)
        
        self.assertIsNone(result)

    def test_get_by_id_only_fallback_invalid_key_format(self):
        """Test _get_by_id_only_fallback() handles invalid key formats gracefully"""
        # Add users with valid keys
        redis_key = f"{self.group_id}:{self.user_uuid1}"
        self.store.put(redis_key, self.user_data1)
        
        # Add keys with invalid format (should be ignored)
        invalid_keys = [
            "invalid_key_no_colon",
            "too:many:colons:here",
            ":",
            "",
            "single_part"
        ]
        
        for invalid_key in invalid_keys:
            self.store.put(invalid_key, {"invalid": "data"})
        
        # Should still find the valid user, ignoring invalid keys
        result = self.user_store._get_by_id_only_fallback(self.user_uuid1)
        
        self.assertIsNotNone(result)
        self.assertEqual(str(result.id), self.user_uuid1)

    def test_get_by_id_only_fallback_handles_get_exceptions(self):
        """Test _get_by_id_only_fallback() handles exceptions during user retrieval"""
        # Mock the store to raise exception on get()
        mock_store = MagicMock()
        mock_store.keys.return_value = [f"{self.group_id}:{self.user_uuid1}"]
        
        # Make get() raise an exception
        mock_store.get.side_effect = Exception("Database error")
        
        user_store = UserStore(mock_store)
        result = user_store._get_by_id_only_fallback(self.user_uuid1)
        
        # Should handle exception gracefully and return None
        self.assertIsNone(result)

    def test_get_by_id_only_fallback_sql_store_direct_lookup(self):
        """Test _get_by_id_only_fallback() with SQL store uses direct lookup"""
        # Create mock SQL store (has get_filtered and session attributes)
        mock_sql_store = MagicMock()
        mock_sql_store.get_filtered = MagicMock()
        mock_sql_store.session = MagicMock()
        mock_sql_store.get.return_value = self.user_data1
        
        user_store = UserStore(mock_sql_store)
        result = user_store._get_by_id_only_fallback(self.user_uuid1)
        
        # Should use direct get() call for SQL store
        mock_sql_store.get.assert_called_once_with(self.user_uuid1)
        self.assertIsNotNone(result)
        self.assertEqual(str(result.id), self.user_uuid1)

    def test_get_by_id_only_fallback_sql_store_get_fails_fallback_to_redis(self):
        """Test _get_by_id_only_fallback() falls back to Redis-style lookup when SQL get() fails"""
        # Create mock SQL store that fails on get()
        mock_sql_store = MagicMock()
        mock_sql_store.get_filtered = MagicMock()
        mock_sql_store.session = MagicMock()
        mock_sql_store.get.side_effect = Exception("SQL error")
        
        # But succeeds on Redis-style lookup
        redis_key = f"{self.group_id}:{self.user_uuid1}"
        mock_sql_store.keys.return_value = [redis_key]
        
        # Mock the get method for the UserStore.get() call in the fallback
        def mock_get_side_effect(key):
            if key == redis_key:
                return self.user_data1
            return None
        mock_sql_store.get.side_effect = [Exception("SQL error"), self.user_data1]
        
        user_store = UserStore(mock_sql_store)
        
        # Mock the UserStore.get method to return the user
        with unittest.mock.patch.object(user_store, 'get', return_value=User(**self.user_data1)):
            result = user_store._get_by_id_only_fallback(self.user_uuid1)
        
        self.assertIsNotNone(result)
        self.assertEqual(str(result.id), self.user_uuid1)

    def test_get_by_id_only_fallback_multiple_users_different_groups(self):
        """Test _get_by_id_only_fallback() searches across multiple groups"""
        # Add users in different groups
        redis_key1 = f"{self.group_id}:{self.user_uuid1}"
        redis_key2 = f"{self.other_group_id}:{self.user_uuid2}"
        redis_key3 = f"third-group:{self.user_uuid3}"
        
        # Modify user_data2 to have user_uuid2 but be in other_group_id
        user_data2_modified = self.user_data2.copy()
        user_data2_modified['group'] = self.other_group_id
        
        self.store.put(redis_key1, self.user_data1)
        self.store.put(redis_key2, user_data2_modified)
        self.store.put(redis_key3, self.user_data3)
        
        # Should find user2 in other_group_id
        result = self.user_store._get_by_id_only_fallback(self.user_uuid2)
        
        self.assertIsNotNone(result)
        self.assertEqual(str(result.id), self.user_uuid2)
        self.assertEqual(result.group, self.other_group_id)

    def test_parse_user_key_valid_format(self):
        """Test _parse_user_key() with valid key format"""
        key = f"{self.group_id}:{self.user_uuid1}"
        group_id, user_id = self.user_store._parse_user_key(key)
        
        self.assertEqual(group_id, self.group_id)
        self.assertEqual(user_id, self.user_uuid1)

    def test_parse_user_key_invalid_format_no_colon(self):
        """Test _parse_user_key() with invalid format (no colon)"""
        key = "invalid_key_no_colon"
        
        with self.assertRaises(ValueError) as context:
            self.user_store._parse_user_key(key)
        
        self.assertIn("Invalid user key format", str(context.exception))

    def test_parse_user_key_invalid_format_too_many_colons(self):
        """Test _parse_user_key() with invalid format (too many colons)"""
        key = "group:user:extra:parts"
        
        with self.assertRaises(ValueError) as context:
            self.user_store._parse_user_key(key)
        
        self.assertIn("Invalid user key format", str(context.exception))

    def test_parse_user_key_empty_parts(self):
        """Test _parse_user_key() with empty parts"""
        key = ":"
        group_id, user_id = self.user_store._parse_user_key(key)
        
        # Should handle empty parts
        self.assertEqual(group_id, "")
        self.assertEqual(user_id, "")

    def test_get_user_key_generation(self):
        """Test _get_user_key() generates correct key format"""
        key = self.user_store._get_user_key(self.group_id, self.user_uuid1)
        
        expected_key = f"{self.group_id}:{self.user_uuid1}"
        self.assertEqual(key, expected_key)

    def test_get_user_key_with_empty_parts(self):
        """Test _get_user_key() with empty parts"""
        key = self.user_store._get_user_key("", "")
        
        self.assertEqual(key, ":")

    def test_list_fallback_missing_method(self):
        """Test that _list_fallback() method is missing and needs implementation"""
        # This test documents that the _list_fallback method is called but not implemented
        try:
            # This should raise AttributeError because _list_fallback is not implemented
            result = self.user_store._list_fallback(self.group_id, 1, 10, None)
            self.fail("_list_fallback should not be implemented yet")
        except AttributeError:
            # This is expected - the method is missing
            pass

    def test_user_store_helper_methods_coverage(self):
        """Test that all documented helper methods exist or are documented as missing"""
        # Test that _get_by_id_only_fallback exists
        self.assertTrue(hasattr(self.user_store, '_get_by_id_only_fallback'))
        self.assertTrue(callable(getattr(self.user_store, '_get_by_id_only_fallback')))
        
        # Test that _parse_user_key exists
        self.assertTrue(hasattr(self.user_store, '_parse_user_key'))
        self.assertTrue(callable(getattr(self.user_store, '_parse_user_key')))
        
        # Test that _get_user_key exists
        self.assertTrue(hasattr(self.user_store, '_get_user_key'))
        self.assertTrue(callable(getattr(self.user_store, '_get_user_key')))
        
        # Document that _list_fallback is missing
        # Note: This method is referenced in the list() method but not implemented
        # It should be implemented to use the underlying store's natural methods
        # rather than duplicating SQL vs Redis logic


if __name__ == '__main__':
    unittest.main()