from typing import Literal, List, Optional
from pydantic import BaseModel, UUID4, Field
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
    endpoint: str
    auth_type: str = Field(..., pattern="^(NONE|API_KEY|BEARER_TOKEN)$")
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
class MyTestCreate(BaseModel):
    name: str
    description: str
    prompt_template: str
    interface_type: str = Field(..., pattern="^(DIRECT_LLM|CHATBOT|PLUGIN_ENABLED|CUSTOM_APP)$")
    connection_config: ConnectionConfig
    validation_config: ValidationConfig
    tags: List[str] = []
    risk_level: str = Field(..., pattern="^(LOW|MEDIUM|HIGH)$")
    status: str = Field(..., pattern="^(DRAFT|ACTIVE|ARCHIVED)$")

class TestUpdate(MyTestCreate):
    pass

class TestSchema(MyTestCreate):
    id: UUID
    created_by: UUID
    created_at: str
    updated_at: str
    lastRun_at: Optional[str] = None
    latest_execution_id: Optional[UUID] = None

class TestList(BaseModel):
    items: List[TestSchema]
    total: int
    page: int
    limit: int