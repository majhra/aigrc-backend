from typing import Optional
from fastapi import APIRouter, Depends, Query
from uuid import UUID

from app.api import deps
from app.modules.reports_store import ReportsStore
from app.schemas.reports import (
    SummaryTestReport,
    ExecutionTestTrendsReport,
    PerformanceTestReport,
    IndividualTestTrendsReport,
    IndividualTestPerformanceReport
)
from app.schemas import User

router = APIRouter()


@router.get("/summary", response_model=SummaryTestReport)
async def get_summary_report(
    current_user: User = Depends(deps.get_current_active_user),
    reports_store: ReportsStore = Depends(deps.get_reports_store),
) -> SummaryTestReport:
    """
    Get a summary report of tests and executions.
    """
    return reports_store.get_summary_report(current_user)


@router.get("/trends", response_model=ExecutionTestTrendsReport)
async def get_execution_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(deps.get_current_active_user),
    reports_store: ReportsStore = Depends(deps.get_reports_store),
) -> ExecutionTestTrendsReport:
    """
    Get execution trends over time.
    """
    return reports_store.get_execution_trends(current_user, days)


@router.get("/performance", response_model=PerformanceTestReport)
async def get_performance_report(
    current_user: User = Depends(deps.get_current_active_user),
    reports_store: ReportsStore = Depends(deps.get_reports_store),
) -> PerformanceTestReport:
    """
    Get performance metrics for tests.
    """
    return reports_store.get_performance_report(current_user)


@router.get("/trends/{test_id}", response_model=IndividualTestTrendsReport)
async def get_individual_test_trends(
    test_id: UUID,
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(deps.get_current_active_user),
    reports_store: ReportsStore = Depends(deps.get_reports_store),
) -> IndividualTestTrendsReport:
    """
    Get execution trends for a specific test over time.
    """
    return reports_store.get_individual_test_trends(test_id, current_user, days)


@router.get("/performance/{test_id}", response_model=IndividualTestPerformanceReport)
async def get_individual_test_performance(
    test_id: UUID,
    current_user: User = Depends(deps.get_current_active_user),
    reports_store: ReportsStore = Depends(deps.get_reports_store),
) -> IndividualTestPerformanceReport:
    """
    Get performance metrics for a specific test.
    """
    return reports_store.get_individual_test_performance(test_id, current_user) 