import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from app.modules.configurations_store import AIConfigurationStore
from app.modules.store_interface import LocalStore
from app.schemas import AIEndpointConfig


class TestAIConfigurationStoreQuery(unittest.TestCase):
    """Test the query() method migration for AIConfigurationStore."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        self.config_store = AIConfigurationStore(self.mock_store)
        
        # Configure mock query method to return expected format by default
        self.mock_store.query.return_value = ([], 0)
        
        # Create test configuration data
        test_timestamp = datetime.now(timezone.utc)
        
        self.test_config = AIEndpointConfig(
            id=str(uuid4()),
            name="Test Config",
            description="A test configuration",
            provider="openai",
            endpoint_url="https://api.openai.com/v1/chat/completions",
            auth_type="api_key",
            model_name="gpt-4",
            tags=["test", "gpt-4"],
            status="active",
            created_by=str(uuid4()),
            group_id=str(uuid4()),
            created_at=test_timestamp,
            updated_at=test_timestamp,
            last_tested_at=None,
            last_test_status=None,
            last_test_error=None,
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time_ms=None,
            connection_config={}
        )

    def test_list_basic_filtering(self):
        """Test list() method with basic filters using query()."""
        # Mock the query method to return config data
        self.mock_store.query.return_value = ([self.test_config.model_dump()], 1)
        
        configs, total = self.config_store.list(
            status="active",
            provider="openai",
            page=1,
            limit=10
        )
        
        # Verify the result
        self.assertEqual(len(configs), 1)
        self.assertEqual(total, 1)
        self.assertEqual(configs[0].name, self.test_config.name)
        
        # Verify query was called with correct filters
        self.mock_store.query.assert_called_once_with(
            filters={'status': 'active', 'provider': 'openai'},
            keys_only=False,
            page=1,
            limit=10,
            order_by="created_at",
            order_direction="desc"
        )

    def test_list_with_search(self):
        """Test list() method with search using OR conditions."""
        # Mock the query method to return config data
        self.mock_store.query.return_value = ([self.test_config.model_dump()], 1)
        
        configs, total = self.config_store.list(
            search="test",
            page=1,
            limit=10
        )
        
        # Verify the result
        self.assertEqual(len(configs), 1)
        self.assertEqual(total, 1)
        
        # Verify query was called with OR search conditions
        self.mock_store.query.assert_called_once_with(
            filters={
                '_or': [
                    {'name__ilike': '%test%'},
                    {'description__ilike': '%test%'},
                    {'model_name__ilike': '%test%'}
                ]
            },
            keys_only=False,
            page=1,
            limit=10,
            order_by="created_at",
            order_direction="desc"
        )

    def test_list_combined_filters_and_search(self):
        """Test list() method with both filters and search."""
        # Mock the query method to return config data
        self.mock_store.query.return_value = ([self.test_config.model_dump()], 1)
        
        configs, total = self.config_store.list(
            status="active",
            provider="openai",
            search="gpt",
            group_id="test-group",
            created_by="test-user",
            page=2,
            limit=5,
            sort_by="name",
            sort_order="asc"
        )
        
        # Verify the result
        self.assertEqual(len(configs), 1)
        self.assertEqual(total, 1)
        
        # Verify query was called with combined filters
        self.mock_store.query.assert_called_once_with(
            filters={
                'status': 'active',
                'provider': 'openai',
                'group_id': 'test-group',
                'created_by': 'test-user',
                '_or': [
                    {'name__ilike': '%gpt%'},
                    {'description__ilike': '%gpt%'},
                    {'model_name__ilike': '%gpt%'}
                ]
            },
            keys_only=False,
            page=2,
            limit=5,
            order_by="name",
            order_direction="asc"
        )

    def test_list_with_tags_search(self):
        """Test list() method with tags search (post-processing)."""
        # Create config data with tags matching search
        config_data = self.test_config.model_dump()
        config_data['tags'] = ['test', 'production']
        
        # Mock the query method to return config data
        self.mock_store.query.return_value = ([config_data], 1)
        
        configs, total = self.config_store.list(
            search="production",  # This should match tags
            page=1,
            limit=10
        )
        
        # Verify the result - should include config because of tags match
        self.assertEqual(len(configs), 1)
        self.assertEqual(total, 1)

    def test_list_conversion_error_handling(self):
        """Test list() method handles conversion errors gracefully."""
        # Mock the query method to return malformed data
        malformed_data = {"invalid": "data", "missing_required_fields": True}
        self.mock_store.query.return_value = ([malformed_data], 1)
        
        configs, total = self.config_store.list(page=1, limit=10)
        
        # Should return empty list when conversion fails
        self.assertEqual(len(configs), 0)
        self.assertEqual(total, 1)  # Total count from query still returned

    def test_list_fallback_when_query_not_supported(self):
        """Test list() method falls back to keys() when query() not supported."""
        # Remove query method to simulate non-SQL store
        del self.mock_store.query
        
        # Mock fallback keys/get approach
        self.mock_store.keys.return_value = [str(self.test_config.id)]
        self.mock_store.get.return_value = self.test_config.model_dump()
        
        configs, total = self.config_store.list(
            status="active",
            page=1,
            limit=10
        )
        
        # Should still work with fallback
        self.assertEqual(len(configs), 1)
        self.assertEqual(total, 1)
        
        # Verify fallback methods were called
        self.mock_store.keys.assert_called_once()

    def test_list_fallback_on_query_exception(self):
        """Test list() method falls back when query() raises exception."""
        # Mock query to raise exception
        self.mock_store.query.side_effect = Exception("SQL error")
        
        # Mock fallback keys/get approach
        self.mock_store.keys.return_value = [str(self.test_config.id)]
        self.mock_store.get.return_value = self.test_config.model_dump()
        
        configs, total = self.config_store.list(page=1, limit=10)
        
        # Should still work with fallback
        self.assertEqual(len(configs), 1)
        self.assertEqual(total, 1)

    def test_convert_to_schema_success(self):
        """Test _convert_to_schema() helper method."""
        # Test data with encrypted fields that should be removed
        data = self.test_config.model_dump()
        data.update({
            'api_key_encrypted': 'encrypted_key',
            'bearer_token_encrypted': 'encrypted_token',
            'azure_client_secret_encrypted': 'encrypted_secret'
        })
        
        result = self.config_store._convert_to_schema(data)
        
        # Should return valid config without encrypted fields
        self.assertIsNotNone(result)
        self.assertEqual(result.name, self.test_config.name)
        self.assertFalse(hasattr(result, 'api_key_encrypted'))

    def test_convert_to_schema_nullable_fields(self):
        """Test _convert_to_schema() handles nullable fields correctly."""
        data = self.test_config.model_dump()
        data.update({
            'last_test_status': '',  # Empty string should become None
            'last_test_error': '',   # Empty string should become None
            'avg_response_time_ms': '100.5'  # String should become float
        })
        
        result = self.config_store._convert_to_schema(data)
        
        # Should handle nullable fields correctly
        self.assertIsNotNone(result)
        self.assertIsNone(result.last_test_status)
        self.assertIsNone(result.last_test_error)
        self.assertEqual(result.avg_response_time_ms, 100.5)

    def test_convert_to_schema_invalid_data(self):
        """Test _convert_to_schema() returns None for invalid data."""
        invalid_data = {"invalid": "data"}
        
        result = self.config_store._convert_to_schema(invalid_data)
        
        # Should return None for invalid data
        self.assertIsNone(result)

    def test_passes_search_filter_tags_match(self):
        """Test _passes_search_filter() for tags matching."""
        config = self.test_config
        config.tags = ['production', 'gpt-4', 'openai']
        
        # Should match tag
        result = self.config_store._passes_search_filter(config, "production")
        self.assertTrue(result)
        
        # Should match partial tag
        result = self.config_store._passes_search_filter(config, "prod")
        self.assertTrue(result)

    def test_passes_search_filter_no_tags_match(self):
        """Test _passes_search_filter() when no tags match."""
        config = self.test_config
        config.tags = ['production', 'gpt-4']
        
        # Should not match when no tags match
        result = self.config_store._passes_search_filter(config, "development")
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()