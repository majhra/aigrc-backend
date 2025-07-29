import unittest
from datetime import datetime
import uuid

from app.modules.store_interface import LocalStore


class TestLocalStoreQuery(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.store = LocalStore()
        
        # Sample test data
        self.test_uuid1 = str(uuid.uuid4())
        self.test_uuid2 = str(uuid.uuid4())
        self.test_uuid3 = str(uuid.uuid4())
        self.group_uuid = str(uuid.uuid4())
        
        # Create test records with different data types
        self.test_data = {
            self.test_uuid1: {
                'id': self.test_uuid1,
                'email': 'goricoaico+test1@gmail.com',
                'full_name': 'Test User One',
                'status': 'ACTIVE',
                'disabled': False,
                'role': 'user',
                'group_id': self.group_uuid,
                'created_at': datetime(2023, 1, 1, 10, 0, 0),
                'tags': ['tag1', 'tag2']
            },
            self.test_uuid2: {
                'id': self.test_uuid2,
                'email': 'goricoaico+test2@gmail.com',
                'full_name': 'Test User Two',
                'status': 'INACTIVE',
                'disabled': True,
                'role': 'admin',
                'group_id': self.group_uuid,
                'created_at': datetime(2023, 1, 2, 10, 0, 0),
                'tags': ['tag2', 'tag3']
            },
            self.test_uuid3: {
                'id': self.test_uuid3,
                'email': 'goricoaico+another@gmail.com',
                'full_name': 'Another User',
                'status': 'PENDING',
                'disabled': False,
                'role': 'user',
                'group_id': str(uuid.uuid4()),  # Different group
                'created_at': datetime(2023, 1, 3, 10, 0, 0),
                'tags': ['tag3', 'tag4']
            }
        }
        
        # Populate store with test data
        for key, value in self.test_data.items():
            self.store.put(key, value)

    def test_query_keys_only_no_filters(self):
        """Test query() with keys_only=True and no filters"""
        result = self.store.query(keys_only=True)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertIn(self.test_uuid1, result)
        self.assertIn(self.test_uuid2, result)
        self.assertIn(self.test_uuid3, result)

    def test_query_full_records_no_filters(self):
        """Test query() with keys_only=False and no filters"""
        result = self.store.query(keys_only=False)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        # Check that we get full records
        for record in result:
            self.assertIsInstance(record, dict)
            self.assertIn('id', record)
            self.assertIn('email', record)

    def test_query_with_basic_filter(self):
        """Test query() with basic equality filter"""
        result = self.store.query(
            filters={'status': 'ACTIVE'},
            keys_only=False
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.test_uuid1)
        self.assertEqual(result[0]['status'], 'ACTIVE')

    def test_query_with_multiple_filters(self):
        """Test query() with multiple AND filters"""
        result = self.store.query(
            filters={
                'status': 'ACTIVE',
                'disabled': False,
                'role': 'user'
            },
            keys_only=False
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], self.test_uuid1)

    def test_query_with_list_filter_in_clause(self):
        """Test query() with list value for IN clause"""
        result = self.store.query(
            filters={'status': ['ACTIVE', 'PENDING']},
            keys_only=False
        )
        
        self.assertEqual(len(result), 2)
        statuses = {r['status'] for r in result}
        self.assertEqual(statuses, {'ACTIVE', 'PENDING'})

    def test_query_with_ilike_operator(self):
        """Test query() with __ilike operator for case-insensitive search"""
        result = self.store.query(
            filters={'email__ilike': '%TEST%'},
            keys_only=False
        )
        
        # Should match test1 and test2 emails (case-insensitive)
        self.assertEqual(len(result), 2)
        emails = {r['email'] for r in result}
        self.assertIn('goricoaico+test1@gmail.com', emails)
        self.assertIn('goricoaico+test2@gmail.com', emails)

    def test_query_with_like_operator(self):
        """Test query() with __like operator for case-sensitive search"""
        result = self.store.query(
            filters={'full_name__like': '%User%'},
            keys_only=False
        )
        
        # Should match all records containing "User"
        self.assertEqual(len(result), 3)

    def test_query_with_in_operator(self):
        """Test query() with __in operator"""
        result = self.store.query(
            filters={'status__in': ['ACTIVE', 'INACTIVE']},
            keys_only=False
        )
        
        self.assertEqual(len(result), 2)
        statuses = {r['status'] for r in result}
        self.assertEqual(statuses, {'ACTIVE', 'INACTIVE'})

    def test_query_with_or_conditions(self):
        """Test query() with _or conditions"""
        result = self.store.query(
            filters={
                '_or': [
                    {'status': 'ACTIVE'},
                    {'role': 'admin'}
                ]
            },
            keys_only=False
        )
        
        # Should match ACTIVE user and admin user
        self.assertEqual(len(result), 2)
        matched_ids = {r['id'] for r in result}
        self.assertIn(self.test_uuid1, matched_ids)  # ACTIVE
        self.assertIn(self.test_uuid2, matched_ids)  # admin

    def test_query_with_or_and_ilike(self):
        """Test query() with OR conditions using __ilike"""
        result = self.store.query(
            filters={
                '_or': [
                    {'email__ilike': '%test1%'},
                    {'full_name__ilike': '%another%'}
                ]
            },
            keys_only=False
        )
        
        self.assertEqual(len(result), 2)
        matched_ids = {r['id'] for r in result}
        self.assertIn(self.test_uuid1, matched_ids)  # test1 email
        self.assertIn(self.test_uuid3, matched_ids)  # Another full_name

    def test_query_with_combined_filters(self):
        """Test query() with both AND and OR conditions"""
        result = self.store.query(
            filters={
                'group_id': self.group_uuid,  # AND condition
                '_or': [
                    {'status': 'ACTIVE'},
                    {'status': 'INACTIVE'}
                ]
            },
            keys_only=False
        )
        
        # Should match users in the same group with ACTIVE or INACTIVE status
        self.assertEqual(len(result), 2)
        matched_ids = {r['id'] for r in result}
        self.assertIn(self.test_uuid1, matched_ids)  # Same group + ACTIVE
        self.assertIn(self.test_uuid2, matched_ids)  # Same group + INACTIVE

    def test_query_with_pagination_keys_only(self):
        """Test query() with pagination returning keys and total count"""
        result, total_count = self.store.query(
            keys_only=True,
            page=1,
            limit=2
        )
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(total_count, 3)

    def test_query_with_pagination_full_records(self):
        """Test query() with pagination returning full records and total count"""
        result, total_count = self.store.query(
            keys_only=False,
            page=2,
            limit=2
        )
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)  # Only 1 record on page 2
        self.assertEqual(total_count, 3)
        self.assertIsInstance(result[0], dict)

    def test_query_with_ordering_asc(self):
        """Test query() with ascending order"""
        result = self.store.query(
            keys_only=False,
            order_by='created_at',
            order_direction='asc'
        )
        
        self.assertEqual(len(result), 3)
        # Should be ordered by created_at ascending
        self.assertEqual(result[0]['id'], self.test_uuid1)  # 2023-01-01
        self.assertEqual(result[1]['id'], self.test_uuid2)  # 2023-01-02
        self.assertEqual(result[2]['id'], self.test_uuid3)  # 2023-01-03

    def test_query_with_ordering_desc(self):
        """Test query() with descending order"""
        result = self.store.query(
            keys_only=False,
            order_by='created_at',
            order_direction='desc'
        )
        
        self.assertEqual(len(result), 3)
        # Should be ordered by created_at descending
        self.assertEqual(result[0]['id'], self.test_uuid3)  # 2023-01-03
        self.assertEqual(result[1]['id'], self.test_uuid2)  # 2023-01-02
        self.assertEqual(result[2]['id'], self.test_uuid1)  # 2023-01-01

    def test_query_with_ordering_by_string_field(self):
        """Test query() with ordering by string field"""
        result = self.store.query(
            keys_only=False,
            order_by='full_name',
            order_direction='asc'
        )
        
        self.assertEqual(len(result), 3)
        # Should be ordered alphabetically
        names = [r['full_name'] for r in result]
        self.assertEqual(names, sorted(names))

    def test_query_with_pagination_and_filters(self):
        """Test query() with both pagination and filters"""
        result, total_count = self.store.query(
            filters={'group_id': self.group_uuid},
            keys_only=False,
            page=1,
            limit=1
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 2)  # 2 users in the same group
        self.assertEqual(result[0]['group_id'], self.group_uuid)

    def test_query_with_pagination_and_ordering(self):
        """Test query() with pagination and ordering"""
        result, total_count = self.store.query(
            keys_only=False,
            page=1,
            limit=2,
            order_by='created_at',
            order_direction='desc'
        )
        
        self.assertEqual(len(result), 2)
        self.assertEqual(total_count, 3)
        # Should get the 2 most recent records
        self.assertEqual(result[0]['id'], self.test_uuid3)  # Most recent
        self.assertEqual(result[1]['id'], self.test_uuid2)  # Second most recent

    def test_query_no_matches(self):
        """Test query() with filters that match no records"""
        result = self.store.query(
            filters={'status': 'NONEXISTENT'},
            keys_only=False
        )
        
        self.assertEqual(result, [])

    def test_query_invalid_column_filter(self):
        """Test query() with filter for non-existent column"""
        result = self.store.query(
            filters={'nonexistent_column': 'value'},
            keys_only=False
        )
        
        # Should return empty list as no records have this field
        self.assertEqual(result, [])

    def test_query_with_none_values(self):
        """Test query() with None values in data"""
        # Add record with None values
        test_uuid_none = str(uuid.uuid4())
        self.store.put(test_uuid_none, {
            'id': test_uuid_none,
            'email': 'goricoaico+none@gmail.com',
            'full_name': None,
            'status': 'ACTIVE'
        })
        
        # Query for records with None full_name
        result = self.store.query(
            filters={'full_name': None},
            keys_only=False
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], test_uuid_none)

    def test_query_edge_case_page_zero(self):
        """Test query() with edge case of page=0"""
        result, total_count = self.store.query(
            keys_only=True,
            page=0,
            limit=1
        )
        
        # Should handle gracefully (offset will be negative)
        self.assertIsInstance(result, list)
        self.assertEqual(total_count, 3)

    def test_query_edge_case_negative_limit(self):
        """Test query() with edge case of negative limit"""
        result, total_count = self.store.query(
            keys_only=True,
            page=1,
            limit=-1
        )
        
        # Should handle gracefully
        self.assertIsInstance(result, list)
        self.assertEqual(total_count, 3)

    def test_values_match_basic_equality(self):
        """Test _values_match() with basic equality"""
        self.assertTrue(self.store._values_match('test', 'test'))
        self.assertTrue(self.store._values_match(123, 123))
        self.assertTrue(self.store._values_match(True, True))
        self.assertFalse(self.store._values_match('test', 'different'))

    def test_values_match_uuid_string_conversion(self):
        """Test _values_match() with UUID to string conversion"""
        test_uuid = uuid.uuid4()
        test_uuid_str = str(test_uuid)
        
        # UUID object should match its string representation
        self.assertTrue(self.store._values_match(test_uuid, test_uuid_str))
        self.assertTrue(self.store._values_match(test_uuid_str, test_uuid))

    def test_values_match_string_conversion(self):
        """Test _values_match() with string conversion of different types"""
        self.assertTrue(self.store._values_match(123, '123'))
        self.assertTrue(self.store._values_match(True, 'True'))
        self.assertTrue(self.store._values_match(False, 'False'))

    def test_values_match_none_values(self):
        """Test _values_match() with None values"""
        self.assertTrue(self.store._values_match(None, None))
        self.assertFalse(self.store._values_match(None, 'something'))
        self.assertFalse(self.store._values_match('something', None))

    def test_values_match_different_types(self):
        """Test _values_match() with different data types"""
        # These should not match (different types that don't have string equivalence)
        self.assertFalse(self.store._values_match([], {}))
        self.assertFalse(self.store._values_match('', None))
        self.assertFalse(self.store._values_match(1, 'different'))
        
        # Note: 0 and False will match through string conversion ('0' vs 'False')
        # This is expected behavior in the current implementation

    def test_query_with_uuid_filter(self):
        """Test query() with UUID values in filters"""
        # Filter by group_id (UUID)
        result = self.store.query(
            filters={'group_id': self.group_uuid},
            keys_only=False
        )
        
        self.assertEqual(len(result), 2)  # Two users in the same group
        for record in result:
            self.assertEqual(record['group_id'], self.group_uuid)

    def test_query_with_uuid_object_filter(self):
        """Test query() with UUID object in filter (should convert to string)"""
        group_uuid_obj = uuid.UUID(self.group_uuid)
        
        result = self.store.query(
            filters={'group_id': group_uuid_obj},
            keys_only=False
        )
        
        self.assertEqual(len(result), 2)  # Should match string UUIDs
        for record in result:
            self.assertEqual(record['group_id'], self.group_uuid)

    def test_query_complex_scenario(self):
        """Test query() with complex combination of all features"""
        result, total_count = self.store.query(
            filters={
                'disabled': False,  # AND condition
                '_or': [  # OR conditions
                    {'status': 'ACTIVE'},
                    {'role': 'user'}
                ]
            },
            keys_only=False,
            page=1,
            limit=10,
            order_by='created_at',
            order_direction='desc'
        )
        
        # Should match users who are not disabled AND (ACTIVE OR user role)
        # This should match test_uuid1 (ACTIVE + user + not disabled) and test_uuid3 (user + not disabled)
        self.assertEqual(len(result), 2)
        self.assertEqual(total_count, 2)
        
        # Check ordering (most recent first)
        self.assertEqual(result[0]['id'], self.test_uuid3)  # 2023-01-03
        self.assertEqual(result[1]['id'], self.test_uuid1)  # 2023-01-01


if __name__ == '__main__':
    unittest.main()