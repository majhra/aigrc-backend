from typing import Literal, List, Optional, Union
from pydantic import BaseModel, UUID4, Field, field_validator
from datetime import datetime
from uuid import UUID

class TestCategory(BaseModel):
    id: UUID4
    name: str
    description: str
    category: Literal["SAFETY", "ACCURACY", "COMPLIANCE"]
    subcategory: str | None = None
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] = "ACTIVE"
    created_at: datetime
    updated_at: datetime
    tags: List[str] = []

class TestCategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: Literal["SAFETY", "ACCURACY", "COMPLIANCE"] | None = None
    subcategory: str | None = None
    priority: Literal["HIGH", "MEDIUM", "LOW"] | None = None
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] | None = None
    tags: List[str] | None = None

class TestParams(BaseModel):
    test: int | None = None
    industry: int | None = None
    params: float | None = None
    result: float | None = None

# Request/Response Models
class ConnectionConfig(BaseModel):
    endpoint: str | None = None
    auth_type: str = Field(..., pattern="^(NONE|API_KEY|BEARER_TOKEN)$")
    auth_string: Optional[str] = None  # API key or bearer token value
    timeout: Optional[int] = None

class ValidationCriterion(BaseModel):
    id: str
    name: str
    description: str
    type: str
    parameters: dict = {}

class ValidationConfig(BaseModel):
    validator_type: str = Field(..., pattern="^(HUMAN|AI|RULE_BASED|HYBRID)$")
    validation_criteria: List[ValidationCriterion]

class AITestCreate(BaseModel):
    name: str
    description: str | None = None
    prompt_template: str | None = None
    interface_type: str = Field(..., pattern="^(DIRECT_LLM|CHATBOT|PLUGIN_ENABLED|CUSTOM_APP)$")
    connection_config: ConnectionConfig
    validation_config: ValidationConfig
    tags: List[str] = []
    risk_level: str = Field(..., pattern="^(LOW|MEDIUM|HIGH)$")
    status: str = Field(..., pattern="^(DRAFT|ACTIVE|ARCHIVED)$")

class TestUpdate(AITestCreate):
    pass

class AITestSchema(AITestCreate):
    id: UUID
    created_by: UUID
    group_id: Optional[Union[str, UUID]] = None  # Owner of the test, optional for backward compatibility
    created_at: datetime
    updated_at: datetime
    lastRun_at: Optional[datetime] = None
    latest_execution_id: Optional[UUID] = None

    @field_validator('group_id', mode='before')
    @classmethod
    def convert_group_id_to_string(cls, v):
        if v is None:
            return None
        return str(v)

class TestList(BaseModel):
    """List of tests with pagination info"""
    items: List[AITestSchema]
    total: int
    page: int
    limit: int