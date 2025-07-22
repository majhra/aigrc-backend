from typing import Dict, List, Optional, Literal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ExecutionEnvironment(BaseModel):
    environment_id: Optional[str] = None
    version: Optional[str] = None
    parameters: Optional[Dict] = None

class TokenUsage(BaseModel):
    prompt: int
    completion: int
    total: int

class PerformanceMetrics(BaseModel):
    response_time: int  # milliseconds
    total_time: int  # milliseconds
    token_usage: TokenUsage
    cost: Optional[float] = None

class ValidationCriterionResult(BaseModel):
    criterion_id: str
    result: bool
    notes: Optional[str] = None
    confidence: Optional[float] = None

class ValidationEvent(BaseModel):
    validator_id: UUID
    validator_type: Literal["HUMAN", "AI", "RULE_BASED"]
    timestamp: datetime
    status: Literal["PASS", "FAIL"]
    #criteria_results: List[ValidationCriterionResult]
    notes: Optional[str] = None
    confidence: Optional[float] = None
    response: Optional[str] = None

class ErrorDetails(BaseModel):
    code: str
    message: str
    details: Optional[Dict] = None

class ExecutedTestCreate(BaseModel):
    input_variables: Optional[Dict[str, str]] = None
    execution_environment: Optional[ExecutionEnvironment] = None

class ExecutedTestSchema(BaseModel):
    id: UUID
    test_id: UUID
    executed_at: datetime
    executed_by: UUID
    execution_environment: Optional[ExecutionEnvironment] = None
    
    # Input/Output Data
    input_variables: Optional[Dict[str, str]] = None
    prompt: str
    response: str
    
    # Performance Metrics
    benchmarks: Optional[PerformanceMetrics] = None
    
    # Validation Information
    validation_status: Literal["PENDING", "IN_PROGRESS", "VALIDATED", "ERROR"] = "PENDING"
    validations: List[ValidationEvent] = []
    
    # Error Information
    error: Optional[ErrorDetails] = None

class ExecutedTestList(BaseModel):
    items: List[ExecutedTestSchema]
    total: int
    page: int
    limit: int
