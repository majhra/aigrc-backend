import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.modules.tests_store import AITestStore
from app.modules.store_interface import LocalStore
from app.schemas import AITestSchema, AITestCreate, User, ConnectionConfig, ValidationConfig, ValidationCriterion


class TestAITestStoreQueryMethods(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        self.test_store = AITestStore(self.mock_store)
        
        # Create test user
        self.test_user = User(
            id=str(uuid4()),
            email="goricoaico+aitest_query@gmail.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        # Create test data with all required fields
        self.test_data_dict = {
            "name": "Test Query Test",
            "description": "A test for query functionality",
            "prompt_template": "Hello {name}",
            "interface_type": "DIRECT_LLM",
            "connection_config": {
                "endpoint": "https://api.example.com/v1/chat/completions",
                "auth_type": "API_KEY",
                "auth_string": "dummy-api-key"
            },
            "validation_config": {
                "validator_type": "HUMAN",
                "validation_criteria": [
                    {
                        "id": "criterion1",
                        "name": "Test Criterion",
                        "description": "A test criterion",
                        "type": "exact_match"
                    }
                ]
            },
            "tags": ["test", "query"],
            "risk_level": "LOW",
            "status": "ACTIVE"
        }
        
        self.test_data = AITestCreate(**self.test_data_dict)
        
        self.test_timestamp = datetime.now(timezone.utc)

    def test_list_with_query_method_basic_filters(self):
        """Test list() method uses query() for basic filters."""
        # Setup mock to have query method
        test_data = {
            "id": str(uuid4()),
            "name": "Test Query Test",
            "description": "A test for query functionality",
            "status": "ACTIVE",
            "risk_level": "LOW",
            "group_id": self.test_user.group,
            "created_by": self.test_user.id,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat(),
            **self.test_data_dict
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with filters
        tests, total = self.test_store.list(
            page=1,
            limit=10,
            status="ACTIVE",
            risk_level="LOW",
            group_id=self.test_user.group
        )
        
        # Verify query was called with correct filters
        self.mock_store.query.assert_called_once_with(
            filters={
                'status': 'ACTIVE',
                'risk_level': 'LOW',
                'group_id': self.test_user.group
            },
            keys_only=False,
            page=1,
            limit=10,
            order_by="created_at",
            order_direction="desc"
        )
        
        # Verify results
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)
        self.assertEqual(tests[0].status, "ACTIVE")
        self.assertEqual(tests[0].risk_level, "LOW")

    def test_list_with_query_method_search_filter(self):
        """Test list() method uses query() for search with OR conditions."""
        test_data = {
            **self.test_data_dict,
            "id": str(uuid4()),
            "name": "Searchable Test Name",
            "description": "A searchable description",
            "status": "ACTIVE",
            "risk_level": "LOW",
            "group_id": self.test_user.group,
            "created_by": self.test_user.id,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with search
        tests, total = self.test_store.list(
            page=1,
            limit=10,
            search="searchable"
        )
        
        # Verify query was called with OR search conditions
        expected_filters = {
            '_or': [
                {'name__ilike': '%searchable%'},
                {'description__ilike': '%searchable%'}
            ]
        }
        
        self.mock_store.query.assert_called_once_with(
            filters=expected_filters,
            keys_only=False,
            page=1,
            limit=10,
            order_by="created_at",
            order_direction="desc"
        )
        
        # Verify results
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)

    def test_list_with_query_method_combined_filters_and_search(self):
        """Test list() method combines filters and search correctly."""
        test_data = {
            **self.test_data_dict,
            "id": str(uuid4()),
            "name": "Active Searchable Test",
            "description": "Active searchable description",
            "status": "ACTIVE",
            "risk_level": "HIGH",
            "group_id": self.test_user.group,
            "created_by": self.test_user.id,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with both filters and search
        tests, total = self.test_store.list(
            page=2,
            limit=5,
            status="ACTIVE",
            risk_level="HIGH",
            search="searchable",
            group_id=self.test_user.group
        )
        
        # Verify query was called with combined filters
        expected_filters = {
            'status': 'ACTIVE',
            'risk_level': 'HIGH',
            'group_id': self.test_user.group,
            '_or': [
                {'name__ilike': '%searchable%'},
                {'description__ilike': '%searchable%'}
            ]
        }
        
        self.mock_store.query.assert_called_once_with(
            filters=expected_filters,
            keys_only=False,
            page=2,
            limit=5,
            order_by="created_at",
            order_direction="desc"
        )
        
        # Verify results
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)

    def test_list_with_search_includes_tag_filtering(self):
        """Test list() method includes tag post-processing for search."""
        test_data_with_tag_match = {
            "id": str(uuid4()),
            "name": "Regular Name",
            "description": "Regular description",
            "status": "ACTIVE",
            "risk_level": "LOW",
            "group_id": self.test_user.group,
            "created_by": self.test_user.id,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat(),
            "tags": ["searchable", "test"],
            **{k: v for k, v in self.test_data.model_dump().items() if k != 'tags'}
        }
        
        # Mock query method response (simulating SQL didn't catch tag match)
        self.mock_store.query.return_value = ([test_data_with_tag_match], 1)
        
        # Call list with search that should match tags
        tests, total = self.test_store.list(search="searchable")
        
        # Verify tag post-processing worked
        self.assertEqual(len(tests), 1)
        self.assertIn("searchable", tests[0].tags)

    def test_get_tests_by_group_uses_query(self):
        """Test get_tests_by_group() method uses query() for efficiency."""
        test_data = {
            "id": str(uuid4()),
            "name": "Group Test",
            "description": "A test for group filtering",
            "status": "ACTIVE",
            "risk_level": "LOW",
            "group_id": self.test_user.group,
            "created_by": self.test_user.id,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat(),
            **self.test_data_dict
        }
        
        # Mock query method response (no pagination)
        self.mock_store.query.return_value = [test_data]
        
        # Call get_tests_by_group
        tests = self.test_store.get_tests_by_group(self.test_user.group)
        
        # Verify query was called correctly
        self.mock_store.query.assert_called_once_with(
            filters={'group_id': self.test_user.group},
            keys_only=False,
            order_by="created_at",
            order_direction="desc"
        )
        
        # Verify results
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].group_id, self.test_user.group)

    def test_fallback_to_old_method_when_no_query(self):
        """Test list() falls back to old method when store doesn't have query()."""
        # Remove query method from mock
        del self.mock_store.query
        
        # Setup old-style mocks
        test_id = str(uuid4())
        self.mock_store.keys.return_value = [test_id]
        
        test_schema = AITestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data_dict
        )
        self.mock_store.get.return_value = test_schema.model_dump()
        
        # Call list
        tests, total = self.test_store.list(page=1, limit=10)
        
        # Verify fallback methods were called
        self.mock_store.keys.assert_called_once()
        self.mock_store.get.assert_called_once_with(test_id)
        
        # Verify results
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)

    def test_fallback_on_query_exception(self):
        """Test list() falls back to old method when query() raises exception."""
        # Setup query to raise exception
        self.mock_store.query.side_effect = Exception("Database error")
        
        # Setup fallback mocks
        test_id = str(uuid4())
        self.mock_store.keys.return_value = [test_id]
        
        test_schema = AITestSchema(
            id=test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data_dict
        )
        self.mock_store.get.return_value = test_schema.model_dump()
        
        # Call list
        tests, total = self.test_store.list(page=1, limit=10)
        
        # Verify query was attempted and fallback was used
        self.mock_store.query.assert_called_once()
        self.mock_store.keys.assert_called_once()
        self.mock_store.get.assert_called_once_with(test_id)
        
        # Verify results
        self.assertEqual(len(tests), 1)
        self.assertEqual(total, 1)

    def test_list_fallback_method_filtering(self):
        """Test _list_fallback() method applies filters correctly."""
        # Create multiple test items with different attributes
        test_items = [
            {
                **self.test_data_dict,
                "id": str(uuid4()),
                "name": "Active Test 1",
                "status": "ACTIVE",
                "risk_level": "LOW",
                "group_id": "group1",
                "created_by": self.test_user.id,
                "created_at": self.test_timestamp.isoformat(),
                "updated_at": self.test_timestamp.isoformat()
            },
            {
                **self.test_data_dict,
                "id": str(uuid4()),
                "name": "Draft Test 2",
                "status": "DRAFT",
                "risk_level": "HIGH",
                "group_id": "group2",
                "created_by": self.test_user.id,
                "created_at": self.test_timestamp.isoformat(),
                "updated_at": self.test_timestamp.isoformat()
            }
        ]
        
        # Mock keys and get methods
        self.mock_store.keys.return_value = [item["id"] for item in test_items]
        self.mock_store.get.side_effect = lambda key: next(
            (item for item in test_items if item["id"] == key), None
        )
        
        # Test status filtering
        tests, total = self.test_store._list_fallback(
            page=1, limit=10, status="ACTIVE"
        )
        
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].status, "ACTIVE")
        
        # Test risk level filtering
        tests, total = self.test_store._list_fallback(
            page=1, limit=10, risk_level="HIGH"
        )
        
        self.assertEqual(len(tests), 1)
        self.assertEqual(tests[0].risk_level, "HIGH")
        
        # Test group filtering
        tests, total = self.test_store._list_fallback(
            page=1, limit=10, group_id="group1"
        )
        
        self.assertEqual(len(tests), 1)
        self.assertEqual(str(tests[0].group_id), "group1")

    def test_empty_store_handling(self):
        """Test handling of empty store responses."""
        # Mock empty query response
        self.mock_store.query.return_value = ([], 0)
        
        tests, total = self.test_store.list()
        
        self.assertEqual(len(tests), 0)
        self.assertEqual(total, 0)

    def test_malformed_data_handling(self):
        """Test handling of malformed data from store."""
        # Mock query with malformed data
        malformed_data = {
            "id": "invalid-data",
            "name": None,  # This will cause schema validation to fail
        }
        
        self.mock_store.query.return_value = ([malformed_data], 1)
        
        tests, total = self.test_store.list()
        
        # Should filter out malformed data
        self.assertEqual(len(tests), 0)
        self.assertEqual(total, 1)  # Total count reflects raw query result


if __name__ == '__main__':
    unittest.main()