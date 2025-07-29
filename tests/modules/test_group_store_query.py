import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.schemas import Group


class TestGroupStoreQuery(unittest.TestCase):
    """Test the query() method migration for GroupStore."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        self.group_store = GroupStore(self.mock_store)
        
        # Configure mock query method to return expected format by default
        self.mock_store.query.return_value = ([], 0)
        
        # Create test group data
        test_timestamp = datetime.now(timezone.utc)
        
        self.test_group = Group(
            id=str(uuid4()),
            name="Test Group",
            description="A test group for testing",
            created_at=test_timestamp,
            updated_at=test_timestamp,
            status="ACTIVE",
            settings={"setting1": "value1"}
        )

    def test_list_basic_filtering(self):
        """Test list() method with basic filters using query()."""
        # Mock the query method to return group data
        self.mock_store.query.return_value = ([self.test_group.model_dump()], 1)
        
        groups, total = self.group_store.list(
            status="ACTIVE",
            page=1,
            limit=10
        )
        
        # Verify the result
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        self.assertEqual(groups[0].name, self.test_group.name)
        
        # Verify query was called with correct filters
        self.mock_store.query.assert_called_once_with(
            filters={'status': 'ACTIVE'},
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )

    def test_list_with_search(self):
        """Test list() method with search using OR conditions."""
        # Mock the query method to return group data
        self.mock_store.query.return_value = ([self.test_group.model_dump()], 1)
        
        groups, total = self.group_store.list(
            search="test",
            page=1,
            limit=10
        )
        
        # Verify the result
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        
        # Verify query was called with OR search conditions
        self.mock_store.query.assert_called_once_with(
            filters={
                '_or': [
                    {'name__ilike': '%test%'},
                    {'description__ilike': '%test%'}
                ]
            },
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )

    def test_list_combined_filters_and_search(self):
        """Test list() method with both filters and search."""
        # Mock the query method to return group data
        self.mock_store.query.return_value = ([self.test_group.model_dump()], 1)
        
        groups, total = self.group_store.list(
            status="ACTIVE",
            search="group",
            page=2,
            limit=5
        )
        
        # Verify the result
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        
        # Verify query was called with combined filters
        self.mock_store.query.assert_called_once_with(
            filters={
                'status': 'ACTIVE',
                '_or': [
                    {'name__ilike': '%group%'},
                    {'description__ilike': '%group%'}
                ]
            },
            keys_only=False,
            page=2,
            limit=5,
            order_by="name",
            order_direction="asc"
        )

    def test_list_conversion_error_handling(self):
        """Test list() method handles conversion errors gracefully."""
        # Mock the query method to return malformed data
        malformed_data = {"invalid": "data", "missing_required_fields": True}
        self.mock_store.query.return_value = ([malformed_data], 1)
        
        groups, total = self.group_store.list(page=1, limit=10)
        
        # Should return empty list when conversion fails
        self.assertEqual(len(groups), 0)
        self.assertEqual(total, 1)  # Total count from query still returned

    def test_list_fallback_when_query_not_supported(self):
        """Test list() method falls back to keys() when query() not supported."""
        # Remove query method to simulate non-SQL store
        del self.mock_store.query
        
        # Mock fallback keys/get approach
        self.mock_store.keys.return_value = [str(self.test_group.id)]
        self.mock_store.get.return_value = self.test_group.model_dump()
        
        groups, total = self.group_store.list(
            status="ACTIVE",
            page=1,
            limit=10
        )
        
        # Should still work with fallback
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        
        # Verify fallback methods were called
        self.mock_store.keys.assert_called_once()

    def test_list_fallback_on_query_exception(self):
        """Test list() method falls back when query() raises exception."""
        # Mock query to raise exception
        self.mock_store.query.side_effect = Exception("SQL error")
        
        # Mock fallback keys/get approach
        self.mock_store.keys.return_value = [str(self.test_group.id)]
        self.mock_store.get.return_value = self.test_group.model_dump()
        
        groups, total = self.group_store.list(page=1, limit=10)
        
        # Should still work with fallback
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)

    def test_get_by_name_exact_match(self):
        """Test get_by_name() with exact case match."""
        # Mock the query method to return group on first call (exact match)
        self.mock_store.query.return_value = [self.test_group.model_dump()]
        
        result = self.group_store.get_by_name(self.test_group.name)
        
        # Should find the group
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)
        
        # Verify query was called with exact match filter
        self.mock_store.query.assert_called_once_with(
            filters={'name': self.test_group.name},
            keys_only=False
        )

    def test_get_by_name_case_insensitive_fallback(self):
        """Test get_by_name() falls back to case-insensitive search."""
        # Mock the query method to return empty on exact match, then group on case-insensitive
        self.mock_store.query.side_effect = [
            [],  # First call (exact match) returns empty
            [self.test_group.model_dump()]  # Second call (case-insensitive) returns group
        ]
        
        result = self.group_store.get_by_name(self.test_group.name.upper())
        
        # Should find the group despite case difference
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)
        
        # Verify both queries were made
        self.assertEqual(self.mock_store.query.call_count, 2)
        
        # Verify the queries were made with correct filters
        calls = self.mock_store.query.call_args_list
        self.assertEqual(calls[0][1]['filters'], {'name': self.test_group.name.upper()})
        self.assertEqual(calls[1][1]['filters'], {'name__ilike': self.test_group.name.upper()})

    def test_get_by_name_not_found(self):
        """Test get_by_name() when group doesn't exist."""
        # Mock the query method to return empty for both calls
        self.mock_store.query.side_effect = [[], []]
        
        result = self.group_store.get_by_name("Non-existent Group")
        
        # Should return None
        self.assertIsNone(result)
        
        # Should have tried both exact and case-insensitive searches
        self.assertEqual(self.mock_store.query.call_count, 2)

    def test_get_by_name_conversion_error(self):
        """Test get_by_name() handles conversion errors gracefully."""
        # Mock the query method to return malformed data
        malformed_data = {"invalid": "data"}
        self.mock_store.query.side_effect = [
            [malformed_data],  # First call returns malformed data
            [self.test_group.model_dump()]  # Second call returns valid data
        ]
        
        result = self.group_store.get_by_name(self.test_group.name)
        
        # Should find the group on second attempt
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)

    def test_get_by_name_fallback_when_query_not_supported(self):
        """Test get_by_name() falls back to keys() when query() not supported."""
        # Remove query method to simulate non-SQL store
        del self.mock_store.query
        
        # Mock fallback keys/get approach
        self.mock_store.keys.return_value = [str(self.test_group.id)]
        self.mock_store.get.return_value = self.test_group.model_dump()
        
        result = self.group_store.get_by_name(self.test_group.name.lower())
        
        # Should still work with fallback (case-insensitive)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)

    def test_get_by_name_fallback_on_query_exception(self):
        """Test get_by_name() falls back when query() raises exception."""
        # Mock query to raise exception
        self.mock_store.query.side_effect = Exception("SQL error")
        
        # Mock fallback keys/get approach
        self.mock_store.keys.return_value = [str(self.test_group.id)]
        self.mock_store.get.return_value = self.test_group.model_dump()
        
        result = self.group_store.get_by_name(self.test_group.name)
        
        # Should still work with fallback
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_group.name)

    def test_get_by_name_fallback_empty_store(self):
        """Test _get_by_name_fallback() with empty store."""
        # Mock empty store
        self.mock_store.keys.return_value = []
        
        result = self.group_store._get_by_name_fallback("Non-existent")
        
        # Should return None
        self.assertIsNone(result)

    def test_list_fallback_with_filters_and_search(self):
        """Test _list_fallback() applies filters and search correctly."""
        # Create multiple test groups with different properties
        active_group = Group(
            id=str(uuid4()),
            name="Active Group",
            description="An active group",
            status="ACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            settings={}
        )
        
        inactive_group = Group(
            id=str(uuid4()),
            name="Inactive Group", 
            description="An inactive group",
            status="INACTIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            settings={}
        )
        
        # Mock keys and get to return both groups
        self.mock_store.keys.return_value = [str(active_group.id), str(inactive_group.id)]
        self.mock_store.get.side_effect = [
            active_group.model_dump(),
            inactive_group.model_dump()
        ]
        
        # Test status filter
        groups, total = self.group_store._list_fallback(
            status="ACTIVE",
            search="active",
            page=1,
            limit=10
        )
        
        # Should return only the active group matching search
        self.assertEqual(len(groups), 1)
        self.assertEqual(total, 1)
        self.assertEqual(groups[0].name, "Active Group")

    def test_list_fallback_pagination(self):
        """Test _list_fallback() pagination works correctly."""
        # Mock multiple groups
        group_ids = [str(uuid4()) for _ in range(5)]
        self.mock_store.keys.return_value = group_ids
        self.mock_store.get.return_value = self.test_group.model_dump()
        
        groups, total = self.group_store._list_fallback(page=2, limit=2)
        
        # Should return page 2 with 2 items (items 3-4 out of 5)
        self.assertEqual(len(groups), 2)
        self.assertEqual(total, 5)

    def test_list_fallback_empty_store(self):
        """Test _list_fallback() with empty store."""
        self.mock_store.keys.return_value = []
        
        groups, total = self.group_store._list_fallback()
        
        self.assertEqual(len(groups), 0)
        self.assertEqual(total, 0)


if __name__ == '__main__':
    unittest.main()