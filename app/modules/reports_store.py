from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Tuple
from collections import defaultdict, Counter
from uuid import UUID

from app.modules.store_interface import StoreProtocol, LocalStore
from app.modules.tests_store import MyTestStore
from app.modules.executions_store import ExecutedTestStore
from app.schemas.reports import (
    TestSummaryMetrics,
    ExecutionSummaryMetrics,
    TestExecutionTrend,
    TestPerformanceMetrics,
    SummaryTestReport,
    ExecutionTestTrendsReport,
    PerformanceTestReport
)
from app.schemas import TestSchema, ExecutedTestSchema, User


class ReportsStore:
    """Store for generating and managing test reports"""
    
    def __init__(
        self,
        tests_store: MyTestStore,
        executions_store: ExecutedTestStore,
        store: StoreProtocol = None
    ):
        self._tests_store = tests_store
        self._executions_store = executions_store
        self._store = store or LocalStore()

    def get_summary_report(self, user: User) -> SummaryTestReport:
        """Generate a comprehensive summary report for tests and executions"""
        now = datetime.now(timezone.utc)
        
        # Get all tests (filtered by user's group)
        tests, _ = self._tests_store.list(group_id=user.group, page=1, limit=10000)
        
        # Calculate test metrics
        test_metrics = self._calculate_test_metrics(tests)
        
        # Calculate execution metrics
        execution_metrics = self._calculate_execution_metrics(tests, user)
        
        return SummaryTestReport(
            test_metrics=test_metrics,
            execution_metrics=execution_metrics,
            generated_at=now
        )

    def get_execution_trends(
        self,
        user: User,
        days: int = 30
    ) -> ExecutionTestTrendsReport:
        """Generate execution trends over a specified period"""
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)
        
        # Get all tests (filtered by user's group)
        tests, _ = self._tests_store.list(group_id=user.group, page=1, limit=10000)
        
        # Collect all executions for these tests
        all_executions = []
        for test in tests:
            executions, _ = self._executions_store.list(
                test_id=str(test.id),
                page=1,
                limit=10000
            )
            all_executions.extend(executions)
        
        # Filter executions by date range
        recent_executions = [
            ex for ex in all_executions
            if ex.executed_at >= start_date
        ]
        
        # Group executions by date
        daily_stats = defaultdict(lambda: {"executions": 0, "validations": 0, "passed": 0})
        
        for execution in recent_executions:
            date_str = execution.executed_at.strftime("%Y-%m-%d")
            daily_stats[date_str]["executions"] += 1
            
            if execution.validation_status == "VALIDATED":
                daily_stats[date_str]["validations"] += 1
                
                # Count passed validations
                passed_count = sum(
                    1 for validation in execution.validations
                    if validation.status == "PASSED"
                )
                daily_stats[date_str]["passed"] += passed_count
        
        # Convert to trend data points
        trends = []
        for i in range(days):
            date = now - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            stats = daily_stats[date_str]
            
            trends.append(TestExecutionTrend(
                date=date_str,
                executions=stats["executions"],
                validations=stats["validations"],
                passed=stats["passed"]
            ))
        
        # Sort by date (oldest first)
        trends.sort(key=lambda x: x.date)
        
        return ExecutionTestTrendsReport(
            trends=trends,
            period_days=days,
            generated_at=now
        )

    def get_performance_report(
        self,
        user: User
    ) -> PerformanceTestReport:
        """Generate performance metrics for all tests"""
        now = datetime.now(timezone.utc)
        
        # Get all tests (filtered by user's group)
        tests, _ = self._tests_store.list(group_id=user.group, page=1, limit=10000)
        
        performance_metrics = []
        
        for test in tests:
            # Get all executions for this test
            executions, _ = self._executions_store.list(
                test_id=str(test.id),
                page=1,
                limit=10000
            )
            
            if not executions:
                # No executions for this test
                performance_metrics.append(TestPerformanceMetrics(
                    test_id=test.id,
                    test_name=test.name,
                    total_executions=0,
                    success_rate=0.0,
                    avg_response_time=None,
                    avg_cost=None,
                    last_executed=None
                ))
                continue
            
            # Calculate metrics
            total_executions = len(executions)
            validated_executions = [ex for ex in executions if ex.validation_status == "VALIDATED"]
            
            # Calculate success rate
            if validated_executions:
                passed_count = sum(
                    1 for ex in validated_executions
                    for validation in ex.validations
                    if validation.status == "PASS"
                )
                success_rate = (passed_count / len(validated_executions)) * 100
            else:
                success_rate = 0.0
            
            # Calculate average response time
            response_times = []
            costs = []
            for ex in executions:
                if ex.benchmarks and ex.benchmarks.response_time:
                    response_times.append(ex.benchmarks.response_time)
                if ex.benchmarks and ex.benchmarks.cost:
                    costs.append(ex.benchmarks.cost)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else None
            avg_cost = sum(costs) / len(costs) if costs else None
            
            # Get last execution time
            last_executed = max(ex.executed_at for ex in executions) if executions else None
            
            performance_metrics.append(TestPerformanceMetrics(
                test_id=test.id,
                test_name=test.name,
                total_executions=total_executions,
                success_rate=success_rate,
                avg_response_time=avg_response_time,
                avg_cost=avg_cost,
                last_executed=last_executed
            ))
        
        return PerformanceTestReport(
            performance_metrics=performance_metrics,
            generated_at=now
        )

    def _calculate_test_metrics(self, tests: List[TestSchema]) -> TestSummaryMetrics:
        """Calculate test-related metrics"""
        total_tests = len(tests)
        
        # Status breakdown
        status_counts = Counter(test.status for test in tests)
        active_tests = status_counts.get("ACTIVE", 0)
        draft_tests = status_counts.get("DRAFT", 0)
        archived_tests = status_counts.get("ARCHIVED", 0)
        
        # Risk level breakdown
        risk_counts = Counter(test.risk_level for test in tests)
        high_risk_tests = risk_counts.get("HIGH", 0)
        medium_risk_tests = risk_counts.get("MEDIUM", 0)
        low_risk_tests = risk_counts.get("LOW", 0)
        
        # Category breakdown (assuming tests have category field)
        # For now, we'll set these to 0 as the current schema doesn't have category
        safety_tests = 0
        accuracy_tests = 0
        compliance_tests = 0
        
        return TestSummaryMetrics(
            total_tests=total_tests,
            active_tests=active_tests,
            draft_tests=draft_tests,
            archived_tests=archived_tests,
            high_risk_tests=high_risk_tests,
            medium_risk_tests=medium_risk_tests,
            low_risk_tests=low_risk_tests,
            safety_tests=safety_tests,
            accuracy_tests=accuracy_tests,
            compliance_tests=compliance_tests
        )

    def _calculate_execution_metrics(
        self,
        tests: List[TestSchema],
        user: User
    ) -> ExecutionSummaryMetrics:
        """Calculate execution-related metrics"""
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        # Collect all executions for these tests
        all_executions = []
        for test in tests:
            executions, _ = self._executions_store.list(
                test_id=str(test.id),
                page=1,
                limit=10000
            )
            all_executions.extend(executions)
        
        total_executions = len(all_executions)
        
        # Status breakdown
        status_counts = Counter(ex.validation_status for ex in all_executions)
        pending_validations = status_counts.get("PENDING", 0)
        in_progress_validations = status_counts.get("IN_PROGRESS", 0)
        validated_executions = status_counts.get("VALIDATED", 0)
        
        # Validation results
        validated_exes = [ex for ex in all_executions if ex.validation_status == "VALIDATED"]
        passed_validations = 0
        failed_validations = 0
        
        for ex in validated_exes:
            for validation in ex.validations:
                if validation.status == "PASS":
                    passed_validations += 1
                elif validation.status == "FAIL":
                    failed_validations += 1
        
        # Calculate acceptance rate
        total_validations = passed_validations + failed_validations
        acceptance_rate = (passed_validations / total_validations * 100) if total_validations > 0 else 0.0
        
        # Recent activity
        recent_executions_7 = [ex for ex in all_executions if ex.executed_at >= seven_days_ago]
        recent_executions_30 = [ex for ex in all_executions if ex.executed_at >= thirty_days_ago]
        
        return ExecutionSummaryMetrics(
            total_executions=total_executions,
            pending_validations=pending_validations,
            in_progress_validations=in_progress_validations,
            validated_executions=validated_executions,
            passed_validations=passed_validations,
            failed_validations=failed_validations,
            acceptance_rate=acceptance_rate,
            executions_last_7_days=len(recent_executions_7),
            executions_last_30_days=len(recent_executions_30)
        ) 