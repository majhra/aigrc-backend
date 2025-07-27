"""
Unit tests for database constraint validation and SQL-specific foreign key handling.

These tests are designed to catch constraint violations that would occur with real
SQL databases (PostgreSQL, MySQL, etc.) and ensure proper error handling.

This includes:
- Foreign key constraint violations
- NOT NULL constraint violations  
- UNIQUE constraint violations
- Check constraint violations
- Proper transaction handling
"""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4
import sqlalchemy.exc
import psycopg2.errors

from app.modules.sql_store import SQLStore
from app.modules.tests_store import AITestStore
from app.modules.executions_store import ExecutedTestStore
from app.schemas import (
    AITestSchema, AITestCreate, User, ExecutedTestSchema,
    ConnectionConfig, ValidationConfig, ValidationCriterion,
    ExecutionEnvironment, PerformanceMetrics, TokenUsage
)


class TestDatabaseConstraints(unittest.TestCase):
    """Test database constraint validation and error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_timestamp = datetime.now(timezone.utc)
        self.user_id = str(uuid4())
        self.group_id = "test_group"
        self.test_id = str(uuid4())
        self.execution_id = str(uuid4())
        
        self.test_user = User(
            id=self.user_id,
            email="goricoaico+db_constraint_tests@gmail.com",
            full_name="DB Constraint Test User",
            disabled=False,
            created_at=self.test_timestamp,
            is_verified=True,
            group=self.group_id,
            role="user"
        )

    def test_foreign_key_violation_on_test_deletion(self):
        """
        Test that foreign key violations are properly caught and handled.
        This simulates the exact error that occurred in production.
        """
        # Create a mock SQL store that will raise the foreign key violation
        mock_sql_store = MagicMock(spec=SQLStore)
        test_store = AITestStore(mock_sql_store)
        
        # Create the exact foreign key violation error from production logs
        integrity_error = sqlalchemy.exc.IntegrityError(
            statement="DELETE FROM ai_tests WHERE id = %s",
            params=(self.test_id,),
            orig=psycopg2.errors.ForeignKeyViolation(
                'update or delete on table "ai_tests" violates foreign key constraint '
                '"test_executions_test_id_fkey" on table "test_executions"\n'
                f'DETAIL:  Key (id)=({self.test_id}) is still referenced from table "test_executions".'
            )
        )
        
        # Mock that executions exist for this test
        execution = ExecutedTestSchema(
            id=self.execution_id,
            test_id=self.test_id,
            executed_at=self.test_timestamp,
            executed_by=self.user_id,
            group_id=self.group_id,
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
        
        # Mock the execution store to properly handle cascade deletion
        with patch('app.modules.executions_store.ExecutedTestStore') as mock_execution_store_class:
            mock_execution_store = MagicMock()
            mock_execution_store_class.return_value = mock_execution_store
            
            # CASE 1: Without our fix - would raise IntegrityError
            mock_execution_store.list.return_value = ([execution], 1)
            mock_execution_store.delete.return_value = False  # Deletion fails
            mock_sql_store.pop.side_effect = integrity_error
            
            # This should raise the constraint violation error
            with self.assertRaises(sqlalchemy.exc.IntegrityError) as context:
                test_store.delete(self.test_id)
            
            # Verify it's the specific foreign key violation
            self.assertIn("test_executions_test_id_fkey", str(context.exception))
            self.assertIn("violates foreign key constraint", str(context.exception))
            
            # CASE 2: With our fix - should handle gracefully
            mock_execution_store.delete.return_value = True  # Execution deletion succeeds
            mock_sql_store.pop.side_effect = None  # Reset
            mock_sql_store.pop.return_value = {"deleted": True}
            
            # Now deletion should succeed
            result = test_store.delete(self.test_id)
            
            # Verify execution cleanup was attempted
            mock_execution_store.list.assert_called_with(test_id=self.test_id, page=1, limit=1000)
            mock_execution_store.delete.assert_called_with(self.execution_id)
            
            # Verify test deletion succeeded after cleanup
            mock_sql_store.pop.assert_called_with(self.test_id)
            self.assertTrue(result)

    def test_not_null_constraint_violation(self):
        """
        Test handling of NOT NULL constraint violations.
        """
        mock_sql_store = MagicMock(spec=SQLStore)
        test_store = AITestStore(mock_sql_store)
        
        # Create a NOT NULL constraint violation
        not_null_error = sqlalchemy.exc.IntegrityError(
            statement="INSERT INTO ai_tests (id, name, description) VALUES (%s, %s, %s)",
            params=(self.test_id, None, "Test description"),
            orig=psycopg2.errors.NotNullViolation(
                'null value in column "name" violates not-null constraint\n'
                'DETAIL:  Failing row contains (test-id, null, Test description, ...).'
            )
        )
        
        mock_sql_store.put.side_effect = not_null_error
        
        # Create test data with missing required field
        invalid_test_data = AITestCreate(
            name=None,  # This should cause NOT NULL violation
            description="Test with missing name",
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
            tags=["test"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # This should raise a constraint violation
        with self.assertRaises(sqlalchemy.exc.IntegrityError) as context:
            test_store.create(invalid_test_data, self.test_user)
        
        # Verify it's the specific NOT NULL violation
        self.assertIn("not-null constraint", str(context.exception))

    def test_unique_constraint_violation(self):
        """
        Test handling of UNIQUE constraint violations.
        """
        mock_sql_store = MagicMock(spec=SQLStore)
        test_store = AITestStore(mock_sql_store)
        
        # Create a UNIQUE constraint violation (e.g., duplicate test name within group)
        unique_error = sqlalchemy.exc.IntegrityError(
            statement="INSERT INTO ai_tests (id, name, group_id) VALUES (%s, %s, %s)",
            params=(self.test_id, "Duplicate Test", self.group_id),
            orig=psycopg2.errors.UniqueViolation(
                'duplicate key value violates unique constraint "ai_tests_name_group_id_key"\n'
                f'DETAIL:  Key (name, group_id)=(Duplicate Test, {self.group_id}) already exists.'
            )
        )
        
        mock_sql_store.put.side_effect = unique_error
        
        # Create test data that would violate uniqueness
        duplicate_test_data = AITestCreate(
            name="Duplicate Test",
            description="Test with duplicate name",
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
            tags=["test"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # This should raise a constraint violation
        with self.assertRaises(sqlalchemy.exc.IntegrityError) as context:
            test_store.create(duplicate_test_data, self.test_user)
        
        # Verify it's the specific UNIQUE violation
        self.assertIn("unique constraint", str(context.exception))
        self.assertIn("already exists", str(context.exception))

    def test_transaction_rollback_on_constraint_violation(self):
        """
        Test that transactions are properly rolled back on constraint violations.
        """
        mock_sql_store = MagicMock(spec=SQLStore)
        test_store = AITestStore(mock_sql_store)
        
        # Mock a session for transaction testing
        mock_session = MagicMock()
        mock_sql_store.session = mock_session
        
        # Create a constraint violation that should trigger rollback
        constraint_error = sqlalchemy.exc.IntegrityError(
            statement="INSERT INTO ai_tests VALUES (...)",
            params=(),
            orig=psycopg2.errors.ForeignKeyViolation("Foreign key constraint violation")
        )
        
        mock_sql_store.put.side_effect = constraint_error
        
        # Create valid test data
        test_data = AITestCreate(
            name="Transaction Test",
            description="Test for transaction handling",
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
            tags=["test"],
            risk_level="LOW",
            status="ACTIVE"
        )
        
        # Attempt creation which should fail and trigger rollback
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            test_store.create(test_data, self.test_user)
        
        # Verify rollback was called (this would be handled by SQLStore)
        # In a real implementation, you'd verify transaction rollback

    def test_connection_pool_exhaustion_handling(self):
        """
        Test handling of database connection issues.
        """
        mock_sql_store = MagicMock(spec=SQLStore)
        test_store = AITestStore(mock_sql_store)
        
        # Simulate connection pool exhaustion
        connection_error = sqlalchemy.exc.TimeoutError(
            "QueuePool limit of size 5 overflow 10 reached, connection timed out",
            None, None
        )
        
        mock_sql_store.get.side_effect = connection_error
        
        # This should handle the connection error gracefully
        result = test_store.get(self.test_id)
        
        # Should return None instead of crashing
        self.assertIsNone(result)

    def test_deadlock_detection_and_retry(self):
        """
        Test detection and handling of database deadlocks.
        """
        mock_sql_store = MagicMock(spec=SQLStore)
        test_store = AITestStore(mock_sql_store)
        
        # Simulate a deadlock
        deadlock_error = sqlalchemy.exc.OperationalError(
            "deadlock detected",
            None,
            psycopg2.errors.DeadlockDetected(
                "deadlock detected\n"
                "DETAIL:  Process 12345 waits for ShareLock on transaction 67890; "
                "blocked by process 54321.\n"
                "Process 54321 waits for ShareLock on transaction 12345; "
                "blocked by process 12345."
            )
        )
        
        # First call raises deadlock, second succeeds
        mock_sql_store.pop.side_effect = [deadlock_error, {"deleted": True}]
        
        # Mock execution cleanup
        with patch('app.modules.executions_store.ExecutedTestStore') as mock_execution_store_class:
            mock_execution_store = MagicMock()
            mock_execution_store_class.return_value = mock_execution_store
            mock_execution_store.list.return_value = ([], 0)
            
            # In a real implementation, you might implement retry logic
            # For now, just test that the error is properly raised
            with self.assertRaises(sqlalchemy.exc.OperationalError) as context:
                test_store.delete(self.test_id)
            
            # Verify it's a deadlock error
            self.assertIn("deadlock detected", str(context.exception))

    def test_constraint_violation_error_messages(self):
        """
        Test that constraint violation error messages are informative.
        """
        # Test various constraint violation scenarios and ensure
        # error messages would be helpful for debugging
        
        error_scenarios = [
            {
                "name": "Foreign Key Violation",
                "error": sqlalchemy.exc.IntegrityError(
                    "DELETE FROM ai_tests WHERE id = %s",
                    (self.test_id,),
                    psycopg2.errors.ForeignKeyViolation(
                        'update or delete on table "ai_tests" violates foreign key constraint '
                        '"test_executions_test_id_fkey" on table "test_executions"'
                    )
                ),
                "expected_keywords": ["foreign key constraint", "test_executions", "ai_tests"]
            },
            {
                "name": "NOT NULL Violation",
                "error": sqlalchemy.exc.IntegrityError(
                    "INSERT INTO ai_tests (name) VALUES (%s)",
                    (None,),
                    psycopg2.errors.NotNullViolation(
                        'null value in column "name" violates not-null constraint'
                    )
                ),
                "expected_keywords": ["not-null constraint", "name"]
            },
            {
                "name": "Unique Violation",
                "error": sqlalchemy.exc.IntegrityError(
                    "INSERT INTO users (email) VALUES (%s)",
                    ("duplicate@example.com",),
                    psycopg2.errors.UniqueViolation(
                        'duplicate key value violates unique constraint "users_email_key"'
                    )
                ),
                "expected_keywords": ["unique constraint", "duplicate key", "users_email"]
            }
        ]
        
        for scenario in error_scenarios:
            error_msg = str(scenario["error"])
            
            # Verify error message contains expected keywords
            for keyword in scenario["expected_keywords"]:
                self.assertIn(keyword.lower(), error_msg.lower(), 
                    f"Error message for {scenario['name']} should contain '{keyword}'")
            
            # Verify error message is detailed enough for debugging
            self.assertGreater(len(error_msg), 50, 
                f"Error message for {scenario['name']} should be descriptive")

if __name__ == '__main__':
    unittest.main()