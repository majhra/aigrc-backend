from typing import List, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from uuid import UUID


class TestSummaryMetrics(BaseModel):
    """Summary metrics for tests"""
    model_config = ConfigDict(from_attributes=True)
    
    total_tests: int = Field(..., description="Total number of tests")
    active_tests: int = Field(..., description="Number of active tests")
    draft_tests: int = Field(..., description="Number of draft tests")
    archived_tests: int = Field(..., description="Number of archived tests")
    
    # Risk level breakdown
    high_risk_tests: int = Field(..., description="Number of high risk tests")
    medium_risk_tests: int = Field(..., description="Number of medium risk tests")
    low_risk_tests: int = Field(..., description="Number of low risk tests")
    
    # Category breakdown
    safety_tests: int = Field(..., description="Number of safety tests")
    accuracy_tests: int = Field(..., description="Number of accuracy tests")
    compliance_tests: int = Field(..., description="Number of compliance tests")


class ExecutionSummaryMetrics(BaseModel):
    """Summary metrics for test executions"""
    model_config = ConfigDict(from_attributes=True)
    
    total_executions: int = Field(..., description="Total number of executions")
    pending_validations: int = Field(..., description="Number of executions pending validation")
    in_progress_validations: int = Field(..., description="Number of executions with validation in progress")
    validated_executions: int = Field(..., description="Number of validated executions")
    
    # Validation results
    passed_validations: int = Field(..., description="Number of passed validations")
    failed_validations: int = Field(..., description="Number of failed validations")
    acceptance_rate: float = Field(..., description="Acceptance rate as percentage (0-100)")
    
    # Recent activity
    executions_last_7_days: int = Field(..., description="Executions in the last 7 days")
    executions_last_30_days: int = Field(..., description="Executions in the last 30 days")


class SummaryTestReport(BaseModel):
    """Complete test summary report"""
    model_config = ConfigDict(from_attributes=True)
    
    test_metrics: TestSummaryMetrics = Field(..., description="Test-related metrics")
    execution_metrics: ExecutionSummaryMetrics = Field(..., description="Execution-related metrics")
    generated_at: datetime = Field(..., description="When this report was generated")


class TestExecutionTrend(BaseModel):
    """Execution trend data point"""
    model_config = ConfigDict(from_attributes=True)
    
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    executions: int = Field(..., description="Number of executions on this date")
    validations: int = Field(..., description="Number of validations on this date")
    passed: int = Field(..., description="Number of passed validations on this date")


class ExecutionTestTrendsReport(BaseModel):
    """Execution trends over time"""
    model_config = ConfigDict(from_attributes=True)
    
    trends: List[TestExecutionTrend] = Field(..., description="Daily execution trends")
    period_days: int = Field(..., description="Number of days in the trend period")
    generated_at: datetime = Field(..., description="When this report was generated")


class TestPerformanceMetrics(BaseModel):
    """Performance metrics for tests"""
    model_config = ConfigDict(from_attributes=True)
    
    test_id: UUID = Field(..., description="Test identifier")
    test_name: str = Field(..., description="Test name")
    total_executions: int = Field(..., description="Total executions for this test")
    success_rate: float = Field(..., description="Success rate as percentage")
    avg_response_time: Optional[float] = Field(None, description="Average response time in seconds")
    avg_cost: Optional[float] = Field(None, description="Average cost per execution")
    last_executed: Optional[datetime] = Field(None, description="Last execution timestamp")


class PerformanceTestReport(BaseModel):
    """Performance report for all tests"""
    model_config = ConfigDict(from_attributes=True)
    
    performance_metrics: List[TestPerformanceMetrics] = Field(..., description="Performance metrics for each test")
    generated_at: datetime = Field(..., description="When this report was generated")


class IndividualTestTrendsReport(BaseModel):
    """Execution trends for a specific test"""
    model_config = ConfigDict(from_attributes=True)
    
    test_id: UUID = Field(..., description="Test identifier")
    test_name: str = Field(..., description="Test name")
    trends: List[TestExecutionTrend] = Field(..., description="Daily execution trends for this test")
    period_days: int = Field(..., description="Number of days in the trend period")
    generated_at: datetime = Field(..., description="When this report was generated")


class IndividualTestPerformanceReport(BaseModel):
    """Performance report for a specific test"""
    model_config = ConfigDict(from_attributes=True)
    
    test_id: UUID = Field(..., description="Test identifier")
    test_name: str = Field(..., description="Test name")
    performance_metrics: TestPerformanceMetrics = Field(..., description="Performance metrics for this test")
    generated_at: datetime = Field(..., description="When this report was generated") 