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
    authType: str = Field(..., pattern="^(NONE|API_KEY|BEARER_TOKEN)$")
    timeout: Optional[int] = None

class ValidationCriterion(BaseModel):
    id: str
    name: str
    description: str
    type: str
    parameters: dict = {}

class ValidationConfig(BaseModel):
    validatorType: str = Field(..., pattern="^(HUMAN|AI|RULE_BASED|HYBRID)$")
    validationCriteria: List[ValidationCriterion]
class TestCreate(BaseModel):
    name: str
    description: str
    promptTemplate: str
    interfaceType: str = Field(..., pattern="^(DIRECT_LLM|CHATBOT|PLUGIN_ENABLED|CUSTOM_APP)$")
    connectionConfig: ConnectionConfig
    validationConfig: ValidationConfig
    tags: List[str] = []
    riskLevel: str = Field(..., pattern="^(LOW|MEDIUM|HIGH)$")
    status: str = Field(..., pattern="^(DRAFT|ACTIVE|ARCHIVED)$")

class TestUpdate(TestCreate):
    pass

class Test(TestCreate):
    id: UUID
    createdBy: UUID
    createdAt: str
    updatedAt: str
    lastRunAt: Optional[str] = None
    latestExecutionId: Optional[UUID] = None

class TestList(BaseModel):
    items: List[Test]
    total: int
    page: int
    limit: int