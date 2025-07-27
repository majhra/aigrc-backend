from typing import Literal, List, Optional, Dict, Any, Union
from pydantic import BaseModel, UUID4, Field, field_validator
from datetime import datetime
from uuid import UUID

# Prompt Category Models
class PromptCategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    category_type: Literal["COMPLIANCE", "SAFETY", "ACCURACY", "CUSTOM"] = "CUSTOM"
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    tags: List[str] = Field(default_factory=list)

class PromptCategoryCreate(PromptCategoryBase):
    pass

class PromptCategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, min_length=1, max_length=500)
    category_type: Literal["COMPLIANCE", "SAFETY", "ACCURACY", "CUSTOM"] | None = None
    priority: Literal["HIGH", "MEDIUM", "LOW"] | None = None
    tags: List[str] | None = None
    status: Literal["ACTIVE", "ARCHIVED"] | None = None

class PromptCategory(PromptCategoryBase):
    id: UUID4
    status: Literal["ACTIVE", "ARCHIVED"] = "ACTIVE"
    created_by: UUID4
    group_id: Optional[Union[str, UUID]] = None
    created_at: datetime
    updated_at: datetime
    prompt_count: int = 0  # Number of prompts in this category
    
    @field_validator('group_id', mode='before')
    @classmethod
    def convert_group_id_to_string(cls, v):
        if v is None:
            return None
        return str(v)

# Prompt Variable Definition
class PromptVariable(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")  # Valid variable name
    description: str
    type: Literal["text", "number", "boolean", "select"] = "text"
    required: bool = True
    default_value: str | None = None
    options: List[str] | None = None  # For select type
    validation_pattern: str | None = None  # Regex pattern for validation

# Prompt Models
class PromptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    content: str = Field(..., min_length=1)  # The actual prompt template
    category_id: UUID4
    variables: List[PromptVariable] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    compliance_frameworks: List[str] = Field(default_factory=list)  # e.g., ["GDPR", "SOX"]

class PromptCreate(PromptBase):
    pass

class PromptUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1, max_length=1000)
    content: str | None = Field(None, min_length=1)
    category_id: UUID4 | None = None
    variables: List[PromptVariable] | None = None
    tags: List[str] | None = None
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None
    compliance_frameworks: List[str] | None = None
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] | None = None

class Prompt(PromptBase):
    id: UUID4
    version: int = 1
    status: Literal["DRAFT", "ACTIVE", "ARCHIVED"] = "DRAFT"
    created_by: UUID4
    group_id: Optional[Union[str, UUID]] = None
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None
    usage_count: int = 0
    
    @field_validator('group_id', mode='before')
    @classmethod
    def convert_group_id_to_string(cls, v):
        if v is None:
            return None
        return str(v)

# Prompt Version History
class PromptVersion(BaseModel):
    id: UUID4
    prompt_id: UUID4
    version: int
    content: str
    variables: List[PromptVariable]
    change_notes: str | None = None
    created_by: UUID4
    created_at: datetime

# Prompt Set (Collection of Prompts)
class PromptSetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=1000)
    category_id: UUID4 | None = None
    tags: List[str] = Field(default_factory=list)

class PromptSetCreate(PromptSetBase):
    prompt_ids: List[UUID4] = Field(default_factory=list)

class PromptSetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, min_length=1, max_length=1000)
    category_id: UUID4 | None = None
    tags: List[str] | None = None
    prompt_ids: List[UUID4] | None = None
    status: Literal["ACTIVE", "ARCHIVED"] | None = None

class PromptSet(PromptSetBase):
    id: UUID4
    prompt_ids: List[UUID4]
    status: Literal["ACTIVE", "ARCHIVED"] = "ACTIVE"
    created_by: UUID4
    group_id: Optional[Union[str, UUID]] = None
    created_at: datetime
    updated_at: datetime
    
    @field_validator('group_id', mode='before')
    @classmethod
    def convert_group_id_to_string(cls, v):
        if v is None:
            return None
        return str(v)

# Response Models with Pagination
class PromptCategoryList(BaseModel):
    items: List[PromptCategory]
    total: int
    page: int
    limit: int

class PromptList(BaseModel):
    items: List[Prompt]
    total: int
    page: int
    limit: int

class PromptSetList(BaseModel):
    items: List[PromptSet]
    total: int
    page: int
    limit: int

# Prompt Validation and Preview
class PromptValidationRequest(BaseModel):
    content: str
    variables: List[PromptVariable]

class PromptValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    variable_placeholders: List[str] = Field(default_factory=list)  # Found {{variable}} patterns

class PromptPreviewRequest(BaseModel):
    content: str
    variable_values: Dict[str, Any]

class PromptPreviewResponse(BaseModel):
    rendered_content: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)