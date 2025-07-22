import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.modules.reports_store import ReportsStore
from app.modules.tests_store import AITestStore
from app.modules.executions_store import ExecutedTestStore
from app.modules.group_store import GroupStore
from app.modules.store_interface import LocalStore
from app.schemas import (
    AITestSchema, AITestCreate, User, ConnectionConfig, ValidationConfig, ValidationCriterion,
    ExecutedTestSchema, ExecutedTestCreate, ValidationEvent, ExecutionEnvironment, PerformanceMetrics, TokenUsage,
    Group, GroupCreate
)
from app.schemas.reports import (
    SummaryTestReport,
    ExecutionTestTrendsReport,
    PerformanceTestReport
)


class TestReportsStore(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        # Use fresh stores for each test to avoid pollution
        self.store = LocalStore()
        self.tests_store = AITestStore(self.store)
        self.executions_store = ExecutedTestStore(self.store)
        self.group_store = GroupStore(self.store)
        self.reports_store = ReportsStore(
            self.tests_store,
            self.executions_store,
            self.store
        )
        
        # Create test user
        self.test_user = User(
            id=str(uuid4()),
            email="goricoaico+reports_store@gmail.com",
            full_name="Test User",
            disabled=False,
            created_at=datetime.now(timezone.utc),
            is_verified=True,
            group="test_group"
        )
        
        # Create test data
        self.test_data = AITestCreate(
            name="Test Test",
            description="A test test",
            prompt_template="Hello {name}",
            interface_type="DIRECT_LLM",
            connection_config=ConnectionConfig(
                endpoint="https://api.galdren.com/v1/chat/completions",
                auth_type="API_KEY",
                auth_string="dummy-api-key"
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
        
        # Create test timestamp
        self.test_timestamp = datetime.now(timezone.utc)

    def tearDown(self):
        """Clean up after each test."""
        # Clear the store to avoid test pollution
        self.store.data.clear()
        self.store.email_index.clear()

    def test_get_summary_report_success(self):
        """Test successful summary report generation."""
        # Create test group
        group = self.group_store.create(
            GroupCreate(name="Test Group", description="Test group"),
            self.test_user
        )
        
        # Update user to belong to the created group
        self.test_user.group = str(group.id)
        
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        # Create test execution
        execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0"
            )
        )
        
        execution = self.executions_store.create(
            str(test.id),
            execution_create,
            self.test_user,
            "Hello World",
            "Hello World Response",
            benchmarks=PerformanceMetrics(
                response_time=100,
                total_time=150,
                token_usage=TokenUsage(prompt=10, completion=5, total=15),
                cost=0.001
            )
        )
        
        # Add validation with correct structure
        validation_event = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Test validation"
        }
        self.executions_store.add_validation(str(execution.id), validation_event)
        
        # Generate summary report
        report = self.reports_store.get_summary_report(self.test_user)
        
        # Verify the report
        self.assertIsInstance(report, SummaryTestReport)
        self.assertEqual(report.test_metrics.total_tests, 1)
        self.assertEqual(report.test_metrics.active_tests, 1)
        self.assertEqual(report.test_metrics.low_risk_tests, 1)
        self.assertEqual(report.execution_metrics.total_executions, 1)
        self.assertEqual(report.execution_metrics.validated_executions, 1)
        self.assertEqual(report.execution_metrics.acceptance_rate, 100.0)

    def test_get_summary_report_empty_data(self):
        """Test summary report generation with no data."""
        report = self.reports_store.get_summary_report(self.test_user)
        
        # Verify the report has zero values
        self.assertIsInstance(report, SummaryTestReport)
        self.assertEqual(report.test_metrics.total_tests, 0)
        self.assertEqual(report.test_metrics.active_tests, 0)
        self.assertEqual(report.execution_metrics.total_executions, 0)
        self.assertEqual(report.execution_metrics.acceptance_rate, 0.0)

    def test_get_summary_report_with_group_filter(self):
        """Test summary report generation with group filter."""
        # Create test group
        group = self.group_store.create(
            GroupCreate(name="Test Group", description="Test group"),
            self.test_user
        )
        
        # Update user to belong to the created group
        self.test_user.group = str(group.id)
        
        # Create test in the group
        test = self.tests_store.create(self.test_data, self.test_user)
        
        # Generate summary report (group filtering is automatic based on user)
        report = self.reports_store.get_summary_report(self.test_user)
        
        # Verify the report
        self.assertIsInstance(report, SummaryTestReport)
        self.assertEqual(report.test_metrics.total_tests, 1)

    def test_get_execution_trends_success(self):
        """Test successful execution trends generation."""
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        # Create test execution
        execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0"
            )
        )
        
        execution = self.executions_store.create(
            str(test.id),
            execution_create,
            self.test_user,
            "Hello World",
            "Hello World Response"
        )
        
        # Generate trends report
        report = self.reports_store.get_execution_trends(self.test_user, days=7)
        
        # Verify the report
        self.assertIsInstance(report, ExecutionTestTrendsReport)
        self.assertEqual(report.period_days, 7)
        self.assertEqual(len(report.trends), 7)
        
        # Check that today has 1 execution
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_trend = next((t for t in report.trends if t.date == today), None)
        self.assertIsNotNone(today_trend)
        self.assertEqual(today_trend.executions, 1)

    def test_get_execution_trends_empty_data(self):
        """Test execution trends generation with no data."""
        report = self.reports_store.get_execution_trends(self.test_user, days=7)
        
        # Verify the report
        self.assertIsInstance(report, ExecutionTestTrendsReport)
        self.assertEqual(report.period_days, 7)
        self.assertEqual(len(report.trends), 7)
        
        # All days should have 0 executions
        for trend in report.trends:
            self.assertEqual(trend.executions, 0)
            self.assertEqual(trend.validations, 0)
            self.assertEqual(trend.passed, 0)

    def test_get_performance_report_success(self):
        """Test successful performance report generation."""
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        # Create test execution with performance data
        execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0"
            )
        )
        
        execution = self.executions_store.create(
            str(test.id),
            execution_create,
            self.test_user,
            "Hello World",
            "Hello World Response",
            benchmarks=PerformanceMetrics(
                response_time=100,
                total_time=150,
                token_usage=TokenUsage(prompt=10, completion=5, total=15),
                cost=0.001
            )
        )
        
        # Add validation with correct structure
        validation_event = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Test validation"
        }
        self.executions_store.add_validation(str(execution.id), validation_event)
        
        # Generate performance report
        report = self.reports_store.get_performance_report(self.test_user)
        
        # Verify the report
        self.assertIsInstance(report, PerformanceTestReport)
        self.assertEqual(len(report.performance_metrics), 1)
        
        metric = report.performance_metrics[0]
        self.assertEqual(metric.test_id, test.id)
        self.assertEqual(metric.test_name, test.name)
        self.assertEqual(metric.total_executions, 1)
        self.assertEqual(metric.success_rate, 100.0)
        self.assertEqual(metric.avg_response_time, 100.0)
        self.assertEqual(metric.avg_cost, 0.001)
        self.assertIsNotNone(metric.last_executed)

    def test_get_performance_report_no_executions(self):
        """Test performance report generation for tests with no executions."""
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        # Generate performance report
        report = self.reports_store.get_performance_report(self.test_user)
        
        # Verify the report
        self.assertIsInstance(report, PerformanceTestReport)
        self.assertEqual(len(report.performance_metrics), 1)
        
        metric = report.performance_metrics[0]
        self.assertEqual(metric.test_id, test.id)
        self.assertEqual(metric.test_name, test.name)
        self.assertEqual(metric.total_executions, 0)
        self.assertEqual(metric.success_rate, 0.0)
        self.assertIsNone(metric.avg_response_time)
        self.assertIsNone(metric.avg_cost)
        self.assertIsNone(metric.last_executed)

    def test_calculate_test_metrics(self):
        """Test test metrics calculation."""
        # Create tests with different statuses and risk levels
        test_data_active = self.test_data.model_copy(update={"status": "ACTIVE", "risk_level": "HIGH"})
        test_data_draft = self.test_data.model_copy(update={"status": "DRAFT", "risk_level": "MEDIUM"})
        test_data_archived = self.test_data.model_copy(update={"status": "ARCHIVED", "risk_level": "LOW"})
        
        test1 = self.tests_store.create(test_data_active, self.test_user)
        test2 = self.tests_store.create(test_data_draft, self.test_user)
        test3 = self.tests_store.create(test_data_archived, self.test_user)
        
        # Get all tests
        tests, _ = self.tests_store.list(page=1, limit=10000)
        
        # Calculate metrics
        metrics = self.reports_store._calculate_test_metrics(tests)
        
        # Verify metrics
        self.assertEqual(metrics.total_tests, 3)
        self.assertEqual(metrics.active_tests, 1)
        self.assertEqual(metrics.draft_tests, 1)
        self.assertEqual(metrics.archived_tests, 1)
        self.assertEqual(metrics.high_risk_tests, 1)
        self.assertEqual(metrics.medium_risk_tests, 1)
        self.assertEqual(metrics.low_risk_tests, 1)

    def test_calculate_execution_metrics(self):
        """Test execution metrics calculation."""
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        # Create executions with different validation statuses
        execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0"
            )
        )
        
        # Create pending execution
        pending_execution = self.executions_store.create(
            str(test.id),
            execution_create,
            self.test_user,
            "Hello World",
            "Hello World Response"
        )
        
        # Create validated execution with passed validation
        validated_execution = self.executions_store.create(
            str(test.id),
            execution_create,
            self.test_user,
            "Hello World",
            "Hello World Response"
        )
        validation_event = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Test validation"
        }
        self.executions_store.add_validation(str(validated_execution.id), validation_event)
        
        # Get all tests
        tests, _ = self.tests_store.list(page=1, limit=10000)
        
        # Calculate metrics
        metrics = self.reports_store._calculate_execution_metrics(tests, self.test_user)
        
        # Verify metrics
        self.assertEqual(metrics.total_executions, 2)
        self.assertEqual(metrics.pending_validations, 1)
        self.assertEqual(metrics.validated_executions, 1)
        self.assertEqual(metrics.passed_validations, 1)
        self.assertEqual(metrics.failed_validations, 0)
        self.assertEqual(metrics.acceptance_rate, 50.0)  # 1 passed out of 2 total executions

    def test_calculate_execution_metrics_all_validation_statuses(self):
        """Test execution metrics calculation with all 4 validation statuses."""
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0"
            )
        )
        
        # Create executions with all validation statuses
        # 1. PENDING execution
        pending_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Pending Test", "Pending Response"
        )
        
        # 2. IN_PROGRESS execution
        in_progress_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "In Progress Test", "In Progress Response"
        )
        # Manually set validation status
        exec_data = self.executions_store._store.get(str(in_progress_exec.id))
        exec_data["validation_status"] = "IN_PROGRESS"
        self.executions_store._store.put(str(in_progress_exec.id), exec_data)
        
        # 3. VALIDATED execution with PASS
        validated_pass_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Validated Pass Test", "Validated Pass Response"
        )
        validation_event_pass = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Pass validation"
        }
        self.executions_store.add_validation(str(validated_pass_exec.id), validation_event_pass)
        
        # 4. VALIDATED execution with FAIL
        validated_fail_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Validated Fail Test", "Validated Fail Response"
        )
        validation_event_fail = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "FAIL",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Fail validation"
        }
        self.executions_store.add_validation(str(validated_fail_exec.id), validation_event_fail)
        
        # 5. ERROR execution
        error_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Error Test", "Error Response"
        )
        # Manually set validation status to ERROR
        exec_data = self.executions_store._store.get(str(error_exec.id))
        exec_data["validation_status"] = "ERROR"
        self.executions_store._store.put(str(error_exec.id), exec_data)
        
        # Get all tests
        tests, _ = self.tests_store.list(page=1, limit=10000)
        
        # Calculate metrics
        metrics = self.reports_store._calculate_execution_metrics(tests, self.test_user)
        
        # Verify metrics
        self.assertEqual(metrics.total_executions, 5)
        self.assertEqual(metrics.pending_validations, 1)
        self.assertEqual(metrics.in_progress_validations, 1)
        self.assertEqual(metrics.validated_executions, 2)  # Both PASS and FAIL
        self.assertEqual(metrics.error_validations, 1)
        self.assertEqual(metrics.passed_validations, 1)
        self.assertEqual(metrics.failed_validations, 1)
        # Acceptance rate: 1 passed out of 5 total = 20%
        self.assertEqual(metrics.acceptance_rate, 20.0)
        
        # Verify all statuses sum to total
        status_sum = (metrics.pending_validations + 
                     metrics.in_progress_validations + 
                     metrics.validated_executions + 
                     metrics.error_validations)
        self.assertEqual(status_sum, metrics.total_executions)

    def test_success_rate_calculation_edge_cases(self):
        """Test success rate calculation edge cases."""
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0"
            )
        )
        
        # Test case 1: Only pending executions (no validations completed)
        for i in range(3):
            self.executions_store.create(
                str(test.id), execution_create, self.test_user,
                f"Pending Test {i}", f"Pending Response {i}"
            )
        
        report = self.reports_store.get_performance_report(self.test_user)
        metric = report.performance_metrics[0]
        # No validations completed, success rate should be 0
        self.assertEqual(metric.success_rate, 0.0)
        
        # Test case 2: Mix of statuses but no PASS validations
        error_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Error Test", "Error Response"
        )
        exec_data = self.executions_store._store.get(str(error_exec.id))
        exec_data["validation_status"] = "ERROR"
        self.executions_store._store.put(str(error_exec.id), exec_data)
        
        fail_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Fail Test", "Fail Response"
        )
        validation_event_fail = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "FAIL",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Fail validation"
        }
        self.executions_store.add_validation(str(fail_exec.id), validation_event_fail)
        
        report = self.reports_store.get_performance_report(self.test_user)
        metric = report.performance_metrics[0]
        # 0 passed out of 5 total = 0%
        self.assertEqual(metric.success_rate, 0.0)

    def test_summary_report_with_mixed_statuses(self):
        """Test summary report generation with mixed validation statuses."""
        # Create test group
        group = self.group_store.create(
            GroupCreate(name="Test Group", description="Test group"),
            self.test_user
        )
        self.test_user.group = str(group.id)
        
        # Create test
        test = self.tests_store.create(self.test_data, self.test_user)
        
        execution_create = ExecutedTestCreate(
            execution_environment=ExecutionEnvironment(
                environment_id="test-env",
                version="1.0.0"
            )
        )
        
        # Create executions with different statuses
        # 2 PENDING
        for i in range(2):
            self.executions_store.create(
                str(test.id), execution_create, self.test_user,
                f"Pending {i}", f"Response {i}"
            )
        
        # 1 ERROR
        error_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Error Test", "Error Response"
        )
        exec_data = self.executions_store._store.get(str(error_exec.id))
        exec_data["validation_status"] = "ERROR"
        self.executions_store._store.put(str(error_exec.id), exec_data)
        
        # 1 VALIDATED with PASS
        pass_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Pass Test", "Pass Response"
        )
        validation_event_pass = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "PASS",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Pass validation"
        }
        self.executions_store.add_validation(str(pass_exec.id), validation_event_pass)
        
        # 1 VALIDATED with FAIL
        fail_exec = self.executions_store.create(
            str(test.id), execution_create, self.test_user,
            "Fail Test", "Fail Response"
        )
        validation_event_fail = {
            "validator_id": str(uuid4()),
            "validator_type": "HUMAN",
            "status": "FAIL",
            "timestamp": datetime.now(timezone.utc),
            "notes": "Fail validation"
        }
        self.executions_store.add_validation(str(fail_exec.id), validation_event_fail)
        
        # Generate summary report
        report = self.reports_store.get_summary_report(self.test_user)
        
        # Verify execution metrics
        exec_metrics = report.execution_metrics
        self.assertEqual(exec_metrics.total_executions, 5)
        self.assertEqual(exec_metrics.pending_validations, 2)
        self.assertEqual(exec_metrics.in_progress_validations, 0)
        self.assertEqual(exec_metrics.validated_executions, 2)
        self.assertEqual(exec_metrics.error_validations, 1)
        self.assertEqual(exec_metrics.passed_validations, 1)
        self.assertEqual(exec_metrics.failed_validations, 1)
        # Acceptance rate: 1 passed out of 5 total = 20%
        self.assertEqual(exec_metrics.acceptance_rate, 20.0)
        
        # Verify all statuses sum to total
        status_sum = (exec_metrics.pending_validations + 
                     exec_metrics.in_progress_validations + 
                     exec_metrics.validated_executions + 
                     exec_metrics.error_validations)
        self.assertEqual(status_sum, exec_metrics.total_executions) 