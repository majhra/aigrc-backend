from typing import Dict, List, Optional, Literal, Union
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

class ExecutionEnvironment(BaseModel):
    environment_id: Optional[str] = None
    version: Optional[str] = None
    parameters: Optional[Dict] = None

class TokenUsage(BaseModel):
    prompt: int
    completion: int
    total: int

class PerformanceMetrics(BaseModel):
    response_time: float  # milliseconds (can be fractional)
    total_time: float  # milliseconds (can be fractional)
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
    group_id: Optional[Union[str, UUID]] = None
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
    
    @field_validator('group_id', mode='before')
    @classmethod
    def convert_group_id_to_string(cls, v):
        if v is None:
            return None
        return str(v)

class ExecutedTestList(BaseModel):
    items: List[ExecutedTestSchema]
    total: int
    page: int
    limit: int
