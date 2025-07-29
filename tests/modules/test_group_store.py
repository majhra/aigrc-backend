import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import timedelta

from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.schemas import Group, GroupCreate, GroupUpdate


class TestGroupStore(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        self.group_store = GroupStore(self.mock_store)
        
        # Configure mock query method to return expected format by default
        self.mock_store.query.return_value = ([], 0)
        
        # Create test group data with timestamp set to 1 second before test runs
        test_timestamp = datetime.now(timezone.utc) - timedelta(seconds=1)
        
        self.test_group = Group(
            id=str(uuid4()),
            name="Test Group",
            description="A test group",
            created_at=test_timestamp,
            updated_at=test_timestamp,
            status="ACTIVE",
            settings={"setting1": "value1"}
        )
        
        self.test_group_id = str(self.test_group.id)

    def test_get_success(self):
        """Test successful group retrieval by ID."""
        # Mock the underlying store to return group data
        self.mock_store.get.return_value = self.test_group.model_dump()
        
        result = self.group_store.get(self.test_group_id)
        
        # Verify the store was called with the correct key
        self.mock_store.get.assert_called_once_with(self.test_group_id)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)
        self.assertEqual(result.id, self.test_group.id)

    def test_get_not_found(self):
        """Test group retrieval when group doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.group_store.get(self.test_group_id)
        
        self.assertIsNone(result)

    def test_get_by_name_success(self):
        """Test successful group retrieval by name."""
        # Mock the query method to return the group on exact match
        self.mock_store.query.return_value = [self.test_group.model_dump()]
        
        result = self.group_store.get_by_name(self.test_group.name)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)
        
        # Verify query was called with exact match filter
        self.mock_store.query.assert_called_once_with(
            filters={'name': self.test_group.name},
            keys_only=False
        )

    def test_get_by_name_not_found(self):
        """Test group retrieval by name when group doesn't exist."""
        # Mock the query method to return empty results for both exact and case-insensitive searches
        self.mock_store.query.side_effect = [[], []]  # Empty for both calls
        
        result = self.group_store.get_by_name("Non-existent Group")
        
        self.assertIsNone(result)

    def test_get_by_name_case_insensitive(self):
        """Test that group retrieval by name is case insensitive."""
        # Mock the query method to return empty on exact match, then the group on case-insensitive search
        self.mock_store.query.side_effect = [
            [],  # First call (exact match) returns empty
            [self.test_group.model_dump()]  # Second call (case-insensitive) returns the group
        ]
        
        result = self.group_store.get_by_name(self.test_group.name.upper())
        
        # Should find the group regardless of case
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)
        
        # Verify both queries were made
        self.assertEqual(self.mock_store.query.call_count, 2)
        
        # First call should be exact match
        first_call = self.mock_store.query.call_args_list[0]
        self.assertEqual(first_call[1]['filters'], {'name': self.test_group.name.upper()})
        
        # Second call should be case-insensitive
        second_call = self.mock_store.query.call_args_list[1] 
        self.assertEqual(second_call[1]['filters'], {'name__ilike': self.test_group.name.upper()})

    def test_list_success(self):
        """Test successful group listing."""
        # Mock the query method to return group data
        self.mock_store.query.return_value = ([self.test_group.model_dump()], 1)
        
        groups, total = self.group_store.list(page=1, limit=10)
        
        # Verify the result
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        self.assertEqual(groups[0].name, self.test_group.name)
        
        # Verify query was called correctly
        self.mock_store.query.assert_called_once_with(
            filters={},
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )

    def test_list_with_status_filter(self):
        """Test group listing with status filter."""
        # Mock the query method to return group data
        self.mock_store.query.return_value = ([self.test_group.model_dump()], 1)
        
        groups, total = self.group_store.list(status="ACTIVE", page=1, limit=10)
        
        # Should return groups with the specified status
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        
        # Verify query was called with status filter
        self.mock_store.query.assert_called_once_with(
            filters={'status': 'ACTIVE'},
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )

    def test_list_with_search(self):
        """Test group listing with search filter."""
        # Mock the query method to return group data
        self.mock_store.query.return_value = ([self.test_group.model_dump()], 1)
        
        groups, total = self.group_store.list(search="test", page=1, limit=10)
        
        # Should return groups matching the search
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        
        # Verify query was called with search filter
        self.mock_store.query.assert_called_once_with(
            filters={'_or': [{'name__ilike': '%test%'}, {'description__ilike': '%test%'}]},
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )

    def test_list_empty(self):
        """Test group listing when no groups exist."""
        # Mock the query method to return empty results (already set in setUp)
        self.mock_store.query.return_value = ([], 0)
        
        groups, total = self.group_store.list(page=1, limit=10)
        
        self.assertEqual(len(groups), 0)
        self.assertEqual(total, 0)

    def test_list_pagination(self):
        """Test group listing with pagination."""
        # Mock the query method to return paginated results (3 groups out of 5 total)
        group_data = [self.test_group.model_dump() for _ in range(3)]
        self.mock_store.query.return_value = (group_data, 5)
        
        groups, total = self.group_store.list(page=1, limit=3)
        
        # Should return paginated results
        self.assertEqual(len(groups), 3)
        self.assertEqual(total, 5)
        
        # Verify query was called with pagination
        self.mock_store.query.assert_called_once_with(
            filters={},
            keys_only=False,
            page=1,
            limit=3,
            order_by="name",
            order_direction="asc"
        )

    def test_create_success(self):
        """Test successful group creation."""
        # Mock the store
        self.mock_store.put.return_value = None
        
        group_data = GroupCreate(
            name="New Group",
            description="A new group",
            settings={"setting1": "value1"}
        )
        
        result = self.group_store.create(group_data, "system")
        
        # Verify the store was called
        self.mock_store.put.assert_called_once()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, group_data.name)
        self.assertEqual(result.description, group_data.description)
        self.assertEqual(result.status, "ACTIVE")
        self.assertIsNotNone(result.id)

    def test_create_without_description(self):
        """Test group creation without description."""
        # Mock the store
        self.mock_store.put.return_value = None
        
        group_data = GroupCreate(name="New Group")
        
        result = self.group_store.create(group_data, "system")
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, group_data.name)
        self.assertIsNone(result.description)

    def test_update_success(self):
        """Test successful group update."""
        # Mock the store to return existing group
        self.mock_store.get.return_value = self.test_group.model_dump()
        self.mock_store.put.return_value = None
        
        update_data = GroupUpdate(name="Updated Group")
        result = self.group_store.update(self.test_group_id, update_data)
        
        # Verify the store was called correctly
        self.mock_store.get.assert_called_once_with(self.test_group_id)
        self.mock_store.put.assert_called_once()
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Updated Group")
        # updated_at should be updated
        self.assertGreaterEqual(result.updated_at, self.test_group.updated_at)

    def test_update_partial(self):
        """Test partial group update."""
        # Mock the store to return existing group
        self.mock_store.get.return_value = self.test_group.model_dump()
        self.mock_store.put.return_value = None
        
        update_data = GroupUpdate(description="Updated description")
        result = self.group_store.update(self.test_group_id, update_data)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertEqual(result.description, "Updated description")
        self.assertEqual(result.name, self.test_group.name)  # Should remain unchanged

    def test_update_group_not_found(self):
        """Test group update when group doesn't exist."""
        self.mock_store.get.return_value = None
        
        update_data = GroupUpdate(name="Updated Group")
        result = self.group_store.update(self.test_group_id, update_data)
        
        self.assertIsNone(result)

    def test_delete_success(self):
        """Test successful group deletion."""
        # Mock the store to return existing group
        self.mock_store.get.return_value = self.test_group.model_dump()
        self.mock_store.pop.return_value = self.test_group.model_dump()
        
        result = self.group_store.delete(self.test_group_id)
        
        # Verify the store was called correctly
        self.mock_store.get.assert_called_once_with(self.test_group_id)
        self.mock_store.pop.assert_called_once_with(self.test_group_id)
        
        # Verify the result
        self.assertTrue(result)

    def test_delete_group_not_found(self):
        """Test group deletion when group doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.group_store.delete(self.test_group_id)
        
        self.assertFalse(result)

    def test_exists_true(self):
        """Test group existence check when group exists."""
        self.mock_store.get.return_value = self.test_group.model_dump()
        
        result = self.group_store.exists(self.test_group_id)
        
        self.assertTrue(result)

    def test_exists_false(self):
        """Test group existence check when group doesn't exist."""
        self.mock_store.get.return_value = None
        
        result = self.group_store.exists(self.test_group_id)
        
        self.assertFalse(result)

    def test_list_with_exception_handling(self):
        """Test group listing with exception handling."""
        # Mock the store to raise an exception
        self.mock_store.keys.return_value = ["group1"]
        self.mock_store.get.side_effect = Exception("Store error")
        
        groups, total = self.group_store.list(page=1, limit=10)
        
        # Should handle the exception gracefully
        self.assertEqual(len(groups), 0)
        self.assertEqual(total, 0)


if __name__ == '__main__':
    unittest.main() 