import unittest
from datetime import datetime, timezone
from uuid import uuid4

from app.modules.executions_store import ExecutedTestStore
from app.modules.store_interface import LocalStore
from app.schemas.executions import (
    ExecutedTestCreate,
    ExecutedTestSchema,
    ValidationEvent,
    ExecutionEnvironment,
    PerformanceMetrics,
    TokenUsage,
    ErrorDetails
)
from app.schemas import User

class TestExecutedTestStore(unittest.TestCase):
    def setUp(self):
        """Set up test data and store before each test"""
        self.store = LocalStore()
        self.executed_test_store = ExecutedTestStore(self.store)
        
        # Create test user
        self.test_user = User(id=str(uuid4()), email="goricoaico+executedstoretest@gmail.com")
        
        # Create test execution data
        self.test_id = str(uuid4())
        self.test_execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0",
                parameters={"test": True}
            ),
            input_variables={"key": "value"}
        )
        
        # Create sample executions for testing
        self.executions = []
        for i in range(3):
            benchmarks = None
            if i < 2:
                benchmarks = PerformanceMetrics(
                    response_time=100 + i * 10,
                    total_time=150 + i * 10,
                    token_usage=TokenUsage(
                        prompt=10 + i,
                        completion=5 + i,
                        total=15 + i * 2
                    ),
                    cost=0.001 * (i + 1)
                )
            
            error = None
            if i == 2:
                error = ErrorDetails(
                    code="ERROR_001",
                    message="Test failed"
                )
            
            execution = self.executed_test_store.create(
                test_id=self.test_id,
                execution=self.test_execution_create,
                user=self.test_user,
                prompt=f"prompt {i}",
                response=f"response {i}",
                benchmarks=benchmarks,
                error=error
            )
            self.executions.append(execution)
        
        # Add validation to first execution
        validation = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "message": "Test passed",
            "timestamp": datetime.now(timezone.utc)
        }
        self.executed_test_store.add_validation(self.executions[0].id, validation)

    def test_create_execution_basic(self):
        """Test creating a basic execution"""
        benchmarks = PerformanceMetrics(
            response_time=100,
            total_time=150,
            token_usage=TokenUsage(
                prompt=10,
                completion=5,
                total=15
            ),
            cost=0.001
        )
        
        execution = self.executed_test_store.create(
            test_id=self.test_id,
            execution=self.test_execution_create,
            user=self.test_user,
            prompt="test prompt",
            response="test response",
            benchmarks=benchmarks,
            error=None
        )
        
        # Verify execution object
        self.assertEqual(str(execution.test_id), self.test_id)
        self.assertEqual(execution.executed_by, self.test_user.id)
        self.assertEqual(execution.prompt, "test prompt")
        self.assertEqual(execution.response, "test response")
        self.assertEqual(execution.benchmarks.response_time, 100)
        self.assertEqual(execution.benchmarks.total_time, 150)
        self.assertEqual(execution.benchmarks.token_usage.prompt, 10)
        self.assertEqual(execution.benchmarks.token_usage.completion, 5)
        self.assertEqual(execution.benchmarks.token_usage.total, 15)
        self.assertEqual(execution.benchmarks.cost, 0.001)
        self.assertIsNone(execution.error)
        self.assertEqual(execution.validation_status, "PENDING")
        self.assertEqual(len(execution.validations), 0)
        
        # Verify storage
        stored = self.executed_test_store.get(execution.id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.id, execution.id)
        self.assertEqual(str(stored.test_id), self.test_id)
        self.assertEqual(stored.executed_by, self.test_user.id)
        
        # Verify index
        execution_ids = self.executed_test_store.get_execution_ids_for_test(self.test_id)
        self.assertIn(str(execution.id), execution_ids)

    def test_create_execution_with_error(self):
        """Test creating an execution with error data"""
        error = ErrorDetails(
            code="ERROR_001",
            message="Test failed"
        )
        
        execution = self.executed_test_store.create(
            test_id=self.test_id,
            execution=self.test_execution_create,
            user=self.test_user,
            prompt="error prompt",
            response="error response",
            benchmarks=None,
            error=error
        )
        
        self.assertEqual(execution.error.code, "ERROR_001")
        self.assertEqual(execution.error.message, "Test failed")
        self.assertIsNone(execution.error.details)
        self.assertIsNone(execution.benchmarks)
        
        # Verify error data is stored correctly
        stored = self.executed_test_store.get(execution.id)
        self.assertEqual(stored.error.code, "ERROR_001")
        self.assertEqual(stored.error.message, "Test failed")
        self.assertIsNone(stored.error.details)

    def test_create_execution_with_complex_input(self):
        """Test creating an execution with complex input data"""
        complex_input = {
            "nested": '{"key": "value"}',  # JSON string
            "list": "[1, 2, 3]",  # JSON string
            "null_value": "null",  # String "null"
            "text": "Some text",
            "number": "42",
            "boolean": "true"
        }
        complex_benchmarks = PerformanceMetrics(
            response_time=200,
            total_time=250,
            token_usage=TokenUsage(
                prompt=20,
                completion=10,
                total=30
            ),
            cost=0.002
        )
        
        execution = self.executed_test_store.create(
            test_id=self.test_id,
            execution=ExecutedTestCreate(
                execution_environment=ExecutionEnvironment(
                    environment_id="test-env",
                    version="1.0.0",
                    parameters={"test": True}
                ),
                input_variables=complex_input
            ),
            user=self.test_user,
            prompt="complex prompt",
            response="complex response",
            benchmarks=complex_benchmarks,
            error=None
        )
        
        # Verify input variables are stored as strings
        self.assertEqual(execution.input_variables, complex_input)
        self.assertEqual(execution.input_variables["nested"], '{"key": "value"}')
        self.assertEqual(execution.input_variables["list"], "[1, 2, 3]")
        self.assertEqual(execution.input_variables["null_value"], "null")
        self.assertEqual(execution.input_variables["text"], "Some text")
        self.assertEqual(execution.input_variables["number"], "42")
        self.assertEqual(execution.input_variables["boolean"], "true")
        
        # Verify benchmarks
        self.assertEqual(execution.benchmarks.response_time, 200)
        self.assertEqual(execution.benchmarks.total_time, 250)
        self.assertEqual(execution.benchmarks.token_usage.prompt, 20)
        self.assertEqual(execution.benchmarks.token_usage.completion, 10)
        self.assertEqual(execution.benchmarks.token_usage.total, 30)
        self.assertEqual(execution.benchmarks.cost, 0.002)
        
        # Verify complex data is stored correctly
        stored = self.executed_test_store.get(execution.id)
        self.assertEqual(stored.input_variables, complex_input)
        self.assertEqual(stored.benchmarks, complex_benchmarks)

    def test_list_executions(self):
        """Test listing executions with various filters"""
        # Test listing all executions
        listed, total = self.executed_test_store.list(self.test_id)
        self.assertEqual(total, 3)
        self.assertEqual(len(listed), 3)
        self.assertTrue(all(isinstance(e, ExecutedTestSchema) for e in listed))
        
        # Test pagination
        listed, total = self.executed_test_store.list(self.test_id, page=1, limit=2)
        self.assertEqual(total, 3)
        self.assertEqual(len(listed), 2)
        self.assertGreaterEqual(listed[0].executed_at, listed[1].executed_at)  # Verify sorting
        
        # Test filtering by status
        listed, total = self.executed_test_store.list(self.test_id, status="VALIDATED")
        self.assertEqual(total, 1)
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].validation_status, "VALIDATED")
        
        # Test filtering by result
        listed, total = self.executed_test_store.list(self.test_id, result="PASS")
        self.assertEqual(total, 1)
        self.assertEqual(len(listed), 1)
        self.assertTrue(any(v.status == "PASS" for v in listed[0].validations))

    def test_add_validation(self):
        """Test adding validations to an execution"""
        execution = self.executions[1]  # Use second execution (no validations yet)
        
        # Add first validation
        validation1 = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "message": "First validation passed",
            "timestamp": datetime.now(timezone.utc)
        }
        updated = self.executed_test_store.add_validation(execution.id, validation1)
        self.assertEqual(updated.validation_status, "VALIDATED")
        self.assertEqual(len(updated.validations), 1)
        self.assertEqual(updated.validations[0].validator_type, "HUMAN")
        self.assertEqual(updated.validations[0].status, "PASS")
        
        # Add second validation
        validation2 = {
            "validator_id": str(uuid4()),
            "validator_type": "AI",
            "status": "FAIL",
            "message": "Second validation failed",
            "timestamp": datetime.now(timezone.utc),
            "confidence": 0.95
        }
        updated = self.executed_test_store.add_validation(execution.id, validation2)
        self.assertEqual(updated.validation_status, "VALIDATED")  # Status remains VALIDATED
        self.assertEqual(len(updated.validations), 2)
        self.assertEqual(updated.validations[1].validator_type, "AI")
        self.assertEqual(updated.validations[1].status, "FAIL")
        self.assertEqual(updated.validations[1].confidence, 0.95)
        
        # Verify storage
        stored = self.executed_test_store.get(execution.id)
        self.assertEqual(stored.validation_status, "VALIDATED")
        self.assertEqual(len(stored.validations), 2)
        self.assertEqual(stored.validations[0].status, "PASS")
        self.assertEqual(stored.validations[1].status, "FAIL")

    def test_delete_execution(self):
        """Test deleting an execution and cleaning up indexes"""
        execution = self.executions[0]
        
        # Verify execution exists
        self.assertIsNotNone(self.executed_test_store.get(execution.id))
        self.assertIn(str(execution.id), self.executed_test_store.get_execution_ids_for_test(self.test_id))
        
        # Delete execution
        self.assertTrue(self.executed_test_store.delete(execution.id))
        
        # Verify execution is removed
        self.assertIsNone(self.executed_test_store.get(execution.id))
        
        # Verify index is cleaned up
        self.assertNotIn(str(execution.id), self.executed_test_store.get_execution_ids_for_test(self.test_id))

    def test_clear_store(self):
        """Test clearing all data from the store"""
        # Add another execution
        execution2 = self.executed_test_store.create(
            test_id=self.test_id,
            execution=ExecutedTestCreate(
                execution_environment=ExecutionEnvironment(
                    environment_id="test-env",
                    version="1.0.0",
                    parameters={"test": True}
                ),
                input_variables={}
            ),
            user=User(id=str(uuid4()), email="test2@example.com"),
            prompt="test prompt 2",
            response="test response 2",
            benchmarks=PerformanceMetrics(
                response_time=100,
                total_time=150,
                token_usage=TokenUsage(
                    prompt=10,
                    completion=5,
                    total=15
                ),
                cost=0.001
            )
        )
        
        # Clear store
        self.executed_test_store.clear()
        
        # Verify all data is removed
        self.assertIsNone(self.executed_test_store.get(self.executions[0].id))
        self.assertIsNone(self.executed_test_store.get(execution2.id))
        self.assertEqual(len(self.executed_test_store.get_execution_ids_for_test(self.test_id)), 0)

    def test_get_nonexistent_execution(self):
        """Test getting a non-existent execution"""
        self.assertIsNone(self.executed_test_store.get(str(uuid4())))

    def test_delete_nonexistent_execution(self):
        """Test deleting a non-existent execution"""
        self.assertFalse(self.executed_test_store.delete(str(uuid4())))

    def test_add_validation_nonexistent(self):
        """Test adding validation to a non-existent execution"""
        validation = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "message": "Test passed",
            "timestamp": datetime.now(timezone.utc)
        }
        self.assertIsNone(self.executed_test_store.add_validation(str(uuid4()), validation)) 