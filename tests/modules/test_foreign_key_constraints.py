"""
Unit tests for foreign key constraint handling and cascade deletion scenarios.

These tests are designed to catch database constraint violations that could cause
500 errors in production, specifically around the relationships between:
- AITest and TestExecution (test_id foreign key)
- User and their created resources 
- Group and their owned resources

The goal is to ensure proper cascade deletion handling.
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.modules.tests_store import AITestStore
from app.modules.executions_store import ExecutedTestStore
from app.modules.store_interface import LocalStore
from app.schemas import (
    AITestSchema, AITestCreate, User, ConnectionConfig, ValidationConfig, 
    ValidationCriterion, ExecutedTestSchema, ExecutedTestCreate, 
    ExecutionEnvironment, PerformanceMetrics, TokenUsage
)


class TestForeignKeyConstraints(unittest.TestCase):
    """Test foreign key constraint handling and cascade deletion."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_store = MagicMock(spec=LocalStore)
        self.test_store = AITestStore(self.mock_store)
        self.execution_store = ExecutedTestStore(self.mock_store)
        
        # Create test user
        self.test_user = User(
            id=str(uuid4()),
            email="goricoaico+constraint_tests@gmail.com",
            full_name="Constraint Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group",
            role="user"
        )
        
        # Create test data
        self.test_data = AITestCreate(
            name="Constraint Test",
            description="Test for constraint handling",
            prompt_template="Hello {name}",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.example.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="test-api-key"
            ),
            validation_config=ValidationConfig(
                validator_type="HUMAN",
                validation_criteria=[
                    ValidationCriterion(
                        id="criterion1",
                        name="Test Criterion",
                        description="A test criterion",
                        type="exact_match"
                    )
                ]
            ),
            tags=["constraint", "test"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        self.test_timestamp = datetime.now(timezone.utc)
        self.test_id = str(uuid4())

    def test_delete_test_with_executions_should_delete_executions_first(self):
        """
        Test that deleting a test with executions properly deletes executions first.
        This prevents foreign key constraint violations.
        """
        # Create a test
        test_schema = AITestSchema(
            id=self.test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        # Create executions that reference this test
        execution1_id = str(uuid4())
        execution2_id = str(uuid4())
        
        execution1 = ExecutedTestSchema(
            id=execution1_id,
            test_id=self.test_id,
            executed_at=self.test_timestamp,
            executed_by=self.test_user.id,
            group_id=self.test_user.group,
            execution_environment=ExecutionEnvironment(
                environment_id="test_env",
                version="1.0.0"
            ),
            input_variables={"name": "test"},
            prompt="Hello test",
            response="Hi there!",
            benchmarks=PerformanceMetrics(
                response_time=100.0,
                total_time=120.0,
                token_usage=TokenUsage(prompt=25, completion=25, total=50),
                cost=0.001
            ),
            validation_status="VALIDATED",
            validations=[]
        )
        
        execution2 = ExecutedTestSchema(
            id=execution2_id,
            test_id=self.test_id,
            executed_at=self.test_timestamp,
            executed_by=self.test_user.id,
            group_id=self.test_user.group,
            execution_environment=ExecutionEnvironment(
                environment_id="test_env",
                version="1.0.0"
            ),
            input_variables={"name": "test2"},
            prompt="Hello test2",
            response="Hi there 2!",
            benchmarks=PerformanceMetrics(
                response_time=120.0,
                total_time=140.0,
                token_usage=TokenUsage(prompt=27, completion=28, total=55),
                cost=0.002
            ),
            validation_status="PENDING",
            validations=[]
        )
        
        # Mock the execution store to return executions when listing by test_id
        with patch.object(self.test_store, '_store') as mock_store:
            # Mock execution store creation and listing
            with patch('app.modules.executions_store.ExecutedTestStore') as mock_execution_store_class:
                mock_execution_store = MagicMock()
                mock_execution_store_class.return_value = mock_execution_store
                
                # Mock that executions exist for this test
                mock_execution_store.list.return_value = ([execution1, execution2], 2)
                
                # Mock successful execution deletions
                mock_execution_store.delete.return_value = True
                
                # Mock successful test deletion
                mock_store.pop.return_value = test_schema.model_dump()
                
                # Perform the deletion
                result = self.test_store.delete(self.test_id)
                
                # Verify executions were deleted first
                mock_execution_store.list.assert_called_once_with(test_id=self.test_id, page=1, limit=1000)
                
                # Verify both executions were deleted
                expected_calls = [
                    unittest.mock.call(execution1_id),
                    unittest.mock.call(execution2_id)
                ]
                mock_execution_store.delete.assert_has_calls(expected_calls, any_order=True)
                
                # Verify test was deleted after executions
                mock_store.pop.assert_called_once_with(self.test_id)
                
                # Verify operation succeeded
                self.assertTrue(result)

    def test_delete_test_handles_execution_deletion_failure_gracefully(self):
        """
        Test that test deletion handles execution deletion failures gracefully.
        Even if execution deletion fails, test deletion should still be attempted.
        """
        test_schema = AITestSchema(
            id=self.test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        with patch.object(self.test_store, '_store') as mock_store:
            with patch('app.modules.executions_store.ExecutedTestStore') as mock_execution_store_class:
                mock_execution_store = MagicMock()
                mock_execution_store_class.return_value = mock_execution_store
                
                # Mock execution store to raise an exception
                mock_execution_store.list.side_effect = Exception("Database connection failed")
                
                # Mock successful test deletion (optimistic case)
                mock_store.pop.return_value = test_schema.model_dump()
                
                # Perform the deletion
                result = self.test_store.delete(self.test_id)
                
                # Should still attempt test deletion despite execution deletion failure
                mock_store.pop.assert_called_once_with(self.test_id)
                
                # Should succeed if the underlying store deletion works
                self.assertTrue(result)

    def test_delete_test_with_no_executions_works_normally(self):
        """
        Test that deleting a test with no executions works as before.
        """
        test_schema = AITestSchema(
            id=self.test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        with patch.object(self.test_store, '_store') as mock_store:
            with patch('app.modules.executions_store.ExecutedTestStore') as mock_execution_store_class:
                mock_execution_store = MagicMock()
                mock_execution_store_class.return_value = mock_execution_store
                
                # Mock no executions exist for this test
                mock_execution_store.list.return_value = ([], 0)
                
                # Mock successful test deletion
                mock_store.pop.return_value = test_schema.model_dump()
                
                # Perform the deletion
                result = self.test_store.delete(self.test_id)
                
                # Should check for executions
                mock_execution_store.list.assert_called_once_with(test_id=self.test_id, page=1, limit=1000)
                
                # Should not call delete on execution store since no executions exist
                mock_execution_store.delete.assert_not_called()
                
                # Should delete the test
                mock_store.pop.assert_called_once_with(self.test_id)
                
                # Should succeed
                self.assertTrue(result)

    def test_delete_nonexistent_test_returns_false(self):
        """
        Test that deleting a non-existent test returns False and handles gracefully.
        """
        with patch.object(self.test_store, '_store') as mock_store:
            with patch('app.modules.executions_store.ExecutedTestStore') as mock_execution_store_class:
                mock_execution_store = MagicMock()
                mock_execution_store_class.return_value = mock_execution_store
                
                # Mock no executions exist
                mock_execution_store.list.return_value = ([], 0)
                
                # Mock test doesn't exist
                mock_store.pop.return_value = None
                
                # Perform the deletion
                result = self.test_store.delete("nonexistent-test-id")
                
                # Should still check for executions (safe approach)
                mock_execution_store.list.assert_called_once_with(test_id="nonexistent-test-id", page=1, limit=1000)
                
                # Should attempt to delete the test
                mock_store.pop.assert_called_once_with("nonexistent-test-id")
                
                # Should return False since test doesn't exist
                self.assertFalse(result)

    def test_sql_foreign_key_constraint_simulation(self):
        """
        Simulate SQL foreign key constraint violation to ensure proper handling.
        This test simulates what would happen with a real SQL database.
        """
        from sqlalchemy.exc import IntegrityError
        import psycopg2.errors
        
        test_schema = AITestSchema(
            id=self.test_id,
            created_by=self.test_user.id,
            group_id=self.test_user.group,
            created_at=self.test_timestamp,
            updated_at=self.test_timestamp,
            **self.test_data.model_dump()
        )
        
        # Create an execution that references the test
        execution = ExecutedTestSchema(
            id=str(uuid4()),
            test_id=self.test_id,
            executed_at=self.test_timestamp,
            executed_by=self.test_user.id,
            group_id=self.test_user.group,
            execution_environment=ExecutionEnvironment(
                environment_id="test_env",
                version="1.0.0"
            ),
            input_variables={"name": "test"},
            prompt="Hello test",
            response="Hi there!",
            benchmarks=PerformanceMetrics(
                response_time=100.0,
                total_time=120.0,
                token_usage=TokenUsage(prompt=25, completion=25, total=50),
                cost=0.001
            ),
            validation_status="VALIDATED",
            validations=[]
        )
        
        with patch.object(self.test_store, '_store') as mock_store:
            # Simulate what happens with OLD code (without cascade deletion)
            # The store would raise an IntegrityError when trying to delete the test
            integrity_error = IntegrityError(
                statement="DELETE FROM ai_tests WHERE id = %s",
                params=("test-id",),
                orig=psycopg2.errors.ForeignKeyViolation(
                    'update or delete on table "ai_tests" violates foreign key constraint '
                    '"test_executions_test_id_fkey" on table "test_executions"\n'
                    'DETAIL:  Key (id)=(test-id) is still referenced from table "test_executions".'
                )
            )
            
            # Without our fix, this would raise an IntegrityError
            mock_store.pop.side_effect = integrity_error
            
            # With our fix, the ExecutionStore should be called first
            with patch('app.modules.executions_store.ExecutedTestStore') as mock_execution_store_class:
                mock_execution_store = MagicMock()
                mock_execution_store_class.return_value = mock_execution_store
                
                # Mock that executions exist and can be deleted
                mock_execution_store.list.return_value = ([execution], 1)
                mock_execution_store.delete.return_value = True
                
                # The test deletion should still fail due to timing or other issues
                # but at least we attempted to clean up executions first
                with self.assertRaises(IntegrityError):
                    self.test_store.delete(self.test_id)
                
                # Verify we attempted to clean up executions first
                mock_execution_store.list.assert_called_once_with(test_id=self.test_id, page=1, limit=1000)
                mock_execution_store.delete.assert_called_once()

if __name__ == '__main__':
    unittest.main()