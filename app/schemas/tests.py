from typing import Literal, List
from pydantic import BaseModel, UUID4
from datetime import datetime

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
    
