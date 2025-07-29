import unittest
from unittest.mock import MagicMock, Mock, patch, call
from datetime import datetime
import uuid
import json

from sqlalchemy import Table, MetaData, Column, String, Boolean, DateTime, Integer, Text, UUID
from sqlalchemy.orm import Session
from sqlalchemy.dialects import postgresql

from app.modules.sql_store import SQLStore
from app.modules.tlogger import TLogger


class TestSQLStore(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Mock logger
        self.logger = MagicMock(spec=TLogger)
        
        # Mock session
        self.session = MagicMock(spec=Session)
        
        # Create a mock table similar to users table
        self.metadata = MetaData()
        self.table = Table(
            'test_table',
            self.metadata,
            Column('id', UUID, primary_key=True),
            Column('email', String(255), unique=True, nullable=False),
            Column('full_name', String(255)),
            Column('password', String(255), nullable=False),
            Column('disabled', Boolean, default=False),
            Column('is_verified', Boolean, default=False),
            Column('role', String(50)),
            Column('group_id', UUID),
            Column('created_at', DateTime, nullable=False),
            Column('last_login', DateTime),
            Column('status', String(20))
        )
        
        # Create SQLStore instance
        self.store = SQLStore(self.session, self.table, self.logger)
        
        # Sample test data
        self.test_uuid = str(uuid.uuid4())
        self.test_data = {
            'id': self.test_uuid,
            'email': 'goricoaico+test@gmail.com',
            'full_name': 'Test User',
            'password': 'hashed_password',
            'disabled': False,
            'is_verified': True,
            'role': 'user',
            'group_id': str(uuid.uuid4()),
            'created_at': datetime.now(),
            'last_login': datetime.now(),
            'status': 'ACTIVE'
        }

    def test_query_keys_only_no_filters(self):
        """Test query() with keys_only=True and no filters"""
        # Mock data
        mock_results = [
            (self.test_uuid,),
            (str(uuid.uuid4()),),
            (str(uuid.uuid4()),)
        ]
        self.session.execute.return_value.fetchall.return_value = mock_results
        
        # Call method
        result = self.store.query(keys_only=True)
        
        # Assertions
        expected_keys = [self.test_uuid, mock_results[1][0], mock_results[2][0]]
        self.assertEqual(result, expected_keys)
        self.session.execute.assert_called_once()

    def test_query_full_records_no_filters(self):
        """Test query() with keys_only=False and no filters"""
        # Mock row objects
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(result[0]['id'], self.test_uuid)
        self.assertEqual(result[0]['email'], 'goricoaico+test@gmail.com')

    def test_query_with_basic_filters(self):
        """Test query() with basic equality filters"""
        filters = {
            'status': 'ACTIVE',
            'disabled': False
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_ilike_operator(self):
        """Test query() with __ilike operator for case-insensitive search"""
        filters = {
            'email__ilike': '%test%'
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_like_operator(self):
        """Test query() with __like operator for case-sensitive search"""
        filters = {
            'full_name__like': 'Test%'
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_in_operator(self):
        """Test query() with __in operator for IN clause"""
        filters = {
            'status__in': ['ACTIVE', 'PENDING', 'INACTIVE']
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_list_filter(self):
        """Test query() with list value for IN clause (automatic)"""
        filters = {
            'status': ['ACTIVE', 'PENDING']
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_or_conditions(self):
        """Test query() with _or conditions"""
        filters = {
            '_or': [
                {'email__ilike': '%test%'},
                {'full_name__ilike': '%user%'}
            ]
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_combined_filters(self):
        """Test query() with mixed AND and OR conditions"""
        filters = {
            'status': 'ACTIVE',
            '_or': [
                {'email__ilike': '%test%'},
                {'full_name__ilike': '%user%'}
            ]
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_pagination_keys_only(self):
        """Test query() with pagination returning keys and total count"""
        mock_results = [
            (self.test_uuid,),
            (str(uuid.uuid4()),)
        ]
        
        # Mock the main query
        self.session.execute.return_value.fetchall.return_value = mock_results
        # Mock the count query
        self.session.execute.return_value.scalar.return_value = 10
        
        # Call method
        result, total_count = self.store.query(
            keys_only=True,
            page=1,
            limit=2
        )
        
        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(total_count, 10)
        self.assertIsInstance(result, list)
        self.assertEqual(len(self.session.execute.call_args_list), 2)  # Count + main query

    def test_query_with_pagination_full_records(self):
        """Test query() with pagination returning full records and total count"""
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        mock_results = [mock_row]
        
        # Mock the main query
        self.session.execute.return_value.fetchall.return_value = mock_results
        # Mock the count query  
        self.session.execute.return_value.scalar.return_value = 5
        
        # Call method
        result, total_count = self.store.query(
            keys_only=False,
            page=2,
            limit=1
        )
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 5)
        self.assertIsInstance(result[0], dict)
        self.assertEqual(len(self.session.execute.call_args_list), 2)  # Count + main query

    def test_query_with_ordering_asc(self):
        """Test query() with ascending order"""
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(
            keys_only=False,
            order_by='created_at',
            order_direction='asc'
        )
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_ordering_desc(self):
        """Test query() with descending order"""
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method
        result = self.store.query(
            keys_only=False,
            order_by='created_at',
            order_direction='desc'
        )
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_invalid_column_filter(self):
        """Test query() ignores filters for non-existent columns"""
        filters = {
            'nonexistent_column': 'value',
            'status': 'ACTIVE'  # This should work
        }
        
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method - should not raise error
        result = self.store.query(filters=filters, keys_only=False)
        
        # Assertions - should only filter by valid column
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_with_invalid_order_by(self):
        """Test query() ignores invalid order_by column"""
        mock_row = Mock()
        for column_name, value in self.test_data.items():
            setattr(mock_row, column_name, value)
        
        self.session.execute.return_value.fetchall.return_value = [mock_row]
        
        # Call method - should not raise error
        result = self.store.query(
            keys_only=False,
            order_by='nonexistent_column'
        )
        
        # Assertions - should ignore invalid order_by
        self.assertEqual(len(result), 1)
        self.session.execute.assert_called_once()

    def test_query_error_handling(self):
        """Test query() error handling"""
        # Make session.execute raise an exception
        self.session.execute.side_effect = Exception("Database error")
        
        # Call method and expect exception
        with self.assertRaises(Exception):
            self.store.query()
        
        # Verify error was logged
        self.logger.error.assert_called_once()

    def test_query_empty_results(self):
        """Test query() with no matching records"""
        self.session.execute.return_value.fetchall.return_value = []
        
        # Call method
        result = self.store.query(keys_only=True)
        
        # Assertions
        self.assertEqual(result, [])
        self.session.execute.assert_called_once()

    def test_query_pagination_with_filters(self):
        """Test query() with both pagination and filters"""
        filters = {
            'status': 'ACTIVE',
            'disabled': False
        }
        
        mock_results = [(self.test_uuid,)]
        
        # Mock the main query
        self.session.execute.return_value.fetchall.return_value = mock_results
        # Mock the count query
        self.session.execute.return_value.scalar.return_value = 3
        
        # Call method
        result, total_count = self.store.query(
            filters=filters,
            keys_only=True,
            page=1,
            limit=1
        )
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 3)
        # Should have 2 calls: count query + main query
        self.assertEqual(len(self.session.execute.call_args_list), 2)

    def test_query_edge_case_zero_page(self):
        """Test query() with edge case of page=0 (should work as page=1)"""
        mock_results = [(self.test_uuid,)]
        
        self.session.execute.return_value.fetchall.return_value = mock_results
        self.session.execute.return_value.scalar.return_value = 1
        
        # Call method
        result, total_count = self.store.query(
            keys_only=True,
            page=0,  # Edge case
            limit=1
        )
        
        # Assertions - should handle gracefully
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 1)

    def test_query_edge_case_negative_limit(self):
        """Test query() with edge case of negative limit"""
        mock_results = []
        
        self.session.execute.return_value.fetchall.return_value = mock_results
        self.session.execute.return_value.scalar.return_value = 0
        
        # Call method
        result, total_count = self.store.query(
            keys_only=True,
            page=1,
            limit=-1  # Edge case
        )
        
        # Assertions - should handle gracefully
        self.assertEqual(len(result), 0)
        self.assertEqual(total_count, 0)


if __name__ == '__main__':
    unittest.main()