from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import uuid


class PromptCategory(Base):
    __tablename__ = "prompt_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category_type = Column(String(20), nullable=False)  # COMPLIANCE, SAFETY, ACCURACY, CUSTOM
    priority = Column(String(10), nullable=False)  # HIGH, MEDIUM, LOW
    tags = Column(JSON)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, ARCHIVED
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    prompt_count = Column(Integer, default=0)

    # Relationships
    creator = relationship("User", back_populates="created_prompt_categories")
    prompts = relationship("Prompt", back_populates="category")


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    content = Column(Text, nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("prompt_categories.id"), index=True)
    variables = Column(JSON)  # Array of PromptVariable objects
    tags = Column(JSON)  # Array of strings
    risk_level = Column(String(10), nullable=False)  # LOW, MEDIUM, HIGH
    compliance_frameworks = Column(JSON)  # Array of strings
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="DRAFT")  # DRAFT, ACTIVE, ARCHIVED
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)

    # Relationships
    creator = relationship("User", back_populates="created_prompts")
    category = relationship("PromptCategory", back_populates="prompts")