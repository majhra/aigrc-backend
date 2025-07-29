import unittest
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone
import uuid

from app.modules.executions_store import ExecutedTestStore
from app.modules.store_interface import LocalStore
from app.schemas.executions import ExecutedTestSchema, ValidationEvent, PerformanceMetrics, ErrorDetails
from app.schemas import User


class TestExecutedTestStoreHelpers(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.store = LocalStore()
        self.executions_store = ExecutedTestStore(self.store)
        
        # Sample test data
        self.test_uuid = str(uuid.uuid4())
        self.user_uuid = str(uuid.uuid4())
        self.execution_uuid = str(uuid.uuid4())
        
        # Sample user
        self.user = User(
            id=self.user_uuid,
            email='goricoaico+test@gmail.com',
            full_name='Test User',
            password='hashed_password',
            group='test-group'
        )
        
        # Sample execution data with proper schema structure
        self.execution_data = {
            'id': self.execution_uuid,
            'test_id': self.test_uuid,
            'executed_at': datetime.now(timezone.utc),
            'executed_by': self.user_uuid,
            'execution_environment': {'platform': 'test'},
            'input_variables': {'key': 'value'},
            'prompt': 'Test prompt',
            'response': 'Test response',
            'benchmarks': {
                'response_time': 150.0,  # Changed from response_time_ms
                'total_time': 200.0,     # Added required field
                'token_usage': {         # Changed from token_count
                    'prompt': 15,
                    'completion': 10,
                    'total': 25
                },
                'cost': 0.01            # Changed from cost_usd
            },
            'validation_status': 'PENDING',
            'validations': [
                {
                    'validator_id': str(uuid.uuid4()),
                    'validator_type': 'HUMAN',     # Added required field
                    'timestamp': datetime.now(timezone.utc),  # Changed from validated_at
                    'status': 'PASS',
                    'notes': 'Test validation'
                }
            ],
            'error': None
        }

    def test_convert_to_schema_valid_data(self):
        """Test _convert_to_schema() with valid data"""
        result = self.executions_store._convert_to_schema(self.execution_data)
        
        self.assertIsInstance(result, ExecutedTestSchema)
        self.assertEqual(str(result.id), self.execution_uuid)  # Convert UUID to string for comparison
        self.assertEqual(str(result.test_id), self.test_uuid)  # Convert UUID to string for comparison
        self.assertEqual(result.prompt, 'Test prompt')
        self.assertEqual(result.response, 'Test response')

    def test_convert_to_schema_none_prompt(self):
        """Test _convert_to_schema() with None prompt"""
        data = self.execution_data.copy()
        data['prompt'] = None
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsInstance(result, ExecutedTestSchema)
        self.assertEqual(result.prompt, "")  # Should be converted to empty string

    def test_convert_to_schema_none_response(self):
        """Test _convert_to_schema() with None response"""
        data = self.execution_data.copy()
        data['response'] = None
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsInstance(result, ExecutedTestSchema)
        self.assertEqual(result.response, "")  # Should be converted to empty string

    def test_convert_to_schema_invalid_input_variables(self):
        """Test _convert_to_schema() with invalid input_variables"""
        data = self.execution_data.copy()
        data['input_variables'] = ""  # Empty string instead of dict
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsInstance(result, ExecutedTestSchema)
        self.assertIsNone(result.input_variables)  # Should be converted to None

    def test_convert_to_schema_invalid_input_variables_non_dict(self):
        """Test _convert_to_schema() with non-dict input_variables"""
        data = self.execution_data.copy()
        data['input_variables'] = "not a dict"
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsInstance(result, ExecutedTestSchema)
        self.assertIsNone(result.input_variables)  # Should be converted to None

    def test_convert_to_schema_invalid_error_field(self):
        """Test _convert_to_schema() with invalid error field"""
        data = self.execution_data.copy()
        data['error'] = ""  # Empty string instead of dict
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsInstance(result, ExecutedTestSchema)
        self.assertIsNone(result.error)  # Should be converted to None

    def test_convert_to_schema_invalid_error_field_non_dict(self):
        """Test _convert_to_schema() with non-dict error field"""
        data = self.execution_data.copy()
        data['error'] = "not a dict"
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsInstance(result, ExecutedTestSchema)
        self.assertIsNone(result.error)  # Should be converted to None

    def test_convert_to_schema_malformed_data(self):
        """Test _convert_to_schema() with malformed data that causes exception"""
        data = {
            'id': 'invalid-uuid',  # This will cause validation error
            'test_id': self.test_uuid,
            'executed_at': 'invalid-date',  # This will cause validation error
        }
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsNone(result)  # Should return None on error

    def test_convert_to_schema_missing_required_fields(self):
        """Test _convert_to_schema() with missing required fields"""
        data = {
            'id': self.execution_uuid,
            # Missing required fields like test_id, executed_at, etc.
        }
        
        result = self.executions_store._convert_to_schema(data)
        
        self.assertIsNone(result)  # Should return None on validation error

    def test_passes_complex_filters_no_filters(self):
        """Test _passes_complex_filters() with no filters applied"""
        execution = ExecutedTestSchema(**self.execution_data)
        
        result = self.executions_store._passes_complex_filters(execution, None, None)
        
        self.assertTrue(result)  # Should pass with no filters

    def test_passes_complex_filters_result_match(self):
        """Test _passes_complex_filters() with matching result filter"""
        execution = ExecutedTestSchema(**self.execution_data)
        
        result = self.executions_store._passes_complex_filters(execution, 'PASS', None)
        
        self.assertTrue(result)  # Should pass because validation has PASS status

    def test_passes_complex_filters_result_no_match(self):
        """Test _passes_complex_filters() with non-matching result filter"""
        execution = ExecutedTestSchema(**self.execution_data)
        
        result = self.executions_store._passes_complex_filters(execution, 'FAIL', None)
        
        self.assertFalse(result)  # Should fail because no validation has FAIL status

    def test_passes_complex_filters_has_errors_false(self):
        """Test _passes_complex_filters() with has_errors=False"""
        execution = ExecutedTestSchema(**self.execution_data)
        
        result = self.executions_store._passes_complex_filters(execution, None, False)
        
        self.assertTrue(result)  # Should pass because execution has no error

    def test_passes_complex_filters_has_errors_true_with_error(self):
        """Test _passes_complex_filters() with has_errors=True and error present"""
        data = self.execution_data.copy()
        data['error'] = ErrorDetails(
            code='TestError',
            message='Test error message',
            details={'code': 500}
        )
        execution = ExecutedTestSchema(**data)
        
        result = self.executions_store._passes_complex_filters(execution, None, True)
        
        self.assertTrue(result)  # Should pass because execution has error

    def test_passes_complex_filters_has_errors_true_without_error(self):
        """Test _passes_complex_filters() with has_errors=True but no error"""
        execution = ExecutedTestSchema(**self.execution_data)
        
        result = self.executions_store._passes_complex_filters(execution, None, True)
        
        self.assertFalse(result)  # Should fail because execution has no error

    def test_passes_complex_filters_has_errors_false_with_error(self):
        """Test _passes_complex_filters() with has_errors=False but error present"""
        data = self.execution_data.copy()
        data['error'] = ErrorDetails(
            code='TestError',
            message='Test error message',
            details={'code': 500}
        )
        execution = ExecutedTestSchema(**data)
        
        result = self.executions_store._passes_complex_filters(execution, None, False)
        
        self.assertFalse(result)  # Should fail because execution has error

    def test_passes_complex_filters_combined_filters(self):
        """Test _passes_complex_filters() with both result and has_errors filters"""
        execution = ExecutedTestSchema(**self.execution_data)
        
        result = self.executions_store._passes_complex_filters(execution, 'PASS', False)
        
        self.assertTrue(result)  # Should pass both filters

    def test_passes_complex_filters_combined_filters_fail(self):
        """Test _passes_complex_filters() with combined filters that fail"""
        execution = ExecutedTestSchema(**self.execution_data)
        
        result = self.executions_store._passes_complex_filters(execution, 'FAIL', False)
        
        self.assertFalse(result)  # Should fail result filter

    def test_list_fallback_basic_functionality(self):
        """Test _list_fallback() basic functionality"""
        # Add test execution to store
        self.store.put(self.execution_uuid, self.execution_data)
        
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 1)
        self.assertIsInstance(result[0], ExecutedTestSchema)
        self.assertEqual(str(result[0].id), self.execution_uuid)  # Convert UUID to string for comparison

    def test_list_fallback_with_status_filter(self):
        """Test _list_fallback() with status filter"""
        # Add test execution to store
        self.store.put(self.execution_uuid, self.execution_data)
        
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status='PENDING',
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 1)
        
        # Test with non-matching status
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status='VALIDATED',
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 0)
        self.assertEqual(total_count, 0)

    def test_list_fallback_with_statuses_filter(self):
        """Test _list_fallback() with statuses list filter"""
        # Add test execution to store
        self.store.put(self.execution_uuid, self.execution_data)
        
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=['PENDING', 'VALIDATED'],
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 1)
        
        # Test with non-matching statuses
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=['VALIDATED', 'ERROR'],
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 0)
        self.assertEqual(total_count, 0)

    def test_list_fallback_with_complex_filters(self):
        """Test _list_fallback() with complex filters (result, has_errors)"""
        # Add test execution to store
        self.store.put(self.execution_uuid, self.execution_data)
        
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=None,
            result='PASS',
            has_errors=False
        )
        
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 1)

    def test_list_fallback_with_pagination(self):
        """Test _list_fallback() with pagination"""
        # Create multiple executions
        execution_ids = []
        for i in range(5):
            exec_id = str(uuid.uuid4())
            exec_data = self.execution_data.copy()
            exec_data['id'] = exec_id
            exec_data['executed_at'] = datetime.now(timezone.utc)
            self.store.put(exec_id, exec_data)
            execution_ids.append(exec_id)
        
        # Test first page
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=2,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 2)
        self.assertEqual(total_count, 5)
        
        # Test second page
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=2,
            limit=2,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 2)
        self.assertEqual(total_count, 5)

    def test_list_fallback_ignores_index_keys(self):
        """Test _list_fallback() ignores test_to_executions index keys"""
        # Add test execution to store
        self.store.put(self.execution_uuid, self.execution_data)
        
        # Add index key (should be ignored)
        index_key = f"test_to_executions:{self.test_uuid}"
        self.store.put(index_key, {'executions': [self.execution_uuid]})
        
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        # Should only find the actual execution, not the index
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 1)
        self.assertEqual(str(result[0].id), self.execution_uuid)

    def test_list_fallback_handles_invalid_executions(self):
        """Test _list_fallback() gracefully handles invalid execution data"""
        # Add valid execution
        self.store.put(self.execution_uuid, self.execution_data)
        
        # Add invalid execution data
        invalid_id = str(uuid.uuid4())
        invalid_data = {'invalid': 'data'}
        self.store.put(invalid_id, invalid_data)
        
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        # Should only return valid execution, invalid one should be skipped
        self.assertEqual(len(result), 1)
        self.assertEqual(total_count, 1)
        self.assertEqual(str(result[0].id), self.execution_uuid)

    def test_list_fallback_empty_store(self):
        """Test _list_fallback() with empty store"""
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(result, [])
        self.assertEqual(total_count, 0)

    def test_list_fallback_wrong_test_id(self):
        """Test _list_fallback() with wrong test_id"""
        # Add execution for different test
        self.store.put(self.execution_uuid, self.execution_data)
        
        wrong_test_id = str(uuid.uuid4())
        result, total_count = self.executions_store._list_fallback(
            test_id=wrong_test_id,
            page=1,
            limit=10,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(result, [])
        self.assertEqual(total_count, 0)

    def test_list_fallback_ordering(self):
        """Test _list_fallback() returns executions in descending executed_at order"""
        # Create executions with different timestamps
        exec1_id = str(uuid.uuid4())
        exec1_data = self.execution_data.copy()
        exec1_data['id'] = exec1_id
        exec1_data['executed_at'] = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        
        exec2_id = str(uuid.uuid4())
        exec2_data = self.execution_data.copy()
        exec2_data['id'] = exec2_id
        exec2_data['executed_at'] = datetime(2023, 1, 2, 10, 0, 0, tzinfo=timezone.utc)
        
        exec3_id = str(uuid.uuid4())
        exec3_data = self.execution_data.copy()
        exec3_data['id'] = exec3_id
        exec3_data['executed_at'] = datetime(2023, 1, 3, 10, 0, 0, tzinfo=timezone.utc)
        
        # Add in random order
        self.store.put(exec2_id, exec2_data)
        self.store.put(exec1_id, exec1_data)
        self.store.put(exec3_id, exec3_data)
        
        result, total_count = self.executions_store._list_fallback(
            test_id=self.test_uuid,
            page=1,
            limit=10,
            status=None,
            statuses=None,
            result=None,
            has_errors=None
        )
        
        self.assertEqual(len(result), 3)
        # Should be ordered by executed_at descending (most recent first)
        self.assertEqual(str(result[0].id), exec3_id)  # 2023-01-03
        self.assertEqual(str(result[1].id), exec2_id)  # 2023-01-02
        self.assertEqual(str(result[2].id), exec1_id)  # 2023-01-01


if __name__ == '__main__':
    unittest.main()