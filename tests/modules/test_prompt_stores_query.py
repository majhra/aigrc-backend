import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.modules.prompts_store import PromptCategoryStore, PromptStore, PromptSetStore
from app.modules.store_interface import LocalStore
from app.schemas import (
    PromptCategory, PromptCategoryCreate, 
    Prompt, PromptCreate, PromptVariable,
    PromptSet, PromptSetCreate,
    User
)


class TestPromptStoresQueryMethods(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        
        # Create test user
        self.test_user = User(
            id=str(uuid4()),
            email="goricoaico+prompt_query@gmail.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        self.test_timestamp = datetime.now(timezone.utc)
        
        # Create test data for PromptCategory
        self.category_data_dict = {
            "name": "Test Category",
            "description": "A test category for query functionality", 
            "category_type": "COMPLIANCE",
            "priority": "HIGH",
            "tags": ["test", "query"],
            "status": "ACTIVE",
            "prompt_count": 0
        }
        
        # Create test data for Prompt
        self.prompt_data_dict = {
            "name": "Test Prompt",
            "description": "A test prompt for query functionality",
            "content": "Hello {name}, how are you?",
            "category_id": str(uuid4()),
            "variables": [],  # Keep it simple for tests
            "tags": ["test", "query"],
            "risk_level": "LOW",
            "compliance_frameworks": ["SOX", "GDPR"],
            "version": 1,
            "status": "ACTIVE",
            "last_used_at": None,  # Allow None for simpler testing
            "usage_count": 0
        }
        
        # Create test data for PromptSet
        self.prompt_set_data_dict = {
            "name": "Test Prompt Set",
            "description": "A test prompt set for query functionality",
            "category_id": str(uuid4()),
            "prompt_ids": [str(uuid4()), str(uuid4())],
            "tags": ["test", "query"],
            "status": "ACTIVE"
        }

    def test_prompt_category_store_list_with_query_basic_filters(self):
        """Test PromptCategoryStore.list() uses query() for basic filters."""
        category_store = PromptCategoryStore(self.mock_store)
        
        test_data = {
            **self.category_data_dict,
            "id": str(uuid4()),
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with filters
        categories, total = category_store.list(
            page=1,
            limit=10,
            status="ACTIVE",
            category_type="COMPLIANCE",
            group_id=self.test_user.group
        )
        
        # Verify query was called with correct filters
        self.mock_store.query.assert_called_once_with(
            filters={
                'status': 'ACTIVE',
                'category_type': 'COMPLIANCE',
                'group_id': self.test_user.group
            },
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )
        
        # Verify results
        self.assertEqual(len(categories), 1)
        self.assertEqual(total, 1)
        self.assertEqual(categories[0].status, "ACTIVE")
        self.assertEqual(categories[0].category_type, "COMPLIANCE")

    def test_prompt_category_store_list_with_search(self):
        """Test PromptCategoryStore.list() uses query() for search with OR conditions."""
        category_store = PromptCategoryStore(self.mock_store)
        
        test_data = {
            **self.category_data_dict,
            "id": str(uuid4()),
            "name": "Searchable Category Name",
            "description": "A searchable description",
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with search
        categories, total = category_store.list(search="searchable")
        
        # Verify query was called with OR search conditions
        expected_filters = {
            '_or': [
                {'name__ilike': '%searchable%'},
                {'description__ilike': '%searchable%'}
                # Note: tags search handled in post-processing since it's JSONB
            ]
        }
        
        self.mock_store.query.assert_called_once_with(
            filters=expected_filters,
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )
        
        # Verify results
        self.assertEqual(len(categories), 1)
        self.assertEqual(total, 1)

    def test_prompt_store_list_with_query_basic_filters(self):
        """Test PromptStore.list() uses query() for basic filters."""
        prompt_store = PromptStore(self.mock_store)
        
        test_data = {
            **self.prompt_data_dict,
            "id": str(uuid4()),
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with filters
        prompts, total = prompt_store.list(
            page=1,
            limit=10,
            status="ACTIVE",
            category_id=self.prompt_data_dict["category_id"],
            risk_level="LOW",
            group_id=self.test_user.group
        )
        
        # Verify query was called with correct filters
        self.mock_store.query.assert_called_once_with(
            filters={
                'status': 'ACTIVE',
                'category_id': self.prompt_data_dict["category_id"],
                'risk_level': 'LOW',
                'group_id': self.test_user.group
            },
            keys_only=False,
            page=1,
            limit=10,
            order_by="updated_at",
            order_direction="desc"
        )
        
        # Verify results
        self.assertEqual(len(prompts), 1)
        self.assertEqual(total, 1)
        self.assertEqual(prompts[0].status, "ACTIVE")
        self.assertEqual(prompts[0].risk_level, "LOW")

    def test_prompt_store_list_with_search(self):
        """Test PromptStore.list() uses query() for search with OR conditions."""
        prompt_store = PromptStore(self.mock_store)
        
        test_data = {
            **self.prompt_data_dict,
            "id": str(uuid4()),
            "name": "Searchable Prompt Name",
            "description": "A searchable description",
            "content": "Searchable content here",
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with search
        prompts, total = prompt_store.list(search="searchable")
        
        # Verify query was called with OR search conditions (tags handled in post-processing)
        expected_filters = {
            '_or': [
                {'name__ilike': '%searchable%'},
                {'description__ilike': '%searchable%'},
                {'content__ilike': '%searchable%'}
                # Note: tags search handled in post-processing since it's JSONB
            ]
        }
        
        self.mock_store.query.assert_called_once_with(
            filters=expected_filters,
            keys_only=False,
            page=1,
            limit=10,
            order_by="updated_at",
            order_direction="desc"
        )
        
        # Verify results
        self.assertEqual(len(prompts), 1)
        self.assertEqual(total, 1)

    def test_prompt_store_list_with_category_type_filter(self):
        """Test PromptStore.list() handles category_type by querying category store."""
        prompt_store = PromptStore(self.mock_store)
        
        # Mock category store
        mock_category_store = MagicMock()
        matching_category = PromptCategory(
            id=str(uuid4()),
            name="Test Category",
            description="Test",
            category_type="COMPLIANCE",
            priority="HIGH",
            tags=[],
            status="ACTIVE",
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            prompt_count=0
        )
        mock_category_store.list.return_value = ([matching_category], 1)
        
        test_data = {
            **self.prompt_data_dict,
            "id": str(uuid4()),
            "category_id": str(matching_category.id),
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with category_type
        prompts, total = prompt_store.list(
            category_type="COMPLIANCE",
            category_store=mock_category_store
        )
        
        # Verify category store was queried
        mock_category_store.list.assert_called_once_with(category_type="COMPLIANCE")
        
        # Verify query was called with category_id__in filter
        expected_filters = {
            'category_id__in': [str(matching_category.id)]
        }
        
        self.mock_store.query.assert_called_once_with(
            filters=expected_filters,
            keys_only=False,
            page=1,
            limit=10,
            order_by="updated_at",
            order_direction="desc"
        )
        
        # Verify results
        self.assertEqual(len(prompts), 1)
        self.assertEqual(total, 1)

    def test_prompt_store_list_with_tags_filter(self):
        """Test PromptStore.list() handles tags filter with post-processing."""
        prompt_store = PromptStore(self.mock_store)
        
        test_data_with_matching_tag = {
            **self.prompt_data_dict,
            "id": str(uuid4()),
            "tags": ["compliance", "security"],
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        test_data_without_matching_tag = {
            **self.prompt_data_dict, 
            "id": str(uuid4()),
            "tags": ["other", "random"],
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response (both items returned from SQL)
        self.mock_store.query.return_value = ([test_data_with_matching_tag, test_data_without_matching_tag], 2)
        
        # Call list with tags filter
        prompts, total = prompt_store.list(tags=["compliance"])
        
        # Verify query was called without tags filter (since it's post-processed)
        self.mock_store.query.assert_called_once_with(
            filters={},
            keys_only=False,
            page=1,
            limit=10,
            order_by="updated_at",
            order_direction="desc"
        )
        
        # Verify post-processing filtered correctly (only one item with matching tag)
        self.assertEqual(len(prompts), 1)
        self.assertEqual(total, 1)
        self.assertIn("compliance", prompts[0].tags)

    def test_prompt_set_store_list_with_query_basic_filters(self):
        """Test PromptSetStore.list() uses query() for basic filters."""
        prompt_set_store = PromptSetStore(self.mock_store)
        
        test_data = {
            **self.prompt_set_data_dict,
            "id": str(uuid4()),
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with filters
        prompt_sets, total = prompt_set_store.list(
            page=1,
            limit=10,
            status="ACTIVE",
            category_id=self.prompt_set_data_dict["category_id"],
            group_id=self.test_user.group
        )
        
        # Verify query was called with correct filters
        self.mock_store.query.assert_called_once_with(
            filters={
                'status': 'ACTIVE',
                'category_id': self.prompt_set_data_dict["category_id"],
                'group_id': self.test_user.group
            },
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )
        
        # Verify results
        self.assertEqual(len(prompt_sets), 1)
        self.assertEqual(total, 1)
        self.assertEqual(prompt_sets[0].status, "ACTIVE")

    def test_prompt_set_store_list_with_search(self):
        """Test PromptSetStore.list() uses query() for search with OR conditions."""
        prompt_set_store = PromptSetStore(self.mock_store)
        
        test_data = {
            **self.prompt_set_data_dict,
            "id": str(uuid4()),
            "name": "Searchable Set Name",
            "description": "A searchable description",
            "created_by": self.test_user.id,
            "group_id": self.test_user.group,
            "created_at": self.test_timestamp.isoformat(),
            "updated_at": self.test_timestamp.isoformat()
        }
        
        # Mock query method response
        self.mock_store.query.return_value = ([test_data], 1)
        
        # Call list with search
        prompt_sets, total = prompt_set_store.list(search="searchable")
        
        # Verify query was called with OR search conditions
        expected_filters = {
            '_or': [
                {'name__ilike': '%searchable%'},
                {'description__ilike': '%searchable%'}
                # Note: tags search handled in post-processing since it's JSONB
            ]
        }
        
        self.mock_store.query.assert_called_once_with(
            filters=expected_filters,
            keys_only=False,
            page=1,
            limit=10,
            order_by="name",
            order_direction="asc"
        )
        
        # Verify results
        self.assertEqual(len(prompt_sets), 1)
        self.assertEqual(total, 1)

    def test_fallback_to_old_method_when_no_query(self):
        """Test all stores fall back to old method when store doesn't have query()."""
        # Remove query method from mock
        del self.mock_store.query
        
        # Test PromptCategoryStore fallback
        category_store = PromptCategoryStore(self.mock_store)
        self.mock_store.keys.return_value = []
        
        categories, total = category_store.list()
        
        # Verify fallback methods were called
        self.mock_store.keys.assert_called()
        
        # Test PromptStore fallback
        prompt_store = PromptStore(self.mock_store)
        self.mock_store.keys.reset_mock()
        
        prompts, total = prompt_store.list()
        
        # Verify fallback methods were called
        self.mock_store.keys.assert_called()
        
        # Test PromptSetStore fallback
        prompt_set_store = PromptSetStore(self.mock_store)
        self.mock_store.keys.reset_mock()
        
        prompt_sets, total = prompt_set_store.list()
        
        # Verify fallback methods were called
        self.mock_store.keys.assert_called()

    def test_combined_filters_and_search(self):
        """Test that all stores correctly combine filters and search."""
        test_cases = [
            {
                "store": PromptCategoryStore(self.mock_store),
                "test_data": self.category_data_dict,
                "filters": {"status": "ACTIVE", "category_type": "COMPLIANCE"},
                "order_by": "name"
            },
            {
                "store": PromptStore(self.mock_store),
                "test_data": self.prompt_data_dict,
                "filters": {"status": "ACTIVE", "risk_level": "LOW"},
                "order_by": "updated_at"
            },
            {
                "store": PromptSetStore(self.mock_store),
                "test_data": self.prompt_set_data_dict,
                "filters": {"status": "ACTIVE"},
                "order_by": "name"
            }
        ]
        
        for case in test_cases:
            with self.subTest(store=case["store"].__class__.__name__):
                self.mock_store.reset_mock()
                
                test_data = {
                    **case["test_data"],
                    "id": str(uuid4()),
                    "name": "Searchable Test Name",
                    "description": "Searchable description",
                    "created_by": self.test_user.id,
                    "group_id": self.test_user.group,
                    "created_at": self.test_timestamp.isoformat(),
                    "updated_at": self.test_timestamp.isoformat()
                }
                
                # Mock query method response
                self.mock_store.query.return_value = ([test_data], 1)
                
                # Call list with both filters and search
                results, total = case["store"].list(
                    search="searchable",
                    **case["filters"]
                )
                
                # Verify query was called with combined filters
                expected_filters = case["filters"].copy()
                expected_filters['_or'] = [
                    {'name__ilike': '%searchable%'},
                    {'description__ilike': '%searchable%'}
                    # Note: tags search now handled in post-processing for all stores
                ]
                if hasattr(case["store"], '__class__') and case["store"].__class__.__name__ == 'PromptStore':
                    # PromptStore has additional content search
                    expected_filters['_or'].append({'content__ilike': '%searchable%'})
                
                self.mock_store.query.assert_called_once()
                call_args = self.mock_store.query.call_args
                self.assertEqual(call_args[1]['filters'], expected_filters)
                self.assertEqual(call_args[1]['order_by'], case["order_by"])

    def test_empty_store_handling(self):
        """Test handling of empty store responses for all stores."""
        stores = [
            PromptCategoryStore(self.mock_store),
            PromptStore(self.mock_store),
            PromptSetStore(self.mock_store)
        ]
        
        for store in stores:
            with self.subTest(store=store.__class__.__name__):
                self.mock_store.reset_mock()
                # Mock empty query response
                self.mock_store.query.return_value = ([], 0)
                
                results, total = store.list()
                
                self.assertEqual(len(results), 0)
                self.assertEqual(total, 0)

    def test_malformed_data_handling(self):
        """Test handling of malformed data from store for all stores."""
        stores = [
            PromptCategoryStore(self.mock_store),
            PromptStore(self.mock_store),
            PromptSetStore(self.mock_store)
        ]
        
        for store in stores:
            with self.subTest(store=store.__class__.__name__):
                self.mock_store.reset_mock()
                # Mock query with malformed data
                malformed_data = {
                    "id": "invalid-data",
                    "name": None,  # This will cause schema validation to fail
                }
                
                self.mock_store.query.return_value = ([malformed_data], 1)
                
                results, total = store.list()
                
                # Should filter out malformed data
                self.assertEqual(len(results), 0)
                self.assertEqual(total, 1)  # Total count reflects raw query result


if __name__ == '__main__':
    unittest.main()